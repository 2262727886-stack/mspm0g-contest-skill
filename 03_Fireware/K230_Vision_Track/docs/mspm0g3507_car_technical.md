# MSPM0G3507 Car Technical Notes

## Scope

This document records the current smart-car control example in
`C:\Users\Administrator\workspace_ccstheia\test_2`.

The project is intended as a reusable CCS/Theia example for:

- MSPM0G3507 SysConfig setup.
- OLED and I2C utility drivers.
- MPU6050 yaw-rate integration.
- TB6612FNG dual motor PWM.
- Dual encoder speed feedback.
- Dual wheel speed PID.
- Simple heading outer loop.
- XDS110 command-line flashing.

## Control Flow

Startup:

1. `SYSCFG_DL_init()`
2. OLED init and I2C0 scan
3. MPU6050 init on I2C1
4. Gyro Z zero calibration
5. Motor and encoder init
6. PID init
7. Wait for PA26 start key

Runtime loop:

1. Poll encoder pins every 1 ms.
2. Poll PA25 and PA26 keys.
3. Every 20 ms, latch encoder counts.
4. If enabled, update MPU yaw and heading correction.
5. Apply heading correction to A/B wheel targets.
6. Filter wheel speed.
7. Run A/B speed PID.
8. Shape and ramp PWM.
9. Write TB6612 A/B outputs.
10. Refresh OLED every 100 ms.

## Pin Map

| Function | Pin | SysConfig |
| --- | --- | --- |
| OLED SDA | PA28 | `I2C_OLED` / I2C0_SDA |
| OLED SCL | PA31 | `I2C_OLED` / I2C0_SCL |
| MPU6050 SDA | PA10 | `I2C_MPU` / I2C1_SDA |
| MPU6050 SCL | PA11 | `I2C_MPU` / I2C1_SCL |
| TB6612 PWMA | PB15 | `PWM_TB6612` / TIMG8_C0 |
| TB6612 PWMB | PB16 | `PWM_TB6612` / TIMG8_C1 |
| TB6612 AIN1 | PA13 | `GPIO_TB6612` |
| TB6612 AIN2 | PA12 | `GPIO_TB6612` |
| TB6612 BIN1 | PB0 | `GPIO_TB6612` |
| TB6612 BIN2 | PB1 | `GPIO_TB6612` |
| Encoder A phase A | PA15 | `GPIO_ENC_A` |
| Encoder A phase B | PA16 | `GPIO_ENC_A` |
| Encoder B phase A | PA17 | `GPIO_ENC_B` |
| Encoder B phase B | PA24 | `GPIO_ENC_B` |
| Stop / gyro zero key | PA25 | `GPIO_KEY` |
| Start key | PA26 | `GPIO_START` |
| LED | PB22 | `GPIO` |

## Main Parameters

Current tuning entry points in `empty.c`:

```c
#define MOTOR_A_TARGET_COUNT      10.0f
#define MOTOR_B_TARGET_COUNT      10.0f
#define MOTOR_PWM_MIN_START       120
#define MOTOR_PWM_MAX_OUTPUT      500
#define MOTOR_PWM_FF_PER_COUNT    10.0f
#define MOTOR_PWM_STEP_PER_PID    20
#define MOTOR_SPEED_FILTER_ALPHA  0.35f
#define HEADING_KP                0.12f
#define HEADING_KD                0.02f
#define HEADING_CORR_MAX          1.5f
```

For first battery tests:

1. Start with `MOTOR_A_TARGET_COUNT` and `MOTOR_B_TARGET_COUNT` low.
2. If acceleration is too sharp, lower `MOTOR_PWM_STEP_PER_PID`.
3. If top speed is still too high, lower `MOTOR_PWM_MAX_OUTPUT`.
4. If straight-line correction oscillates, lower `HEADING_KP` or
   `HEADING_CORR_MAX`.
5. If heading correction is sluggish, raise `HEADING_KP` slightly.

## Driver Contracts

`i2c_utils.[ch]`:

- Provides blocking write/read helpers.
- Uses DriverLib controller transfer APIs with explicit timeouts.

`oled.[ch]`:

- SSD1306 128x64 display.
- Page-based text output.

`mpu6050.[ch]`:

- Uses `I2C_MPU_INST` when present.
- Compiles to placeholder functions when `I2C_MPU_INST` is not configured.
- Supports address `0x68`, then tries `0x69`.

`motor.[ch]`:

- Uses TB6612 signed duty convention.
- Positive duty and negative duty map to opposite direction pins.
- `DL_TimerG_setCaptureCompareValue()` uses `(timer, value, ccIndex)`.

`encoder.[ch]`:

- Polling quadrature decoder.
- Exposes `Encoder_GetSpeedCountA()` and `Encoder_GetSpeedCountB()`.
- Keeps `Encoder_GetSpeedCount()` as a B-channel compatibility wrapper.

`pid.[ch]`:

- Stores `kp`, `ki`, `kd`, target, integral, error, and output.
- Limits integral and output.

## Build And Flash

Build from `Debug`:

```powershell
& 'C:\ti\ccs2020\ccs\utils\bin\gmake.exe' -k all
```

Flash:

```powershell
& 'C:\ti\uniflash_9.5.0\dslite.bat' --config='C:\Users\Administrator\workspace_ccstheia\test_2\targetConfigs\MSPM0G3507.ccxml' --flash --verbose 'C:\Users\Administrator\workspace_ccstheia\test_2\Debug\test_2.out'
```

## Known Tradeoffs

- PA10/PA11 cannot support UART0/VOFA and MPU6050 I2C1 at the same time.
- The current MPU build uses OLED as the primary runtime monitor.
- Encoder polling is simple but can miss edges at high speed.
- Gyro heading is integrated from `gz`; long runs will drift. Press PA25 to
  stop and re-zero yaw.
