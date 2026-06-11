# pid_tuner_car Pin Map

禁用引脚先排除：PA2~PA6 为时钟引脚，PA19/PA20 为 SWD 调试接口；PA10/PA11 在本工程用于 UART0/CH340，因此不能再接 MPU6050/I2C1。

| 外设功能 | 芯片/模块型号 | 天猛星引脚 | IOMUX索引 | 片上复用功能 | 备注 |
|----------|--------------|-----------|-----------|-------------|------|
| 启停按键 | 轻触开关 | PA25 | PINCM55 | GPIO 上拉输入 | 按下接 GND，短按切换运行/停车 |
| 状态 LED | 板载 LED | PB22 | PINCM50 | GPIO 输出 | 亮=运行，灭=停车 |
| PID 调试 TX | CH340/USB 串口 | PA10 | PINCM21 | UART0_TX | 115200 8N1，MCU 发 CSV |
| PID 调试 RX | CH340/USB 串口 | PA11 | PINCM22 | UART0_RX | 115200 8N1，PC 发命令 |
| 右轮 PWM | TB6612FNG PWMA | PB15 | PINCM32 | TIMG8_C0 | A 通道=右轮 |
| 左轮 PWM | TB6612FNG PWMB | PB16 | PINCM33 | TIMG8_C1 | B 通道=左轮 |
| 右轮方向 1 | TB6612FNG AIN1 | PA13 | PINCM35 | GPIO | A 通道 H 桥 |
| 右轮方向 2 | TB6612FNG AIN2 | PA12 | PINCM34 | GPIO | A 通道 H 桥 |
| 左轮方向 1 | TB6612FNG BIN1 | PB0 | PINCM12 | GPIO | B 通道 H 桥 |
| 左轮方向 2 | TB6612FNG BIN2 | PB1 | PINCM13 | GPIO | B 通道 H 桥 |
| 右轮编码器 A 相 | MG310 霍尔编码器 | PA15 | PINCM37 | GPIO 双边沿中断 | 速度计数，脉冲/20ms |
| 左轮编码器 A 相 | MG310 霍尔编码器 | PA17 | PINCM39 | GPIO 双边沿中断 | 速度计数，脉冲/20ms |
