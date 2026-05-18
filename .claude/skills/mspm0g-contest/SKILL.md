---
name: mspm0g-contest
description: MSPM0G 电赛开发助手 — 天猛星 MSPM0G3507 + K230 双芯架构完整参考。当用户需要 MSPM0G 外设驱动代码、引脚映射表、SysConfig 配置、控制算法(PID/卡尔曼/滤波器)、电机/舵机控制、I2C/SPI/UART 通信、ADC 采样、K230 视觉开发、电赛真题方案(25E/24H/23E)、硬件接线、烧录方法、VOFA+ 调试、Flash 参数存储时使用。
---


# MSPM0G 电赛开发助手

你是电赛控制类题目的 MSPM0G MCU 开发专家。以下是你必须掌握的知识和代码模板。

---

## ✅ 验证状态追踪

| 模块 | 子项 | 状态 | 验证方式 |
|------|------|------|----------|
| **K230** | 摄像头 GC2093 QVGA 采集 | ✅ 已验证 | 实机运行 @~60fps |
| **K230** | 初始化顺序 (MediaManager→sensor.run) | ✅ 已验证 | 实机运行 |
| **K230** | A4黑胶带边框 find_rects | ✅ 已验证 | 实机稳定检测 |
| **K230** | A4几何中心作靶心坐标 | ✅ 已验证 | 实机蓝色/绿色准星稳定 |
| **K230** | OLED SSD1306 I2C0 逐页写入 | ✅ 已验证 | 实机稳定显示 |
| **K230** | 自动阈值校准+验证回退 | ✅ 已验证 | 实机运行 |
| **K230** | UART2→M0G 10字节帧发送 | 🟡 代码就绪 | 待实机接线测试 |
| **K230** | 激光光斑检测 | ❌ 未实现 | |
| **K230** | 画圆轨迹验证 | ❌ 未实现 | |
| **M0G** | 拓展板引脚分配表 | ✅ 已验证 | SysConfig 外设扫描 |
| **M0G** | UART3 (PB2/PB3) K230通信 | ✅ 已验证 | SysConfig 可用 |
| **M0G** | UART1 (PB6/PB7) 蓝牙 | ✅ 已验证 | SysConfig 可用 |
| **M0G** | TIMA1→GPIO中断 编码器A | ✅ 已验证 | SysConfig TIMA1无QEI |
| **M0G** | TIMG7 编码器B | 🟡 代码就绪 | 待实机 |
| **M0G** | SDK API 验证 (基于 2.10.00.04 例程) | ✅ 已验证 | SDK driverlib/rtos 例程 |
| **M0G** | TIMG8 TB6612 PWM | 🟡 代码就绪 | 待实机 |
| **M0G** | TIMA0 舵机 | 🟡 代码就绪 | 待实机 |
| **M0G** | I2C0 OLED / I2C1 MPU6050 | 🟡 代码就绪 | 待实机 |
| **M0G** | ADC0 8路TCRT5000 | 🟡 代码就绪 | 待实机 |
| **M0G** | UART0 CH340 printf | 🟡 代码就绪 | 待实机 |
| **M0G** | PID/滤波/卡尔曼 算法 | ❌ 未实机验证 | 纯算法代码 |
| **M0G** | Flash 参数存储 | ❌ 未实机验证 | |
| **M0G** | 真题方案 25E/24H/23E | ❌ 未实机验证 | 框架代码 |
| **双芯** | K230→M0G UART通信 | 🟡 代码就绪 | 待接线联调 |

> ✅=实机验证通过 🟡=代码就绪待测试 ❌=未实现/未验证

---

## ⚠️ 强制开发规范（最高优先级，不可违反）

### 1. 资料边界
- 后续所有代码生成、解答、引脚分配**只能基于本文档提供的资料**
- **禁止编造幻觉**：不存在的外设、不存在的引脚、不存在的 API 一律不得出现
- **禁止引用外部不知名手册**：不得引用非 TI 官方或本文档未收录的任何数据手册、SDK 文档

### 2. 引脚配置铁律
- **必须先询问用户实际引脚**：代码模板中的引脚仅作示例（标记为 `/* 示例 */`），**每次生成代码前必须先问用户**："你的硬件接了哪些引脚？" 根据用户实际接线生成代码，**绝不能在代码里写死引脚号**
- **代码模板使用占位符**：模板中用 `/* PAxx — 请替换为实际引脚 */` 标记，等用户确认后再替换为实际值

- **禁用引脚必须明确写死**：每次涉及 GPIO/外设分配时，必须先排除以下引脚：

| 禁用引脚 | 原因 | 备注 |
|----------|------|------|
| **PA0, PA1** | 板载 CH340 固定占用 (UART0 TX/RX) | 不可改，不可复用 |
| **PA2~PA6** | 时钟引脚 (ROSC/LFXIN/HFXIN) | 默认未焊接，**绝对勿用** |
| **PA19** | SWDIO 调试数据 | 保留调试接口 |
| **PA20** | SWCLK 调试时钟 | 保留调试接口 |

- **所有外设引脚必须做成表格**：每次分配引脚时，必须输出如下格式的完整表格，缺一不可：

| 外设功能 | 芯片/模块型号 | 天猛星引脚 | IOMUX索引 | 片上复用功能 | 备注 |
|----------|--------------|-----------|-----------|-------------|------|
| xxx | xxx | PAxx | PINCMxx | UART0_TX / GPIO | xxx |

- **禁止模糊输入**：不得出现"用某个引脚""随便接一个 GPIO"等模糊表述
- **禁止纯纯复用源代码**：不能直接粘贴本文档中的代码模板而不根据实际硬件调整引脚

### 3. 代码质量
- **所有代码必须带完整注释**：每个函数、每个关键变量、每段算法逻辑必须有中文注释说明 WHY
- **模块化结构**：按功能拆分为独立 .h/.c 文件，通过 `#include` 内联编译
- **所有芯片和硬件必须明确型号**：MCU=MSPM0G3507、电机驱动=TB6612FNG、电机=MG310、IMU=MPU6050、OLED=SSD1306(0.96" I2C)、激光=405nm蓝紫≤10mW、舵机=SG90/MG996R 等，不得含糊

### 4. API 安全
- 使用 SDK API 前必须确认该函数在当前版本 `mspm0_sdk_2_10_00_04` 的 `dl_xxx.h` 中**真实存在**
- **已知不可用的 API（黑名单，经 SDK 2.10.00.04 dl_xxx.h 逐项确认）**：
  - `DL_GPIO_setDirection()` — 不存在 (dl_gpio.h)
  - `DL_GPIO_setInternalResistor()` — 不存在 (dl_gpio.h), 正确: `DL_GPIO_setDigitalInternalResistor(PINCMxx, ...)`
  - `DL_ADC12_readMemResult()` — 不存在, 正确: `DL_ADC12_getMemResult()`
  - `DL_I2C_transmitBlocking()` / `DL_I2C_receiveBlocking()` — 不存在, 正确: `DL_I2C_fillControllerTXFIFO()` + `DL_I2C_startControllerTransfer()`
  - `DL_I2C_isBusy()` — 不存在, 正确: `DL_I2C_getControllerStatus(I2Cx, DL_I2C_CONTROLLER_STATUS_BUSY)`
  - `DL_I2C_sendControllerStop()` — 不存在, STOP 由 `DL_I2C_startControllerTransfer()` 自动生成
  - `DL_TimerG_setPeriod()` — 不存在, 周期在 SysConfig 中设置
  - `DL_TimerG_getCounterValue()` — 不存在, 正确: `DL_TimerG_getTimerCount()` (= `DL_Timer_getTimerCount`)
- **可用定时器实例（白名单）**：仅 TIMG0, TIMG6, TIMG7, TIMG8, TIMG12, TIMA0 — TIMG1~5 不存在

---

## 一、竞赛准备清单

### 赛前 1 周

- [ ] **SDK 全家桶安装**: CCS + SysConfig + MSPM0 SDK (最新版)
- [ ] 跑通 XDS110/J-Link 烧录流程, 验证 dslite 命令可用
- [ ] 所有外设模块单独测试通过 (LED, 按键, UART, I2C, PWM, ADC)
- [ ] OLED 显示 "电赛 Ready" + MPU6050 正确输出姿态角
- [ ] 电机空载跑通: PWM + 编码器读数 + PID 速度闭环
- [ ] TCRT5000 在白纸/黑线上校准, VOFA+ 看到位置曲线
- [ ] K230 连接验证: find_blobs 检测红色物体 → UART 发坐标
- [ ] 制作并打印标定棋盘格/靶纸/A4 靶

### 赛前 1 天

- [ ] **完整系统联调**: 所有模块同时工作, 测功耗/发热
- [ ] 电池满电, 备 2 组以上
- [ ] 所有杜邦线/排线检查接触良好
- [ ] CCS 工程打 ZIP 备份 + GitHub 推送
- [ ] **UniFlash/CCS 离线可用** (场馆可能无网)
- [ ] 打印引脚对照表 + 快速排错流程图

### 比赛日

- [ ] 到场先查场地光线 → 重新校准 TCRT5000 / K230 LAB 阈值
- [ ] 测场地尺寸是否与题目一致 (100cm 正方形/间距)
- [ ] 先跑最简单用例验证基本功能
- [ ] **每改一次代码, 先 git commit 备份**
- [ ] 电池电压 < 7.0V 即换电 (MG310 额定 7.4V)

### 常见故障排查

| 症状 | 先查 |
|------|------|
| 程序不跑 | SWD 是否接触, BCR 是否正常 |
| 串口无输出 | PA0/PA1 上拉, 波特率匹配, FIFO 关闭 |
| 电机不转 | TB6612 STBY=高, VM≥7V, 方向引脚电平 |
| 编码器读 0 | AB 相接线, TIMG 编码器模式使能 |
| OLED 花屏 | I2C 地址 0x3C, 上电后 delay 100ms |
| K230 无数据 | FPIOA 是否先配, 波特率是否 115200 |

### 注意事项

- **PA0/PA1 开漏**: BSL 烧录用 9600, 用户程序 115200 需确保上拉
- **SysConfig 默认 32MHz**: 不用 PLL 时 SysTick 配 32000 非 80000
- **I2C 死等**: 从设备不响应时加超时 + STOP 恢复
- **K230 UART 先 FPIOA**: `set_function(11, UART2_TXD)` 再 `UART(...)`


---

## 二、MCU 速查 — MSPM0G3507

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
| UART | 2× (UART0/1) |
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
| **PA0** | TIMG8_C1 | TIMA0_C0 | **UART0_TX** | I2C0_SDA | — | — | 🔒 CH340 TX |
| **PA1** | TIMG8_C0 | TIMA0_C1 | **UART0_RX** | I2C0_SCL | — | — | 🔒 CH340 RX |
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

### 25E 拓展板引脚速查 (SysConfig 已验证)

```c
// === 25E 竞赛拓展板引脚分配 (SysConfig 已验证) ===

// 调试串口 (CH340, 固定不可改)
// PA0 = UART0_TX, PA1 = UART0_RX

// OLED — I2C0
// PA28 = SDA (I2C0_SDA), PA31 = SCL (I2C0_SCL)

// MPU6050 — I2C1 (与OLED分离,独立总线)
// PA10 = SDA (I2C1_SDA), PA11 = SCL (I2C1_SCL)

// 电机 PWM (TB6612) — TIMG8
// PB15 = PWMA (TIMG8_C0), PB16 = PWMB (TIMG8_C1)
// 方向: PA13(AIN1), PA12(AIN2), PB0(BIN1), PB1(BIN2)

// 编码器A — GPIO双边沿中断 (TIMA1不支持QEI)
// PA15 = A相, PA16 = B相

// 编码器B — TIMG7 正交编码
// PA17 = A相 (TIMG7_CH0), PA24 = B相 (TIMG7_CH1)

// 舵机 — TIMA0
// PB9 = 舵机1 (TIMA0_CH1), PB8 = 舵机2 (TIMA0_CH0)

// 超声波 HC-SR04
// PA8 = TRIG, PA9 = ECHO

// K230 通信 — UART3
// PB2 = TX → K230, PB3 = RX ← K230

// 蓝牙 — UART1
// PB6 = RX (USART1_TX), PB7 = TX (USART1_RX)

// TCRT5000 循迹 — ADC12 (8路)
// PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7

// 蜂鸣器 / LED / 按键
// PB17 = 蜂鸣器, PB27 = LED, PA26 = K1, PA25 = K2
```

### 外设引脚决策表 (拓展板)

**生成代码时必须使用此表，不能使用默认推荐引脚。**

| 外设需求 | 拓展板引脚 | 片上资源 | 原因 |
|----------|-----------|----------|------|
| **OLED SDA/SCL** | PA28, PA31 | I2C0 | 板载上拉 |
| **MPU6050 SDA/SCL** | PA10, PA11 | I2C1 | **独立总线**,不与OLED冲突 |
| **电机 PWM** | PB15, PB16 | TIMG8_C0/C1 | 不与TIMA0冲突 |
| **电机方向** | PA13,PA12,PB0,PB1 | GPIO | TB6612 AIN1/2, BIN1/2 |
| **编码器A** | PA15, PA16 | GPIO双边沿中断 | TIMA1不支持QEI |
| **编码器B** | PA17, PA24 | TIMG7_CH0/CH1 | 正交编码模式 |
| **舵机** | PB9, PB8 | TIMA0_CH1/CH0 | 50Hz PWM |
| **超声波** | PA8(TRIG), PA9(ECHO) | GPIO | 输入捕获 |
| **K230 UART** | PB2(TX), PB3(RX) | UART3 | ✅ 不与CH340冲突 |
| **蓝牙** | PB6(RX), PB7(TX) | UART1 | 无线调参 |
| **TCRT5000** | 8路见上表 | ADC12 | 8路ADC |
| **蜂鸣器** | PB17 | GPIO | 有源蜂鸣器 |
| **LED** | PB27 | GPIO | 红色指示灯 |
| **按键 K1/K2** | PA26, PA25 | GPIO IN | 上拉 |

---

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
| **TB6612 PWMA** | 电机驱动 | PB15 (TIMG8_C0) | 左电机PWM, 20kHz |
| **TB6612 PWMB** | | PB16 (TIMG8_C1) | 右电机PWM |
| **TB6612 AIN1** | | PA13 | 左电机方向1 |
| **TB6612 AIN2** | | PA12 | 左电机方向2 |
| **TB6612 BIN1** | | PB0 | 右电机方向1 |
| **TB6612 BIN2** | | PB1 | 右电机方向2 |
| **TB6612 STBY** | | 3.3V | 使能 |
| **TB6612 VM** | | 电池 7.4V | 电机电源 |
| **TB6612 VCC** | | 3.3V | 逻辑电源 |
| **MG310 编码器A-A** | 电机编码器 | PA15 (GPIO中断) | 双边沿中断 |
| **MG310 编码器A-B** | | PA16 (GPIO中断) | 双边沿中断 |
| **MG310 编码器B-A** | 电机编码器 | PA17 (TIMG7_CH0) | TIMG7正交编码 |
| **MG310 编码器B-B** | | PA24 (TIMG7_CH1) | |
| **TCRT5000 ×8** | 红外循迹 | PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7 | 8路ADC |
| **MPU6050 SDA** | 六轴陀螺仪 | PA10 (I2C1_SDA) | **独立I2C1总线** |
| **MPU6050 SCL** | | PA11 (I2C1_SCL) | |
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
| **CH340 串口** | 调试/USB | PA0(TX), PA1(RX) | 🔒 板载固定 |
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

### 已禁用的天猛星引脚

| 引脚 | 原因 |
|------|------|
| PA2~PA6 | 时钟引脚, 默认未焊接 |
| PA0, PA1 | 板载CH340固定占用 |

### 信号冲突检查

| 总线 | 设备 | 地址/通道 |
|------|------|----------|
| I2C0 | MPU6050 + OLED | 0x68 + 0x3C (不同地址, 可共存) |
| TIMG8 PWM | TB6612 (ch0,ch1) | PB15, PB16 |
| TIMA0 PWM | 舵机 ×2 (ch0,ch1) | PB8, PB9 |
| I2C0 | OLED SSD1306 | 0x3C |
| I2C1 | MPU6050 | 0x68 |
| ADC | TCRT5000 ×8 | PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7 |
| TIMG7 编码器 | MG310 电机B | PA17, PA24 |
| GPIO 中断 | MG310 电机A | PA15, PA16 |

### 25E 竞赛拓展板引脚分配 (用户实测)

以下引脚表为 25E 竞赛拓展板实际分配，**生成代码时必须使用此表而非默认推荐引脚**。

| 外设功能 | 芯片/模块 | 天猛星引脚 | 片上复用 | 备注 |
|----------|----------|-----------|----------|------|
| **OLED SCL** | SSD1306 | PA31 | I2C0_SCL | I2C0总线 |
| **OLED SDA** | SSD1306 | PA28 | I2C0_SDA | 地址 0x3C |
| **MPU6050 SCL** | MPU6050 | PA11 | I2C1_SCL | **独立于OLED的总线** |
| **MPU6050 SDA** | MPU6050 | PA10 | I2C1_SDA | 地址 0x68 |
| **TB6612 PWMA** | TB6612FNG | PB15 | TIMG8_C0 | 左电机 PWM |
| **TB6612 PWMB** | TB6612FNG | PB16 | TIMG8_C1 | 右电机 PWM |
| **TB6612 AIN1** | TB6612FNG | PA13 | GPIO | 左电机方向1 |
| **TB6612 AIN2** | TB6612FNG | PA12 | GPIO | 左电机方向2 |
| **TB6612 BIN1** | TB6612FNG | PB0 | GPIO | 右电机方向1 |
| **TB6612 BIN2** | TB6612FNG | PB1 | GPIO | 右电机方向2 |
| **电机A 编码器 A相** | MG310 | PA15 | GPIO 双边沿中断 | TIMA1不支持QEI |
| **电机A 编码器 B相** | MG310 | PA16 | GPIO 双边沿中断 | 软件解码AB相 |
| **电机B 编码器 A相** | MG310 | PA17 | TIMG7_CH0 | TIMG7编码器模式 |
| **电机B 编码器 B相** | MG310 | PA24 | TIMG7_CH1 | |
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
| **CH340 串口** | 调试/USB | PA0(TX), PA1(RX) | UART0 | 🔒 板载固定 |

**信号冲突检查 (拓展板)：**

| 总线 | 设备 | 地址/通道 | 状态 |
|------|------|----------|------|
| I2C0 | OLED | 0x3C | ✅ 独占 |
| I2C1 | MPU6050 | 0x68 | ✅ 独占（与OLED分离） |
| TIMA0 | 舵机×2 (CH0,CH1) | PB8, PB9 | ✅ |
| GPIO中断 | 电机A编码器 (PA15/PA16) | 双边沿中断 | ✅ 软件解码 |
| TIMG7 | 电机B编码器 (CH0,CH1) | PA17, PA24 | ✅ |
| TIMG8 | TB6612 PWMA/PWMB | PB15, PB16 | ✅ |
| UART0 | CH340 调试 | PA0, PA1 | 🔒 |
| UART1 | 蓝牙 HC-05/06 | PB6, PB7 | ✅ |
| UART3 | K230 通信 | PB2, PB3 | ✅ 已验证 |

**SysConfig 验证结果：**

| # | 问题 | 结果 | 方案 |
|---|------|------|------|
| **1** | TIMA1 编码器模式 | ❌ TIMA1 不支持 QEI | **用 GPIO 双边沿中断**读 PA15/PA16 编码器 |
| **2** | UART3 是否存在 | ✅ 可用 | PB2=TX, PB3=RX 接 K230 |
| **3** | PB6=USART1_TX | ✅ 可用 | 蓝牙 USART1 正常工作 |

---

## 四、CCS 工程配置

### 新建工程步骤
1. CCS → File → New → CCS Project
2. Target: MSPM0G3507
3. Project template: Empty Project (with main.c)
4. 勾选 SysConfig support
5. 打开 `.syscfg` 文件，使用图形界面配置外设

### 关键文件说明
- `ti_msp_dl_config.h` — SysConfig 自动生成，包含所有外设初始化
- `ti_msp_dl_config.c` — SysConfig 自动生成的初始化函数 `SYSCFG_DL_init()`
- `main.c` — 用户代码，在 `SYSCFG_DL_init()` 之后编写
- SDK 默认安装路径: `C:\ti\mspm0_sdk_2_10_00_04\`

### main.c 框架
```c
#include "ti_msp_dl_config.h"

int main(void) {
    SYSCFG_DL_init();           // 初始化所有 SysConfig 外设
    __enable_irq();             // 全局中断使能

    while (1) {
        // 主循环
    }
}
```

---

## 五、SysConfig GUI 配置指南

### 界面布局

打开 `.syscfg` 文件后，CCS 会显示 SysConfig 图形界面：

```
┌──────────────────────────┬─────────────────────────────┐
│  左侧: Available Peripherals │  右侧: 配置面板              │
│  (可添加的外设列表)          │  (选定外设的参数配置)         │
│                            │                             │
│  📌 ADD 按钮 → 搜索外设     │  已添加的外设会显示在这里      │
│  ├── GPIO                  │  点击可修改引脚、参数         │
│  ├── UART                  │                             │
│  ├── I2C                   │                             │
│  ├── SPI                   │                             │
│  ├── Timer                 │                             │
│  ├── ADC                   │                             │
│  ├── OPA                   │                             │
│  └── SYSCTL (时钟)         │                             │
└──────────────────────────┴─────────────────────────────┘
```

### 配置步骤：UART0 调试串口

```
1. 点左侧 "ADD" → 搜索 "UART" → 选 "UART (Main)"
2. 配置面板中:
   Name:          UART_0
   TX Pin:        PA0  ← 下拉选择
   RX Pin:        PA1
   Baud Rate:     115200
   Data Bits:     8
   Parity:        None
   Stop Bits:     1
3. Advanced → TX FIFO Size: 选 "Disabled" (避免短字符串卡 FIFO)
4. 保存 (Ctrl+S)
```

### 配置步骤：GPIO 输出 (LED)

```
1. 点 "ADD" → 搜索 "GPIO" → 选 "GPIO Pin"
2. 配置:
   Pin:           PA7
   Direction:     Output
   Initial Value: Low
   (PA7 无特殊功能冲突, 直接可用)
3. 需要多个 GPIO 时重复 ADD, 每个引脚一个实例
```

### 配置步骤：GPIO 输入 (按键)

```
1. 点 "ADD" → "GPIO Pin"
2. 配置:
   Pin:           PA14
   Direction:     Input
   Pull:          Pull-up  (或 Pull-down 取决于硬件)
   Interrupt:     Falling edge (如果上拉, 按下=低电平)
3. 启用中断后 SysConfig 自动生成 IRQHandler 框架
```

### 配置步骤：I2C0 (OLED + MPU6050)

```
1. 点 "ADD" → 搜索 "I2C" → 选 "I2C (Main)"
2. 配置:
   Name:          I2C_0
   SDA Pin:       PA28  ← 官方引脚表 I2C0_SDA
   SCL Pin:       PA31  ← 官方引脚表 I2C0_SCL
   Speed:         400 kHz (Fast Mode)
   Mode:          Controller (主机)
3. ⚠️ 不需要配内部上拉 (PA28/PA31 已有)
```

### 配置步骤：PWM (电机)

```
1. 点 "ADD" → 搜索 "Timer" → 选 "Timer G" (通用定时器)
   或选 "Timer A" (高级定时器, 带死区)
2. 电机推荐 TIMA0:
   Name:          TIMA_0
   Mode:          PWM
   Period:        4000 (80MHz/4000 = 20kHz)
   CC0 Pin:       PB0  ← TIMA0_C2
   CC1 Pin:       PB1  ← TIMA0_C3
3. 保存后, ti_msp_dl_config.h 自动生成:
   - DL_TimerA_setPeriod(TIMA0, 4000)
   - DL_TimerA_setCaptureCompareValue(TIMA0, 0, duty)
```

### 配置步骤：编码器 (TIMG 正交编码)

```
1. 点 "ADD" → "Timer G"
2. 配置:
   Name:          TIMG_6
   Mode:          Encoder / QEI (正交编码接口)
   A Phase Pin:   PB2
   B Phase Pin:   PB3
3. 自动生成初始化代码, DL_TimerG_getTimerCount() 读脉冲数
```

### 配置步骤：ADC (TCRT5000)

```
1. 点 "ADD" → 搜索 "ADC" → 选 "ADC12"
2. 配置:
   Name:          ADC_0
   Resolution:    12-bit
   Sample Time:   默认
   Memory 0:      Channel 0 → 选 PA24
   Memory 1:      Channel 1 → 选 PA25
   ...依次添加 5 路
3. 如需软件触发:
   Trigger:       Software
   Conversion Mode: Single
```

### 配置步骤：时钟 (SYSCTL)

```
1. 左侧 → 已有一项 "SYSCTL" (默认添加)
2. 点开 SYSCTL:
   SYSOSC:        32MHz (默认)
   SYSPLL:        Disabled (默认) — 省电, 32MHz 够用
   MCLK Source:   SYSOSC
   MCLK Divider:  /1 (不分频)
3. 如需 80MHz:
   SYSPLL:        Enabled
   SYSPLL Source: SYSOSC
   SYSPLL Ref:    32MHz
   MCLK Source:   SYSPLL (80MHz)
   ⚠️ 96MHz 超频不支持, 最大 80MHz
4. 配完查 CPUCLK_FREQ 宏确认 (ti_msp_dl_config.h)
```

### 常见 SysConfig 错误

| 错误提示 | 原因 | 解决 |
|----------|------|------|
| "Pin conflict" | 两个外设用了同一引脚 | 改其中一个 |
| "Function not available" | 引脚不支持该功能 | 换引脚 |
| "Timer instance not available" | 定时器已被占用 | 用另一个 TIMG |
| "Pull-up not valid on open drain" | 开漏引脚不支持内部上拉 | 加外部上拉或换引脚 |

---

## 六、外设初始化代码模板

### ⚠️ SDK 架构铁律 (基于 SDK 2.10.00.04 例程验证)

```
SysConfig (.syscfg)           →  生成 ti_msp_dl_config.c/h  →  代码调用运行时 API
(配置引脚/时钟/外设/中断)         (SYSCFG_DL_init() 完成所有初始化)   (启动/读写/改占空比)
```

**所有外设的引脚分配、模式选择、时钟分频、中断使能全在 SysConfig GUI 完成。代码里不写任何 `xxx_init()` 函数。**

| 错误做法 (禁止) | 正确做法 |
|-----------------|---------|
| `DL_GPIO_setDirection()` 代码配引脚 | SysConfig GPIO Pin → Direction |
| `DL_TimerG_setPeriod()` 代码设周期 | SysConfig Timer → Period |
| `DL_GPIO_setInternalResistor()` 代码设上下拉 | SysConfig GPIO Pin → Pull |
| 手写 IRQHandler 注册 | SysConfig 勾选 Interrupt → 自动生成 |

**运行时 API (SysConfig 初始化后可用)：**

| 功能 | 正确 API | 来源 |
|------|---------|------|
| GPIO 输出 | `DL_GPIO_setPins/clearPins/togglePins(PORT, PIN)` | SDK 例程 |
| GPIO 读取 | `DL_GPIO_readPins(PORT, PIN)` | SDK 例程 |
| 启动 PWM | `DL_TimerG_startCounter(TIMGx)` | SDK 例程 |
| 改占空比 | `DL_TimerG_setCaptureCompareValue(TIMGx, CH, val)` | dl_timerg.h |
| 读编码器 | `DL_TimerG_getTimerCount(TIMGx)` | dl_timerg.h |
| 读捕获值 | `DL_TimerG_getCaptureCompareValue(TIMGx, CH)` | SDK 例程 |
| UART 发送 | `DL_UART_transmitDataBlocking(UARTx, byte)` | SDK 例程 |
| UART 接收 | `DL_UART_receiveData(UARTx)` | SDK 例程 |
| I2C 写 | `DL_I2C_fillControllerTXFIFO + startControllerTransfer` | SDK 例程 |
| ADC 读取 | `DL_ADC12_startConversion + DL_ADC12_getMemResult` | SDK 例程 |

### main.c 标准框架

```c
#include "ti_msp_dl_config.h"

int main(void) {
    SYSCFG_DL_init();           // SysConfig 生成的全部外设初始化
    __enable_irq();             // 全局中断使能

    // 启动需要显式启动的外设
    DL_TimerG_startCounter(TIMG8);  // PWM
    DL_TimerG_startCounter(TIMG7);  // 编码器

    while (1) {
        // 业务逻辑: 读传感器 → PID → 控电机 → 喂狗
        DL_WDT_feed(WDT);
    }
}
```

---

### --- GPIO ---

> **SDK铁律: GPIO 方向/上下拉/中断 全在 SysConfig 配置, 代码只做运行时操作**

**SysConfig 配置 GPIO 输出 (LED/蜂鸣器)：**
```
ADD → GPIO Pin → Pin: PB27 → Direction: Output → Initial: Low → 保存
```

**SysConfig 配置 GPIO 输入 (按键带中断)：**
```
ADD → GPIO Pin → Pin: PA26 → Direction: Input → Pull: Pull-up
                → Interrupt: Falling edge → 保存
```

**运行时代码 (极简)：**
```c
// 25E 拓展板: LED=PB27, 蜂鸣器=PB17, K1=PA26, K2=PA25
// 以下宏用 SysConfig 生成的 IOMUX 名: CONFIG_GPIO_LED/CONFIG_GPIO_BUZZER 等
#define LED_ON()   DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_27)
#define LED_OFF()  DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_27)
#define BEEP_ON()  DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_17)
#define BEEP_OFF() DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_17)

// 按键读取
if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0) { /* K1按下 */ }

// GPIO 中断 (SysConfig 自动生成 GROUP1_IRQHandler 框架)
void GROUP1_IRQHandler(void) {
    if (DL_GPIO_getEnabledInterruptStatus(GPIOA, DL_GPIO_PIN_26)) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_26);
        // 处理按键
    }
}
```

### --- Timer (TIMG) ---

> **SDK铁律: 定时器周期/模式/引脚全在 SysConfig 配置, `DL_TimerG_setPeriod()` 不存在!**

**SysConfig 配置 PWM (TB6612)：**
```
ADD → Timer G → Name: TIMG_8 → Mode: PWM
  → PWM Pin0: PB15 (TIMG8_C0) → PWM Pin1: PB16 (TIMG8_C1)
  → Period: 4000 (32MHz/4000=8kHz 或 PLL 80MHz/4000=20kHz)
  → 保存
```

**SysConfig 配置编码器 (TIMG7 QEI)：**
```
ADD → Timer G → Name: TIMG_7 → Mode: Encoder/QEI
  → Phase A: PA17 → Phase B: PA24 → 保存
```

**运行时代码：**
```c
// PWM 启动和占空比调整
DL_TimerG_startCounter(TIMG8);  // 启动 PWM
DL_TimerG_setCaptureCompareValue(TIMG8, 0, duty_a);  // CH0=PB15
DL_TimerG_setCaptureCompareValue(TIMG8, 1, duty_b);  // CH1=PB16

// 编码器读取 (TIMG7)
int32_t enc = (int32_t)DL_TimerG_getTimerCount(TIMG7);

// 输入捕获 (TIMG12 HC-SR04)
void TIMG12_IRQHandler(void) {
    if (DL_TimerG_getPendingInterrupt(TIMG12) & DL_TIMERG_IIDX_CAPTURE_C0) {
        uint32_t cap = DL_TimerG_getCaptureCompareValue(TIMG12, 0);
        // ...
    }
}
```

**编码器B 读取 (TIMG7 AB 相正交编码, PA17/PA24)：**
```c
// 25E 拓展板: 电机B编码器=PA17(TIMG7_CH0), PA24(TIMG7_CH1)
// SysConfig: TIMG7 → Encoder Mode → A=PA17, B=PA24
volatile int32_t encoder_b_count = 0;

void encoder_b_init(void) {
    DL_TimerG_startCounter(TIMG7);
}

int32_t encoder_b_read(void) {
    return (int32_t)DL_TimerG_getTimerCount(TIMG7);
}

void TIMG7_IRQHandler(void) {
    static int32_t last = 0;
    int32_t cur = (int32_t)DL_TimerG_getTimerCount(TIMG7);
    encoder_b_count += (cur - last);
    last = cur;
}
```

**编码器A 读取 (GPIO 双边沿中断, PA15/PA16)：**
```c
// 25E 拓展板: 电机A编码器=PA15(A相), PA16(B相)
// TIMA1不支持QEI, 用 GPIO 双边沿中断软件解码
// SysConfig: PA15/PA16 → GPIO Input → Both Edge Interrupt
volatile int32_t encoder_a_count = 0;

void GROUP1_IRQHandler(void) {
    uint32_t st = DL_GPIO_getEnabledInterruptStatus(GPIOA,
                    DL_GPIO_PIN_15 | DL_GPIO_PIN_16);
    static uint8_t last_a = 0, last_b = 0;
    uint8_t a = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_15) != 0);
    uint8_t b = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16) != 0);

    if (st & DL_GPIO_PIN_15) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_15);
        if (a == b) encoder_a_count++;
        else        encoder_a_count--;
    }
    if (st & DL_GPIO_PIN_16) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_16);
        if (a != b) encoder_a_count++;
        else        encoder_a_count--;
    }
}
```

**精确延时 (us/ms 级)：**
```c
// 使用 TIMG 周期中断做系统滴答
volatile uint32_t g_ms_ticks = 0;

void TICK_IRQHandler(void) {
    g_ms_ticks++;
}

void delay_ms(uint32_t ms) {
    uint32_t start = g_ms_ticks;
    while ((g_ms_ticks - start) < ms) {
        __WFI();  // 省电等待
    }
}

void delay_us(uint32_t us) {
    // 使用 DWT 周期计数器（需先启用）：
    // SysTick 或 DWT->CYCCNT
    uint32_t start = SysTick->VAL;
    uint32_t ticks = us * (SystemCoreClock / 1000000);
    while ((start - SysTick->VAL) < ticks);
}
```

### --- ADC ---

**单通道连续采样：**
```c
volatile uint16_t g_adc_result = 0;

void adc_init(void) {
    // SysConfig: ADC0 → 单通道 → 软件触发 → 12-bit
    DL_ADC12_enableConversions(ADC0);
}

uint16_t adc_read_channel(uint8_t ch) {
    DL_ADC12_setMemAddrMode(ADC0, DL_ADC12_MEM_ADDR_MODE_LARGE_OFFSET,
                             0, DL_ADC12_MEM_ADDR_CTRL_CH(ch), NULL);
    DL_ADC12_startConversion(ADC0);
    while (DL_ADC12_isConversionInProgress(ADC0));
    return DL_ADC12_getMemResult(ADC0, 0);
}
```

**多通道 DMA 采集：**
```c
#define ADC_BUF_SIZE 64
volatile uint16_t adc_buf[ADC_BUF_SIZE];

// SysConfig: ADC0 → Sequence Mode → 触发源=Timer → DMA 自动传输
void adc_dma_init(void) {
    DL_ADC12_enableDMA(ADC0);
    DL_DMA_setSrcAddr(DMA_CH0, (uint32_t)&ADC0->MEMRES[0]);
    DL_DMA_setDstAddr(DMA_CH0, (uint32_t)adc_buf);
    DL_DMA_setTransferSize(DMA_CH0, ADC_BUF_SIZE);
    DL_DMA_enableChannel(DMA_CH0);
    DL_ADC12_startConversion(ADC0);
}
```

### --- UART ---

**调试串口 (printf 重定向)：**
```c
#include <stdio.h>

int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

// SysConfig: UART0(PA0=TX,PA1=RX, 板载CH340) → 115200-8-N-1
void uart_init(void) {
    // SysConfig 自动生成完整初始化
}

// 接收中断
void UART0_INST_IRQHandler(void) {
    uint8_t data = DL_UART_receiveData(UART0);
    // 环形缓冲存入 data
}
```

### --- I2C ---

**0.96" OLED (SSD1306 I2C0) 驱动：**
```c
// 25E 拓展板: OLED 在 I2C0 (PA28=SDA, PA31=SCL)
#define OLED_ADDR 0x3C

void i2c0_init(void) {
    // SysConfig: I2C0(PA28=SDA,PA31=SCL) → Controller → 400kHz
}

void oled_write_cmd(uint8_t cmd) {
    uint8_t buf[2] = {0x00, cmd};
    DL_I2C_fillControllerTXFIFO(I2C0, buf, 2);
    DL_I2C_startControllerTransfer(I2C0, DL_I2C_CONTROLLER_DIRECTION_TX, 2);
    while (DL_I2C_getControllerStatus(I2C0, DL_I2C_CONTROLLER_STATUS_BUSY));
}

void oled_write_data_buf(uint8_t *data, uint16_t len) {
    while (len) {
        uint8_t buf[65];  // 64字节数据 + 1控制字节
        uint16_t chunk = len > 64 ? 64 : len;
        buf[0] = 0x40;
        memcpy(buf + 1, data, chunk);
        DL_I2C_fillControllerTXFIFO(I2C0, buf, chunk + 1);
        DL_I2C_startControllerTransfer(I2C0, DL_I2C_CONTROLLER_DIRECTION_TX, chunk + 1);
        while (DL_I2C_getControllerStatus(I2C0, DL_I2C_CONTROLLER_STATUS_BUSY));
        data += chunk;
        len -= chunk;
    }
}
```

### --- SPI ---

**主机模式发送：**
```c
void spi_init(void) {
    // SysConfig: SPI0 → 主机模式 → CPOL=0, CPHA=0 → 最高 32MHz
}

void spi_transfer(uint8_t *tx, uint8_t *rx, uint16_t len) {
    DL_SPI_transferBlocking(SPI0, tx, rx, len);
}
```

### --- HC-SR04 超声波测距 ---

```c
// 25E 拓展板: TRIG=PA8(GPIO OUT), ECHO=PA9(GPIO IN 输入捕获)
// SysConfig: TIMG12 → Input Capture → PA9=ECHO
#define TRIG_PIN  DL_GPIO_PIN_8
#define TRIG_PORT GPIOA

volatile uint32_t echo_start = 0;
volatile uint32_t echo_end = 0;
volatile bool     echo_done = false;

void hcsr04_trigger(void) {
    DL_GPIO_setPins(TRIG_PORT, TRIG_PIN);
    delay_us(10);
    DL_GPIO_clearPins(TRIG_PORT, TRIG_PIN);
}

// 输入捕获中断 (ECHO=PA9 双边沿捕获)
void TIMG12_IRQHandler(void) {
    uint32_t status = DL_TimerG_getPendingInterrupt(TIMG12);
    if (status & DL_TIMERG_IIDX_CAPTURE_C0) {
        static bool rising = true;
        if (rising) {
            echo_start = DL_TimerG_getCaptureCompareValue(TIMG12, 0);
            DL_TimerG_setCaptureEdge(TIMG12, 0, DL_TIMER_CAPTURE_EDGE_FALLING);
        } else {
            echo_end = DL_TimerG_getCaptureCompareValue(TIMG12, 0);
            echo_done = true;
            DL_TimerG_setCaptureEdge(TIMG12, 0, DL_TIMER_CAPTURE_EDGE_RISING);
        }
        rising = !rising;
        DL_TimerG_clearInterruptStatus(TIMG12, DL_TIMERG_IIDX_CAPTURE_C0);
    }
}

float hcsr04_get_distance_cm(void) {
    echo_done = false;
    hcsr04_trigger();
    while (!echo_done);  // 实际项目中设超时防止卡死
    uint32_t ticks = (echo_end > echo_start) ? (echo_end - echo_start)
                    : (0xFFFF - echo_start + echo_end);
    // 声速 340m/s, Timer 时钟 1MHz → 1us/tick, 距离 = ticks*340/20000 = ticks/58.8
    return ticks / 58.8f;
}
```

### --- MPU6050 完整驱动 (I2C1) ---

```c
// 25E 拓展板: MPU6050 在 I2C1 (PA10=SDA, PA11=SCL), 独立于 OLED 的 I2C0
#define MPU6050_ADDR  0x68
#define MPU6050_PWR_MGMT_1   0x6B
#define MPU6050_ACCEL_XOUT_H 0x3B
#define MPU6050_GYRO_XOUT_H  0x43
#define MPU6050_SMPLRT_DIV   0x19
#define MPU6050_CONFIG       0x1A
#define MPU6050_GYRO_CONFIG  0x1B
#define MPU6050_ACCEL_CONFIG 0x1C

// I2C1 基础读写
void mpu6050_write_reg(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = {reg, val};
    DL_I2C_fillControllerTXFIFO(I2C1, buf, 2);
    DL_I2C_startControllerTransfer(I2C1, DL_I2C_CONTROLLER_DIRECTION_TX, 2);
    while (DL_I2C_getControllerStatus(I2C1, DL_I2C_CONTROLLER_STATUS_BUSY));
}

uint8_t mpu6050_read_reg(uint8_t reg) {
    uint8_t val = 0;
    // 写寄存器地址 (STOP自动生成)
    DL_I2C_fillControllerTXFIFO(I2C1, &reg, 1);
    DL_I2C_startControllerTransfer(I2C1, DL_I2C_CONTROLLER_DIRECTION_TX, 1);
    while (DL_I2C_getControllerStatus(I2C1, DL_I2C_CONTROLLER_STATUS_BUSY));
    // 读数据
    DL_I2C_startControllerTransfer(I2C1, DL_I2C_CONTROLLER_DIRECTION_RX, 1);
    while (DL_I2C_getControllerStatus(I2C1, DL_I2C_CONTROLLER_STATUS_BUSY));
    val = DL_I2C_receiveControllerData(I2C1);
    return val;
}

// 初始化: 唤醒, ±2000°/s, ±8g, 1kHz 采样
void mpu6050_init(void) {
    mpu6050_write_reg(MPU6050_PWR_MGMT_1, 0x00);
    delay_ms(100);
    mpu6050_write_reg(MPU6050_SMPLRT_DIV, 0x00);
    mpu6050_write_reg(MPU6050_CONFIG, 0x00);
    mpu6050_write_reg(MPU6050_GYRO_CONFIG, 0x18);   // ±2000°/s
    mpu6050_write_reg(MPU6050_ACCEL_CONFIG, 0x10);  // ±8g
}

typedef struct {
    int16_t ax, ay, az;
    int16_t gx, gy, gz;
    int16_t temp;
} MPU6050_Data;

void mpu6050_read_all(MPU6050_Data *data) {
    uint8_t buf[14];
    mpu6050_read_data(MPU6050_ACCEL_XOUT_H, buf, 14);
    data->ax   = (int16_t)((buf[0] << 8) | buf[1]);
    data->ay   = (int16_t)((buf[2] << 8) | buf[3]);
    data->az   = (int16_t)((buf[4] << 8) | buf[5]);
    data->temp = (int16_t)((buf[6] << 8) | buf[7]);
    data->gx   = (int16_t)((buf[8] << 8) | buf[9]);
    data->gy   = (int16_t)((buf[10] << 8) | buf[11]);
    data->gz   = (int16_t)((buf[12] << 8) | buf[13]);
}

// 加速度计 → 角度 (pitch: atan2(-ax, sqrt(ay^2+az^2)), roll: atan2(ay, az))
// 注意: 6轴 Mahony 无磁力计修正, yaw 会漂移, 仅 pitch/roll 可靠
float mpu6050_accel_pitch(float ax, float ay, float az) {
    return atan2f(-ax, sqrtf(ay*ay + az*az)) * 57.29578f;
}
float mpu6050_accel_roll(float ay, float az) {
    return atan2f(ay, az) * 57.29578f;
}

// Mahony AHRS 姿态解算 (六轴, 2K 参数)
typedef struct {
    float q0, q1, q2, q3;  // 四元数
    float kp, ki;           // PI 增益
    float integral_fb_x, integral_fb_y, integral_fb_z;
} MahonyAHRS;

void mahony_init(MahonyAHRS *m, float kp, float ki) {
    m->q0 = 1.0f; m->q1 = 0.0f; m->q2 = 0.0f; m->q3 = 0.0f;
    m->kp = kp; m->ki = ki;
    m->integral_fb_x = m->integral_fb_y = m->integral_fb_z = 0.0f;
}

void mahony_update(MahonyAHRS *m, float gx, float gy, float gz,
                   float ax, float ay, float az, float dt) {
    float recip_norm;
    float hx, hy, bx, bz;
    float vx, vy, vz, wx, wy, wz;
    float ex, ey, ez;
    float qa, qb, qc;

    // 加速度计归一化
    recip_norm = 1.0f / sqrtf(ax*ax + ay*ay + az*az);
    ax *= recip_norm; ay *= recip_norm; az *= recip_norm;

    // 重力方向估计
    vx = 2.0f * (m->q1*m->q3 - m->q0*m->q2);
    vy = 2.0f * (m->q0*m->q1 + m->q2*m->q3);
    vz = m->q0*m->q0 - m->q1*m->q1 - m->q2*m->q2 + m->q3*m->q3;

    // 误差
    ex = ay*vz - az*vy;
    ey = az*vx - ax*vz;
    ez = ax*vy - ay*vx;

    // 积分反馈
    m->integral_fb_x += m->ki * ex * dt;
    m->integral_fb_y += m->ki * ey * dt;
    m->integral_fb_z += m->ki * ez * dt;

    // 修正陀螺仪
    gx += m->kp*ex + m->integral_fb_x;
    gy += m->kp*ey + m->integral_fb_y;
    gz += m->kp*ez + m->integral_fb_z;

    // 四元数更新
    qa = m->q0; qb = m->q1; qc = m->q2;
    m->q0 += (-qb*gx - qc*gy - m->q3*gz) * 0.5f * dt;
    m->q1 += ( qa*gx + qc*gz - m->q3*gy) * 0.5f * dt;
    m->q2 += ( qa*gy - qb*gz + m->q3*gx) * 0.5f * dt;
    m->q3 += ( qa*gz + qb*gy - qc*gx) * 0.5f * dt;

    // 归一化
    recip_norm = 1.0f / sqrtf(m->q0*m->q0 + m->q1*m->q1 + m->q2*m->q2 + m->q3*m->q3);
    m->q0 *= recip_norm; m->q1 *= recip_norm; m->q2 *= recip_norm; m->q3 *= recip_norm;
}

// 从四元数提取 pitch/roll (度)
float mahony_get_pitch(MahonyAHRS *m) {
    return asinf(2.0f*(m->q2*m->q3 + m->q0*m->q1)) * 57.29578f;
}
float mahony_get_roll(MahonyAHRS *m) {
    return atan2f(2.0f*(m->q0*m->q2 - m->q1*m->q3),
                  1.0f - 2.0f*(m->q2*m->q2 + m->q1*m->q1)) * 57.29578f;
}
```

### --- SSD1306 OLED 完整驱动 ---

```c
#define OLED_ADDR  0x3C
#define OLED_WIDTH 128
#define OLED_HEIGHT 64
#define OLED_PAGES (OLED_HEIGHT / 8)  // 8 pages

static uint8_t oled_framebuffer[OLED_WIDTH * OLED_PAGES];

void oled_write_cmd(uint8_t cmd) {
    uint8_t buf[2] = {0x00, cmd};
    DL_I2C_transmitBlocking(I2C0, OLED_ADDR, buf, 2);
}

void oled_write_data_buf(uint8_t *data, uint16_t len) {
    // I2C 硬件限制: 一次最多发 128 字节; 批量写入
    while (len) {
        uint16_t chunk = (len > 127) ? 127 : len;
        // 先发 control byte 0x40，再发数据；这里简化用 blocking 逐个 page 刷
        uint8_t buf[129];
        buf[0] = 0x40;
        for (uint16_t i = 0; i < chunk; i++) buf[i+1] = data[i];
        DL_I2C_transmitBlocking(I2C0, OLED_ADDR, buf, chunk + 1);
        data += chunk;
        len  -= chunk;
    }
}

void oled_init(void) {
    // 初始化序列
    uint8_t init_cmds[] = {
        0xAE, 0xD5, 0x80, 0xA8, 0x3F, 0xD3, 0x00, 0x40,
        0x8D, 0x14, 0x20, 0x00, 0xA1, 0xC8, 0xDA, 0x12,
        0x81, 0xCF, 0xD9, 0xF1, 0xDB, 0x40, 0xA4, 0xA6, 0xAF
    };
    for (int i = 0; i < sizeof(init_cmds); i++) oled_write_cmd(init_cmds[i]);
    memset(oled_framebuffer, 0, sizeof(oled_framebuffer));
    oled_refresh();
}

void oled_refresh(void) {
    oled_write_cmd(0x21); oled_write_cmd(0x00); oled_write_cmd(0x7F); // 列范围
    oled_write_cmd(0x22); oled_write_cmd(0x00); oled_write_cmd(0x07); // 页范围
    oled_write_data_buf(oled_framebuffer, sizeof(oled_framebuffer));
}

void oled_clear(void) {
    memset(oled_framebuffer, 0, sizeof(oled_framebuffer));
}

void oled_draw_pixel(uint8_t x, uint8_t y, uint8_t color) {
    if (x >= OLED_WIDTH || y >= OLED_HEIGHT) return;
    if (color) oled_framebuffer[x + (y/8)*OLED_WIDTH] |=  (1 << (y%8));
    else       oled_framebuffer[x + (y/8)*OLED_WIDTH] &= ~(1 << (y%8));
}

// Bresenham 画线
void oled_draw_line(uint8_t x0, uint8_t y0, uint8_t x1, uint8_t y1) {
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    while (1) {
        oled_draw_pixel(x0, y0, 1);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

// 6x8 ASCII 字库 (可打印字符 0x20-0x7F, 每字符 6 字节)
void oled_putchar(uint8_t x, uint8_t y, char c) {
    if (c < 0x20 || c > 0x7F) return;
    // 用户需要自行提供 font6x8[c - 0x20][6] 字库
    extern const uint8_t font6x8[][6];
    uint8_t idx = c - 0x20;
    for (uint8_t col = 0; col < 6; col++) {
        uint8_t data = font6x8[idx][col];
        for (uint8_t row = 0; row < 8; row++) {
            oled_draw_pixel(x + col, y + row, (data >> row) & 1);
        }
    }
}

void oled_puts(uint8_t x, uint8_t y, const char *str) {
    while (*str) {
        oled_putchar(x, y, *str++);
        x += 6;
        if (x > OLED_WIDTH - 6) { x = 0; y += 8; }
        if (y >= OLED_HEIGHT) return;
    }
}

// 显示有符号浮点数（PID 调试常用）
void oled_show_float(uint8_t x, uint8_t y, const char *label, float val) {
    char buf[22];
    snprintf(buf, sizeof(buf), "%s:%.2f", label, val);
    oled_puts(x, y, buf);
}
```

**中文显示方法:** 将汉字取模（16×16 点阵，纵向列行式），每个汉字 32 字节。通过 `oled_draw_pixel` 逐点写入 framebuffer。建议用 PCtoLCD2002 等工具生成字模，然后构建 `const uint8_t hanzi_table[][32]` 数组查表显示。

### --- 矩阵按键扫描 (拓展板未使用, 仅供参考) ---

> ⚠️ 矩阵按键不在25E拓展板上。以下为旧版参考代码, 正确做法: SysConfig GPIO Pin 配方向+上下拉, 代码只做读写。

```c
// 4×4 矩阵按键 (4 行输出 + 4 列输入)
// 行: PB8~PB11 (输出), 列: PB12~PB15 (输入, 内部下拉)
// ⚠️ 避开 PA0/PA1(CH340)和时钟引脚 PA2~PA6
#define KEY_ROWS 4
#define KEY_COLS 4

static const uint8_t key_map[KEY_ROWS][KEY_COLS] = {
    {'1','2','3','A'},
    {'4','5','6','B'},
    {'7','8','9','C'},
    {'*','0','#','D'}
};

void matrix_key_init(void) {
    for (int r = 0; r < KEY_ROWS; r++) {
        DL_GPIO_setDirection(GPIOB, (1 << (8 + r)), DL_GPIO_OUTPUT);
        DL_GPIO_clearPins(GPIOB, (1 << (8 + r)));
    }
    for (int c = 0; c < KEY_COLS; c++) {
        DL_GPIO_setDirection(GPIOB, (1 << (12 + c)), DL_GPIO_INPUT);
        DL_GPIO_setInternalResistor(GPIOB, (1 << (12 + c)), DL_GPIO_RESISTOR_PULL_DOWN);
    }
}

char matrix_key_scan(void) {
    for (int r = 0; r < KEY_ROWS; r++) {
        DL_GPIO_setPins(GPIOB, (1 << (8 + r)));
        delay_us(10);
        for (int c = 0; c < KEY_COLS; c++) {
            if (DL_GPIO_readPins(GPIOB, (1 << (12 + c)))) {
                DL_GPIO_clearPins(GPIOB, (1 << (8 + r)));
                delay_ms(20);
                while (DL_GPIO_readPins(GPIOB, (1 << (12 + c))));
                return key_map[r][c];
            }
        }
        DL_GPIO_clearPins(GPIOB, (1 << (8 + r)));
    }
    return 0;
}
```

### --- EC11 旋转编码器 (拓展板未使用, 仅供参考) ---

> ⚠️ 拓展板上EC11引脚(PA16/PA17)已被编码器A占用。以下为旧版参考, 正确做法: SysConfig 配GPIO双边沿中断。

```c
// A相 PA16, B相 PA17, 按键 PB4 (均有中断, 避开PB2/PB3编码器)
// SysConfig: PA16/PA17/PB4 → GPIO 输入 → 双边沿中断 → GROUP1_IRQHandler
volatile int32_t ec11_count = 0;
volatile bool    ec11_button = false;

void GROUP1_IRQHandler(void) {
    uint32_t status = DL_GPIO_getEnabledInterruptStatus(GPIOA,
                        DL_GPIO_PIN_16 | DL_GPIO_PIN_17);
    status |= DL_GPIO_getEnabledInterruptStatus(GPIOB, DL_GPIO_PIN_4);
    // A/B 相位判断 (PA16=A, PA17=B)
    if (status & DL_GPIO_PIN_16) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_16);
        if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16)) {
            if (!DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_17)) ec11_count++;
            else                                         ec11_count--;
        } else {
            if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_17)) ec11_count++;
            else                                          ec11_count--;
        }
    }
    if (status & DL_GPIO_PIN_17) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_17);
        if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_17)) {
            if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16)) ec11_count++;
            else                                          ec11_count--;
        } else {
            if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16)) ec11_count--;
            else                                          ec11_count++;
        }
    }
    if (status & DL_GPIO_PIN_4) {
        DL_GPIO_clearInterruptStatus(GPIOB, DL_GPIO_PIN_4);
        ec11_button = true;
    }
}
```

### --- UART 协议解析 ---

```c
// 帧格式: 帧头(2B) + 长度(1B) + 命令(1B) + 数据(NB) + 校验(1B, 和校验)
#define FRAME_HEAD1 0xA5
#define FRAME_HEAD2 0x5A
#define RX_BUF_SIZE  128

typedef struct {
    uint8_t buf[RX_BUF_SIZE];
    uint8_t head;
    uint8_t tail;
    uint8_t parse_state;  // 0:等HEAD1, 1:等HEAD2, 2:等LEN, 3:收数据
    uint8_t data_len;
    uint8_t data_idx;
    uint8_t checksum;
} UART_RingBuf;

static UART_RingBuf uart_rx = {0};

void UART0_INST_IRQHandler(void) {
    uint8_t byte = DL_UART_receiveData(UART0);
    // 存入环形缓冲
    uart_rx.buf[uart_rx.head] = byte;
    uart_rx.head = (uart_rx.head + 1) % RX_BUF_SIZE;
}

// 主循环中调用解析
bool uart_parse_frame(uint8_t *cmd, uint8_t *data, uint8_t *data_len) {
    while (uart_rx.tail != uart_rx.head) {
        uint8_t b = uart_rx.buf[uart_rx.tail];
        uart_rx.tail = (uart_rx.tail + 1) % RX_BUF_SIZE;

        switch (uart_rx.parse_state) {
        case 0:
            if (b == FRAME_HEAD1) { uart_rx.parse_state = 1; uart_rx.checksum = b; }
            break;
        case 1:
            if (b == FRAME_HEAD2) { uart_rx.parse_state = 2; uart_rx.checksum += b; }
            else uart_rx.parse_state = 0;
            break;
        case 2:
            if (b <= RX_BUF_SIZE - 4) {
                uart_rx.data_len = b;
                uart_rx.data_idx = 0;
                uart_rx.parse_state = 3;
                uart_rx.checksum += b;
            } else uart_rx.parse_state = 0;
            break;
        case 3:
            uart_rx.checksum += b;
            if (uart_rx.data_idx == 0) *cmd = b;
            else data[uart_rx.data_idx - 1] = b;
            uart_rx.data_idx++;
            if (uart_rx.data_idx >= uart_rx.data_len) {
                // 校验
                uint8_t check_sum = uart_rx.checksum;
                uart_rx.parse_state = 0;
                *data_len = uart_rx.data_len - 1;  // 不含命令字节
                if (check_sum == 0) return true;    // 和校验正确
            }
            break;
        }
    }
    return false;
}

// 打包发送
void uart_send_frame(uint8_t cmd, uint8_t *data, uint8_t len) {
    uint8_t checksum = FRAME_HEAD1 + FRAME_HEAD2 + (len + 1) + cmd;
    DL_UART_transmitDataBlocking(UART0, FRAME_HEAD1);
    DL_UART_transmitDataBlocking(UART0, FRAME_HEAD2);
    DL_UART_transmitDataBlocking(UART0, len + 1);
    DL_UART_transmitDataBlocking(UART0, cmd);
    for (int i = 0; i < len; i++) {
        checksum += data[i];
        DL_UART_transmitDataBlocking(UART0, data[i]);
    }
    DL_UART_transmitDataBlocking(UART0, (uint8_t)(-checksum));  // 补码和校验
}
```

### --- OPA ---

**内部运放射随器 (信号缓冲)：**
```c
void opa_init(void) {
    // SysConfig: OPA0 → 跟随器模式 → 内部连接
    DL_OPA_enable(OPA0);
}
```

**内部运放差分放大 (电流检测)：**
```c
// SysConfig: OPA0 → 差分放大模式 → Gain=16
// Vin+ = PA15, Vin- = PA14 (外部接采样电阻两端)
void opa_diff_init(void) {
    DL_OPA_setGain(OPA0, DL_OPA_GAIN_16);
    DL_OPA_enable(OPA0);
}
```

---

## 七、I2C 总线共享指南 (拓展板已物理分离)

> **拓展板已将 OLED(I2C0) 和 MPU6050(I2C1) 分离到独立总线，不再需要软件调度。**
> 以下内容适用于旧版同总线方案，仅作参考。

### 旧版问题

OLED (0x3C) 和 MPU6050 (0x68) 共用 I2C0，同时刷 OLED 和读 MPU6050 会阻塞总线。

### 解决方案

```c
/* === I2C 设备管理 === */
typedef struct {
    uint8_t addr;          /* 从机地址 */
    uint32_t last_access;  /* 上次访问时间戳 */
    uint32_t min_interval; /* 最小访问间隔 (ms) */
} I2C_Device;

static I2C_Device i2c_dev_oled = {0x3C, 0, 100};  /* OLED: 100ms 间隔 */
static I2C_Device i2c_dev_mpu  = {0x68, 0, 5};     /* MPU: 5ms 间隔 */

/* 设备内核对 I2C 总线访问 */
bool i2c_device_access(I2C_Device *dev) {
    if (g_ms_ticks - dev->last_access < dev->min_interval) return false;
    dev->last_access = g_ms_ticks;
    return true;
}

/* 主循环调度 */
void main_loop(void) {
    while (1) {
        /* 每 100ms 刷新一次 OLED (耗时约 20ms, 发 1024 字节) */
        if (i2c_device_access(&i2c_dev_oled)) {
            oled_update_display();  /* 只刷新变化的部分, 不全刷 */
        }
        /* 每 5ms 读一次 MPU6050 (耗时约 1ms, 发 14 字节) */
        if (i2c_device_access(&i2c_dev_mpu)) {
            mpu6050_read_all(&mpu_data);
        }
        /* PID 计算不依赖 I2C, 随时可以执行 */
        pid_control_loop();
    }
}
```

### I2C 冲突检测

```c
/* 发送前检查总线是否忙 */
if (DL_I2C_getControllerStatus(I2C0, DL_I2C_CONTROLLER_STATUS_BUSY)) {
    return;  // 上次传输未完成, 跳过
}

/* 超时保护: startControllerTransfer 自动生成 STOP, 无需手动 */
#define I2C_TIMEOUT_MS  10
uint32_t t0 = g_ms_ticks;
while (DL_I2C_getControllerStatus(I2C0, DL_I2C_CONTROLLER_STATUS_BUSY)) {
    if (g_ms_ticks - t0 > I2C_TIMEOUT_MS) {
        DL_I2C_disableStopCondition(I2C0);  // 异常时强制释放总线
        break;
    }
}
```

### OLED 部分刷新 (省带宽)

```c
/* 只刷新变化区域而不是整屏 */
void oled_update_partial(uint8_t page_start, uint8_t page_end) {
    oled_write_cmd(0x21); oled_write_cmd(0x00); oled_write_cmd(127);  /* 列 */
    oled_write_cmd(0x22); oled_write_cmd(page_start); oled_write_cmd(page_end);
    oled_write_data_buf(&oled_framebuffer[page_start * 128],
                         (page_end - page_start + 1) * 128);
}
```

---

## 八、控制算法

### PID 控制器

```c
typedef struct {
    float Kp, Ki, Kd;           // 系数
    float setpoint;             // 目标值
    float integral;             // 积分累加
    float prev_error;           // 上次误差
    float out_min, out_max;     // 输出限幅
    float integral_limit;       // 积分分离阈值
} PID_Controller;

float pid_update(PID_Controller *pid, float measurement, float dt) {
    float error = pid->setpoint - measurement;

    // 比例
    float p_out = pid->Kp * error;

    // 积分 (带分离 — 大误差时不积分)
    if (fabsf(error) < pid->integral_limit) {
        pid->integral += error * dt;
    }
    float i_out = pid->Ki * pid->integral;

    // 微分 (对测量值微分，避免微分冲击)
    float d_out = pid->Kd * (measurement - pid->prev_error) / dt;
    pid->prev_error = measurement;

    // 输出合成 + 限幅 + 抗饱和
    float output = p_out + i_out + d_out;
    if (output > pid->out_max) {
        output = pid->out_max;
        // 抗积分饱和：超限时不累积积分
    } else if (output < pid->out_min) {
        output = pid->out_min;
    }

    return output;
}

void pid_reset(PID_Controller *pid) {
    pid->integral = 0;
    pid->prev_error = 0;
}
```

### 滤波器

**一阶低通滤波器：**
```c
typedef struct {
    float alpha;   // 滤波系数 = dt/(RC+dt), 取值范围 (0,1]
    float output;
} LowPassFilter;

float lpf_update(LowPassFilter *f, float input) {
    f->output = f->alpha * input + (1.0f - f->alpha) * f->output;
    return f->output;
}
```

**滑动平均滤波：**
```c
#define MA_WINDOW 8
typedef struct {
    uint16_t buf[MA_WINDOW];
    uint8_t  idx;
    uint32_t sum;
    uint8_t  count;
} MovingAvg;

uint16_t ma_update(MovingAvg *ma, uint16_t val) {
    ma->sum -= ma->buf[ma->idx];
    ma->sum += val;
    ma->buf[ma->idx] = val;
    ma->idx = (ma->idx + 1) % MA_WINDOW;
    if (ma->count < MA_WINDOW) ma->count++;
    return (uint16_t)(ma->sum / ma->count);
}
```

**互补滤波 (IMU 姿态融合)：**
```c
// 陀螺仪积分 + 加速度计修正
typedef struct {
    float angle;     // 输出角度
    float alpha;     // 互补系数, 典型 0.98
    float dt;        // 采样周期
} ComplementaryFilter;

float cf_update(ComplementaryFilter *cf, float gyro_rate, float accel_angle) {
    // gyro_rate: 陀螺仪角速度 (°/s)
    // accel_angle: 加速度计推算的角度
    cf->angle = cf->alpha * (cf->angle + gyro_rate * cf->dt)
              + (1.0f - cf->alpha) * accel_angle;
    return cf->angle;
}
```

**卡尔曼滤波 (1D，适合单轴角度融合)：**
```c
typedef struct {
    float x;   // 状态估计
    float p;   // 估计协方差
    float q;   // 过程噪声
    float r;   // 测量噪声
    float k;   // 卡尔曼增益
} Kalman1D;

void kalman1d_init(Kalman1D *kf, float q, float r) {
    kf->x = 0; kf->p = 1; kf->q = q; kf->r = r; kf->k = 0;
}

float kalman1d_update(Kalman1D *kf, float measurement) {
    kf->p += kf->q;
    kf->k  = kf->p / (kf->p + kf->r);
    kf->x += kf->k * (measurement - kf->x);
    kf->p *= (1 - kf->k);
    return kf->x;
}

// 陀螺仪+加速度计角度融合示例：
// 每 dt 秒调用: angle = kalman1d_update(&kf,
//     accel_angle + (angle + gyro_rate*dt)  // 融合输入
// );
// 或直接用: 先用 gyro*dt 做预测，再用 accel 做更新
```

### 电机控制

**直流电机速度闭环 (PWM + 编码器)：**
```c
typedef struct {
    PID_Controller speed_pid;
    uint32_t pwm_channel;
    uint32_t pwm_period;
    int32_t  target_speed;   // 目标速度 (编码器脉冲/控制周期)
    int32_t  current_speed;
    // 编码器读数
    int32_t  last_encoder;
} DC_Motor;

void motor_speed_control(DC_Motor *motor, int32_t encoder_val, float dt) {
    motor->current_speed = encoder_val - motor->last_encoder;
    motor->last_encoder = encoder_val;

    float output = pid_update(&motor->speed_pid,
                              (float)motor->current_speed, dt);

    // 将 PID 输出映射到 PWM 占空比
    if (output > motor->pwm_period) output = motor->pwm_period;
    if (output < 0) output = 0;

    DL_TimerG_setCaptureCompareValue(TIMG0, motor->pwm_channel, (uint32_t)output);
}
```

**舵机控制 (TIMA0 50Hz PWM, 500~2500us)：**
```c
// 25E 拓展板: 舵机1=PB9(TIMA0_CH1), 舵机2=PB8(TIMA0_CH0)
// 20ms 周期 = 50Hz, 脉宽 0.5~2.5ms 对应 0°~180°
// SysConfig: TIMA0 → PWM → PB8=CH0, PB9=CH1, period=25000
#define SERVO_PERIOD  25000
#define SERVO_MIN     625    // 0.5ms 对应
#define SERVO_MAX     3125   // 2.5ms 对应
#define SERVO_MID     1875   // 1.5ms 对应 90°

void servo1_set_angle(uint32_t angle_deg) { // 舵机1 PB9=CH1, 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    DL_TimerG_setCaptureCompareValue(TIMA0, 1, pulse);
}
void servo2_set_angle(uint32_t angle_deg) { // 舵机2 PB8=CH0, 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    DL_TimerG_setCaptureCompareValue(TIMA0, 0, pulse);
}
```

**步进电机控制 (A4988/DRV8825 脉冲+方向)：**
```c
// STEP 引脚连接 GPIO, DIR 连接 GPIO
void stepper_step(int steps, uint8_t dir_pin_state, uint32_t step_delay_us) {
    // 设置方向
    if (dir_pin_state) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_8);
    else DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_8);

    for (int i = 0; i < steps; i++) {
        DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_9);   // STEP high
        delay_us(step_delay_us / 2);
        DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_9); // STEP low
        delay_us(step_delay_us / 2);
    }
}
```

---

## 九、调试与调参工具

### --- 串口 PID 调参 (配合 VOFA+ / SerialPlot) ---

**VOFA+ FireWater 协议 — 实时发送多变量波形：**

```c
// Vofa+ 的 FireWater 协议: 每帧以尾部 0x00 0x00 0x80 0x7F 结束
// 支持同时显示多条 float 曲线
void vofa_send_floats(float *data, uint8_t count) {
    uint8_t *p = (uint8_t*)data;
    for (int i = 0; i < count * 4; i++) {
        DL_UART_transmitDataBlocking(UART0, p[i]);
    }
    // 帧尾
    uint8_t tail[4] = {0x00, 0x00, 0x80, 0x7F};
    for (int i = 0; i < 4; i++) DL_UART_transmitDataBlocking(UART0, tail[i]);
}

// 使用示例: 在控制循环中发送 PID 相关变量用于调参
// float debug_data[4] = {setpoint, measurement, pwm_output, pid->integral};
// vofa_send_floats(debug_data, 4);
```

**SerialPlot 兼容格式 (float 二进制 + 同步帧头)：**

```c
// SerialPlot: 帧头 + N 个 float (大端), 波特率 921600 或更高
void serialplot_send(float *data, uint8_t count) {
    uint8_t header[2] = {0xAA, 0xAA};  // 自定义帧头
    for (int i = 0; i < 2; i++) DL_UART_transmitDataBlocking(UART0, header[i]);

    for (int i = 0; i < count; i++) {
        // 大端 float
        uint32_t raw;
        memcpy(&raw, &data[i], 4);
        DL_UART_transmitDataBlocking(UART0, (raw >> 24) & 0xFF);
        DL_UART_transmitDataBlocking(UART0, (raw >> 16) & 0xFF);
        DL_UART_transmitDataBlocking(UART0, (raw >> 8) & 0xFF);
        DL_UART_transmitDataBlocking(UART0, raw & 0xFF);
    }
}
```

**串口调试助手 PID 在线调参 (文本协议)：**

```c
// 协议: "P 1.5\n" "I 0.02\n" "D 0.1\n" "T 1000\n" (target)
// PC 端发送 → MSPM0 解析 → 更新 PID 参数
void uart_pid_tune(PID_Controller *pid, float *target) {
    static char line[32];
    static uint8_t idx = 0;
    while (DL_UART_isDataAvailable(UART0)) {
        char c = DL_UART_receiveData(UART0);
        if (c == '\r') continue;
        if (c == '\n') {
            line[idx] = 0;
            char cmd; float val;
            if (sscanf(line, "%c %f", &cmd, &val) == 2) {
                switch (cmd) {
                case 'P': pid->Kp = val; break;
                case 'I': pid->Ki = val; break;
                case 'D': pid->Kd = val; break;
                case 'T': *target   = val; break;
                }
            }
            idx = 0;
        } else if (idx < sizeof(line) - 1) {
            line[idx++] = c;
        }
    }
}

// 打印当前参数 (方便确认)
void uart_print_pid_params(PID_Controller *pid, float target) {
    printf("Kp=%.3f Ki=%.4f Kd=%.3f Target=%.2f\r\n",
           pid->Kp, pid->Ki, pid->Kd, target);
}
```

### --- 按键长按/短按/双击识别 ---

```c
typedef struct {
    uint32_t press_time;
    uint32_t release_time;
    uint8_t  state;      // 0:idle, 1:pressed, 2:waiting_double
    uint8_t  event;      // 0:none, 1:short, 2:long, 3:double
} Button;

#define BTN_SHORT_MS   30
#define BTN_LONG_MS    800
#define BTN_DOUBLE_MS  400
extern volatile uint32_t g_ms_ticks;  // 1ms 系统滴答

void button_update(Button *btn, bool pressed) {
    btn->event = 0;
    switch (btn->state) {
    case 0: // idle
        if (pressed) {
            btn->state = 1;
            btn->press_time = g_ms_ticks;
        }
        break;
    case 1: // pressed
        if (!pressed) {
            uint32_t hold = g_ms_ticks - btn->press_time;
            if (hold >= BTN_LONG_MS) {
                btn->event = 2;  // 长按
                btn->state = 0;
            } else if (hold >= BTN_SHORT_MS) {
                btn->state = 2;
                btn->release_time = g_ms_ticks;
            }
        }
        break;
    case 2: // waiting_double
        if (pressed) {
            btn->state = 1;
            btn->press_time = g_ms_ticks;
        } else if ((g_ms_ticks - btn->release_time) > BTN_DOUBLE_MS) {
            btn->event = 1;  // 短按
            btn->state = 0;
        }
        break;
    }
}
// 主循环调用: button_update(&btn, DL_GPIO_readPins(...) == 0);
// if (btn.event == 1) { /* 短按 */ }
// if (btn.event == 2) { /* 长按 */ }
// if (btn.event == 3) { /* 双击 — 在 case 1 第一个短按释放后进入 case 2 时若再次按下即双击 */ }
```

## 十、看门狗 WDT 配置

### 概述

看门狗定时器 (WDT) 是一个独立运行的递减计数器，主程序必须周期"喂狗"。如果在设定时间内没有喂狗，WDT 会触发系统复位。这是电赛控制题**最低成本的安全保障**——程序卡死时自动重启，避免小车失控。

### SysConfig 配置

```
1. 点 "ADD" → 搜索 "WDT" → 选 "Watchdog Timer"
2. 配置:
   Clock Source:  LFOSC (32.768kHz, 低功耗独立时钟)
   Period:        1 second (1 秒窗口)
   Window:        No window (简单模式)
3. 保存
```

### 基础代码

```c
#include "ti_msp_dl_config.h"

int main(void)
{
    SYSCFG_DL_init();

    /* WDT 使能 (SysConfig 自动生成 DL_WDT_enable) */
    /* ⚠️ 使能后必须按时喂狗, 否则 1 秒后复位 */
    printf("System boot, WDT enabled\r\n");

    while (1)
    {
        /* === 控制循环 === */
        read_sensors();
        pid_control();
        motor_output();

        /* === 喂狗 (必须放在主循环能到达的地方) === */
        DL_WDT_feed(WDT);
        /* 如果上面任何一步卡死 > 1 秒 → 自动复位 */
    }
}
```

### 中断里喂狗 (错误示范)

```c
/* ❌ 危险! 中断里喂狗是假安全 */
void SysTick_Handler(void) {
    DL_WDT_feed(WDT);  // 中断还在跑但主循环卡死了!
}
/* 正确: 必须在主循环喂狗, 中断只负责置标志 */
```

### 关键 API

| 函数 | 作用 |
|------|------|
| `DL_WDT_setPeriod(WDT, period)` | 设置超时周期 |
| `DL_WDT_enable(WDT)` | 使能看门狗 |
| `DL_WDT_feed(WDT)` | 清零计数器 (喂狗) |
| `DL_WDT_getCount(WDT)` | 读当前计数值 (调试用) |

### 周期选项

| 宏 | 大致时间 | 适用场景 |
|----|---------|----------|
| `DL_WDT_PERIOD_100MS` | 100ms | 高速控制, 喂狗频繁 |
| `DL_WDT_PERIOD_500MS` | 500ms | 一般控制 |
| `DL_WDT_PERIOD_1S` | **1 秒** | 推荐, 容忍短暂阻塞 |
| `DL_WDT_PERIOD_2S` | 2 秒 | 宽松, 适合慢速循环 |
| `DL_WDT_PERIOD_5S` | 5 秒 | 宽松, 适合 OLED 刷新 |

### 复位原因检测

```c
/* 启动时检查是否 WDT 触发过复位 */
if (DL_SYSCTL_getResetCause() & DL_SYSCTL_RESET_CAUSE_WDT) {
    printf("上次复位原因: 看门狗超时!\r\n");
    // 可能是程序卡死, 记录错误方便排查
    DL_SYSCTL_clearResetCause(DL_SYSCTL_RESET_CAUSE_WDT);
}
```

---

## 十一、Flash 参数存储 (校准值持久化)

### 概述

TCRT5000 黑白阈值、PID 参数、编码器偏移这些值在断电后会丢失。MSPM0G3507 的 Flash 可以在**运行时**写入指定扇区实现持久化存储。

### Flash 布局

```
MSPM0G3507 Flash: 128KB
┌─────────────────────────────┐ 0x0000_0000
│  用户程序 (~100KB)           │
│  .text, .rodata, .data ...  │
├─────────────────────────────┤ 0x0001_9000  ← 程序结束地址
│  空闲空间                     │
├─────────────────────────────┤ 0x0001_F000  ← 用来存参数
│  参数存储扇区 (4KB)           │  最后一个扇区
└─────────────────────────────┘ 0x0002_0000
```

### 参数结构体 + 读写代码

```c
#include "ti_msp_dl_config.h"

/* 参数存储的 Flash 起始地址 (最后一个扇区, 避开程序区) */
#define PARAM_FLASH_ADDR   0x0001F000
#define PARAM_FLASH_SIZE   2048  /* 实际使用 2KB */

/* 参数结构体 (对齐到 4 字节) */
typedef struct __attribute__((aligned(4))) {
    uint32_t magic;           /* 魔数: 0xAA55_EE11 表示数据有效 */
    uint32_t version;         /* 版本号, 结构体改了就 +1 */
    /* ---- TCRT5000 校准 ---- */
    uint16_t tcrt_min[5];     /* 白底最小值 */
    uint16_t tcrt_max[5];     /* 黑线最大值 */
    /* ---- PID 参数 ---- */
    float    pid_kp;
    float    pid_ki;
    float    pid_kd;
    float    base_speed;
    /* ---- 编码器偏移 ---- */
    int32_t  encoder_offset;
    /* ---- 校验 ---- */
    uint32_t crc32;           /* 整个结构体的 CRC32 */
} PersistentParams;

static PersistentParams g_params;

/* ---- Flash 扇区擦除 ---- */
void flash_erase_params(void) {
    DL_FlashCTL_unprotectSector(
        DL_FLASHCTL_MAIN_SECTOR_31,  /* 最后一个扇区 */
        DL_FLASHCTL_READ_WRITE_PERMISSION);
    DL_FlashCTL_eraseSector(DL_FLASHCTL_MAIN_SECTOR_31);
}

/* ---- 写入参数到 Flash ---- */
void flash_save_params(void) {
    /* 计算 CRC32 (简化校验和) */
    uint32_t checksum = 0;
    uint32_t *p = (uint32_t *)&g_params;
    for (int i = 0; i < sizeof(g_params) / 4 - 1; i++) {
        checksum ^= p[i];
    }
    g_params.crc32 = checksum;

    flash_erase_params();

    /* ⚠️ 按 4 字节对齐写入 (MSPM0 Flash 编程要求) */
    DL_FlashCTL_programMemory(PARAM_FLASH_ADDR,
                              (uint32_t *)&g_params,
                              sizeof(g_params));
}

/* ---- 从 Flash 读取参数 ---- */
bool flash_load_params(void) {
    PersistentParams *stored = (PersistentParams *)PARAM_FLASH_ADDR;

    /* 检查魔数 */
    if (stored->magic != 0xAA55EE11) {
        printf("Flash 参数未初始化, 使用默认值\r\n");
        return false;
    }

    /* 检查 CRC */
    uint32_t checksum = 0;
    uint32_t *p = (uint32_t *)stored;
    for (int i = 0; i < sizeof(PersistentParams) / 4 - 1; i++) {
        checksum ^= p[i];
    }
    if (checksum != stored->crc32) {
        printf("Flash 参数 CRC 错误, 使用默认值\r\n");
        return false;
    }

    /* 加载 */
    memcpy(&g_params, stored, sizeof(PersistentParams));
    printf("Flash 参数加载成功\r\n");
    return true;
}

/* ---- 初始化默认参数 ---- */
void params_init_default(void) {
    g_params.magic   = 0xAA55EE11;
    g_params.version = 1;
    memset(g_params.tcrt_min, 0, sizeof(g_params.tcrt_min));
    memset(g_params.tcrt_max, 0, sizeof(g_params.tcrt_max));
    g_params.pid_kp  = 2.0f;
    g_params.pid_ki  = 0.1f;
    g_params.pid_kd  = 0.05f;
    g_params.base_speed = 0.5f;
    g_params.encoder_offset = 0;
}

/* ---- 主程序使用 ---- */
int main(void)
{
    SYSCFG_DL_init();
    __enable_irq();

    params_init_default();
    /* 尝试从 Flash 加载, 成功则覆盖默认值 */
    flash_load_params();

    printf("PID: Kp=%.2f Ki=%.3f Kd=%.3f\r\n",
           g_params.pid_kp, g_params.pid_ki, g_params.pid_kd);

    /* 运行时修改参数后保存 */
    g_params.pid_kp = 3.5f;   /* 调好参数 */
    flash_save_params();       /* 永久保存 */
    printf("参数已保存到 Flash\r\n");
    /* 下次上电自动加载 */
}
```

### 关键 API

| 函数 | 作用 |
|------|------|
| `DL_FlashCTL_unprotectSector(sector, perm)` | 解锁扇区写保护 |
| `DL_FlashCTL_eraseSector(sector)` | 擦除扇区 (写前必须擦) |
| `DL_FlashCTL_programMemory(addr, data, len)` | 写入 Flash (4 字节对齐) |

### 注意事项

| 问题 | 解决 |
|------|------|
| **Flash 写前必须擦除** | 整个扇区一次擦除 (~20ms), 所以先读到 RAM 改完再回写 |
| **4 字节对齐** | 写入地址和数据长度必须是 4 的倍数 |
| **擦写寿命** | ~10 万次, 不要每帧都写 (只在"保存"按钮按下时写) |
| **写期间不能中断** | Flash 写操作时 CPU 暂停, 不要在 PWM 中断里写 |
| **扇区选择** | 用最后一个扇区, 确保不覆盖程序代码 |
## 十二、中文取模教程

### 工具

推荐 **PCtoLCD2002** (免费, 百度搜索下载)

### 取模设置

```
模式: 字符模式
选项 → 字模选项:
  点阵格式:  阴码 (1=点亮, 0=熄灭)
  取模走向:  纵向取模, 字节倒序
  字体大小:  16×16 (每个汉字 32 字节)
  输出格式:  C51 格式
```

### 操作步骤

```
1. 输入汉字, 如 "电赛"
2. 设置字体大小 16×16
3. 点击 "生成字模"
4. 复制生成的数组
```

### 天猛星 OLED 汉字显示代码

```c
/* PCtoLCD2002 生成: 16×16 纵向列行式, 阴码 */
typedef struct {
    uint8_t code[32];  /* 16×16 / 8 = 32 字节 */
} Hanzi16;

static const Hanzi16 hanzi_e = {  /* 电 */
    {0x00,0x01,0x00,0x01,0x00,0x01,0xF8,0x3F,
     0x08,0x21,0x08,0x21,0x08,0x21,0xF8,0x3F,
     0x08,0x21,0x08,0x21,0x08,0x21,0xF8,0x3F,
     0x00,0x01,0x00,0x01,0x00,0x01,0x00,0x01}
};

void oled_draw_hanzi16(uint8_t x, uint8_t y, const Hanzi16 *hz) {
    for (uint8_t col = 0; col < 16; col++) {
        uint16_t data = hz->code[col*2] | (hz->code[col*2+1] << 8);
        for (uint8_t row = 0; row < 16; row++) {
            oled_draw_pixel(x + col, y + row, (data >> row) & 1);
        }
    }
}

void oled_puts_cn(uint8_t x, uint8_t y, const char *str) {
    /* 查表法: 根据字符串查找对应的 Hanzi16 结构体 */
    /* 需要预建汉字-字模映射表 */
    while (*str) {
        if (*str & 0x80) {  /* 中文 (UTF-8 高位) */
            /* GB2312 区位码查表, 此处简化为直接跳过 */
            str += 3;  /* UTF-8 中文 3 字节 */
            x += 16;
        } else {  /* ASCII */
            oled_putchar(x, y, *str++);
            x += 6;
        }
        if (x > OLED_WIDTH - 16) { x = 0; y += 16; }
    }
}
```

---

## 十三、烧录与调试工具链

### 三种烧录方式

| 方式 | 工具 | 接口 | 速度 | 推荐度 | 文件格式 |
|------|------|------|------|--------|----------|
| **XDS110** | TI XDS110 + UniFlash/CCS | SWD (PA19/PA20) | 快 | ⭐⭐⭐ 强烈推荐 | .out |
| **J-Link** | SEGGER J-Link + UniFlash | SWD (PA19/PA20) | 快 | ⭐⭐⭐ | .out |
| **串口(BSL)** | UniFlash + 板载CH340 | PA0(TX)/PA1(RX) | 慢 | ⚠️ 不稳定！程序可能不运行 | .txt/.hex |

**⚠️ BSL 串口烧录已知问题：**
- 烧录成功但程序可能不执行（多次 CRC 验证失败，即使冷启动也无法运行）
- PA0/PA1 开漏导致 115200 通信不可靠
- **强烈建议使用 XDS110，CLI 一键烧录：** `dslite flash --config=xxx.ccxml firmware.out`

### J-Link 烧录步骤

```
1. 用杜邦线连接:  J-Link        天猛星
                  SWDIO (TMS) → PA19
                  SWCLK       → PA20
                  3.3V        → 3.3V
                  GND         → GND
2. 打开 UniFlash → Device: MSPM0G3507
3. 选择 Connection: SEGGER J-Link
4. Load Image → 选择 .out 文件
5. 勾选 "Run Target After Program Load"
6. 点击 "Load Image" 烧录
```

### XDS110 烧录步骤

```
1. 杜邦线连接:    XDS110       天猛星
                  TMS/SWDIO  → PA19
                  TCK/SWCLK  → PA20
                  3V3        → 3.3V
                  GND        → GND
2. UniFlash → Connection: Texas Instruments XDS110 USB Debug Probe
3. Load Image → 烧录
4. 无需按 BSL/RST 键
```

### 串口(BSL)烧录（仅紧急备用）

```
1. Type-C 连接电脑 (CH340 串口)
2. 按住 BSL 键不放
3. 按一下 RST 键，1秒后松 RST
4. 10秒内 UniFlash 点击 "Load Image"
5. ⚠️ 即使报红字 "Image Loading failed..." 也是正常
   只要绿色进度条到100%就是烧录成功
```

### CCS 生成 .txt 文件 (串口烧录用)

CCS 默认只生成 `.out`，需在 **Project → Properties → Build → Steps → Post-build steps** 添加：

```
${CCS_INSTALL_ROOT}/tools/compiler/ti-cgt-armllvm_4.0.2.LTS/bin/tiarmhex --ti_txt ${ProjName}.out
```

---

### printf 重定向到串口 (CCS)

```c
#include "ti_msp_dl_config.h"
#include <stdio.h>
#include <string.h>

/* fputc 重定向到 UART0 (PA0=TX) */
int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

/* 完整重定向: 如需 fputs/puts 也重定向 */
int fputs(const char *s, FILE *f) {
    uint16_t len = strlen(s);
    for (uint16_t i = 0; i < len; i++)
        DL_UART_transmitDataBlocking(UART0, (uint8_t)s[i]);
    return len;
}

int puts(const char *s) {
    int n = fputs(s, stdout);
    fputs("\n", stdout);
    return n + 1;
}
```

**SysConfig UART 配置要点：**
- UART0: PA0=TX, PA1=RX, 115200-8-N-1
- **建议关闭 TX FIFO** (TX FIFO Size = 0)，否则短字符串可能不发送
- 或发送后调用 `DL_UART_flushTXFIFO(UART0)`

---

### VOFA+ PID 实时调参

> VOFA+ FireWater/JustFloat 协议代码和操作步骤见 [第六章：调试与调参工具](#六调试与调参工具)。此处不重复。

---

### Python 串口抓取脚本

```python
"""serial_capture.py — 抓取 PID 调试数据的 Python 脚本"""
import serial
import csv
import sys
from datetime import datetime

# === 配置 ===
PORT = 'COM3'       # ⚠️ 需根据实际串口号修改, 不确定时运行后看提示
BAUD = 115200
CSV_PATH = 'pid_data.csv'

def list_ports():
    """列出可用串口"""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("未找到串口! 请检查 USB 连接")
        return
    print("可用串口:")
    for p in ports:
        print(f"  {p.device} — {p.description}")

def capture():
    if PORT == 'COM3':
        list_ports()
        print(f"\n请在脚本中修改 PORT 变量为实际串口号")
    
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"已连接 {PORT}, 开始抓取... (Ctrl+C 停止)")
    
    with open(CSV_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'ch0', 'ch1', 'ch2', 'ch3'])
        
        try:
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        vals = [float(v.strip()) for v in line.split(',') if v.strip()]
                        ts = datetime.now().isoformat()
                        writer.writerow([ts] + vals)
                        f.flush()  # 实时写入磁盘
                        print(f"[{ts}] {vals}")
                    except ValueError:
                        pass  # 非数据行跳过
        except KeyboardInterrupt:
            print(f"\n已保存到 {CSV_PATH}")
        finally:
            ser.close()

if __name__ == '__main__':
    capture()
```

---

### 串口日志调试

**串口助手确认串口号：**
```
1. 设备管理器 → 端口(COM和LPT) → 找 "USB-SERIAL CH340"
2. 记下 COM 号 (如 COM5)
3. 串口助手选对应 COM, 115200-8-N-1, 打开
4. 按天猛星 RST, 应能看到 printf 输出
```

**CCS 调试时查看串口输出：**
- CCS 内建的 Terminal 视图可直接看 UART 输出
- 或另开 VOFA+/串口助手查看

**常见串口问题：**

| 问题 | 解决 |
|------|------|
| 串口打不开 | 检查是否被 CCS/其他程序占用, 关掉CCS Terminal |
| 数据乱码 | 检查波特率是否匹配 (115200) |
| printf 无输出 | 检查 fputc 重定向, 确认 UART0 在 SysConfig 中已配置 |
| 短字符串丢失 | 关闭 UART TX FIFO 或发送后 flush |



---

## 十四、端到端完整工程示例

### 工程配置 (SysConfig)

```
CCS Project: mspm0g_test
MCU: MSPM0G3507
SYSCTL: SYSOSC 32MHz (默认)
添加外设:
  ├── UART0:  PA0=TX, PA1=RX, 115200
  ├── GPIO:   PA7=Output(LED), PA14=Input+PullUp(按键)
  └── I2C0:   PA28=SDA, PA31=SCL, 400kHz
```

### main.c (完整可编译)

```c
/**
 * 天猛星 MSPM0G3507 拓展板测试工程
 * 功能: UART printf + PB27 LED + PA26按键 + I2C0/I2C1 扫描
 * 引脚: PA0/1=UART0, PB27=LED, PA26=K1, PA28/31=I2C0(OLED), PA10/11=I2C1(MPU6050)
 */
#include "ti_msp_dl_config.h"
#include <stdio.h>

/* ---- printf 重定向到 UART0 ---- */
int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

/* ---- SysTick 1ms (时钟=32MHz) ---- */
volatile uint32_t g_ms_ticks = 0;
void SysTick_Handler(void) { g_ms_ticks++; }
void delay_ms(uint32_t ms) {
    uint32_t start = g_ms_ticks;
    while ((g_ms_ticks - start) < ms) { __WFI(); }
}

/* ---- I2C 扫描 ---- */
void i2c_scan(DL_I2C_TypeDef *i2c) {
    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        DL_I2C_fillControllerTXFIFO(i2c, &addr, 1);
        DL_I2C_startControllerTransfer(i2c, DL_I2C_CONTROLLER_DIRECTION_TX, 1);
        while (DL_I2C_getControllerStatus(i2c, DL_I2C_CONTROLLER_STATUS_BUSY));
        if (DL_I2C_getControllerStatus(i2c, DL_I2C_CONTROLLER_STATUS_ADDR_ACK)) {
            printf("0x%02X ", addr);  // 设备存在
        }
        // STOP 由 startControllerTransfer 自动生成
    }
    printf("\r\n");
}

/* ---- 主函数 ---- */
int main(void)
{
    SYSCFG_DL_init();
    SysTick_Config(SystemCoreClock / 1000);  /* 使用实际 MCLK 频率 */
    __enable_irq();

    printf("\r\n========================================\r\n");
    printf("  天猛星 MSPM0G3507 拓展板测试\r\n");
    printf("  UART0: PA0/PA1, LED: PB27, KEY: PA26\r\n");
    printf("  I2C0(OLED): PA28/PA31, I2C1(MPU6050): PA10/PA11\r\n");
    printf("  MCLK: %lu Hz\r\n", SystemCoreClock);
    printf("========================================\r\n\r\n");

    /* I2C 扫描 (I2C0=OLED 0x3C, I2C1=MPU6050 0x68) */
    printf("I2C0: "); i2c_scan(I2C0);
    printf("I2C1: "); i2c_scan(I2C1);

    uint32_t led_tick = 0, scan_tick = 0;
    uint8_t led_state = 0;

    while (1)
    {
        /* 500ms LED 闪烁 (PB27) */
        if (g_ms_ticks - led_tick >= 500) {
            led_tick = g_ms_ticks;
            led_state = !led_state;
            if (led_state) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_27);
            else           DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_27);
            printf("[%6lu] LED=%s\r\n", g_ms_ticks, led_state ? "ON" : "OFF");
        }

        /* 按键检测 (K1=PA26, 按下=低电平) */
        if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0) {
            delay_ms(20);
            if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0) {
                printf("[%6lu] K1 PRESSED!\r\n", g_ms_ticks);
                while (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0);
            }
        }

        /* 每 5 秒重新扫描 I2C */
        if (g_ms_ticks - scan_tick >= 5000) {
            scan_tick = g_ms_ticks;
            printf("I2C0: "); i2c_scan(I2C0);
            printf("I2C1: "); i2c_scan(I2C1);
        }
    }
}
```

---

## 十五、K230 CanMV API 速查

K230 是嘉楠科技 RISC-V AI 芯片，CanMV 是其 MicroPython 移植。仅软定时器可用，硬件 Timer 0-5 暂不可用。

### --- system ---

```python
import machine, gc, uos, time, utime, uhashlib, ucryptolib

machine.reset()          # SoC 复位
machine.temperature()    # 芯片温度 (float)
machine.chipid()         # 芯片 ID → bytearray(32)
machine.mem_copy(dst, src, size)

gc.enable(); gc.disable(); gc.collect()
gc.mem_alloc()                      # 已分配堆内存 (byte)
gc.mem_free()                        # 可用堆内存 (byte)
gc.sys_total()                       # 系统总内存
gc.sys_heap() / sys_page() / sys_mmz()  # 返回 (total, free, used) 元组

utime.sleep(seconds); utime.sleep_ms(ms); utime.sleep_us(us)
utime.ticks_ms(); utime.ticks_us(); utime.ticks_diff(t1, t2)
c = utime.clock()         # 创建时钟对象
c.tick()                  # 记录当前时间
c.fps()                   # 返回帧率
c.reset(); c.avg()        # 重置 / 平均耗时

uhashlib.sha256([data])   # 硬件加速 SHA256
obj.update(data)          # 追加数据
obj.digest()              # 获取哈希 → bytes (只能调用一次！)
# hexdigest 未实现，用 binascii.hexlify(hash.digest()) 代替

ucryptolib.aes(key, mode=0, IV, AAD)   # AES-GCM 硬件加速
ucryptolib.sm4(key, mode, IV)          # SM4-ECB/CBC
cipher.encrypt(pt); cipher.decrypt(ct)
```

### --- FPIOA (引脚复用) ---

```python
# ⚠️ K230 所有外设需先通过 FPIOA 配置引脚功能，再使用！
from machine import FPIOA
fpioa = FPIOA()
# 将 GPIO11 配置为 UART2_TXD
fpioa.set_function(11, FPIOA.UART2_TXD)
# 将 GPIO12 配置为 UART2_RXD
fpioa.set_function(12, FPIOA.UART2_RXD)
# 查询引脚当前功能
fpioa.get_pin_func(11)
# 查询功能当前所在引脚
fpioa.get_pin_num(FPIOA.UART2_TXD)
# 打印所有引脚配置信息
fpioa.help()
# 每个引脚同一时刻只能激活一种功能
```

### --- GPIO / ADC / PWM ---

```python
from machine import Pin, ADC, PWM, FPIOA

fpioa = FPIOA()
# 先配置FPIOA，再使用GPIO
fpioa.set_function(pin_number, FPIOA.GPIOx)

# GPIO: 64 个引脚 [0~63], 3.3V电平
pin = Pin(2, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
pin.value(1); pin.value(0)
pin.on(); pin.off(); pin.high(); pin.low()
# drive: 0~15, 默认7, 最大15(除BOOT0/1)
# Pin.irq() 自 2025年5月固件起支持; 老固件用 GPIO.irq()(仅GPIOHS引脚)

# 板载RGB灯: 共阳, GPIO62=R, GPIO20=G, GPIO63=B (低电平亮)
# 板载按键: GPIO53, 按下=高电平, 需配置内部下拉

# ⚠️ ADC: 仅 FPC 排线座引出, 4通道, 最高 1.8V 输入!
# 普通排针上无 ADC 功能, 超1.8V会烧毁芯片
adc = ADC(0)
adc.read_u16()     # 0~4095
adc.read_uv()      # 0~1800000 uV

# PWM: 6 通道 [0~5], ch0-2 同频率, ch3-5 同频率
pwm = PWM(0, freq=1000, duty=50, enable=True)
pwm.freq(2000); pwm.duty(30)
pwm.enable(True/False); pwm.deinit()
```

### --- UART / I2C / SPI ---

```python
from machine import UART, I2C, I2C_Slave, SPI

# UART: UART2(GPIO11=TXD,GPIO12=RXD) 和 UART3(GPIO50=TXD,GPIO51=RXD) 可用
# UART0(GPIO38/39) 被大核RT-Smart占用, UART1不可用
u = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS,
         parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)
u.write(buf); u.read([n]); u.readline(); u.readinto(buf)

# I2C: I2C0(GPIO48=SCL,GPIO49=SDA) I2C1(GPIO40=SCL,GPIO41=SDA)
# ⚠️ 庐山派板载I2C已有内部上拉电阻, 外设不用再加
i2c = I2C(0, freq=100000)
i2c.scan()                      # → [addr, ...]
i2c.readfrom(addr, len, True)   # → bytes
i2c.writeto(addr, buf, True)    # → 发送字节数
i2c.readfrom_mem(addr, memaddr, nbytes, mem_size=8)
i2c.writeto_mem(addr, memaddr, buf, mem_size=8)
i2c.deinit()

# I2C 从机 (需编译时开启)
i2c_s = I2C_Slave(I2C_Slave.list()[0], addr=0x10, mem_size=20)
i2c_s.readfrom_mem(0, n)        # 读主设备写入的数据
i2c_s.writeto_mem(0, data)      # 写数据供主设备读取

# SPI: 3 个模块 [0~2]
spi = SPI(0, baudrate=5000000, polarity=0, phase=0, bits=8)
spi.write(buf); spi.read(nbytes); spi.readinto(buf)
spi.write_readinto(wbuf, rbuf)  # 全双工
spi.deinit()
```

### --- GPIO 中断 (Pin.irq / GPIO.irq) ---

```python
# 方法1: Pin.irq() — 2025年5月+固件支持
from machine import Pin
pin = Pin(53, Pin.IN, Pin.PULL_DOWN)
pin.irq(handler=lambda p: print("pressed"), trigger=Pin.IRQ_RISING)

# 方法2: GPIO.irq() — 老固件兼容, 仅GPIOHS引脚
from machine import GPIO
# GPIOHS 引脚号 0~31 对应可中断引脚(非物理引脚号)
GPIO.irq(0, GPIO.IRQ_RISING, lambda n: print(f"GPIOHS{n}"), GPIO.WAKEUP_NOT_SUPPORT, 7)
# TRIGGER: GPIO.IRQ_RISING / IRQ_FALLING / IRQ_BOTH
```

### --- Timer / RTC / Display ---

```python
from machine import Timer, RTC

# ⚠️ 硬件 Timer [0-5] 暂不可用，只用软件定时器
tim = Timer(-1)  # -1 = 软件定时器
tim.init(period=100, mode=Timer.ONE_SHOT, callback=lambda t: print(1))
tim.init(period=1000, mode=Timer.PERIODIC, callback=lambda t: print(2))
tim.deinit()

rtc = RTC()
rtc.init((2024, 2, 28, 2, 23, 59, 0, 0))
rtc.datetime()  # → (year, mon, day, wday, hour, min, sec, microsec)

# LCD (SPI 接口)
from machine import SPI_LCD
lcd = SPI_LCD(spi, pin_dc, pin_cs, pin_rst, bl=pin_bl, type=SPI_LCD.ST7789)
lcd.configure(320, 240, hmirror=False, vflip=True, bgr=False)
img = lcd.init()               # → Image 对象 (显存)
img.clear()
img.draw_string_advanced(0, 0, 32, "你好", color=(255, 0, 0))
lcd.show()                     # 刷新到屏幕
lcd.fill(color); lcd.pixel(x, y, color)
lcd.light(50)                  # 背光 0~100
```

### ⚠️ 画面分辨率 — 最高优先级

电赛视觉第一要务是**帧率**，不是分辨率。分辨率每提高一档，像素数翻倍，find_rects/find_blobs 耗时倍增。

| 分辨率 | 像素 | 纯采集帧率 | 加检测后帧率 | 推荐用途 |
|--------|------|-----------|-------------|----------|
| **QVGA (320×240)** | 7.7万 | ~90fps | **50~70fps** | 光电追踪 / 巡线 / **默认首选** |
| VGA (640×480) | 30.7万 | ~60fps | 20~30fps | 靶心圆检测 / 精度要求高 |
| HD (1280×720) | 92万 | ~30fps | 5~10fps | YOLO 推理输入 |

**铁律**：
1. **默认 320×240**，除非精度不够再升
2. **严禁高斯模糊等重滤镜**在低帧率下叠加 — 先降分辨率再考虑滤镜
3. Display 虚拟屏尺寸**独立于采集分辨率**，可以用 640×480 显示但只采集 320×240
4. 25E 靶面检测 320×240 完全足够：50cm 靶面 / 320px = 1.56mm/px

### ⚠️ K230 代码生成铁律 (防幻觉)

**生成任何 K230 代码前，必须先对照下方「已验证模板」逐行检查：**
1. 导入必须是 `from media.sensor import *` 等星号导入，禁止 `import sensor`
2. Sensor 构造不传 `id` 参数
3. 初始化顺序严格: set_framesize → set_pixformat → Display.init → MediaManager.init → sensor.run
4. 主循环首行必须是 `os.exitpoint()`
5. 抓帧必须是 `sensor.snapshot(chn=CAM_CHN_ID_0)`
6. 禁止编造不存在的 API (如 `sensor.reset()` 不存在，正确是 `sensor = Sensor(...); sensor.reset()`)

### ✅ K230 已验证代码模板

以下模板在 GC2093 + QVGA + A4黑框+红色靶心场景下**实测通过**。**所有后续 K230 代码必须以此模板为蓝本扩展。**

```python
"""
K230 代码模板 (已验证) — GC2093 QVGA A4黑框+红色靶心
所有 K230 代码必须基于此模板, 禁止 AI 幻觉生成
"""
from media.sensor import *
from media.display import *
from media.media import *
import time, os, gc

# ===== 一、初始化 (顺序不可变) =====
sensor = Sensor(width=1920, height=1080)     # 不传 id
sensor.reset()
sensor.set_framesize(width=320, height=240)   # 先尺寸(QVGA高帧率)
sensor.set_pixformat(Sensor.RGB565)            # 后格式
sensor.set_hmirror(False)
sensor.set_vflip(False)
Display.init(Display.VIRT, width=640, height=480, to_ide=True)
MediaManager.init()
sensor.run()

# ===== 二、阈值 (现场 IDE 阈值编辑器校准) =====
TAPE_GRAY  = (0, 109)
RED_TARGET = [(52,100,24,127,-49,41), (29,73,19,127,-57,89)]

# ===== 三、检测变量 =====
a4_corners = None; a4_ok = False; a4_stable = 0; a4_last = None
target_ok = False; target_cx = 0; target_cy = 0
clock = time.clock(); fc = 0
IW, IH = 320, 240

print("启动...")

# ===== 四、过滤函数 =====
def a4_filter_valid(rects):
    good = []
    for r in rects:
        w, h = r.w(), r.h()
        if w <= 0 or h <= 0: continue
        ratio = max(w, h) / min(w, h)
        area = w * h
        if 1.15 < ratio < 1.80 and IW*IH*0.03 < area < IW*IH*0.85:
            good.append(r)
    return good

def corners_near(c1, c2, d=15):
    if c1 is None or c2 is None: return False
    for p, q in zip(c1, c2):
        if abs(p[0]-q[0]) > d or abs(p[1]-q[1]) > d: return False
    return True

# ===== 五、主循环 =====
try:
    while True:
        os.exitpoint()  # 必须! IDE中断
        clock.tick(); fc += 1
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # --- A4检测 ---
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([TAPE_GRAY])
        bin_img.open(1)
        rects = a4_filter_valid(bin_img.find_rects(threshold=10000))
        if rects: ...
        # (业务逻辑在此扩展)

        Display.show_image(img)
        if fc % 300 == 0: gc.collect()

except KeyboardInterrupt: print("stop")
except BaseException as e: print(f"err: {e}")
finally:
    sensor.stop(); Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP); time.sleep_ms(100)
    MediaManager.deinit()
```

### ✅ K230 OLED SSD1306 已验证驱动

以下代码在 K230 + SSD1306 128×64 I2C 上实测通过。**逐页写入模式防止水平寻址丢字节导致的画面平移。**

```python
# ===== OLED SSD1306 I2C 驱动 (已验证) =====
from machine import I2C

OLED_ADDR = 0x3C
OLED_W = 128; OLED_H = 64; OLED_PAGES = OLED_H // 8
oled_fb = bytearray(OLED_W * OLED_PAGES)
i2c = I2C(0, freq=400000)  # I2C0 与GC2093共用, I2C1需FPIOA配置

def oled_cmd(c):
    """写命令, 带重试"""
    for _ in range(3):
        try:
            i2c.writeto(OLED_ADDR, bytearray([0x00, c]))
            return
        except OSError:
            time.sleep_us(100)

def oled_data(data):
    """写数据, 64字节小包 + 包间延时 — 与GC2093共享I2C0不冲突"""
    for i in range(0, len(data), 64):
        chunk = data[i:i+64]
        for _ in range(3):
            try:
                i2c.writeto(OLED_ADDR, bytearray([0x40]) + chunk)
                break
            except OSError:
                time.sleep_us(200)
        time.sleep_us(50)

def oled_init():
    for c in bytes([0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0x00,0x40,
                     0x8D,0x14,0x20,0x00,0xA1,0xC8,0xDA,0x12,
                     0x81,0xCF,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF]):
        oled_cmd(c)

def oled_refresh():
    """逐页写入 — 每页重置列指针, 防I2C丢字节导致画面平移"""
    for page in range(OLED_PAGES):
        oled_cmd(0xB0 | page)    # 页地址 0xB0~0xB7
        oled_cmd(0x00)           # 列低4位=0
        oled_cmd(0x10)           # 列高4位=0
        page_data = oled_fb[page*OLED_W : (page+1)*OLED_W]
        oled_data(page_data)

def oled_cls():
    for i in range(len(oled_fb)): oled_fb[i] = 0

def oled_px(x, y, c):
    if 0 <= x < OLED_W and 0 <= y < OLED_H:
        idx = x + (y//8)*OLED_W
        if c: oled_fb[idx] |= (1 << (y&7))
        else:  oled_fb[idx] &= ~(1 << (y&7))

# 6x8 ASCII 字模 (0x20~0x7E, 每字符6字节纵向)
_F6 = [b'\x00\x00\x00\x00\x00\x00',b'\x00\x00\x5f\x00\x00\x00', ...]  # 完整字模见工程文件

def oled_ch(x, y, ch):
    if ch < 0x20 or ch > 0x7E: return
    g = _F6[ch - 0x20]
    for col in range(6):
        d = g[col]
        for row in range(8):
            oled_px(x+col, y+row, (d>>row)&1)

def oled_str(x, y, s):
    cx, cy = x, y
    for c in s:
        if c == '\n': cx = x; cy += 9; continue
        if cy >= OLED_H: return
        oled_ch(cx, cy, ord(c))
        cx += 6
        if cx > OLED_W - 6: cx = x; cy += 9

# 主循环中调用 (每20帧刷新, 加延时等I2C释放)
# if fc % 20 == 0:
#     time.sleep_us(500)
#     oled_cls()
#     oled_str(0, 0, "Hello K230")
#     oled_refresh()
```

**关键坑:**
1. **必须逐页写入** (0xB0+page), 不能用水平寻址 (0x21) — 后者I2C丢字节会导致整屏平移
2. **64字节小包 + 50μs包间延时** — 与 GC2093 共享 I2C0 时不阻塞
3. **写入前延时 500μs** — 等 camera I2C 释放
4. **每 20 帧刷新** (~0.3s) — 降低 I2C 占用, OLED 保持稳定显示

### --- Sensor (摄像头) ---

```python
# ⚠️ 必须用星号导入, 否则 CAM_CHN_ID_0 不可用!
from media.sensor import *
from media.display import *
from media.media import *
import os

# GC2093: 1920×1080, OV5647: 2592×1944. 不要传 id=0 参数!
sensor = Sensor(width=1920, height=1080)
sensor.reset()
# 电赛默认 QVGA 320×240 → 高帧率优先!
# 需要精度时改为 width=640, height=480
sensor.set_framesize(width=320, height=240)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

# Display 可以独立于采集分辨率, 640×480 显示更清晰
Display.init(Display.VIRT, width=640, height=480, to_ide=True)

# ⚠️ MediaManager.init() 必须在 sensor.run() 之前!
MediaManager.init()
sensor.run()

# 主循环中必须 os.exitpoint() 允许 IDE 中断
while True:
    os.exitpoint()
    img = sensor.snapshot(chn=CAM_CHN_ID_0)   # 捕获一帧 → Image
    Display.show_image(img)                    # 推送到 IDE (自动缩放)

# 退出清理
sensor.stop()
Display.deinit()
os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
time.sleep_ms(100)
MediaManager.deinit()

# 支持传感器: OV5647(2592×1944@10fps), GC2093(1920×1080@60fps), IMX335
# 像素格式: RGB565, RGB888, YUV420SP, GRAYSCALE
# 关键坑:
# 1. 不要传 id=0 参数给 Sensor(), 否则 "Can not found sensor on 0"
# 2. 必须 from media.sensor import * 而非 import Sensor, 否则 CAM_CHN_ID_0 未定义
# 3. set_framesize 必须在 set_pixformat 之前
# 4. 初始化顺序: Display.init → MediaManager.init → sensor.run (不可变)
# 5. 主循环中必须调用 os.exitpoint() 否则 IDE 无法 Ctrl+C 停止
# 6. 默认 320×240 高帧率, 不要无谓升分辨率!
```

### --- Display ---

```python
from media.display import Display

# 支持的屏幕: ST7701(800×480), LT9611 HDMI(1920×1080), HX8377(1080×1920), VIRT(IDE调试)
# VIRT: 虚拟显示, 图像回传 CanMV IDE
Display.init(Display.VIRT, width=640, height=480, to_ide=True)
Display.show_image(img, x=0, y=0, layer=LAYER_OSD0)
Display.bind_layer(src=sensor.bind_info(), dstlayer=LAYER_VIDEO1)
Display.deinit()
```

### --- YOLO 推理 ---

```python
from libs.YOLO import YOLOv5, YOLOv8, YOLO11

# task_type: "classify"/"detect"/"segment"
# mode: "image" 或 "video"
yolo = YOLOv5(task_type="detect", mode="image",
    kmodel_path="/data/kmodel.kmodel",
    labels=["apple","banana","orange"],
    rgb888p_size=[1280,720],
    model_input_size=[320,320],
    conf_thresh=0.5, nms_thresh=0.45,
    max_boxes_num=50, debug_mode=0)

yolo.config_preprocess()
res = yolo.run(img_numpy)       # HWC→CHW 格式, ulab.numpy.ndarray
yolo.draw_result(res, img_ori)  # 绘制结果到 Image
yolo.deinit()
# YOLOv8/YOLO11 接口相同，仅类名不同
```

### --- PipeLine (视频流) ---

```python
from libs.PipeLine import PipeLine, ScopedTiming

pl = PipeLine(rgb888p_size=[1280,720], display_size=[1920,1080], display_mode="hdmi")
pl.create()
while True:
    img = pl.get_frame()       # 从 sensor 取一帧
    # ... 推理 ...
    pl.show_image()            # 显示结果
pl.destroy()
```

---

## 十六、K230 API 已知问题

| # | 模块 | 问题 |
|---|------|------|
| 1 | **gc** | 概述 `sys_totoal` 拼写错误 → 应为 `sys_total` |
| 2 | **hashlib** | 返回值文档错误——`sha256()/digest()/update()` 返回值表格写"0成功/非0失败"，实际 `sha256()` 返回对象、`digest()` 返回 bytes、`update()` 返回 None |
| 3 | **ucryptolib** | SM4 的 `mode` 参数未映射——文档只说支持 ECB/CBC，但未说明 `mode=0` 是 ECB 还是 CBC（示例中 `mode=1` 是 CBC） |
| 4 | **Timer** | **硬件定时器 [0-5] 暂不可用**，仅 `Timer(-1)` 软件定时器可用。多路定时需求需自行用 `ticks_ms` 实现 |
| 5 | **I2C Slave** | `I2C_Slave.list()` 返回设备 ID 列表，但 ID 含义未说明。需从示例代码反推用法 |
| 6 | **hashlib** | `hexdigest()` 方法未实现，需用 `binascii.hexlify(hash.digest())` 替代 |
| 7 | **Sensor** | 说明"同时使用多个传感器时，仅需其中一个执行 run"，但 stop 需每个都调用——容易遗漏 |
| 8 | **Display** | `bind_layer()` 必须在 `init()` 之前调用，顺序要求容易出错 |
| 9 | **uctypes** | 位域定义语法 `offset \| type \| lsbit<<BF_POS \| bitsize<<BF_LEN` 极易写错，无误用保护 |
| 10 | **Pin 中断** | 老固件(≤2025.4)不支持 Pin.irq()，**2025年5月+固件**已支持。老版本可用 `GPIO.irq()`(仅GPIOHS引脚)替代 |
| 11 | **ADC 电压** | ADC 仅支持 **1.8V 输入**，超压会烧毁芯片！ADC 仅在 FPC 排线座引出，普通排针无 ADC |
| 12 | **I2C 上拉** | I2C0/1 板载已有内部上拉电阻，外接 I2C 模块不需再加 |
| 13 | **FPIOA 必配** | 所有外设使用前必须 `fpioa.set_function()`，否则不工作 |
| 14 | **固件分支** | `canmv_k230`(RTOS纯MicroPython)是唯一维护分支，旧 `k230_canmv`(Linux+RTOS双系统)已停止维护 |
| 15 | **UART 中断** | UART 等外设硬件中断未暴露给 MicroPython，仅 GPIO 中断可用 |
| 16 | **OLED I2C0 平移** | OLED 与 GC2093 共享 I2C0 时, 水平寻址模式 (0x21) 丢字节会导致画面左右平移。**解决**: 逐页写入 (0xB0+page), 每页重置列指针。每20帧刷新+500μs延时 |

---

## 十七、K230 + MSPM0G 双芯方案

### 架构总览

```
┌──────────────────────────────────────────────────────┐
│                    K230 (视觉大脑)                     │
│  Sensor → Image → find_blobs/circles/apriltags       │
│  → 坐标计算 → UART 发送                              │
│  功耗: 3W, 独立电池                                   │
└────────────────────┬─────────────────────────────────┘
                     │ UART (115200, 帧协议)
┌────────────────────┴─────────────────────────────────┐
│                   MSPM0G (运动小脑)                    │
│  接收坐标 → PID 控制 → 电机/舵机执行                   │
│  功耗: 0.1W, 独立电池                                 │
└──────────────────────────────────────────────────────┘
```

**双芯硬件连接：**

> **默认方案 (USB拔插)**：K230 GPIO11/12 → M0G PA1/PA0 (竞赛时拔USB)
>
> **拓展板方案 (专用UART3)**：K230 GPIO11/12 → M0G PB3/PB2 (USART3, 不占用CH340)

| K230 (庐山派) | MSPM0G 拓展板 | 方案 | 说明 |
|---------------|--------------|------|------|
| GPIO11 (UART2_TXD) | PB3 (USART3_RX) | 拓展板 | 视觉→控制 |
| GPIO12 (UART2_RXD) | PB2 (USART3_TX) | 拓展板 | 可选ACK |
| GPIO11 (UART2_TXD) | PA1 (UART0_RX) | 默认 | 需拔USB |
| GPIO12 (UART2_RXD) | PA0 (UART0_TX) | 默认 | 需拔USB |
| GND | GND | 通用 | 必须共地 |
| 独立电池 5V | 独立电池 7.4V | 通用 | 供电隔离 |

**⚠️ K230 启动前必须配置 FPIOA：**
```python
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
# 之后才能 uart = UART(UART.UART2, ...)
```

### K230 视觉竞赛速查

```python
# === 红光斑检测 (23年E题核心) ===
# ⚠️ K230 CanMV 标准初始化顺序 (已验证)
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART
import struct, time, os, gc

# FPIOA (UART2)
from machine import FPIOA
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart = UART(UART.UART2, baudrate=115200)

# 摄像头: GC2093=1920×1080, 不要传 id=0
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=640, height=480)  # 先设尺寸
sensor.set_pixformat(Sensor.RGB565)           # 再设格式
Display.init(Display.VIRT, width=640, height=480, to_ide=True)
MediaManager.init()
sensor.run()

# LAB红色阈值: (L_min, L_max, A_min, A_max, B_min, B_max)
# 现场用 IDE 阈值编辑器校准！以下为参考值
RED_THRESHOLD   = [(30, 100, 15, 127, 0, 127)]
GREEN_THRESHOLD = [(30, 100, -128, -15, 0, 127)]

def pixel_to_screen(px, py, img_w=640, img_h=480, screen_w=50, screen_h=50):
    """像素坐标 → 屏幕坐标(cm), 原点屏幕中心"""
    return ((px - img_w/2) * screen_w / img_w,
            (py - img_h/2) * screen_h / img_h)

while True:
    os.exitpoint()  # 允许 IDE Ctrl+C 中断
    img = sensor.snapshot(chn=CAM_CHN_ID_0)
    blobs = img.find_blobs(RED_THRESHOLD, pixels_threshold=5,
                           area_threshold=10, merge=True)
    if blobs:
        b = blobs[0]
        img.draw_cross(b.cx(), b.cy(), color=(0,255,0), size=10)
        sx, sy = pixel_to_screen(b.cx(), b.cy())
        # UART 发给 M0G
        buf = bytearray(10)
        buf[0]=0xA5; buf[1]=0x5A; buf[2]=0x01
        struct.pack_into('<h', buf, 3, int(sx*10))
        struct.pack_into('<h', buf, 5, int(sy*10))
        struct.pack_into('<h', buf, 7, len(blobs))
        buf[9] = sum(buf[:9]) & 0xFF ^ 0xFF
        uart.write(buf)
    gc.collect()
```

### 双芯通信帧协议 (10字节定长)

```
| 0xA5 | 0x5A | CMD | X(2B) | Y(2B) | EXTRA(2B) | CHKSUM |
  帧头   帧头   命令   坐标    坐标    附加数据     校验(=前9B异或)
```

```c
// === M0G 端接收 ===
// CMD定义:
#define CMD_BLOB_POS   0x01  // 光斑坐标, X/Y单位0.1mm
#define CMD_CIRCLE     0x02  // 圆检测, EXTRA=半径(cm*10)
#define CMD_PHASE      0x03  // 画圆相位, EXTRA=0~359度
#define CMD_LOST       0x04  // 目标丢失
#define CMD_STOP       0xFF  // 急停

void handle_vision_frame(uint8_t cmd, int16_t x, int16_t y, int16_t extra) {
    switch (cmd) {
    case CMD_BLOB_POS:
        target_x_cm = x / 10.0f;
        target_y_cm = y / 10.0f;
        break;
    case CMD_CIRCLE:
        target_center_x = x / 10.0f;
        target_center_y = y / 10.0f;
        target_radius   = extra / 10.0f;
        break;
    case CMD_LOST:
        gimbal_scan();  // 扫描搜索
        break;
    }
}
```

### K230 电赛常用 API 快速索引

| 电赛需求 | API 调用 |
|----------|----------|
| 红色光斑位置 | `find_blobs([(30,100,15,127,0,127)])` |
| 靶心红圆 | `find_circles(threshold=2000, r_min=5, r_max=30)` |
| A4 纸黑框 | `find_rects(threshold=10000)` |
| 黑线方向 | `get_regression([(0,100,-128,127,-128,127)])` |
| AprilTag 3D位姿 | `find_apriltags(families=TAG36H11)` |
| 二维码内容 | `find_qrcodes()` |
| 十字路口检测 | `find_line_segments()` + 线段角度差 ~90° |
| YOLO自定义检测 | `YOLOv5(task_type="detect", ...)` |
| 图像二值化 | `binary([(lo,hi)])` |
| 直方图均衡化 | `histeq(adaptive=True)` |
| 光斑轨迹绘制 | `draw_circle()`, `draw_cross()` |
| 镜头校正 | `lens_corr(strength=1.8)` |

### 三道真题 K230+M0G 分工表

**23年 E — 运动目标追踪：**
```
K230:  同时检测红绿两光斑位置 → 计算距离差 → UART发送
M0G红: 开环走预编路径(正方形/A4)
M0G绿: 接收K230坐标 → PID追踪红点
约束:  红绿系统不通信, K230仅作为"裁判"验证
```

**24年 H — 自动行驶小车：**
```
M0G主导: TCRT5000巡线 + 编码器 + PID转向 + 路径规划
K230辅助(可选):
  - get_regression() 检测黑线中线,辅助弯道
  - find_apriltags() 贴在ABCD点,精确定位
  - 摄像头防止完全跑偏
```

**25年 E — 简易瞄准装置：**
```
M0G主导: 巡线 + 位置推算 + 云台瞄准 + 画圆同步
K230增强:
  - find_blobs(RED) 精确检测靶心
  - 每帧验证激光光斑落点
  - 画圆: find_circles() 验证光斑沿6cm圆弧
  - 闭环: K230 → UART偏差 → M0G微调云台
```

### K230 全功能视觉管道

```python
"""vision_pipeline.py — 电赛通用视觉管道, 可切换模式"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART
import struct, time, os, gc

class VisionPipeline:
    def __init__(self, mode="blob_red"):
        self.mode = mode
        # 标准初始化顺序
        self.sensor = Sensor(width=1920, height=1080)
        self.sensor.reset()
        self.sensor.set_framesize(width=640, height=480)
        self.sensor.set_pixformat(Sensor.RGB565)
        Display.init(Display.VIRT, width=640, height=480, to_ide=True)
        MediaManager.init()
        self.sensor.run()
        self.uart = UART(UART.UART2, baudrate=115200)
        self.clock = time.clock()
        self.last_blob = None

    def pixel_to_cm(self, px, py):
        return ((px-160)*50/320, (py-120)*50/240)

    def send(self, cmd, x, y, extra=0):
        buf = bytearray(10)
        buf[0]=0xA5; buf[1]=0x5A; buf[2]=cmd
        struct.pack_into('<h', buf, 3, int(x*10))
        struct.pack_into('<h', buf, 5, int(y*10))
        struct.pack_into('<h', buf, 7, int(extra))
        buf[9] = sum(buf[:9]) & 0xFF ^ 0xFF
        self.uart.write(buf)

    def run_blob_red(self, img):
        blobs = img.find_blobs([(30,100,15,127,0,127)],
                               pixels_threshold=5, merge=True)
        if blobs:
            b = blobs[0]
            img.draw_cross(b.cx(), b.cy(), size=10)
            sx, sy = self.pixel_to_cm(b.cx(), b.cy())
            self.send(0x01, sx, sy, len(blobs))
            self.last_blob = (b.cx(), b.cy())
        else:
            self.send(0x04, 0, 0, 0)  # lost

    def run_circles(self, img):
        circles = img.find_circles(threshold=1800, r_min=5, r_max=35)
        if circles:
            c = circles[0]
            img.draw_circle(c.x(), c.y(), c.r(), color=(255,0,0))
            sx, sy = self.pixel_to_cm(c.x(), c.y())
            self.send(0x02, sx, sy, c.r())

    def run_apriltag(self, img):
        tags = img.find_apriltags(families=image.TAG36H11)
        for t in tags:
            img.draw_rectangle(t.rect())
            self.send(0x02, t.x_translation(), t.y_translation(),
                      int(t.z_translation()))

    def loop(self):
        while True:
            os.exitpoint()
            self.clock.tick()
            img = self.sensor.snapshot(chn=CAM_CHN_ID_0)
            if self.mode == "blob_red":
                self.run_blob_red(img)
            elif self.mode == "circles":
                self.run_circles(img)
            elif self.mode == "apriltag":
                self.run_apriltag(img)
            if self.clock.fps() > 50:
                gc.collect()

# 启动
vp = VisionPipeline(mode="blob_red")
vp.loop()
```

### K230 内存与帧率

| 分辨率 | 帧率 | 用途 |
|--------|------|------|
| QVGA (320x240) | 90fps | 光斑追踪 |
| VGA (640x480) | 30fps | 靶心检测 |
| HD (1280x720) | 30fps | YOLO推理输入 |

### 视觉方案选择决策树

```
需要检测什么?
├─ 红/绿激光光斑 → find_blobs(LAB阈值)
├─ 靶心红色圆环  → find_circles() 或 find_blobs
├─ 黑线方向      → get_regression()
├─ A4纸/矩形标记 → find_rects()
├─ 需要3D位姿    → find_apriltags() (贴AprilTag)
├─ 二维码信息    → find_qrcodes()
├─ 自定义物体    → YOLO训练 + kmodel部署
└─ 光斑轨迹验证  → find_circles() + draw操作

精度: AprilTag > find_circles > find_blobs
速度: find_blobs > find_circles > AprilTag
```

### K230 视觉常见坑

| # | 问题 | 解决 |
|---|------|------|
| 1 | **LAB阈值不准** | 必须在场地灯光下重校准, 自然光/日光灯/LED 差异巨大 |
| 2 | **QVGA够用** | 追踪不需要高分辨率, QVGA 90fps 远好于 VGA 30fps |
| 3 | **GC导致帧间隔抖动** | `if fps>50: gc.collect()`, 避免每帧都 GC |
| 4 | **uart.write阻塞** | 10字节帧协议, 115200波特率 ≈ 1ms发送, 不阻塞 |
| 5 | **blob合并误判** | 设 `merge=True` 时注意 `margin` 参数, 两光斑靠近时可能合并 |
| 6 | **MMZ内存耗尽** | 大Image用 `alloc=image.ALLOC_MMZ`, 用完 `del` |
| 7 | **Sensor未stop** | 多 Sensor 每个都要单独 stop |
| 8 | **Display bind_layer顺序** | 必须先 bind_layer 再 init |

---

## 十八、电赛真题方案



> 以下三题为 2023-2025 年 TI 杯电赛控制类真题，均基于 MSPM0G3507 + K230 双芯架构。


### 18.1 25年电赛 E 题 — 简易自行瞄准装置

### 系统架构

```
                    ┌─────────────┐
        TCRT5000×5  │   MSPM0G    │
        循迹阵列 ───→│   (巡迹+PID) │──→ TB6612 → 电机A(左)
                    │             │──→ TB6612 → 电机B(右)
    EC11编码器×2 ──→│             │
                    │             │──→ 舵机1 (Pan/水平)
        按键/OLED ──┤             │──→ 舵机2 (Tilt/俯仰)
                    └─────────────┘
                           │
                    蓝紫激光笔 (接继电器/MOS)
```

**场地坐标系 (cm)：**
```
A(0,0) ────────── B(100,0)
  │                  │
  │   行驶轨迹(黑线)   │
  │   逆时针方向       │
  │                  │
D(0,100) ──────── C(100,100)

靶面中心: (50, -50)，靶面与AB平行，竖立
靶面高度: ≤50cm
```

### --- TCRT5000 五路循迹 ---

```c
// 5路红外传感器接 ADC0 通道 0~4
#define TCRT_CHANNELS 5
static uint16_t tcrt_min[TCRT_CHANNELS];  // 白底校准值
static uint16_t tcrt_max[TCRT_CHANNELS];  // 黑线校准值

// 上电自动校准: 小车在白底上放3秒，再在黑线上放3秒
void tcrt_calibrate_white(void) {
    for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
        tcrt_min[ch] = 4095;  // 初始最大化
    }
    for (int i = 0; i < 200; i++) {
        for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
            uint16_t val = adc_read_channel(ch);
            if (val < tcrt_min[ch]) tcrt_min[ch] = val;
        }
        delay_ms(10);
    }
}

void tcrt_calibrate_black(void) {
    for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
        tcrt_max[ch] = 0;
    }
    for (int i = 0; i < 200; i++) {
        for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
            uint16_t val = adc_read_channel(ch);
            if (val > tcrt_max[ch]) tcrt_max[ch] = val;
        }
        delay_ms(10);
    }
}

// 归一化: 0.0(全白) ~ 1.0(全黑)
float tcrt_read_normalized(uint8_t ch) {
    uint16_t val = adc_read_channel(ch);
    float norm = (float)(val - tcrt_min[ch]) / (tcrt_max[ch] - tcrt_min[ch] + 1);
    if (norm < 0) norm = 0;
    if (norm > 1.0f) norm = 1.0f;
    return norm;
}

// 加权位置计算: 返回-1.0(最左) ~ +1.0(最右), 0为居中
float tcrt_get_position(void) {
    float sum_val = 0, sum_weight = 0;
    float sensor_positions[5] = {-1.0f, -0.5f, 0.0f, 0.5f, 1.0f};
    for (int i = 0; i < TCRT_CHANNELS; i++) {
        float v = tcrt_read_normalized(i);
        // 阈值过滤噪声
        if (v > 0.1f) {
            sum_val += v * sensor_positions[i];
            sum_weight += v;
        }
    }
    if (sum_weight < 0.05f) return 0.0f;  // 全部白，保持直行
    return sum_val / sum_weight;
}

// 判断是否完全离线 (5路全白 = 冲出赛道)
bool tcrt_is_lost(void) {
    float sum = 0;
    for (int i = 0; i < TCRT_CHANNELS; i++) sum += tcrt_read_normalized(i);
    return sum < 0.1f;
}
```

### --- 巡线转向 PID ---

```c
// 转向 PID: 输入为线位置误差(-1~+1), 输出为差速修正(-1~+1)
PID_Controller steer_pid;

// 差分驱动: base_speed 基础速度, steer_output 转向修正(-1~+1)
void differential_drive(float base_speed, float steer_output) {
    float left_speed  = base_speed * (1.0f - steer_output);
    float right_speed = base_speed * (1.0f + steer_output);

    // 限幅
    if (left_speed  < 0) left_speed  = 0;
    if (right_speed < 0) right_speed = 0;
    if (left_speed  > 1.0f) left_speed  = 1.0f;
    if (right_speed > 1.0f) right_speed = 1.0f;

    // 写入 PWM 占空比 (TIMG8: CH0=PB15左, CH1=PB16右)
    uint32_t period = 4000; // 20kHz
    pwm_set_duty(0, left_speed * period);   // TIMG8_CH0 → 左电机
    pwm_set_duty(1, right_speed * period);  // TIMG8_CH1 → 右电机
}

// 主控循环 (放在 1kHz 定时中断或主循环中)
float line_err = tcrt_get_position();
float steer = pid_update(&steer_pid, line_err, 0.001f); // dt=1ms
differential_drive(0.5f, steer);  // 50% 基础速度
```

### --- 圈数检测 ---

```c
// 基于十字路口的圈数检测: 行驶轨迹是正方形，连续检测到4段直线+4个直角转弯
// 简化方案: 用编码器距离 + 方向判断
volatile uint8_t lap_count = 0;
volatile uint8_t segment = 0;     // 0=AB, 1=BC, 2=CD, 3=DA
volatile float   segment_dist = 0; // 当前段已行驶距离

// 编码器累计: 在定时中断中每1ms累加
// MG310 电机: 减速比 1:20.409, 霍尔编码器 13PPR
// 输出轴 PPR = 13 × 20.409 ≈ 265 (霍尔版) 或 500 × 20.409 ≈ 10204 (GMR版)
// 车轮: 48mm 橡胶轮胎, 周长 = π×4.8cm
#define WHEEL_CIRCUMFERENCE 15.08f  // π×4.8cm (MG310常用48mm轮胎)
#define ENCODER_PPR         265     // 霍尔编码器输出轴脉冲数/圈(13×20.409)
// #define ENCODER_PPR      10204  // GMR编码器版(高精度), 按需切换

void lap_detector_update(int32_t enc_left, int32_t enc_right, float dt) {
    // 左右轮平均距离
    float avg_pulses = (enc_left + enc_right) / 2.0f;
    float distance_cm = avg_pulses / ENCODER_PPR * WHEEL_CIRCUMFERENCE;
    segment_dist += fabsf(distance_cm);

    // 每100cm切换段
    if (segment_dist >= 100.0f) {
        segment_dist -= 100.0f;
        segment = (segment + 1) % 4;
        if (segment == 0) lap_count++;
    }
}
```

### --- 二维云台舵机控制 ---

```c
// 25E 拓展板: 舵机1=PB9(TIMA0_CH1, Pan), 舵机2=PB8(TIMA0_CH0, Tilt)
void gimbal_set_pan(float angle_deg) {
    servo1_set_angle(angle_deg + 90);  // 映射 0~180
}
void gimbal_set_tilt(float angle_deg) {
    servo2_set_angle(angle_deg);       // 0~60 → 0~180
}

// 激光笔开关 (拓展板: 激光未专门分配, 可用 PB27 LED 位或 GPIO 扩展)
// #define LASER_ON()   DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_27)
// #define LASER_OFF()  DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_27)
```

### --- 瞄准几何解算 ---

```c
// 场地坐标系 (cm): A(0,0), B(100,0), C(100,100), D(0,100)
// 靶心坐标 (cm): (50, -50)
#define TARGET_X  50.0f
#define TARGET_Y -50.0f
#define TARGET_Z  25.0f  // 靶心高度(cm), 实测校准
#define GIMBAL_Z   8.0f  // 云台离地高度(cm)

// 根据小车位置计算 Pan 角度 (绕Z轴旋转)
float compute_pan_angle(float car_x, float car_y, float car_heading) {
    // car_heading: 小车朝向角度(°), 逆时针, 0=AB方向(右), 90=BC方向(上)
    float dx = TARGET_X - car_x;
    float dy = TARGET_Y - car_y;
    // 目标相对于小车的世界坐标系方位角
    float world_azimuth = atan2f(dy, dx) * 57.29578f;  // 转度
    // Pan 云台在小车坐标中的角度 (相对于车头)
    float pan = world_azimuth - car_heading;
    // 归一化到 ±180°
    while (pan > 180) pan -= 360;
    while (pan < -180) pan += 360;
    return pan;
}

// 计算 Tilt 俯仰角度
float compute_tilt_angle(float car_x, float car_y) {
    float dx = TARGET_X - car_x;
    float dy = TARGET_Y - car_y;
    float horizontal_dist = sqrtf(dx*dx + dy*dy);
    float dz = TARGET_Z - GIMBAL_Z;
    return atan2f(dz, horizontal_dist) * 57.29578f;
}

// 计算小车在正方形轨迹上的实时位置 (简化: 基于累计距离推算)
void compute_car_position(float total_distance_cm,
                          float *x, float *y, float *heading) {
    float d = fmodf(total_distance_cm, 400.0f);  // 单圈400cm
    if (d < 100) {           // AB段: (d, 0), 方向 0°
        *x = d; *y = 0; *heading = 0;
    } else if (d < 200) {   // BC段: (100, d-100), 方向 90°
        *x = 100; *y = d - 100; *heading = 90;
    } else if (d < 300) {   // CD段: (300-d, 100), 方向 180°
        *x = 300 - d; *y = 100; *heading = 180;
    } else {                // DA段: (0, 400-d), 方向 270°
        *x = 0; *y = 400 - d; *heading = 270;
    }
}
```

### --- 同步画圆算法 (发挥部分3) ---

```c
// 需求: 小车行驶1圈期间, 激光沿靶面上半径6cm的红色圆弧同步画1圈
// 同步误差 < 1/4圈

// 靶面坐标系: X→(水平,平行AB), Z→(垂直,靶面高度)
// 靶心在靶面上的坐标: (0, 0)  (即靶面中心)
// 画圆半径: 6cm

float sync_draw_circle_phase(float car_total_distance_cm) {
    // 小车行驶距离 → 0~2π 相位
    return fmodf(car_total_distance_cm, 400.0f) / 400.0f * 6.2831853f;
}

// 计算激光在靶面上的目标点 (靶面坐标系, cm)
void get_laser_target_on_target(float phase, float radius,
                                float *tx, float *tz) {
    *tx = radius * cosf(phase);   // 水平偏移
    *tz = radius * sinf(phase);   // 垂直偏移
}

// 将靶面坐标转换为云台角度
void target_to_gimbal(float target_x, float target_z,
                      float car_x, float car_y,
                      float *pan, float *tilt) {
    // 靶面点在空间中的实际坐标
    float world_x = TARGET_X + target_x;  // 靶面水平
    float world_z = TARGET_Z + target_z;  // 靶面垂直
    float world_y = TARGET_Y;

    float dx = world_x - car_x;
    float dy = world_y - car_y;
    *pan  = atan2f(dy, dx) * 57.29578f;
    float h_dist = sqrtf(dx*dx + dy*dy);
    *tilt = atan2f(world_z - GIMBAL_Z, h_dist) * 57.29578f;
}
```

### --- 参数设置界面 (OLED + EC11) ---

```c
// 可调参数
typedef struct {
    uint8_t  laps;        // 圈数 1~5
    float    base_speed;  // 基础速度 0.2~1.0
    float    pid_kp;      // 转向 Kp
    float    pid_ki;      // 转向 Ki
    float    pid_kd;      // 转向 Kd
    bool     laser_mode;  // 连续发光/瞄准
} ContestParams;

static ContestParams params = {1, 0.5f, 2.0f, 0.1f, 0.05f, true};

// EC11 旋转选择菜单
void menu_edit_params(void) {
    oled_clear();
    oled_puts(0, 0, ">> Laps Speed Kp Ki Kd");
    // EC11 旋钮选参数, 按键切换, 长按确认
    // 每次修改后 oled_show_float() 刷新显示
    oled_refresh();
}
```

### --- 完整控制流程 (发挥部分) ---

```c
// 状态机
typedef enum {
    STATE_IDLE,              // 等待启动
    STATE_AUTO_TRACK,        // 自动巡线 (基本要求1)
    STATE_AIM_STATIC,        // 静止瞄准 (基本要求2)
    STATE_AIM_MOVING,        // 移动瞄准 (基本要求3)
    STATE_COMBINED,          // 巡线+连续瞄准 (发挥部分)
    STATE_COMPLETE,          // 完成
} SystemState;

// 主循环控制 (简化)
void contest_loop(void) {
    static float total_dist = 0;
    static float lap_start_dist = 0;
    static uint32_t start_time = 0;

    // 读取编码器
    int32_t enc_l = encoder_read_left();
    int32_t enc_r = encoder_read_right();

    // 巡线
    float line_err = tcrt_get_position();
    float steer = pid_update(&steer_pid, line_err, 0.001f);

    // 圈数检测
    lap_detector_update(enc_l, enc_r, 0.001f);
    total_dist += (enc_l + enc_r) / 2.0f / ENCODER_PPR * WHEEL_CIRCUMFERENCE;

    // 瞄准解算
    float cx, cy, heading;
    compute_car_position(total_dist, &cx, &cy, &heading);
    float pan  = compute_pan_angle(cx, cy, heading);
    float tilt = compute_tilt_angle(cx, cy);

    // 画圆模式 (发挥3): 叠加圆偏移
    if (params.laser_mode && params.laps > 0) {
        float phase = sync_draw_circle_phase(total_dist);
        float tx, tz;
        get_laser_target_on_target(phase, 6.0f, &tx, &tz);
        target_to_gimbal(tx, tz, cx, cy, &pan, &tilt);
    }

    // 执行
    gimbal_set_pan(pan);
    gimbal_set_tilt(tilt);
    differential_drive(params.base_speed, steer);

    // UART 调试输出
    // float debug[4] = {line_err, steer, pan, tilt};
    // vofa_send_floats(debug, 4);
}
```

---

### 18.2 24年电赛 H 题 — 自动行驶小车

### 赛道几何模型

```
        100cm (直线段)
    A ────────────────── B
   /←─── r=40cm ───→\     ↑
  │    左半圆弧         │    │ 直线段间距
  │                    │    │ 2×40=80cm
   \                  /     ↓
    D ────────────────── C

场地: 220cm×120cm (含边距)
轨迹总长一圈: 2×100 + 2×π×40 ≈ 451.3cm
半圆弧长: ≈125.7cm
```

**四节点 (弧线顶点/切点)：**
```
A: 左上切点  B: 右上切点
C: 右下切点  D: 左下切点
```

**要求路径：**
| 要求 | 路径 | 通过点 | 限时 |
|------|------|--------|------|
| (1) | A→B | B停车 | ≤15s |
| (2) | 顺时针一圈 | A→B→C→D→A | ≤30s |
| (3) | A→C→B→D→A | 通过所有4点 | ≤40s |
| (4) | 要求(3)路径×4圈 | 每圈4点 | 越少越好 |

### --- 赛道段定义 ---

```c
// 赛道段类型
typedef enum {
    SEG_STRAIGHT,   // 直线段 (100cm)
    SEG_LEFT_ARC,   // 左半圆弧 (r=40cm, πr≈125.7cm)
    SEG_RIGHT_ARC,  // 右半圆弧
} SegmentType;

typedef struct {
    SegmentType type;
    float       length_cm;    // 段长度
    uint32_t    encoder_ticks;// 编码器脉冲数
} TrackSegment;

// 4段组成一圈 (从A开始顺时针):
// S0: A→B 上直线, S1: B→C 右弧, S2: C→D 下直线, S3: D→A 左弧
static const TrackSegment track_lap[4] = {
    {SEG_STRAIGHT,  100.0f, 0},  // S0: 上直线, 换算后填充
    {SEG_RIGHT_ARC, 125.7f, 0},  // S1: 右弧
    {SEG_STRAIGHT,  100.0f, 0},  // S2: 下直线
    {SEG_LEFT_ARC,  125.7f, 0},  // S3: 左弧
};

// 编码器距离换算
#define ENC_TICKS_PER_CM (ENCODER_PPR / WHEEL_CIRCUMFERENCE)

// 段编码器脉冲数初始化
void track_segments_init(void) {
    for (int i = 0; i < 4; i++) {
        ((TrackSegment*)track_lap)[i].encoder_ticks =
            (uint32_t)(track_lap[i].length_cm * ENC_TICKS_PER_CM);
    }
}
```

### --- 路线规划 (路径表) ---

```c
// 路径定义: 按序经过的段号, 段号0~3 对应 S0~S3
// 要求(1): A→B, 只走 S0
static const int8_t route_1[] = {0, -1};  // -1 表示终点

// 要求(2): A→B→C→D→A, 顺时针一圈 S0→S1→S2→S3
static const int8_t route_2[] = {0, 1, 2, 3, -1};

// 要求(3): A→C→B→D→A
// A→C: 左弧向下 S3 → 下直线向左 S2
// C→B: 右弧向上 S1 (反向)  → 实际就是 S1 段，但方向相反
// 注意: 小车只能前进，所以沿赛道反向行驶时是"正常循迹方向"的逆
// 简化处理: A→C = S3+S2, C→B = S1, B→D = S0+S3, D→A = S3
// 即: S3→S2→S1→S0→S3→S3 → 合并为两圈中的 6 段
static const int8_t route_3[] = {3, 2, 1, 0, 3, -1};
// 说明: A →(S3左弧)→ D →(S2下直线)→ C →(S1右弧)→ B →(S0上直线+B→A→左弧)→ D →(S3左弧)→ A

// 要求(4): 要求(3) 路径 × 4
static int8_t route_4[24];  // 动态生成: route_3 重复4次
```

### --- 弯道/直道自适应 PID ---

```c
// 弯道和直道用不同 PID 参数
// 弯道线更弯，需要更大的 Kp 来跟踪
PID_Controller pid_straight;   // 直道转向PID
PID_Controller pid_curve;      // 弯道转向PID

// 判断当前是在直道还是弯道
SegmentType current_segment_type(void) {
    return track_lap[current_seg_idx].type;
}

float adaptive_steer(float line_err, float dt) {
    float steer;
    if (current_segment_type() == SEG_STRAIGHT) {
        steer = pid_update(&pid_straight, line_err, dt);
    } else {
        steer = pid_update(&pid_curve, line_err, dt);
    }
    return steer;
}

// 典型参数:
// pid_straight: Kp=1.8, Ki=0.08, Kd=0.05
// pid_curve:    Kp=3.0, Ki=0.15, Kd=0.10
```

### --- 节点检测 (A/B/C/D 点) ---

```c
// 检测到达节点: 编码器距离 + 线传感器突变 (弧线→直线过渡处)
// 弧线-直线交汇处, 5路传感器会有短暂的特殊模式

volatile uint8_t  reached_point = 0;   // 0=无, 1/2/3/4=A/B/C/D的检测标志
volatile uint32_t point_timestamp = 0; // 到达时刻

void check_point_reached(void) {
    // 方法1: 编码器距离——当前段剩余距离 < 阈值
    if (seg_remaining_dist < 3.0f) {  // 距离目标点 < 3cm
        reached_point = 1;
        point_timestamp = g_ms_ticks;
        return;
    }

    // 方法2: 传感器模式检测——5路全部"看到线"且位置居中
    // (弧线切点处线比较直，可用于辅助判断)
    float sum = 0;
    for (int i = 0; i < TCRT_CHANNELS; i++) sum += tcrt_read_normalized(i);
    float pos = fabsf(tcrt_get_position());
    if (sum > 1.5f && pos < 0.15f && seg_remaining_dist < 8.0f) {
        reached_point = 1;
        point_timestamp = g_ms_ticks;
    }
}
```

### --- 定点刹车控制 ---

```c
// S曲线减速: 距离目标点越近, 速度越低
// 参考公式: v = sqrt(2 * a * d), a 为减速度
#define MAX_SPEED      0.6f   // 直道巡航速度 (占空比)
#define MIN_SPEED      0.15f  // 弯道最低速度
#define DECEL_RATE     0.3f   // 减速度 (m/s^2, 按实际调)

float compute_target_speed(float dist_to_stop, bool is_final_stop) {
    if (!is_final_stop) {
        // 途经点: 不减速太多, 流畅通过
        return (dist_to_stop < 15.0f) ? MAX_SPEED * 0.6f : MAX_SPEED;
    }
    // 终点停车: 渐进减速
    if (dist_to_stop > 40.0f) return MAX_SPEED;
    if (dist_to_stop < 5.0f)  return 0.0f;   // 刹车
    // 中间: 线性减速
    return MAX_SPEED * dist_to_stop / 40.0f;
}

// 刹车执行 (拓展板: AIN1=PA13, AIN2=PA12, BIN1=PB0, BIN2=PB1)
void brake_now(void) {
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_13);   // AIN1=0
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_12);   // AIN2=0
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0);    // BIN1=0
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);    // BIN2=0
    pwm_set_duty(0, 0);   // PWMA=0
    pwm_set_duty(1, 0);   // PWMB=0
}
```

### --- 声光指示 ---

```c
#define BUZZER_PIN  DL_GPIO_PIN_17  // PB17 蜂鸣器 (拓展板)
#define LED_PIN     DL_GPIO_PIN_27  // PB27 LED (拓展板)

void indicator_beep(uint8_t times, uint32_t duration_ms) {
    for (int i = 0; i < times; i++) {
        DL_GPIO_setPins(GPIOB, BUZZER_PIN);  // 蜂鸣器
        DL_GPIO_setPins(GPIOB, LED_PIN);     // LED
        delay_ms(duration_ms);
        DL_GPIO_clearPins(GPIOB, BUZZER_PIN);
        DL_GPIO_clearPins(GPIOB, LED_PIN);
        if (times > 1) delay_ms(150);
    }
}

// 到达每个点: 短鸣 1声 + LED 闪 1次
void point_indicator(void) {
    indicator_beep(1, 200);
}

// 最终停车: 长鸣 3声 + LED 长亮 2秒
void stop_indicator(void) {
    DL_GPIO_setPins(GPIOA, LED_PIN);
    indicator_beep(3, 500);
    DL_GPIO_clearPins(GPIOA, LED_PIN);
}
```

### --- 前进锁定 (不得后退) ---

```c
// TB6612 AIN1/AIN2 控制左电机方向
// BIN1/BIN2 控制右电机方向
// 前进: AIN1=1, AIN2=0 / BIN1=1, BIN2=0
// 后退: AIN1=0, AIN2=1 (本题禁用)

typedef enum {
    MOTOR_FORWARD = 0,
    // MOTOR_BACKWARD = 1,  // 本题禁用
    MOTOR_BRAKE    = 2,
} MotorDirection;

void motor_set_forward(void) {
    // 拓展板: AIN1=PA13, AIN2=PA12, BIN1=PB0, BIN2=PB1
    DL_GPIO_setPins(GPIOA, DL_GPIO_PIN_13);   // AIN1=1
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_12); // AIN2=0
    DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_0);    // BIN1=1
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);  // BIN2=0
}

// 安全封装: 差分驱动只调整占空比, 不动方向
void safe_differential_drive(float left, float right) {
    motor_set_forward();  // 始终前进
    pwm_set_duty(0, (uint32_t)(left  * 4000));  // TIMG8_CH0=PB15
    pwm_set_duty(1, (uint32_t)(right * 4000));  // TIMG8_CH1=PB16
}
```

### --- H 题主控逻辑 ---

```c
typedef struct {
    uint8_t  route_type;    // 1/2/3/4 对应要求(1)~(4)
    uint8_t  total_points;  // 本路线总途经点
    uint8_t  point_idx;     // 当前途经点序号
    uint8_t  lap_count;     // 已完成圈数
    int8_t   seg_sequence[32]; // 段序列
    uint8_t  seg_count;     // 段序列长度
    uint8_t  seg_idx;       // 当前段索引
    float    seg_progress;  // 当前段已走距离
    bool     is_finished;
} H_ContestState;

void h_contest_init(H_ContestState *s, uint8_t route_type) {
    s->route_type = route_type;
    s->point_idx  = 0;
    s->lap_count  = 0;
    s->seg_idx    = 0;
    s->seg_progress = 0;
    s->is_finished  = false;

    // 根据路线类型填充段序列
    const int8_t (*route)[];
    switch (route_type) {
    case 1: route = &route_1; break;
    case 2: route = &route_2; break;
    case 3: route = &route_3; break;
    case 4: // 重复 route_3 × 4
        for (int i = 0; i < 4; i++) {
            for (int j = 0; route_3[j] >= 0; j++)
                s->seg_sequence[i*5 + j] = route_3[j];
        }
        s->seg_sequence[20] = -1;
        route = NULL; break;
    default: return;
    }
    if (route) {
        for (int i = 0; (*route)[i] >= 0; i++)
            s->seg_sequence[i] = (*route)[i];
        s->seg_sequence[i] = -1;
    }
}

void h_contest_loop(H_ContestState *s) {
    if (s->is_finished) return;

    // 读编码器
    int32_t enc_l = encoder_read_left();
    int32_t enc_r = encoder_read_right();
    float avg_dist = (enc_l + enc_r) / 2.0f / ENC_TICKS_PER_CM;

    // 更新段进度
    s->seg_progress += avg_dist;
    int8_t seg = s->seg_sequence[s->seg_idx];
    if (seg < 0) { s->is_finished = true; brake_now(); stop_indicator(); return; }
    float seg_len = track_lap[seg].length_cm;

    // 检测是否到达节点
    float remaining = seg_len - s->seg_progress;
    if (remaining < 2.0f) {
        s->point_idx++;
        point_indicator();
        s->seg_progress = 0;
        s->seg_idx++;
        // 判断是否是终点
        if (s->seg_sequence[s->seg_idx] < 0) {
            s->lap_count++;
            if (s->route_type == 4 && s->lap_count >= 4) {
                s->is_finished = true;
                brake_now();
                stop_indicator();
                return;
            }
        }
    }

    // 巡线 + 速度控制
    float line_err = tcrt_get_position();
    float steer = adaptive_steer(line_err, 0.001f);

    bool is_final = (s->seg_sequence[s->seg_idx] < 0);
    float speed = compute_target_speed(remaining, is_final);
    safe_differential_drive(speed + steer, speed - steer);
}
```

---

### 18.3 23年电赛 E 题 — 运动目标控制与自动追踪系统

### 系统架构

```
┌──── RED 系统 (独立MCU) ────┐     ┌──── GREEN 系统 (独立MCU) ────┐
│                             │     │                               │
│  MSPM0G #1                  │     │  MSPM0G #2                    │
│  ├─ 键盘(模式选择+启动)      │     │  ├─ OV7725+FIFO(摄像头)        │
│  ├─ OLED(显示当前路径)       │     │  ├─ OLED(显示追踪状态)          │
│  ├─ 舵机1(Pan)              │     │  ├─ 舵机1(Pan)                │
│  ├─ 舵机2(Tilt)             │     │  ├─ 舵机2(Tilt)              │
│  └─ 红色激光笔(MOS驱动)      │     │  └─ 绿色激光笔(MOS驱动)        │
└─────────────────────────────┘     └───────────────────────────────┘
         ↕ 不能通信 ↕                         ↕ 摄像头 ↕
    ┌─────────────────────────────────────────────────────┐
    │           白色屏幕 (1m 前方, >0.6×0.6m)              │
    │    ┌─────────────────────┐                          │
    │    │   0.5m×0.5m 正方形   │                          │
    │    │   中心 = 原点(0,0)    │                          │
    │    └─────────────────────┘                          │
    └─────────────────────────────────────────────────────┘
```

**坐标系 (屏幕平面，单位 cm)：**
- 原点: (0, 0) = 屏幕中心
- 正方形: (±25, ±25)
- 屏幕距云台: 100cm (Z方向)
- Pan/Tilt 角度: 绕 Z 轴 / 绕水平轴

### --- 红色系统: 路径生成 ---

**正方形边线路径 (基本要求2)：**
```c
// 屏幕 0.5m×0.5m, 边线路径: 上→右→下→左, 顺时针
// 光斑距边线 ≤2cm, 即路径在 ±23cm 处 (中心往边 25cm 减 2cm)
#define SQ_HALF  23.0f  // 正方形半边距

typedef struct {
    float x, y;    // 屏幕坐标 (cm)
} Point2D;

// 正方形路径 (50个采样点, 30秒走一圈 → 每点 0.6s → 每步 4cm)
static Point2D square_path[200];
static uint16_t  square_path_len = 0;

void generate_square_path(void) {
    // 上边: (SQ_HALF, -SQ_HALF) → (SQ_HALF, SQ_HALF)  右移
    // 左边: (SQ_HALF, SQ_HALF) → (-SQ_HALF, SQ_HALF)   下移
    // 下边: (-SQ_HALF, SQ_HALF) → (-SQ_HALF, -SQ_HALF) 左移
    // 右边: (-SQ_HALF, -SQ_HALF) → (SQ_HALF, -SQ_HALF) 上移
    // 用 Bresenham 或直接等距采样填充
    float step = 1.0f;  // 每步 1cm
    float xs[] = { SQ_HALF,  SQ_HALF, -SQ_HALF, -SQ_HALF,  SQ_HALF};
    float ys[] = {-SQ_HALF,  SQ_HALF,  SQ_HALF, -SQ_HALF, -SQ_HALF};
    int idx = 0;
    for (int seg = 0; seg < 4; seg++) {
        float dx = xs[seg+1] - xs[seg];
        float dy = ys[seg+1] - ys[seg];
        float dist = sqrtf(dx*dx + dy*dy);
        int steps = (int)(dist / step);
        for (int i = 0; i < steps; i++) {
            float t = (float)i / steps;
            square_path[idx].x = xs[seg] + dx * t;
            square_path[idx].y = ys[seg] + dy * t;
            idx++;
        }
    }
    square_path_len = idx;
}
```

**A4 靶纸路径 (基本要求3/4)：**
```c
// A4: 29.7cm×21cm, 胶带宽 1.8cm
// 光斑沿胶带中心线移动 → 路径比 A4 边缘内移 0.9cm
#define A4_HALF_W  14.85f  // 29.7/2
#define A4_HALF_H  10.5f   // 21/2
#define TAPE_OFFSET 0.9f   // 胶带半宽

static Point2D a4_path[200];
static uint16_t  a4_path_len = 0;

// 旋转任意角度 θ (弧度)
void generate_a4_path(float center_x, float center_y, float theta) {
    float hw = A4_HALF_W - TAPE_OFFSET;
    float hh = A4_HALF_H - TAPE_OFFSET;
    float corners[4][2] = {
        { hw, -hh}, { hw,  hh}, {-hw,  hh}, {-hw, -hh}
    };
    // 旋转 + 平移
    float c = cosf(theta), s = sinf(theta);
    float xs[5], ys[5];
    for (int i = 0; i < 4; i++) {
        float rx = corners[i][0]*c - corners[i][1]*s + center_x;
        float ry = corners[i][0]*s + corners[i][1]*c + center_y;
        xs[i] = rx; ys[i] = ry;
    }
    xs[4] = xs[0]; ys[4] = ys[0];  // 闭合

    float step = 0.8f;
    int idx = 0;
    for (int seg = 0; seg < 4; seg++) {
        float dx = xs[seg+1] - xs[seg];
        float dy = ys[seg+1] - ys[seg];
        float dist = sqrtf(dx*dx + dy*dy);
        int steps = (int)(dist / step);
        for (int i = 0; i < steps; i++) {
            float t = (float)i / steps;
            a4_path[idx].x = xs[seg] + dx * t;
            a4_path[idx].y = ys[seg] + dy * t;
            idx++;
        }
    }
    a4_path_len = idx;
}
```

**屏幕坐标 → 云台角度：**
```c
#define SCREEN_DIST 100.0f  // 屏幕距云台 1m = 100cm

void screen_to_gimbal(float sx, float sy, float *pan, float *tilt) {
    // sx, sy: 屏幕上的目标坐标 (cm), 原点(0,0)=屏幕中心
    // 转换: 水平偏移 → Pan角, 垂直偏移+距离 → Tilt角
    *pan  = atan2f(sx, SCREEN_DIST) * 57.29578f;
    float h_dist = sqrtf(SCREEN_DIST*SCREEN_DIST + sx*sx);
    *tilt = atan2f(sy, h_dist) * 57.29578f;
}
```

**红色系统主控：**
```c
typedef enum {
    RED_IDLE,
    RED_RESET,      // 基本要求1: 回到原点
    RED_SQUARE,     // 基本要求2: 正方形边线
    RED_A4_NORMAL,  // 基本要求3: A4靶纸
    RED_A4_ROTATED, // 基本要求4: 旋转A4靶纸
    RED_PAUSED,     // 制动
} RedState;

void red_system_loop(RedState *state, uint32_t *path_idx, uint32_t elapsed_ms) {
    Point2D target;
    switch (*state) {
    case RED_RESET:
        target.x = 0; target.y = 0;  // 原点
        if (elapsed_ms > 1000) *state = RED_IDLE;  // 1秒到原点
        break;
    case RED_SQUARE:
        // 30秒 200步 → 每步 150ms
        *path_idx = (elapsed_ms / 150) % square_path_len;
        if (elapsed_ms > 30000) *state = RED_IDLE;
        target = square_path[*path_idx];
        break;
    case RED_A4_NORMAL:
    case RED_A4_ROTATED:
        *path_idx = (elapsed_ms / 150) % a4_path_len;
        if (elapsed_ms > 30000) *state = RED_IDLE;
        target = a4_path[*path_idx];
        break;
    case RED_PAUSED:
        return;  // 不动
    default: return;
    }
    float pan, tilt;
    screen_to_gimbal(target.x, target.y, &pan, &tilt);
    gimbal_set_pan(pan);
    gimbal_set_tilt(tilt);
}
```

### --- 绿色系统: 摄像头红光斑检测 ---

```c
// OV7725 + AL422B FIFO 摄像头模块
// 典型连接: 8-bit parallel D0~D7 + PCLK + VSYNC + HREF
// FIFO 读: 先拉低 OE, 再给 RE 脉冲读出 1 字节

// 简化方案: 只读 80×60 下采样图像, 仅检查红色通道
#define CAM_WIDTH   80
#define CAM_HEIGHT  60
#define RED_THRESHOLD  200  // R 通道阈值 (0~255), 按实测调整
#define MIN_RED_PIXELS  5   // 最少红色像素数

typedef struct {
    uint16_t sum_x, sum_y;
    uint16_t count;
    float    cx, cy;  // 光斑中心 (屏幕坐标 cm)
    bool     detected;
} RedSpot;

// 从 FIFO 读一帧并检测红光斑
// 原理: 仅读 R 分量(每像素 2 字节 RGB565), 超过阈值则累计质心
RedSpot detect_red_spot(void) {
    RedSpot spot = {0};

    // FIFO 复位读指针
    fifo_reset_read();

    for (int y = 0; y < CAM_HEIGHT; y++) {
        for (int x = 0; x < CAM_WIDTH; x++) {
            uint16_t pixel = fifo_read_16();  // RGB565
            uint8_t r = (pixel >> 11) & 0x1F; // R 分量 5-bit
            r = (r << 3) | (r >> 2);           // 扩展到 8-bit
            if (r > RED_THRESHOLD) {
                spot.sum_x += x;
                spot.sum_y += y;
                spot.count++;
            }
        }
    }

    if (spot.count >= MIN_RED_PIXELS) {
        spot.detected = true;
        // 像素坐标 → 屏幕坐标
        // 假设摄像头视角与屏幕对应, 屏幕 50cm 范围映射到 80px
        float scale_x = 50.0f / CAM_WIDTH;   // cm/pixel
        float scale_y = 50.0f / CAM_HEIGHT;
        spot.cx = ((float)spot.sum_x / spot.count - CAM_WIDTH/2)  * scale_x;
        spot.cy = ((float)spot.sum_y / spot.count - CAM_HEIGHT/2) * scale_y;
    }

    return spot;
}

// FIFO 基础操作 (GPIO 模拟)
#define FIFO_OE_PIN  DL_GPIO_PIN_14  // PA14
#define FIFO_RE_PIN  DL_GPIO_PIN_15  // PA15
// D0~D7 接 GPIOB 全口

uint16_t fifo_read_16(void) {
    uint8_t hi, lo;
    DL_GPIO_clearPins(GPIOA, FIFO_OE_PIN);    // OE=0
    DL_GPIO_clearPins(GPIOA, FIFO_RE_PIN);    delay_us(1);
    hi = DL_GPIO_readPins(GPIOB, 0xFF);       // 读 D0~D7
    DL_GPIO_setPins(GPIOA, FIFO_RE_PIN);      // RE=1
    DL_GPIO_clearPins(GPIOA, FIFO_RE_PIN);    delay_us(1);
    lo = DL_GPIO_readPins(GPIOB, 0xFF);
    DL_GPIO_setPins(GPIOA, FIFO_RE_PIN);
    DL_GPIO_setPins(GPIOA, FIFO_OE_PIN);      // OE=1
    return ((uint16_t)hi << 8) | lo;
}
```

**无摄像头的简化方案 — 四象限光电传感器：**
```c
// 如果摄像方案太复杂, 可用 4 个光敏电阻/光电管构成四象限检测
// 4 个传感器对准屏幕, 比较各象限亮度 → 估算红点位置
// 精度低于摄像方案, 但 MCU 开销极小

typedef struct {
    uint16_t top_left, top_right, bot_left, bot_right;
} QuadrantSensor;

Point2D quadrant_to_position(QuadrantSensor *q) {
    float total = q->tl + q->tr + q->bl + q->br + 1;
    float x = ((q->tr + q->br) - (q->tl + q->bl)) / total * 25.0f;
    float y = ((q->bl + q->br) - (q->tl + q->tr)) / total * 25.0f;
    return (Point2D){x, y};
}
```

### --- 绿色系统: 视觉追踪闭环 ---

```c
typedef enum {
    GREEN_IDLE,
    GREEN_TRACKING,   // 追踪中
    GREEN_LOST,       // 丢失目标
    GREEN_PAUSED,     // 制动
} GreenState;

// 视觉追踪 PID (两个独立的 PID: X方向 + Y方向)
PID_Controller pid_track_x;  // X→Pan
PID_Controller pid_track_y;  // Y→Tilt

void green_system_loop(GreenState *state) {
    RedSpot spot = detect_red_spot();

    if (!spot.detected) {
        *state = GREEN_LOST;
        // 丢失目标: 扫描搜索 (缓慢扫 Pan)
        static float scan_angle = -45;
        scan_angle += 0.5f;
        if (scan_angle > 45) scan_angle = -45;
        gimbal_set_pan(scan_angle);
        return;
    }

    *state = GREEN_TRACKING;

    // X/Y 误差 → PID → 修正云台角度
    float current_pan  = pid_get_last_output(&pid_track_x);
    float current_tilt = pid_get_last_output(&pid_track_y);

    float pan_correction  = pid_update(&pid_track_x, spot.cx, 0.02f);
    float tilt_correction = pid_update(&pid_track_y, spot.cy, 0.02f);

    gimbal_set_pan(pan_correction);
    gimbal_set_tilt(tilt_correction);

    // 判断追踪成功: 误差 < 3cm (对应角度 ≈ arctan(3/100) ≈ 1.7°)
    float err_pan  = fabsf(spot.cx) * 57.29578f / SCREEN_DIST;
    float err_tilt = fabsf(spot.cy) * 57.29578f / SCREEN_DIST;
    if (err_pan < 1.7f && err_tilt < 1.7f) {
        // 追踪成功: 连续声光
        DL_GPIO_setPins(GPIOA, LED_PIN);
    } else {
        DL_GPIO_clearPins(GPIOA, LED_PIN);
    }
}
```

### --- 双系统暂停与制动 ---

```c
// 两个系统独立按键: KEY1(红)暂停, KEY2(绿)暂停
// 题目要求: 同时按下暂停键, 两个光斑应"立即制动"
// 因为红/绿系统不通信, "同时按下"靠人工实现
// 制动: 立即停止 PWM 更新 → 舵机停在原位

volatile bool g_red_paused  = false;
volatile bool g_green_paused = false;

// 在按键中断中:
void pause_button_isr(void) {
    // 关激光 (通过 MOS)
    LASER_OFF();
    // 设置暂停标志 → 主循环停止舵机角度更新
    g_red_paused = true;  // 或 g_green_paused = true
}

// 一键启动追踪 (发挥部分1):
// 按下启动键 → green_system_loop 立即执行 detect_red_spot + PID 追踪
```

### --- 双系统完整初始化 ---

```c
// 红色系统 main()
void red_main(void) {
    SYSCFG_DL_init();
    __enable_irq();
    oled_init();
    generate_square_path();
    generate_a4_path(5.0f, 8.0f, 0.0f);  // A4贴屏幕右上角

    RedState state = RED_IDLE;
    uint32_t start_ms = 0;
    uint32_t path_idx = 0;

    while (1) {
        // 按键选择模式
        if (btn_mode_pressed()) {
            state = (state + 1) % 5;  // 循环切换模式
            start_ms = g_ms_ticks;
        }
        if (btn_pause_pressed()) g_red_paused = !g_red_paused;
        if (g_red_paused) { LASER_OFF(); continue; }
        LASER_ON();

        uint32_t elapsed = g_ms_ticks - start_ms;
        red_system_loop(&state, &path_idx, elapsed);
        delay_ms(20);
    }
}

// 绿色系统 main()
void green_main(void) {
    SYSCFG_DL_init();
    __enable_irq();
    oled_init();
    camera_init();  // 初始化 OV7725+FIFO

    GreenState state = GREEN_IDLE;
    pid_init(&pid_track_x, 0.8f, 0.02f, 0.1f);  // 视觉 X PID
    pid_init(&pid_track_y, 0.8f, 0.02f, 0.1f);  // 视觉 Y PID

    while (1) {
        if (btn_track_start_pressed()) {
            state = GREEN_TRACKING;
        }
        if (btn_pause_pressed()) g_green_paused = !g_green_paused;
        if (g_green_paused) { LASER_OFF(); continue; }
        LASER_ON();

        green_system_loop(&state);
        delay_ms(20);
    }
}
```

---

## 十九、硬件连接速查

### 常用模块接线

**TB6612 电机驱动：**
| TB6612 | MSPM0G | 说明 |
|--------|--------|------|
| PWMA | PB15 (TIMG8_C0) | PWM, 20kHz |
| PWMB | PB16 (TIMG8_C1) | PWM, 20kHz |
| AIN1 | PA13 | 方向 1 |
| AIN2 | PA12 | 方向 2 |
| BIN1 | PB0 | 方向 1 |
| BIN2 | PB1 | 方向 2 |
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

---

## 二十、工作流程

当用户提出需求时，按以下优先级处理：

1. **外设初始化** → 优先引导用户使用 SysConfig 图形配置，同时给出手动 DriverLib 代码作为备选
2. **算法实现** → 给出可直接编译的 C 代码，注明参数整定方法
3. **硬件连接** → 给出引脚对照表 + 注意事项
4. **问题排查** → 从电气、时序、代码逻辑三个层面诊断

## 二十一、注意事项

- MSPM0G 是 3.3V 系统，GPIO 不可直接接 5V（部分引脚可耐受 5V，查看数据手册）
- **天猛星 PA2~PA6 为时钟引脚，默认未焊接，勿用！** PA0/PA1 被 CH340 固定占用
- **PA0/PA1 是开漏(Open-Drain)引脚**，用作 UART 时必须加外部 4.7kΩ~10kΩ 上拉电阻到 3.3V，否则 115200 波特率下无法通信（BSL 9600 勉强可用但也不稳定）
- **SWCLK=PA20, SWDIO=PA19**（非 PA0/PA1）
- ADC 输入电压范围 0 ~ VREF，超出会损坏
- 使用内部运放前必须先使能，使用后及时禁用省电
- 中断回调函数中不要做耗时操作，只置标志位
- PWM 死区用于 H 桥，避免上下管直通短路
- I2C 默认使用 PA28(SDA)+PA31(SCL)，板载已有上拉可不再加
- 电机编码器线长尽量短，必要时加屏蔽
- 双 K230+M0G 系统必须共地，供电独立隔离

---

