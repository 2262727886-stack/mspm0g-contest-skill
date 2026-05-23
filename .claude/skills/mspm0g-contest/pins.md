# 引脚映射 + 硬件接线速查

## MCU 速查 — MSPM0G3507

### 核心参数
| 项目 | 参数 |
|------|------|
| 内核 | ARM Cortex-M0+ |
| 主频 | 最高 80MHz (PLL from 4~48MHz OSC) |
| Flash | 128KB |
| SRAM | 32KB |
| ADC | 2×12-bit, 最高 4MSPS, 最多 16 通道 |
| OPA | 2×零漂移运放 |
| 比较器 | 3×高速比较器 (COMP0/1/2) |
| 通用定时器 | 7×16-bit (TIMG0~TIMG6) |
| 高级定时器 | 1×16-bit (TIMA0, 支持互补 PWM / 死区) |
| UART | 以 SysConfig 实际可选实例为准；本文模板使用 UART0/1/2/3 时必须先在 SysConfig 中确认 |
| I2C | 2× (I2C0/1) |
| SPI | 2× (SPI0/1) |
| CAN | CAN-FD ×1 |
| 供电 | 1.62V ~ 3.6V |
| 封装 | LQFP48 / LQFP64 / VQFN32 |

### 天猛星引脚全映射 (源自官方引脚配置表)

**文档来源**: 天猛星官方 markDown1779010001946 | **封装**: LQFP64 | **电平**: 3.3V

#### PA 端口 (31个GPIO)

| 引脚 | 功能1 | 功能2 | 功能3 | 功能4 | 功能5 | 功能6 | Skill分配 |
|------|-------|-------|-------|-------|-------|-------|-----------|
| **PA0** | TIMG8_C1 | TIMA0_C0 | **UART0_TX** | I2C0_SDA | — | — | ⚠️ 开漏, BSL |
| **PA1** | TIMG8_C0 | TIMA0_C1 | **UART0_RX** | I2C0_SCL | — | — | ⚠️ 开漏, BSL |
| **PA2** | ROSC | TIMG8_C1 | TIMG7_C1 | SPI0_CS0 | SPI1_CS0 | — | 🚫 时钟ROSC |
| **PA7** | TIMA0_C1 | TIMG7_C1 | TIMA0_C2 | TIMG8_C0 | — | — | ✅ TB6612 AIN1 |
| **PA8** | TIMA0_C0 | SPI0_CS0 | UART1_TX | **TIMA1_C0** | — | — | ✅ 舵机1 Pan |
| **PA9** | TIMA0_C1 | SPI0_PICO | UART1_RX | **TIMA1_C1** | — | — | ✅ 舵机2 Tilt |
| **PA10** | I2C1_SDA | I2C0_SDA | SPI0_POCI | TIMG12_C0 | TIMA1_C0 | TIMA0_C2 | ✅ 激光MOS |
| **PA11** | I2C_SCL | I2C0_SCL | SPI0_SCK | TIMA1_C1 | UART0_RX | — | ✅ 蜂鸣器 |
| **PA12** | **TIMA0_C3** | TIMG0_C0 | CAN_TX | SPI0_SCK | — | — | ✅ 编码器/备用 |
| **PA13** | CAN_RX | TIMG0_C1 | SPI0_POCI | UART3_RX | — | — | ✅ 编码器/备用 |
| **PA14** | TIMG12_C0 | SPI0_POCI | UART3_TX | — | — | — | ✅ TB6612 AIN2 |
| **PA15** | DAC_OUT | I2C_SCL | SPI_CS2 | TIMA1_C0 | TIMA0_C2 | — | ✅ TB6612 BIN1 |
| **PA16** | TIMA1_C1 | SPI1_POCI | I2C1_SDA | — | — | — | ✅ EC11 A相 |
| **PA17** | UART1_TX | SPI1_SCK | I2C1_SCL | TIMA0_C3 | TIMG7_C0 | TIMA1_C0 | ✅ EC11 B相 |
| **PA18** | I2C1_SDA | UART1_RX | SPI1_PICO | TIMG7_C1 | TIMA1_C1 | **BSL** | ✅ TB6612 BIN2 |
| **PA19** | — | — | — | — | — | — | 🔒 **SWDIO** |
| **PA20** | — | — | — | — | — | — | 🔒 **SWCLK** |
| **PA21** | VREF- | UART2_TX | TIMA0_C0 | TIMG6_C0 | TIMG8_C0 | — | ⚠️ ADC负基准 |
| **PA22** | UART2_RX | TIMG8_C1 | TIMA_C1 | TIMG6_C1 | — | — | ✅ 备用 |
| **PA23** | VREF+ | UART2_TX | SPI0_CS3 | TIMA0_C3 | TIMG0_C0 | TIMG7_C0 | ⚠️ ADC正基准 |
| **PA24** | UART2_RX | SPI0_CS2 | TIMG0_C1 | TIMG7_C1 | TIMA1_C1 | — | ✅ TCRT5000 左1 |
| **PA25** | TIMA0_C3 | TIMG12_C1 | SPI1_CS3 | UART3_RX | — | — | ✅ TCRT5000 左2 |
| **PA26** | UART3_TX | SPI1_CS0 | CAN_TX | TIMG8_C0 | TIMG7_C0 | — | ✅ TCRT5000 中 |
| **PA27** | TIMG7_C1 | TIMG8_C1 | SPI1_CS1 | CAN_RX | — | — | ✅ TCRT5000 右2 |
| **PA28** | **I2C0_SDA** | TIMA1_C0 | TIMA0_C3 | TIMG7_C0 | UART0_TX | — | ✅ **I2C0 SDA** |
| **PA29** | I2C1_SCL | TIMG8_C0 | TIMG6_C0 | — | — | — | ✅ TCRT5000 右1 |
| **PA30** | TIMG8_C1 | TIMG6_C1 | I2C1_SDA | — | — | — | ✅ 备用 |
| **PA31** | **I2C0_SCL** | TIMG12_C1 | TIMG7_C1 | TIMA1_C1 | UART0_RX | — | ✅ **I2C0 SCL** |

#### PB 端口 (27个GPIO)

| 引脚 | 功能1 | 功能2 | 功能3 | 功能4 | 功能5 | Skill分配 |
|-------|-------|-------|-------|-------|-------|-----------|
| **PB0** | TIMA1_C0 | TIMA0_C2 | SPI1_CS2 | UART0_TX | — | ✅ TB6612 PWMA |
| **PB1** | TIMA1_C1 | SPI1_CS3 | UART0_RX | — | — | ✅ TB6612 PWMB |
| **PB2** | TIMA1_C0 | TIMA0_C3 | UART3_TX | TIMG6_C0 | I2C1_SCL | ✅ 编码器A |
| **PB3** | TIMA1_C1 | TIMG6_C1 | UART3_RX | I2C_SDA | — | ✅ 编码器B |
| **PB4** | UART1_TX | TIMA1_C0 | TIMA0_C2 | — | — | ✅ EC11按键 / SPI0_SCK |
| **PB5** | TIMA1_C1 | UART1_RX | — | — | — | ✅ SPI0_CS0 |
| **PB6** | TIMG6_C0 | TIMG8_C0 | UART1_RX | SPI_CS0 | SPI0_CS1 | ✅ SPI0_PICO |
| **PB7** | SPI1_POCI | SPI0_CS2 | TIMG8_C1 | TIMG6_C1 | UART1_RX | ✅ SPI0_POCI |
| **PB8** | TIMA0_C0 | SPI_PICO | — | — | — | ✅ 矩阵按键行0 |
| **PB9** | SPI_SCK | TIMA0_C1 | — | — | — | ✅ 矩阵按键行1 / 步进STEP |
| **PB10** | **TIMG0_C0** | TIMG8_C0 | TIMG6_C0 | — | — | ✅ 矩阵按键行2 |
| **PB11** | **TIMG0_C1** | TIMG8_C1 | TIMG6_C1 | — | — | ✅ 矩阵按键行3 |
| **PB12** | TIMA0_C1 | TIMA0_C2 | UART3_TX | — | — | ✅ 矩阵按键列0 |
| **PB13** | TIMG12_C0 | TIMA0_C3 | UART3_RX | — | — | ✅ 矩阵按键列1 |
| **PB14** | SPI1_CS3 | SPI1_POCI | SPI0_CS3 | TIMG12_C1 | TIMA0_C0 | ✅ 矩阵按键列2 |
| **PB15** | TIMG8_C0 | TIMG7_C0 | UART2_TX | SPI1_PICO | — | ✅ 矩阵按键列3 |
| **PB16** | TIMG7_C1 | TIMG8_C1 | UART2_RX | SPI1_SCK | — | ✅ 备用 |
| **PB17** | TIMA0_C2 | TIMA1_C0 | SPI0_PICO | UART2_TX | SPI1_CS1 | ✅ 备用 |
| **PB18** | TIMA1_C1 | SPI1_CS2 | SPI0_SCK | UART2_RX | — | ✅ 备用 |
| **PB19** | TIMG8_C1 | TIMG7_C1 | SPI0_POCI | — | — | ✅ 备用 |
| **PB20** | TIMA0_C1 | TIMG12_C0 | TIMA0_C2 | SPI1_CS0 | SPI0_CS2 | ✅ 备用 |
| **PB21** | TIMG8_C0 | SPI1_POCI | — | — | — | ✅ 备用 |
| **PB22** | SPI1_PICO | TIMG8_C1 | — | — | — | 💡 **板载LED** |
| **PB23** | SPI1_SCK | — | — | — | — | ✅ 备用 |
| **PB24** | TIMG12_C1 | TIMA0_C3 | SPI0_CS3 | SPI0_CS1 | — | ✅ 备用 |
| **PB25** | SPI0_CS0 | — | — | — | — | ✅ 备用 |
| **PB26** | TIMA1_C0 | TIMA0_C3 | TIMG6_C0 | SPI0_CS1 | — | ✅ 备用 |
| **PB27** | TIMG_C1 | TIMA1_C1 | SPI1_CS1 | — | — | ✅ 备用 |

**图例**: 🔒=固定占用 🚫=禁用 ⚠️=谨慎使用 💡=板载LED ✅=已分配

**关键说明**:
- **PA3~PA6 官方不列** — 确认未引出，不可用
- **CHIP/AGND** — 板载参考电压输出和模拟地
- **TIMA1 确实存在** — PB0~PB3, PA8~PA11, PA16~PA18 均有 TIMA1 功能
- **TIMG0 可用** — PB10(TIMG0_C0), PB11(TIMG0_C1)
- **PA18 带有 BSL 功能** — 可能是 BSL 按键


## 三、硬件清单与引脚总表

### MG310 电机参数

| 参数 | 值 |
|------|-----|
| 型号 | MG310 直流减速电机 |
| 额定电压 | **7.4V** (7~13V) |
| 空载转速 | 500±13% RPM |
| 空载电流 | ≤220mA |
| 额定转速 | 400±13% RPM |
| 额定扭矩 | 0.4 Kgf·cm |
| 堵转电流 | ≤2.0A (不可长时间堵转) |
| 减速比 | **1:20.409** |
| 编码器(霍尔) | 13 PPR → 输出轴 **265 脉冲/圈** |
| 编码器(GMR) | 500 PPR → 输出轴 **10204 脉冲/圈** |
| 车轮 | 48mm 橡胶轮胎, 周长 **15.08cm** |
| 厘米脉冲 | 265 / 15.08 ≈ **17.6 脉冲/cm** (霍尔版) |

### M0G 端硬件引脚总表

| 硬件模块 | 型号/规格 | 天猛星引脚 | 说明 |
|----------|----------|-----------|------|
| **TB6612 PWMA** | 电机驱动 | PB15 (TIMG8_C0) | **右电机** (A通道) PWM, 20kHz |
| **TB6612 PWMB** | | PB16 (TIMG8_C1) | **左电机** (B通道) PWM |
| **TB6612 AIN1** | | PA13 | **右电机** 方向1 |
| **TB6612 AIN2** | | PA12 | **右电机** 方向2 |
| **TB6612 BIN1** | | PB0 | **左电机** 方向1 |
| **TB6612 BIN2** | | PB1 | **左电机** 方向2 |
| **TB6612 STBY** | | 3.3V | 使能 |
| **TB6612 VM** | | 电池 7.4V | 电机电源 |
| **TB6612 VCC** | | 3.3V | 逻辑电源 |
| **MG310 编码器A-A** | 电机编码器 | PA15 (GPIO中断/TIMA1_CH0) | **右轮** A相 双边沿中断 |
| **MG310 编码器A-B** | | PA16 (GPIO中断/TIMA1_CH1) | **右轮** B相 |
| **MG310 编码器B-A** | 电机编码器 | PA17 (TIMG7_CH0) | **左轮** A相 TIMG7正交编码 |
| **MG310 编码器B-B** | | PA24 (TIMG7_CH1) | **左轮** B相 |
| **TCRT5000 ×8** | 红外循迹 | PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7 | 8路ADC |
| **MPU6050 SDA** | 六轴陀螺仪 | 待用户确认，禁止 PA10 | PA10 被 CH340 占用 |
| **MPU6050 SCL** | | 待用户确认，禁止 PA11 | PA11 被 CH340 占用 |
| **OLED SDA** | 0.96" SSD1306 | PA28 (I2C0_SDA) | I2C0总线 |
| **OLED SCL** | | PA31 (I2C0_SCL) | |
| **舵机1** | SG90/MG996R | PB9 (TIMA0_CH1) | 50Hz PWM |
| **舵机2** | SG90/MG996R | PB8 (TIMA0_CH0) | 50Hz PWM |
| **激光笔** | 蓝紫405nm | 待分配 | GPIO控制MOS |
| **蜂鸣器** | 有源蜂鸣器 | PB17 | GPIO |
| **LED 指示** | 红色LED | PB27 | GPIO |
| **按键 K1** | 轻触按键 | PA26 | 上拉 |
| **按键 K2** | 轻触按键 | PA25 | 上拉 |
| **蓝牙 RX** | HC-05/06 | PB6 (USART1_TX) | |
| **蓝牙 TX** | HC-05/06 | PB7 (USART1_RX) | |
| **K230 通信 TX** | → K230 | PB2 (USART3_TX) | 视觉数据 |
| **K230 通信 RX** | ← K230 | PB3 (USART3_RX) | |
| **CH340 串口** | 调试/USB | PA10(TX), PA11(RX) | 🔒 板载固定 |
| **SWD 调试** | XDS110 | PA19(SWDIO), PA20(SWCLK) | 🔒 调试接口 |

### K230 端硬件引脚总表

| 硬件模块 | 型号/规格 | 庐山派引脚 | 说明 |
|----------|----------|-----------|------|
| **摄像头 SCL** | OV5647/GC2093 | GPIO48 (I2C0_SCL) | 板载已有上拉 |
| **摄像头 SDA** | | GPIO49 (I2C0_SDA) | |
| **UART2 TXD** | → M0G | GPIO11 (FPIOA) | 视觉数据发送 |
| **UART2 RXD** | ← M0G | GPIO12 (FPIOA) | 可选ACK |
| **RGB灯 R** | 板载共阳 | GPIO62 | 低电平亮 |
| **RGB灯 G** | | GPIO20 | |
| **RGB灯 B** | | GPIO63 | |
| **用户按键** | 侧按 | GPIO53 | 下拉,按下=高 |

### 电源方案

| 供电对象 | 电压 | 来源 |
|----------|------|------|
| **M0G 天猛星** | 3.3V | 7.4V电池 → AMS1117-3.3 |
| **TB6612 电机** | 7.4V | 2S锂电池直供 |
| **MG310 编码器** | 3.3V/5V | 与M0G同电源 |
| **舵机** | 5~6V | 独立LDO或电池分压 |
| **K230 庐山派** | 5V (Type-C) | 独立电池/充电宝 |
| **激光笔** | 3.3V | M0G供电, MOS开关 |

### 25E 竞赛拓展板引脚分配 (用户实测)

以下引脚表为 25E 竞赛拓展板实际分配，**生成代码时必须使用此表而非默认推荐引脚**。

| 外设功能 | 芯片/模块 | 天猛星引脚 | 片上复用 | 备注 |
|----------|----------|-----------|----------|------|
| **OLED SCL** | SSD1306 | PA31 | I2C0_SCL | I2C0总线 |
| **OLED SDA** | SSD1306 | PA28 | I2C0_SDA | 地址 0x3C |
| **MPU6050 SCL** | MPU6050 | 待用户确认，禁止 PA11 | I2C1/软件I2C | PA11 被 CH340 占用 |
| **MPU6050 SDA** | MPU6050 | 待用户确认，禁止 PA10 | I2C1/软件I2C | PA10 被 CH340 占用 |
| **TB6612 PWMA** | TB6612FNG | PB15 | TIMG8_C0 | **右电机** (A通道) PWM |
| **TB6612 PWMB** | TB6612FNG | PB16 | TIMG8_C1 | **左电机** (B通道) PWM |
| **TB6612 AIN1** | TB6612FNG | PA13 | GPIO | **右电机** 方向1 |
| **TB6612 AIN2** | TB6612FNG | PA12 | GPIO | **右电机** 方向2 |
| **TB6612 BIN1** | TB6612FNG | PB0 | GPIO | **左电机** 方向1 |
| **TB6612 BIN2** | TB6612FNG | PB1 | GPIO | **左电机** 方向2 |
| **电机A 编码器 A相 (右轮)** | MG310 | PA15 | GPIO双边沿 / TIMA1_CH0 | TIMA1不支持QEI, 用GPIO中断 |
| **电机A 编码器 B相 (右轮)** | MG310 | PA16 | GPIO双边沿 / TIMA1_CH1 | 软件解码AB相 |
| **电机B 编码器 A相 (左轮)** | MG310 | PA17 | TIMG7_CH0 | TIMG7编码器模式 |
| **电机B 编码器 B相 (左轮)** | MG310 | PA24 | TIMG7_CH1 | |
| **舵机1** | SG90/MG996R | PB9 | TIMA0_CH1 | 50Hz PWM |
| **舵机2** | SG90/MG996R | PB8 | TIMA0_CH0 | 50Hz PWM |
| **超声波 TRIG** | HC-SR04 | PA8 | GPIO OUT | |
| **超声波 ECHO** | HC-SR04 | PA9 | GPIO IN | 输入捕获 |
| **蓝牙 RX** | HC-05/06 | PB6 | USART1_TX | ⚠️ 接收蓝牙数据 |
| **蓝牙 TX** | HC-05/06 | PB7 | USART1_RX | ⚠️ 发送给蓝牙 |
| **K230 通信 TX** | ← M0G | PB2 | USART3_TX | ✅ 已验证 |
| **K230 通信 RX** | → M0G | PB3 | USART3_RX | 接 K230 GPIO11(TXD)/12(RXD) |
| **TCRT5000 ×8** | 红外循迹 | PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7 | ADC | 8路ADC |
| **蜂鸣器** | 有源蜂鸣器 | PB17 | GPIO | |
| **LED** | 红色LED | PB27 | GPIO | |
| **按键 K1** | 轻触按键 | PA26 | GPIO IN | 上拉,按下=低 |
| **按键 K2** | 轻触按键 | PA25 | GPIO IN | |
| **CH340 串口** | 调试/USB | PA10(TX), PA11(RX) | UART0 | 🔒 板载固定 |

**信号冲突检查 (拓展板)：**

| 总线 | 设备 | 地址/通道 | 状态 |
|------|------|----------|------|
| I2C0 | OLED | 0x3C | ✅ 独占 |
| I2C1 | MPU6050 | 0x68 | ✅ 独占（与OLED分离） |
| TIMA0 | 舵机×2 (CH0,CH1) | PB8, PB9 | ✅ |
| GPIO中断 | 电机A编码器-右轮 (PA15/PA16) | 双边沿中断 / TIMA1_CH0/CH1 | ✅ 软件解码 |
| TIMG7 | 电机B编码器-左轮 (CH0,CH1) | PA17, PA24 | ✅ |
| TIMG8 | TB6612 PWMA/PWMB | PB15, PB16 | ✅ |
| UART0 | CH340 调试 | PA10, PA11 | 🔒 |
| UART1 | 蓝牙 HC-05/06 | PB6, PB7 | ✅ |
| UART3 | K230 通信 | PB2, PB3 | ✅ 已验证 |

**SysConfig 验证结果：**

| # | 问题 | 结果 | 方案 |
|---|------|------|------|
| **1** | TIMA1 编码器模式 | ❌ TIMA1 不支持 QEI | **用 GPIO 双边沿中断**读 PA15/PA16 编码器 |
| **2** | UART3 是否存在 | ✅ 可用 | PB2=TX, PB3=RX 接 K230 |
| **3** | PB6=USART1_TX | ✅ 可用 | 蓝牙 USART1 正常工作 |

---


## 十八、硬件连接速查

### 常用模块接线

**TB6612 电机驱动 (⚠️ A通道=右轮, B通道=左轮)：**
| TB6612 | MSPM0G | 说明 |
|--------|--------|------|
| PWMA | PB15 (TIMG8_C0) | **右轮** PWM, 20kHz |
| PWMB | PB16 (TIMG8_C1) | **左轮** PWM, 20kHz |
| AIN1 | PA13 | **右轮** 方向1 |
| AIN2 | PA12 | **右轮** 方向2 |
| BIN1 | PB0 | **左轮** 方向1 |
| BIN2 | PB1 | **左轮** 方向2 |
| STBY | 3.3V | 使能 |
| VM | 电池+ (7~12V) | 电机电源 |
| VCC | 3.3V | 逻辑电源 |

**MPU6050 (I2C 陀螺仪+加速度计)：**
| MPU6050 | MSPM0G |
|---------|--------|
| SDA | PA28 (I2C0_SDA) |
| SCL | PA31 (I2C0_SCL) |
| VCC | 3.3V |
| AD0 | GND (地址 0x68) |

**0.96" OLED SSD1306 (I2C)：**
| OLED | MSPM0G |
|------|--------|
| SDA | PA28 (I2C0_SDA) |
| SCL | PA31 (I2C0_SCL) |
| VCC | 3.3V |
| 地址 | 0x3C |

**HC-05 蓝牙模块 (UART)：**
| HC-05 | MSPM0G |
|-------|--------|
| TX | PA1 (UART0_RX) |
| RX | PA0 (UART0_TX) |
| VCC | 5V 或 3.3V |

**AMS1117-3.3 LDO 供电方案：**
```
电池 7.4V ──┬── AMS1117-3.3 ── MCU VDD
             └── TB6612 VM (电机供电)
地平面统一，模拟地与数字地单点接地
电机供电和 MCU 供电之间加 100uF + 0.1uF 去耦
```

### 电源设计注意事项
- ADC 参考电压使用内部 2.5V VREF，避免电源噪声
- 电机 PWM 频率 > 20kHz（超出人耳听觉范围）
- 电机驱动与 MCU 之间加光耦隔离（建议 6N137）或至少加 100Ω 限流电阻
- 每个 IC 的 VDD 引脚就近放置 0.1uF + 10uF 去耦电容
- 电池输入加 TVS 管防反接/浪涌

