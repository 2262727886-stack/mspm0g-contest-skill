# MSPM0G3507 CCS/Theia Car Example

Use this project as the current known-good MSPM0G3507 smart-car example:

```text
C:\Users\Administrator\workspace_ccstheia\test_2
```

## What It Covers

- CCS/Theia managed project with SysConfig.
- XDS110 flashing through `targetConfigs/MSPM0G3507.ccxml`.
- SSD1306 OLED on I2C0.
- MPU6050 on I2C1.
- TB6612FNG dual motor driver on TIMG8 PWM.
- Two wheel encoders using GPIO polling (4x quadrature decoding).
- **Cascaded position+speed PID**: inner speed loop + outer position loop.
- Gyro heading PD with soft-start ramp and offset sanity checks.
- PA26 start key (full calibration on start).
- PA25 calibration key (encoder zero + gyro recalibration).
- UART debug CSV output (100ms interval).
- UART runtime PID tuning commands.

## Verified Pin Map

| Function | Pin | Peripheral / Mode |
| --- | --- | --- |
| OLED SDA | PA28 | I2C0_SDA |
| OLED SCL | PA31 | I2C0_SCL |
| MPU6050 SDA | PA10 | I2C1_SDA |
| MPU6050 SCL | PA11 | I2C1_SCL |
| TB6612 PWMA (right) | PB15 | TIMG8_C0 |
| TB6612 PWMB (left) | PB16 | TIMG8_C1 |
| TB6612 AIN1 | PA13 | GPIO output |
| TB6612 AIN2 | PA12 | GPIO output |
| TB6612 BIN1 | PB0 | GPIO output |
| TB6612 BIN2 | PB1 | GPIO output |
| Encoder A phase A (right) | PA15 | GPIO input pull-up |
| Encoder A phase B (right) | PA16 | GPIO input pull-up |
| Encoder B phase A (left) | PA17 | GPIO input pull-up |
| Encoder B phase B (left) | PA24 | GPIO input pull-up |
| Gyro zero / CAL key | PA25 | GPIO input pull-up |
| Start key | PA26 | GPIO input pull-up |
| Board LED | PB22 | GPIO output |

**Wheel mapping**: B = left wheel, A = right wheel.

PA10/PA11 are a conflict pair: use them for either UART0/VOFA or I2C1/MPU6050,
not both. This example uses I2C1/MPU6050, so UART0 debug is disabled.

## Control Architecture (2025-05-22)

```
                    ┌──────────────────────────┐
Encoder A/B ────────→│  Position Accum (int32)  │
                     │  g_pos_a, g_pos_b        │
                     └──────────┬───────────────┘
                                │ pos_err = target - actual
                                ▼
                     ┌──────────────────────────┐
                     │  Position PI (outer)      │
                     │  POS_KP=0.3 POS_KI=0.01  │
                     │  Clamped: ±POS_CORR_MAX  │
                     └──────────┬───────────────┘
                                │ pos_corr
                                ▼
            ┌───────────────────────────────────┐
            │  Speed Target = BASE + pos_corr   │
            │                ± heading_corr     │
            │  Capped: 0 ~ MAX_SPEED_TARGET     │
            └───────────────┬───────────────────┘
                            │
                            ▼
            ┌──────────────────────────┐
            │  Speed PID (inner)       │
            │  Kp=20 Ki=0.10 Kd=0      │
            └──────────┬───────────────┘
                       │ pid_out
                       ▼
            ┌──────────────────────────┐
            │  PWM shaper + ramp       │
            │  FF_PER_COUNT=12         │
            │  STEP_PER_PID=20         │
            └──────────┬───────────────┘
                       │
                       ▼
            ┌──────────────────────────┐
            │  TB6612 (TIMG8 PWM)      │
            └──────────────────────────┘

Heading PD (outer, parallel):
  MPU6050 gz → yaw integration → PD → heading_corr
  Soft-start: ramps 0→100% over 1 second after start
  Offset sanity: rejects |offset| > 2 deg/s
  Min samples: requires ≥50/200 successful reads
```

### Anti-runaway protections

| Mechanism | Value | Effect |
|-----------|-------|--------|
| `POS_CORR_MAX` | ±6.0 | Position correction capped |
| `MOTOR_MAX_SPEED_TARGET` | 18.0 | Speed target hard limit (3× base) |
| `POS_ERR_MAX` | 30 | Target stops advancing if any wheel >30 counts behind |
| `HEADING_CORR_MAX` | ±5.0 | Heading correction capped |
| Heading soft-start | 50 cycles (1s) | Correction ramps 0→100% gradually |
| PWM ramp | 20/step | Each 20ms: PWM changes ≤20 units |

## Primary Tuning Macros

```c
// Speed base target (counts per 20ms)
// MG310: 265PPR × 4x = 1060 counts/rev, wheel=15.08cm → ~70.3 counts/cm
// 9 counts/20ms → 450 counts/s → ~6.4 cm/s
#define MOTOR_A_TARGET_COUNT      9.0f
#define MOTOR_B_TARGET_COUNT      9.0f

// PWM limits
#define MOTOR_PWM_MIN_START       50
#define MOTOR_PWM_MAX_OUTPUT      500
#define MOTOR_PWM_FF_PER_COUNT    12.0f
#define MOTOR_PWM_STEP_PER_PID    20

// Speed filter
#define MOTOR_SPEED_FILTER_ALPHA  0.65f

// Position PI
#define POS_KP                    0.3f
#define POS_KI                    0.01f
#define POS_MAX_INTEGRAL          10.0f
#define POS_ERR_MAX               30
#define POS_CORR_MAX              6.0f
#define MOTOR_MAX_SPEED_TARGET    18.0f

// Heading PD
#define HEADING_KP                1.5f
#define HEADING_KD                0.08f
#define HEADING_CORR_MAX          5.0f
```

## Control Flow

1. **Power-on**: MPU6050 init → 300ms stabilization → 1s gyro calibration
2. **PA26 start**: stop motors → reset encoders/positions → 1s gyro recalibration → enable
3. **PA25 calibrate**: stop motors → reset encoders/positions → 1s gyro recalibration → "CAL OK"
4. **Running**: every 20ms: read encoders → update positions → position PI → heading PD → speed PID → PWM

## UART Debug (100ms CSV)

```
a_tgt,b_tgt,a_spd,b_spd,a_pwm,b_pwm,a_err,b_err,pos_err_a,pos_err_b,head_corr_x10,en
```

Commands: `kp=`, `ki=`, `kd=`, `t=` (target), `stop`, `start`, `reset`

## Driver Notes

- `mpu6050.c` guarded by `#ifndef I2C_MPU_INST` for UART-debug builds.
- `motor.c` uses `DL_TimerG_setCaptureCompareValue(timer, value, ccIndex)`.
- `encoder.c` uses 1ms GPIO polling with 4x quadrature; position int32_t accumulators.
- `pid.c` is position-form PID with integral + output clamping.
- `mpu_zero_yaw()` blocks ~1s (200 samples × 5ms); sanity-checks offset < 2 deg/s.
- `mpu_reset_yaw()` is non-blocking (zeroes yaw only, no recalibration).
- Heading soft-start: `g_heading_confidence` counter, ramps 0→1 over 50 cycles.
