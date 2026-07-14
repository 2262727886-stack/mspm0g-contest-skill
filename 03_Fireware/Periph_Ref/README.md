# Periph_Ref — 外设参考驱动

逐个外设模块的独立参考实现，可直接复制驱动的 `.c/.h` 文件到你的工程使用。

| 目录 | 外设 | 通信接口 | 说明 |
|------|------|---------|------|
| `Encoder_Poll/` | 编码器 | GPIO 中断 | 轮询测速 + 4倍频 |
| `IR_Tracking/` | 红外循迹 | GPIO ADC | 灰度循迹传感器 |
| `Motor_TB6612/` | TB6612FNG | TIMG PWM | 电机驱动基础版 |
| `Motor_TB6612_Verified/` | TB6612FNG | TIMG PWM | 电机驱动验证版 |
| `MPU6050_Driver/` | MPU6050 | I2C1 | DMP 姿态解算 |
| `OLED_I2C/` | SSD1306 | I2C0 | 0.96" OLED 显示 |
| `PID_Speed/` | PID 速度环 | - | 增量式速度 PI |
| `Servo_SG90/` | SG90 舵机 | TIMA0 PWM | 50Hz PWM 控制 |

每个子目录是自包含的 CCS Theia 工程，包含 `empty.syscfg`（SysConfig 引脚配置）、驱动源码、板级初始化代码（`Board/`）。
