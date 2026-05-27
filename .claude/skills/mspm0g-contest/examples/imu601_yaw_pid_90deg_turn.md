# IMU601 Yaw PID 90-Degree Turn Example

This example records a verified Tianmengxing MSPM0G3507 car setup:

- ATK/正点原子 IMU601 over UART
- SSD1306 OLED over I2C
- TB6612FNG motor driver
- PA25 for gyro zero calibration
- PA26 for one-shot clockwise 90-degree turn
- PA10 software UART TX for VOFA/debug curves

## Pin Map

| Function | Device | Tianmengxing Pin | Peripheral | Note |
|---|---|---:|---|---|
| IMU601 RX from MCU | IMU601 | PA0 | UART0_TX | MCU TX -> IMU RX |
| IMU601 TX to MCU | IMU601 | PA1 | UART0_RX | IMU TX -> MCU RX |
| OLED SDA | SSD1306 | PA28 | I2C0_SDA | Address 0x3C |
| OLED SCL | SSD1306 | PA31 | I2C0_SCL | 400 kHz works |
| Debug TX | CH340/VOFA | PA10 | GPIO bit-bang UART TX | 9600 baud if 115200 is garbled |
| Gyro zero key | Key | PA25 | GPIO input pull-up | Active low |
| Turn start key | Key | PA26 | GPIO input pull-up | Active low |
| Right motor PWM | TB6612 PWMA | PB15 | TIMG8_C0 | A channel = right wheel |
| Left motor PWM | TB6612 PWMB | PB16 | TIMG8_C1 | B channel = left wheel |
| Right motor IN1 | TB6612 AIN1 | PA13 | GPIO output | Right wheel direction |
| Right motor IN2 | TB6612 AIN2 | PA12 | GPIO output | Right wheel direction |
| Left motor IN1 | TB6612 BIN1 | PB0 | GPIO output | Left wheel direction |
| Left motor IN2 | TB6612 BIN2 | PB1 | GPIO output | Left wheel direction |

## SysConfig Requirements

Add a PWM instance:

- Name: `MOTOR_PWM`
- Peripheral: `TIMG8`
- Timer count: `2133`
- Channel 0: `PB15 / TIMG8_C0`, right motor PWM
- Channel 1: `PB16 / TIMG8_C1`, left motor PWM
- Initial compare/duty: stopped

The generated project should expose:

```c
MOTOR_PWM_INST
DL_TIMER_CC_0_INDEX
DL_TIMER_CC_1_INDEX
```

Start the timer after `SYSCFG_DL_init()`:

```c
DL_TimerG_startCounter(MOTOR_PWM_INST);
```

## IMU601 Settings

IMU601 ATKP frames:

- Upload frame header: `55 55`
- ACK frame header: `55 AF`
- Attitude msg id: `0x01`
- Gyro/acc msg id: `0x03`

Set:

```c
REG_UPSET = 0x0005;  // attitude + gyro/acc
REG_UPRATE = 0x0002;
```

Use a UART RX interrupt only to move bytes into a ring buffer. Parse ATKP packets in the main loop.

## Control Constants

Verified stable starting values:

```c
#define MOTOR_PWM_MAX           (2133U)
#define TURN_CONTROL_PERIOD_MS  (20U)
#define TURN_TARGET_DEG         (90.0f)
#define TURN_KP                 (9.0f)
#define TURN_KI                 (0.06f)
#define TURN_KD                 (0.7f)
#define TURN_PWM_MIN            (180)
#define TURN_PWM_MAX            (620)
#define TURN_NEAR_ERR_DEG       (12.0f)
#define TURN_NEAR_PWM_MIN       (70)
#define TURN_NEAR_PWM_MAX       (260)
#define TURN_STOP_ERR_DEG       (3.0f)
#define TURN_STOP_GYRO_DPS      (25.0f)
#define TURN_SETTLE_TICKS       (3U)
#define TURN_INTEGRAL_LIMIT     (600.0f)
#define TURN_TIMEOUT_MS         (3000U)     /* ⚠️ 超时保护: 防卡死 */
```

## ⚠️ yaw 方向铁律

IMU601 yaw: **逆时针为正(+), 顺时针为负(-)**。

顺时针 90° 目标 = `currentYaw - 90`，不是 `+90`！

```c
/* ✅ 正确: 顺时针 */
targetYaw = wrap_angle_180(currentYaw - TURN_TARGET_DEG);

/* ❌ 错误: 这是逆时针 */
targetYaw = wrap_angle_180(currentYaw + TURN_TARGET_DEG);
```

## ⚠️ 误差公式

误差 = 当前 - 目标（不是 目标 - 当前）：

```c
/* ✅ 正确: err>0 表示还没到目标, 需要继续顺时针转 */
errorDeg = wrap_angle_180(currentYaw - targetYaw);

/* ❌ 错误: 符号反了 */
errorDeg = wrap_angle_180(targetYaw - currentYaw);
```

## Control Loop

Configure SysTick at 1 ms. In the SysTick ISR, increment a tick counter. The main loop checks `tickCounter % 20 == 0` and calls the turn controller every 20 ms.

On PA26 press:

```c
targetYaw = wrap_angle_180(currentYaw - TURN_TARGET_DEG); /* ⚠️ 顺时针减 */
integral = 0.0f;
turnStartMs = g_millis;  /* 超时保护计时 */
turnActive = true;
```

Every control tick:

```c
/* 超时保护: 防止电机卡死导致系统挂起 */
if (g_millis - turnStartMs >= TURN_TIMEOUT_MS) {
    turnActive = false; motor_stop(); return;
}

errorDeg = wrap_angle_180(currentYaw - targetYaw); /* ⚠️ 当前-目标 */
integral += errorDeg * 0.02f;
// clamp integral to prevent windup
if (integral >  TURN_INTEGRAL_LIMIT) integral =  TURN_INTEGRAL_LIMIT;
if (integral < -TURN_INTEGRAL_LIMIT) integral = -TURN_INTEGRAL_LIMIT;
output = TURN_KP * errorDeg + TURN_KI * integral + TURN_KD * gyroZ; /* ⚠️ +Kd: 顺时针gyroZ为负, 起阻尼作用 */
pwm = clamp_turn_pwm(output, errorDeg);
motor_left_set(pwm);
motor_right_set(-pwm);
```

Stop when:

```c
abs(errorDeg) <= TURN_STOP_ERR_DEG &&
abs(gyroZ) <= TURN_STOP_GYRO_DPS
```

for `TURN_SETTLE_TICKS` consecutive control ticks. Then:

```c
turnActive = false;
integral = 0.0f;
motor_stop();
```

## PWM and Direction Helpers

The verified project used inverted compare values:

```c
DL_TimerG_setCaptureCompareValue(
    MOTOR_PWM_INST,
    MOTOR_PWM_MAX - duty,
    DL_TIMER_CC_0_INDEX);
```

Positive turn output for clockwise:

```c
motor_left_set(pwm);
motor_right_set(-pwm);
```

If the car turns counterclockwise, use one of these fixes:

- Change `TURN_TARGET_DEG` to `-90.0f`
- Swap the signs in `motor_left_set()` / `motor_right_set()`
- Swap motor left/right mapping if the wiring is reversed

## OLED and VOFA Debug

OLED should be nonblocking:

```c
while (1) {
    OLED_Service();
    key_zero_service();
    key_turn_service();
    turn_control_service();
    imu_uart_parse_service();
    debug_uart_service();
}
```

During the turn, show:

- `T:` yaw error in degrees
- `P:` current PWM output

Useful VOFA CSV format:

```text
gx,gy,gz,yaw
```

If more tuning is needed:

```text
yaw,target,error,pwm
```

## Troubleshooting

Robot reaches 90 degrees but shakes:

- Lower `TURN_NEAR_PWM_MIN`
- Lower `TURN_NEAR_PWM_MAX`
- Increase `TURN_STOP_ERR_DEG`
- Clear the integral term when stopping

Robot cannot start turning:

- Raise `TURN_PWM_MIN`
- Check TB6612 standby/power wiring
- Check PWM timer is started

Robot turns the wrong direction:

- **⚠️ IMU601 yaw: 顺时针为负!** 目标用 `currentYaw - 90`，不是 `+90`
- Invert `TURN_TARGET_DEG`
- Swap left/right PWM signs
- Confirm A channel is right wheel and B channel is left wheel

Robot oscillates back and forth at target:

- **根因**: 最小 PWM 强制电机不停 → 冲过头 → 反向冲 → 循环
- Set `TURN_KI = 0` (纯 PD, 积分只添乱)
- Near-target minimum PWM must be ≥ far-zone minimum PWM (别设太低)
- Add timeout protection (`TURN_TIMEOUT_MS`) to prevent infinite loop

Robot gets stuck before reaching 90 degrees:

- **根因**: 近目标区最小 PWM 太低 → 低于电机摩擦力 → 卡死
- `TURN_NEAR_PWM_MIN` must be ≥ `TURN_PWM_MIN` (建议都设 120)
- Stop condition won't trigger if motor is stalled (error stuck > 3°)
- Timeout forces stop → back to IDLE

Yaw only changes while moving:

- That is normal for angle output. Use gyro `gz` to observe instantaneous angular velocity and yaw to control final heading.

OLED refresh slow:

- Keep OLED update nonblocking
- Do not redraw the full screen every loop
- Do not use blocking delays inside the control loop

Serial output garbled:

- PA10 software UART at 115200 can be unreliable because bit-bang timing is affected by interrupts
- Use 9600 baud for stable VOFA/debug output

Recommended test order:

1. Lift wheels off the ground.
2. Power the motor supply and MCU with common ground.
3. Press PA25 while stationary to calibrate gyro zero.
4. Press PA26 once.
5. Confirm yaw goes close to 90 degrees and motors stop.
6. Put the car on the ground and retune PWM limits if needed.
