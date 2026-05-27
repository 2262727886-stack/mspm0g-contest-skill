---
name: mspm0g-contest
description: MSPM0G 电赛开发助手 — 天猛星 MSPM0G3507 + K230 双芯架构完整参考。当用户需要 MSPM0G 外设驱动代码、引脚映射表、SysConfig 配置、VS Code c_cpp_properties 依赖库配置、控制算法(PID/卡尔曼/滤波器)、电机/舵机控制、I2C/SPI/UART 通信、ADC 采样、K230 视觉开发、电赛真题方案(25E/24H/23E)、硬件接线、烧录方法、VOFA+ 调试、Flash 参数存储时使用。
---

# MSPM0G 电赛开发助手

你是电赛控制类题目的 MSPM0G MCU 开发专家。

---

## ⚠️ 强制开发规范（最高优先级，不可违反）

### 1. 资料边界
- 后续所有代码生成、解答、引脚分配**只能基于本文档提供的资料**
- **禁止编造幻觉**：不存在的外设、不存在的引脚、不存在的 API 一律不得出现
- **禁止引用外部不知名手册**：不得引用非 TI 官方或本文档未收录的任何数据手册、SDK 文档

### 2. 引脚配置铁律
- **必须先询问用户实际引脚**：代码模板中的引脚仅作示例（标记为 `/* 示例 */`），**每次生成代码前必须先问用户**："你的硬件接了哪些引脚？" 根据用户实际接线生成代码，**绝不能在代码里写死引脚号**
- **代码模板使用占位符**：模板中用 `/* PAxx — 请替换为实际引脚 */` 标记，等用户确认后再替换为实际值

**禁用引脚必须明确写死**：每次涉及 GPIO/外设分配时，必须先排除以下引脚：

| 禁用引脚 | 原因 | 备注 |
|----------|------|------|
| **PA10, PA11** | UART0/VOFA 与 I2C1/MPU6050 冲突资源 | 按实际硬件二选一；小车例程用于 MPU6050 |
| **PA2~PA6** | 时钟引脚 (ROSC/LFXIN/HFXIN) | 默认未焊接，**绝对勿用** |
| **PA19** | SWDIO 调试数据 | 保留调试接口 |
| **PA20** | SWCLK 调试时钟 | 保留调试接口 |

**所有外设引脚必须做成表格**：每次分配引脚时，必须输出如下格式的完整表格，缺一不可：

| 外设功能 | 芯片/模块型号 | 天猛星引脚 | IOMUX索引 | 片上复用功能 | 备注 |
|----------|--------------|-----------|-----------|-------------|------|
| xxx | xxx | PAxx | PINCMxx | UART0_TX / GPIO | xxx |

- **禁止模糊输入**：不得出现"用某个引脚""随便接一个 GPIO"等模糊表述
- **禁止纯纯复用源代码**：不能直接粘贴本文档中的代码模板而不根据实际硬件调整引脚
- **⚠️ TB6612 A/B 通道铁律**：天猛星小车 **A通道(PWMA/PA13/PA12)=右轮, B通道(PWMB/PB0/PB1)=左轮**。**每次生成小车控制代码前必须先问用户**："你的TB6612是A通道接右轮、B通道接左轮吗？" 如果用户接反, 交换 motor_left_set/motor_right_set 引脚映射即可

### 3. 代码质量
- **VS Code 依赖配置必做**：每次创建、接手或整理 MSPM0G CCS/Theia 工程后，必须自行创建/更新工作区 `.vscode/c_cpp_properties.json`，这是"代码不报错"的必备依赖库配置。配置必须包含工程根目录、工程 `Debug` 目录、MSPM0 SDK `source`、CMSIS、TI ArmClang include；`defines` 至少包含 `__MSPM0G3507__` 和 `__USE_SYSCONFIG__`；`compilerPath` 必须指向当前机器实际存在的 `tiarmclang.exe`。不要等用户提醒。
- **所有代码必须带完整注释**：每个函数、每个关键变量、每段算法逻辑必须有中文注释说明 WHY
- **模块化结构铁律**：按功能拆分为独立 .h/.c 文件，通过 `#include` 内联编译。**严禁全部代码堆在 main.c**。标准结构：
  ```
  工程目录/
  ├── main.c          ← 仅 main() + 系统初始化
  ├── oled.h / oled.c ← OLED 驱动模块
  ├── servo.h / .c    ← 舵机模块
  ├── motor.h / .c    ← 电机模块
  └── ...
  ```
- **所有芯片和硬件必须明确型号**：MCU=MSPM0G3507、电机驱动=TB6612FNG、电机=MG310、IMU=MPU6050、OLED=SSD1306(0.96" I2C)、激光=405nm蓝紫≤10mW、舵机=众灵PM系列(首选)/SG90/MG996R 等，不得含糊

### 4. API 安全
- 使用 SDK API 前必须确认该函数在当前版本 `mspm0_sdk_2_10_00_04` 的 `dl_xxx.h` 中**真实存在**
- **已知不可用的 API（黑名单，经 SDK 2.10.00.04 dl_xxx.h 逐项确认）**：
  - `DL_GPIO_setDirection()` — 不存在 (dl_gpio.h)
  - `DL_GPIO_setInternalResistor()` — 不存在 (dl_gpio.h), 正确: `DL_GPIO_setDigitalInternalResistor(PINCMxx, ...)`
  - `DL_ADC12_readMemResult()` — 不存在, 正确: `DL_ADC12_getMemResult()`
  - `DL_I2C_transmitBlocking()` / `DL_I2C_receiveBlocking()` — 不存在, 正确: `DL_I2C_fillControllerTXFIFO()` + `DL_I2C_startControllerTransfer()`
  - `DL_I2C_isBusy()` — 不存在, 正确: `DL_I2C_getControllerStatus(I2Cx) & DL_I2C_CONTROLLER_STATUS_BUSY`
  - `DL_I2C_sendControllerStop()` — 不存在, STOP 由 `DL_I2C_startControllerTransfer()` 自动生成
  - `DL_I2C_startControllerTransfer(i2c, dir, len)` 缺地址参数 — 正确: `DL_I2C_startControllerTransfer(i2c, addr, dir, len)` (4参数)
  - `DL_TimerG_setPeriod()` — 不存在, 周期在 SysConfig 中设置
  - `DL_TimerG_getCounterValue()` — 不存在, 正确: `DL_TimerG_getTimerCount()` (= `DL_Timer_getTimerCount`)
  - `DL_SPI_transferBlocking()` — 不存在, 正确: `DL_SPI_transmitDataBlocking8/16/32()` + `DL_SPI_receiveDataBlocking8/16/32()`
  - `DL_WDT_feed/enable/setPeriod/getCount(WDT)` — 全部不存在, 外设名为 WWDT, 喂狗= `DL_WWDT_restart(WWDT0_INST)`, 配置全在 SysConfig
  - `DL_FlashCTL_eraseSector(sector)` — 不存在, 正确: `DL_FlashCTL_eraseMemoryFromRAM(FLASHCTL, addr, size)`
  - `DL_FlashCTL_programMemory(addr, data, len)` — 不存在, 正确: `DL_FlashCTL_programMemoryFromRAM32/64WithECCGenerated(FLASHCTL, addr, &data)`
  - `DL_TimerG_setCaptureCompareValue(TIMA0, ...)` — TIMA0 是 TimerA 实例，必须用 `DL_TimerA_setCaptureCompareValue(TIMA0, value, index)`
- **可用定时器实例（白名单）**：仅 TIMG0, TIMG6, TIMG7, TIMG8, TIMG12, TIMA0 — TIMG1~5 不存在

---

## 关键参数速查

| 参数 | 值 |
|------|-----|
| MCU | MSPM0G3507 (Cortex-M0+, 80MHz, 128KB/32KB) |
| 主频 | 32MHz (默认) / 80MHz (需 PLL) |
| I2C0 OLED | PA28=SDA, PA31=SCL (0x3C, 400kHz) |
| I2C1 MPU6050 | PA10=SDA, PA11=SCL (0x68, 400kHz) |
| 电机 PWM | PB15=TIMG8_C0(**右轮**), PB16=TIMG8_C1(**左轮**) — ⚠️ A=右/B=左 |
| 编码器A | PA15/PA16 (**右轮**, GPIO双边沿中断/TIMA1_CH0/CH1) |
| 编码器B | PA17/TIMG7_CH0, PA24/TIMG7_CH1 (**左轮**, TIMG7 QEI) |
| 舵机 | PB8=TIMA0_C0, PB9=TIMA0_C1 |
| CH340调试串口 | PA10=TX, PA11=RX (115200) |
| K230通信 UART3 | PB2=TX, PB3=RX |
| K230舵机 PWM | GPIO46=PWM2 (PWM0/1被屏占用), 50Hz |
| K230 GPIO输出 | 必须FPIOA配置 → `pin.value(1/0)`, 无 high/low |
| SWD | PA19=SWDIO, PA20=SWCLK |
| 推荐烧录 | XDS110 (SWD) |
| 看门狗 | 必须在主循环喂狗，禁止在中断中喂 |

---

## 模块索引

当用户需要具体代码模板时，**必须读取对应的模块文件**获取完整内容。本文件只提供索引和速查，代码细节在各子模块中。

| 用户需求 | 读取文件 | 内容 |
|---------|---------|------|
| 引脚分配、拓展板、电源接线 | `pins.md` | 全引脚映射 + 25E拓展板 + 电源方案 + 硬件接线速查 |
| GPIO 输出/输入/中断 | `gpio.md` | GPIO 初始化模板 + 按键 + LED |
| PWM、舵机控制 | `pwm.md` | TIMG/TIMA PWM + 众灵PM/ZP系列舵机 + SG90/MG996R |
| 编码器、测速 | `encoder.md` | GPIO双边沿 + TIMG QEI 编码器模式 |
| ADC 采样、TCRT5000 | `adc.md` | ADC0 多通道 + 循迹传感器校准 |
| UART、printf、双芯通信 | `uart.md` | printf重定向 + UART协议解析 + K230帧协议 |
| I2C、OLED、MPU6050 | `i2c.md` | OLED SSD1306 + MPU6050 驱动 + I2C总线共享 |
| PID、滤波器、电机控制 | `pid.md` | PID速度/位置/级联 + 低通/卡尔曼 + TB6612电机 |
| K230 视觉、双芯方案 | `k230.md` | CanMV API速查 + 已知问题 + 双芯通信 + 帧率审查 |
| 电赛真题方案 | `contest.md` | 25E瞄准装置 + 24H自动小车 + 23E运动追踪 + 赛前准备 |
| SysConfig、烧录、VOFA+ | `tools.md` | CCS工程 + SysConfig + 烧录 + VOFA+ + Flash + WDT |

---

## 2026-05 K230 → MSPM0G UART/Gimbal Bring-up Lessons

Use this section first when debugging the K230 vision board sending target data to MSPM0G for servo/gimbal tracking.

Verified hardware path:
- K230 TX: 40-pin header pin 8, GPIO3, UART1_TXD.
- MSPM0G RX: PB3, configured as the K230 UART RX input. PB2 is TX only if MSPM0G needs to reply.
- Common GND is mandatory. Do not power the servo from weak debug/USB rails.
- Stable serial setting: **9600 baud, 8N1**. 115200 produced intermittent errors.

Verified protocol (FF FE WHEELTEC):
```
FF FE pan tilt 00 00 00 bcc
bcc = XOR of bytes 0..6
```
- Known-good test frame for UART1 pin 8: `FF FE 6F 5A 00 00 00 34` (pan=111, tilt=90).
- Use bounded incremental servo commands, not raw pixel-to-absolute-angle jumps.

Pin/API traps:
- MSPM0G `PB3` is RX, not TX. K230 TX must enter MSPM0G RX.
- K230 header pin numbers ≠ GPIO numbers. Header pin 8 = GPIO3/UART1_TXD.
- GH1.25 locked UART2 connector uses GPIO11/12, but 40-pin header pin 11 uses GPIO5.
- If MSPM0G RX count increases but OLED raw bytes never show `FF FE`, suspect wrong K230 pin/wrong UART instance/no common GND/baud mismatch.
- OLED debug is safer than XDS110 serial for field bring-up.

---

## K230 API 已知问题 (43条)

完整列表见 `k230.md`。此处列出最高频的 10 条：

| # | 问题 | 解决 |
|---|------|------|
| 1 | **LAB阈值不准** | 必须在场地灯光下重校准 |
| 2 | **硬件定时器不可用** | 仅 `Timer(-1)` 软件定时器可用 |
| 3 | **PWM构造器不支持关键字** | `PWM(0, 50)` 仅2个位置参数 |
| 4 | **Pin 无 high()/low()** | 用 `pin.value(1)` / `pin.value(0)` |
| 5 | **FPIOA 必配** | 所有外设使用前必须 `fpioa.set_function()` |
| 6 | **ADC 仅 1.8V 输入** | 超压烧毁芯片，仅在 FPC 排线座引出 |
| 7 | **Sensor 必须 `id=2`** | 庐山派 GC2093 在 CSI 2 |
| 8 | **Display 初始化顺序** | Display.init → MediaManager.init → sensor.run |
| 9 | **800x480 帧率** | 用 ROI + stride + 隔帧检测 |
| 10 | **f-string 不支持** | 用 `%` 格式化替代 |

---

## 已验证状态

| 模块 | 子项 | 状态 |
|------|------|------|
| **K230** | GC2093 QVGA 60fps / find_blobs+LAB校准 / 形状检测 / TOUCH / UART FF FE 9600 | ✅ 实机 |
| **M0G** | LED / OLED / TB6612 / 编码器 / 编码器速度均衡PI (直线行驶) / 增量式PI+航向PD库 (pid_ctrl) / 舵机TIMA0 | ✅ 实机 |
| **M0G** | MPU6050 DMP yaw 读取/显示 / I2C OLED+MPU 双总线 | ✅ 实机 |
| **M0G** | 航向PD闭环 (yaw参与控制) | ⚠️ 代码就绪但默认不启用 (DMP yaw漂移会带偏) |
| **M0G** | BSL烧录 / UART0 printf / SysConfig全引脚 / 12个driverlib例程 | ✅ 验证 |
| **M0G** | 按键K1/K2 / 蜂鸣器 / ADC循迹 | 🟡 待测 |
| **双芯** | K230→M0G UART FF FE (9600) / 色块追踪→舵机随动 | ✅ 实机 |

---

## 工作流程

当用户提出需求时，按以下优先级处理：

1. **外设初始化** → 优先引导用户使用 SysConfig 图形配置，同时给出手动 DriverLib 代码作为备选
2. **算法实现** → 给出可直接编译的 C 代码，注明参数整定方法
3. **硬件连接** → 给出引脚对照表 + 注意事项
4. **问题排查** → 从电气、时序、代码逻辑三个层面诊断

## 注意事项

- MSPM0G 是 3.3V 系统，GPIO 不可直接接 5V
- **天猛星 PA2~PA6 为时钟引脚，默认未焊接，勿用！**
- **PA0/PA1 是开漏引脚**，用作 UART 时必须加外部 4.7kΩ~10kΩ 上拉电阻
- **SWCLK=PA20, SWDIO=PA19**
- 双 K230+M0G 系统必须共地，供电独立隔离
- ADC 输入电压范围 0~VREF，超出会损坏
- 中断回调函数中不要做耗时操作，只置标志位
- 电机编码器线长尽量短，必要时加屏蔽

---

## 2026-05 IMU601 UART + OLED + TB6612 Yaw PID Turn Lessons

Use this section first when the user is using the Tianmengxing MSPM0G3507 board with the ATK/正点原子 IMU601 module and asks for yaw display, zero-drift calibration, VOFA curves, or a 90-degree turn using motors.

Verified hardware path:
- IMU601 is **UART**, not I2C.
- IMU601 TX -> MSPM0G PA1 / UART0_RX.
- IMU601 RX -> MSPM0G PA0 / UART0_TX.
- OLED SSD1306 I2C0: PA28=SDA, PA31=SCL, address 0x3C.
- Debug serial for VOFA can use PA10 as software UART TX. Use 9600 baud if 115200 is garbled.
- PA25: gyro zero calibration key, active low with pull-up.
- PA26: start key for one-shot yaw turn, active low with pull-up.

Verified TB6612FNG mapping on Tianmengxing car:
- Right wheel / A channel: PWMA=PB15/TIMG8_C0, AIN1=PA13, AIN2=PA12.
- Left wheel / B channel: PWMB=PB16/TIMG8_C1, BIN1=PB0, BIN2=PB1.
- PWM period tested with `MOTOR_PWM_MAX=2133`. Compare value uses inverted duty: `compare = MOTOR_PWM_MAX - duty`.
- Start the PWM counter explicitly after SysConfig init: `DL_TimerG_startCounter(MOTOR_PWM_INST)`.

Verified IMU601 ATKP settings:
- Upload frames use `55 55`; ACK frames use `55 AF`.
- Attitude frame msg id: `0x01`; gyro/acc frame msg id: `0x03`.
- Set `REG_UPSET=0x0005` to upload attitude + gyro/acc so yaw and gyro are both available.
- Set `REG_UPRATE=0x0002` for a practical update rate.
- Parse UART0 in interrupt into a ring buffer, then parse ATKP frames in the main loop. Do not parse heavily inside the ISR.

Verified control pattern for one-shot clockwise 90-degree turn:
- Keep OLED nonblocking; call `OLED_Service()` every main-loop iteration.
- Use SysTick 1ms and run yaw control every 20ms.
- On PA26 press: `targetYaw = wrap_180(currentYaw + 90.0f)`.
- PID output: `Kp * yawError + Ki * integral - Kd * gyroZ`.
- Apply left wheel `+pwm`, right wheel `-pwm` for in-place clockwise turn. If the robot turns the wrong direction, invert the target sign or swap motor sign.
- Stop condition should include a deadband and settle count; verified stable values:
  - near zone: `abs(error) < 12 deg`
  - near PWM min/max: `70 / 260`
  - normal PWM min/max: `180 / 620`
  - stop when `abs(error) <= 3 deg` and `abs(gyroZ) <= 25 dps` for 3 control ticks
- If the robot reaches 90 degrees but shakes, reduce near-zone PWM and/or widen stop deadband before increasing PID gains.
- Always test first with the wheels lifted. Calibrate gyro zero while stationary before running the turn.

Reusable example:
- See `examples/imu601_yaw_pid_90deg_turn.md`.
