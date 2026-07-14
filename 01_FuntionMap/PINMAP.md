# MSPM0G3507 Car Pin Map

This file is the verified wiring reference for this project.

| Function | Module | MSPM0G Pin | IOMUX / Peripheral | Notes |
|---|---|---|---|---|
| Right motor PWM | TB6612FNG PWMA | PB15 | TIMG8_C0 | Motor A is the right wheel |
| Right motor direction | TB6612FNG AIN1 | PA13 | GPIO / PINCM35 | Forward polarity is set in `motor_right_set()` |
| Right motor direction | TB6612FNG AIN2 | PA12 | GPIO / PINCM34 | Forward polarity is set in `motor_right_set()` |
| Left motor PWM | TB6612FNG PWMB | PB16 | TIMG8_C1 | Motor B is the left wheel |
| Left motor direction | TB6612FNG BIN1 | PB0 | GPIO / PINCM12 | Forward polarity is set in `motor_left_set()` |
| Left motor direction | TB6612FNG BIN2 | PB1 | GPIO / PINCM13 | Forward polarity is set in `motor_left_set()` |
| Encoder A phase A | Right encoder | PA15 | GPIO edge interrupt / PINCM37 | Enabled for speed counting |
| Encoder A phase B | Right encoder | PA16 | GPIO input / PINCM38 | Reserved for direction checks |
| Encoder B phase A | Left encoder | PA17 | GPIO edge interrupt / PINCM39 | Enabled for speed counting |
| Encoder B phase B | Left encoder | PA24 | GPIO input / PINCM54 | Reserved for direction checks |
| Camera UART TX | Camera | PB2 | UART3_TX | MSPM0 TX to camera RX |
| Camera UART RX | Camera | PB3 | UART3_RX | MSPM0 RX from camera TX |
| Servo PWM 0 | Servo | PB8 | TIMA0_CH0 | Not enabled in clean bring-up code yet |
| Servo PWM 1 | Servo | PB9 | TIMA0_CH1 | Not enabled in clean bring-up code yet |
| Ultrasonic trigger | Ultrasonic TRIG | PA8 | GPIO | Not enabled in clean bring-up code yet |
| Ultrasonic echo | Ultrasonic ECHO | PA9 | GPIO / capture candidate | Not enabled in clean bring-up code yet |
| MPU6050 SCL | MPU6050 | PA11 | I2C1_SCL / PINCM22 | 0x68 |
| MPU6050 SDA | MPU6050 | PA10 | I2C1_SDA / PINCM21 | 0x68 |
| Debug UART RX | CH340 TX | PA1 | UART0_RX | Not enabled in clean bring-up code yet |
| Debug UART TX | CH340 RX | PA0 | UART0_TX | PA0/PA1 may need pull-ups depending on board |
