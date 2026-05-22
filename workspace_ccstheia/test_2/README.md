# MSPM0G3507 Smart Car CCS Example

This CCS/Theia project is a working MSPM0G3507 car-control example. It brings up
OLED, MPU6050, TB6612 motor PWM, dual wheel encoders, dual speed PID, and a
simple gyro heading outer loop.

## Hardware

| Module | Signal | MSPM0G3507 Pin | SysConfig Name | Note |
| --- | --- | --- | --- | --- |
| SSD1306 OLED | SDA | PA28 | I2C0_SDA | Address 0x3C |
| SSD1306 OLED | SCL | PA31 | I2C0_SCL | 400 kHz |
| MPU6050 | SDA | PA10 | I2C1_SDA | Expansion-board gyro |
| MPU6050 | SCL | PA11 | I2C1_SCL | Expansion-board gyro |
| TB6612FNG | PWMA | PB15 | TIMG8_C0 | Motor A PWM |
| TB6612FNG | PWMB | PB16 | TIMG8_C1 | Motor B PWM |
| TB6612FNG | AIN1 | PA13 | GPIO | Motor A direction |
| TB6612FNG | AIN2 | PA12 | GPIO | Motor A direction |
| TB6612FNG | BIN1 | PB0 | GPIO | Motor B direction |
| TB6612FNG | BIN2 | PB1 | GPIO | Motor B direction |
| Encoder A | A phase | PA15 | GPIO input pull-up | A_A phase |
| Encoder A | B phase | PA16 | GPIO input pull-up | A_B phase |
| Encoder B | A phase | PA17 | GPIO input pull-up | B_A phase |
| Encoder B | B phase | PA24 | GPIO input pull-up | B_B phase |
| Key | Gyro zero / stop | PA25 | GPIO input pull-up | Active low |
| Key | Start | PA26 | GPIO input pull-up | Active low |
| Board LED | LED | PB22 | GPIO | Heartbeat |

Keep PA19/PA20 for SWD. Avoid PA2-PA6 because they are clock-related pins.

PA10/PA11 are used by MPU6050 I2C1 in this car example. They cannot also be used
for UART0/VOFA at the same time. To debug PID through VOFA, temporarily remove
`I2C_MPU` from SysConfig and restore UART0 on PA10/PA11.

## Source Layout

| File | Purpose |
| --- | --- |
| `empty.c` | Main control loop, keys, speed PID, gyro heading loop, OLED status |
| `empty.syscfg` | MSPM0G3507 pin and peripheral configuration |
| `i2c_utils.[ch]` | Blocking I2C register read/write helpers |
| `oled.[ch]` | SSD1306 128x64 OLED driver |
| `mpu6050.[ch]` | MPU6050 init and scaled raw data reader |
| `motor.[ch]` | TB6612FNG direction and TIMG8 PWM output |
| `encoder.[ch]` | A/B wheel quadrature polling decoder |
| `pid.[ch]` | Small PID controller with integral/output limits |

## Runtime Behavior

1. Power on: motors are disabled.
2. OLED scans I2C0, initializes MPU6050 on I2C1, and shows status.
3. Press PA26 to start the car.
4. Press PA25 to stop the car and recalibrate gyro yaw zero.
5. The speed loop runs every 20 ms.
6. The heading loop integrates MPU6050 `gz` into yaw and adjusts left/right
   wheel target speeds to hold the startup heading.

Important tuning macros live near the top of `empty.c`:

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

For battery testing, reduce `MOTOR_A_TARGET_COUNT` and `MOTOR_B_TARGET_COUNT`
first. Then reduce `MOTOR_PWM_MAX_OUTPUT` or `MOTOR_PWM_STEP_PER_PID` if the car
still accelerates too aggressively.

## Build

From the project `Debug` directory:

```powershell
& 'C:\ti\ccs2020\ccs\utils\bin\gmake.exe' -k all
```

The generated firmware is:

```text
C:\Users\Administrator\workspace_ccstheia\test_2\Debug\test_2.out
```

## Flash With XDS110

```powershell
& 'C:\ti\uniflash_9.5.0\dslite.bat' --config='C:\Users\Administrator\workspace_ccstheia\test_2\targetConfigs\MSPM0G3507.ccxml' --flash --verbose 'C:\Users\Administrator\workspace_ccstheia\test_2\Debug\test_2.out'
```

## Notes

- `DL_TimerG_setCaptureCompareValue()` was verified in SDK
  `mspm0_sdk_2_10_00_04` as `(timer, value, ccIndex)`.
- The current encoder implementation uses 1 ms GPIO polling. It is simple and
  works for bring-up. If the wheel speed becomes high enough to miss edges,
  move the encoder readers to timer capture/QEI-style hardware support.
- OLED is the primary runtime monitor in this MPU build because PA10/PA11 are
  occupied by I2C1 instead of UART0.

## K230 -> MSPM0G Gimbal UART Bring-up (Verified 2026-05-23)

This project now keeps the K230/MSPM0G UART lessons from the gimbal tracking
bring-up. The stable jumper-wire setup is:

| Signal | Connection |
| --- | --- |
| K230 TX | 40-pin header pin 8, GPIO3, UART1_TXD |
| MSPM0G RX | PB3, UART3_RX |
| Ground | K230 GND to MSPM0G GND |
| Baud | 9600 8N1 |
| Frame | `FF FE pan tilt 00 00 00 BCC` |
| BCC | XOR of bytes 0..6 |

Do not confuse K230 GPIO numbers with 40-pin header numbers. Header pin 8 is
GPIO3. Header pin 11 is GPIO5. The GH1.25 connector marked `2` uses GPIO11/12,
but it requires the locked cable and was not used in this jumper-wire setup.

### Debug sequence

1. Flash the MSPM0G `servo_test` OLED debug firmware.
2. Run `k230_uart_all_test.py` on K230 before running vision tracking.
3. Move the K230 TX jumper among candidate header pins if needed.
4. Confirm OLED `HEAD` and `FRAME` continuously increase and OLED `RAW` shows
   repeating `FF FE ...`.
5. Only then run `k230_wheeltec_track.py`.

`k230_uart_all_test.py` sends unique pan values so OLED `P:` identifies the
physical TX line:

| K230 UART | 40-pin header | GPIO | Expected OLED `P:` |
| --- | --- | --- | --- |
| UART1 TX | pin 8 | GPIO3 | 111 |
| UART2 TX | pin 11 | GPIO5 | 122 |
| UART3 TX | pin 37 | GPIO32 | 133 |
| UART4 TX | pin 29 | GPIO36 | 144 |

### Mistakes found during bring-up

- PB3 was mistakenly suspected as TX; in this SysConfig it is RX. PB2 is TX.
- 115200 baud produced intermittent headers and BCC errors with the jumper-wire
  setup. 9600 is the current verified baud.
- Vision tracking was debugged too early. Fixed UART frames must be stable before
  tuning LAB thresholds or servo gains.
- One-byte `pan` values must stay <=255. The current tracker clamps to a smaller
  safe gimbal range.
- Direct pixel-to-absolute-servo mapping can cause hard 180-degree jumps. The
  tracker now uses incremental steps, a deadband, and limited angle range.
