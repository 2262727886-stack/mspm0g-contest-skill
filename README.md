# MSPM0G3507 电赛智能小车开发套件

> 基于 TI MSPM0G3507 (Cortex-M0+) + 嘉楠 K230 (RISC-V) 双芯架构的电赛控制类题目全栈开发方案。覆盖底盘运动控制、IMU 姿态解码、视觉追踪、蓝牙调参、舵机云台等完整功能链，所有代码均已实机验证。

[![MCU](https://img.shields.io/badge/MCU-MSPM0G3507-blue)](https://www.ti.com/product/MSPM0G3507)
[![SDK](https://img.shields.io/badge/SDK-mspm0_sdk__2__10__00__04-green)](https://www.ti.com/tool/MSPM0-SDK)
[![IDE](https://img.shields.io/badge/IDE-CCS%20Theia%20%7C%20VS%20Code-orange)](https://www.ti.com/tool/CCSTHEIA)
[![K230](https://img.shields.io/badge/CoPro-K230__庐山派-purple)](https://developer.canaan-creative.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)
[![Stars](https://img.shields.io/github/stars/2262727886-stack/mspm0g-contest-skill?style=social)](https://github.com/2262727886-stack/mspm0g-contest-skill)

中文 | English (coming soon)

[![Star History Chart](https://api.star-history.com/svg?repos=2262727886-stack/mspm0g-contest-skill&type=Date)](https://star-history.com/#2262727886-stack/mspm0g-contest-skill)

> ⚡ **如果你是第一次接触这个项目**，不要先啃全部代码。
> **最省事的用法是直接用 Claude Code 加载 Skill**，它会根据你的实际接线生成正确的驱动代码。

---

## 目录

- [系统架构图](#系统架构图)
- [先看你该怎么用](#先看你该怎么用)
- [这个项目适合什么场景](#这个项目适合什么场景)
- [它不是做什么的](#它不是做什么的)
- [5 分钟上手](#5-分钟上手)
- [硬件平台详解](#硬件平台详解)
- [引脚分配速查](#引脚分配速查)
- [工程目录详解](#工程目录详解)
- [推荐学习路径](#推荐学习路径)
- [Claude Code Skill 完整指南](#claude-code-skill-完整指南)
- [PID 调参指南](#pid-调参指南)
- [K230 视觉方案](#k230-视觉方案)
- [开发环境搭建](#开发环境搭建)
- [烧录方法](#烧录方法)
- [调试技巧](#调试技巧)
- [常见问题排查](#常见问题排查)
- [电赛真题方案](#电赛真题方案)
- [API 安全黑名单](#api-安全黑名单)
- [安全提醒](#安全提醒)
- [主要文件说明](#主要文件说明)
- [依赖清单](#依赖清单)
- [致谢](#致谢)
- [License](#license)

---

## 系统架构图

```text
┌────────────────────── K230 视觉端 (MicroPython) ──────────────────────┐
│                                                                       │
│  GC2093 摄像头 → LAB 色块识别 → UART (9600 8N1) → MSPM0G 主控        │
│  (CSI 2)          (找色块)         FF FE 帧协议                       │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌────────────────────── MSPM0G3507 主控端 (C) ──────────────────────────┐
│                                                                       │
│  MPU6050(I2C1) + 编码器×2(TIMG7/GPIO) + TB6612(TIMG8) + 舵机(TIMA0)  │
│                                    │                                  │
│            ┌───────────────────────┘                                  │
│            ▼                                                          │
│  PID 级联控制器: 速度PI(内环) + 位置P(外环) + 航向PD + 转弯PID        │
│            │                                                          │
│            ▼                                                          │
│  SSD1306 OLED(I2C0) + JDY-31蓝牙(UART) + VOFA+调试(UART0)             │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```

---

## 先看你该怎么用

- **想用 AI 自动生成代码，不想记引脚和 API**：走 Skill 路线，见 [Claude Code Skill](#claude-code-skill-完整指南)。
- **已经有电赛小车，想看现有代码怎么写的**：直接看 `workspace_ccstheia/mpu6050_clean/`，最干净的基线工程。
- **想从零搭一辆电赛小车**：按 [推荐学习路径](#推荐学习路径) 从基础外设逐步搭建。
- **想基于 K230 做视觉追踪**：看 `workspace_ccstheia/test_2/` 和 [K230 视觉方案](#k230-视觉方案)。
- **想深入了解内部设计**：看 `.claude/skills/mspm0g-contest/SKILL.md`。

---

## 这个项目适合什么场景

- 差速底盘控制：TB6612FNG + MG310 编码电机，速度/位置闭环
- 姿态感知：MPU6050 DMP 或 IMU601 UART，Yaw/Pitch/Roll 实时读取
- PID 参数整定：增量式速度 PI + 航向 PD + 转弯 PID，已调优参数可直接用
- 视觉目标追踪：K230 庐山派 + GC2093 摄像头，LAB 色块识别 + 双芯通信
- 舵机云台：众灵 PM 系列舵机 (500~2500us, 50Hz)，姿态随动
- 蓝牙无线调参：JDY-31 BLE 透传，手机/Python 远程调速调参
- 实时调试：OLED 多页显示 + VOFA+ 波形输出

## 它不是做什么的

- 它**不是**"一个 main.c 就能跑所有功能"的万能模板。不同题目需要不同外设组合。
- 它**不是** RTOS 方案。当前所有代码基于裸机 (nortos)，定时由 TIMG 硬件驱动。
- 它**不是**自动避障或 SLAM 方案。视觉部分只是色块识别 + 位置输出。

这个项目更在意的是：**让你少踩引脚配置的坑、少查 SDK API 是否存在、少在"代码写对了但跑不起来"上浪费时间。**

---

## 5 分钟上手

### 第 1 步：克隆仓库

```bash
git clone https://github.com/2262727886-stack/mspm0g-contest-skill.git
cd mspm0g-contest-skill
```

### 第 2 步：安装工具链

| 工具 | 下载地址 | 说明 |
|------|---------|------|
| CCS Theia | https://www.ti.com/tool/CCSTHEIA | TI 官方 IDE |
| MSPM0 SDK | https://www.ti.com/tool/MSPM0-SDK | v2.10.00.04 |
| XDS110 驱动 | 随 CCS Theia 安装 | SWD 调试器 |

### 第 3 步：打开基线工程

CCS Theia → File → Open Folder → 选 `workspace_ccstheia/mpu6050_clean/`

### 第 4 步：检查引脚

打开 `.syscfg`，确认外设引脚和你的实际接线一致。**这是最多人出错的步骤。**

### 第 5 步：编译 + 烧录

Ctrl+B 编译 → Debug 按钮 → XDS110 烧录

### VS Code 用户

工程已配好 `.vscode/c_cpp_properties.json`，直接打开 `workspace_ccstheia` 根目录即可。

---

## 硬件平台详解

### MCU 对比

| 参数 | MSPM0G3507 | K230 庐山派 |
|------|-----------|-------------|
| 架构 | Cortex-M0+ | RISC-V 双核 |
| 主频 | 32MHz(默认)/80MHz(PLL) | 1.6GHz(大核) |
| Flash | 128KB | -- |
| SRAM | 32KB | 512MB LPDDR4 |
| 开发语言 | C (TI Arm Clang) | MicroPython (CanMV) |
| 调试接口 | SWD (XDS110) | USB 串口 REPL |
| OS | 裸机 (nortos) | RT-Smart |

### 外设清单

| 组件 | 型号 | 规格 | 接口 | 状态 |
|------|------|------|------|------|
| 电机驱动 | TB6612FNG | 双H桥, 1.2A/3.2A峰值 | TIMG8 PWM | 已验证 |
| 编码电机 | MG310 | 霍尔编码, AB双相 | TIMG7 QEI + GPIO中断 | 已验证 |
| IMU(方案一) | MPU6050 | 6轴, DMP姿态解码 | I2C1 (PA10/PA11) | 已验证 |
| IMU(方案二) | IMU601(正点原子) | 6轴, UART ATKP协议 | UART0 (PA0/PA1) | 已验证 |
| 显示 | SSD1306 | 0.96" 128x64 OLED | I2C0 (PA28/PA31) | 已验证 |
| 蓝牙 | JDY-31 | BLE 4.2, 9600 baud | UART | 已验证 |
| 舵机 | 众灵 PM 系列 | 500-2500us, 50Hz, 10-80KG | TIMA0 PWM | 已验证 |
| 摄像头 | GC2093 | 最大1920x1080 | K230 CSI 2 | 已验证 |
| 调试器 | XDS110 | SWD | PA19/PA20 | 已验证 |

---

## 引脚分配速查

> 以下为 mpu6050_clean 工程默认引脚。Claude Skill 每次生成代码前会要求确认实际接线。

### 运动控制

| 功能 | 模块 | 引脚 | IOMUX | 复用功能 | 备注 |
|------|------|------|-------|---------|------|
| 右轮 PWM | TB6612 A | PB15 | PINCM43 | TIMG8_C0 | A=右轮 |
| 左轮 PWM | TB6612 B | PB16 | PINCM44 | TIMG8_C1 | B=左轮 |
| 右轮编码器 A | MG310 | PA15 | PINCM15 | GPIO 双边沿中断 | 4倍频 |
| 右轮编码器 B | MG310 | PA16 | PINCM16 | GPIO 双边沿中断 | 方向 |
| 左轮编码器 A | MG310 | PA17 | PINCM17 | TIMG7_CH0 | QEI |
| 左轮编码器 B | MG310 | PA24 | PINCM24 | TIMG7_CH1 | 硬件4倍频 |

### 传感器与通信

| 功能 | 模块 | 引脚 | IOMUX | 复用功能 | 备注 |
|------|------|------|-------|---------|------|
| MPU6050 SDA | InvenSense | PA10 | PINCM6 | I2C1_SDA | 0x68 |
| MPU6050 SCL | InvenSense | PA11 | PINCM7 | I2C1_SCL | 400kHz |
| OLED SDA | SSD1306 | PA28 | PINCM34 | I2C0_SDA | 0x3C |
| OLED SCL | SSD1306 | PA31 | PINCM35 | I2C0_SCL | 400kHz |
| K230 TX | MSPM0G | PB2 | PINCM30 | UART3_TX | 9600 8N1 |
| K230 RX | MSPM0G | PB3 | PINCM31 | UART3_RX | FF FE 帧 |
| 调试 TX | CH340 | PA10 | PINCM6 | UART0_TX | 与 I2C1 冲突 |
| 调试 RX | CH340 | PA11 | PINCM7 | UART0_RX | 115200 |

### 执行器与交互

| 功能 | 模块 | 引脚 | IOMUX | 复用功能 | 备注 |
|------|------|------|-------|---------|------|
| 舵机1 PWM | 众灵 PM | PB8 | PINCM36 | TIMA0_C0 | 50Hz |
| 舵机2 PWM | 众灵 PM | PB9 | PINCM37 | TIMA0_C1 | 50Hz |
| 校准按键 | 轻触开关 | PA25 | PINCM25 | GPIO 上拉 | 校准 |
| 启动按键 | 轻触开关 | PA26 | PINCM26 | GPIO 上拉 | 启动 |
| SWDIO | XDS110 | PA19 | -- | SWD 数据 | 保留 |
| SWCLK | XDS110 | PA20 | -- | SWD 时钟 | 保留 |

### 禁用引脚

| 禁用引脚 | 原因 |
|----------|------|
| PA2~PA6 | 时钟引脚 (ROSC/LFXIN/HFXIN)，默认未焊接 |
| PA19,PA20 | SWD 调试接口，不可复用 |
| PA10,PA11 | UART0 与 I2C1 冲突，二选一 |

---

## 工程目录详解

```
workspace_ccstheia/
├── mpu6050_clean/               [基线工程 - 推荐入门]
│   ├── main.c                     系统初始化 + 主循环
│   ├── pid_ctrl.c/h               增量式速度PI + 航向PD
│   ├── oled.c/h                   SSD1306 I2C 驱动
│   ├── mpu_port.c/h               MPU6050 DMP 移植层
│   ├── encoder.c/h                编码器 4倍频解码
│   ├── motor.c/h                  电机 PWM + 方向控制
│   └── empty.syscfg               SysConfig 引脚配置
│
├── imu601/                       [IMU601 UART方案 + 90度转弯]
│   ├── empty.c                     直行 + 原地旋转
│   ├── imu601.c/h                  ATKP 协议解析
│   └── motor.c/h                  电机控制
│
├── jdy31_pid_test/               [蓝牙 PID 在线调参]
│   ├── main.c                     BLE 通信 + PID 修改
│   └── _jdy31_docs/              JDY-31 AT 指令
│
├── servo_test/                   [舵机云台]
│   ├── main.c                     MPU6050 -> 舵机随动
│   └── gimbal.c/h                 云台限幅/平滑
│
├── test_2/                       [K230 视觉追踪 - 双芯全功能]
│   ├── empty.c                     UART接收 + 舵机跟踪
│   ├── k230_servo_track.py        色块追踪脚本
│   ├── k230_shape_detect.py       形状检测脚本
│   └── docs/                      通信协议文档
│
├── mpu6050/                      [MPU6050 原始工程]
├── my_TI/                        [基础外设测试]
├── test_1/                       [PID 参数调优]
├── empty_LP_MSPM0G3507_nortos_ticlang/  [空工程模板]
│
└── .vscode/
    └── c_cpp_properties.json     [IntelliSense 依赖库配置]
```

---

## 推荐学习路径

```
第1步: mpu6050_clean   (1-2天)  -> 编码器+PWM+PID底盘控制基础
第2步: imu601          (1天)    -> UART vs I2C IMU方案 + 转弯PID
第3步: jdy31_pid_test  (0.5天)  -> 蓝牙透传 + 在线改PID
第4步: test_2           (2-3天)  -> K230+MSPM0G全链路 + LAB色块校准
```

---

## Claude Code Skill 完整指南

本仓库配套 Claude Code Skill (`.claude/skills/mspm0g-contest/`)，提供 12 个外设模块驱动模板 + 完整引脚映射 + API 黑名单。

### 加载方式

打开仓库文件夹，Claude Code 自动识别。输入 `/mspm0g-contest <需求>`。

### 常用命令

| 场景 | 命令 | 输出 |
|------|------|------|
| 引脚分配 | `/mspm0g-contest 引脚分配` | 完整引脚表 (含 IOMUX) |
| PWM 驱动 | `/mspm0g-contest 输出TIMG8 PWM` | motor.c/h 可编译 |
| I2C 驱动 | `/mspm0g-contest OLED驱动` | SSD1306 完整驱动 |
| UART | `/mspm0g-contest K230通信` | FF FE 帧解析 |
| PID | `/mspm0g-contest PID参数` | 增量式 + 级联 PID |
| MPU6050 | `/mspm0g-contest MPU6050读取Yaw` | DMP 初始化 + 读取 |
| K230 | `/mspm0g-contest K230找色块` | LAB 检测 + UART |
| 真题 | `/mspm0g-contest 25E方案` | 解题思路 + 代码框架 |

### Skill 参考文档

| 文档 | 内容 | 何时需要 |
|------|------|---------|
| SKILL.md | 开发铁律、API黑名单、参数速查 | 所有场景 |
| pins.md | 完整引脚映射 + 硬件接线 | 分配外设 |
| gpio.md | GPIO 输入/输出/中断 | 按键/LED/编码器 |
| pwm.md | TIMG/TIMA PWM + 舵机 | 电机/舵机 |
| adc.md | ADC 单通道/多通道 | 电池/激光 |
| uart.md | UART + K230通信 + 帧解析 | 串口/双芯 |
| i2c.md | I2C OLED + MPU6050 | 显示/IMU |
| pid.md | PID + 卡尔曼 + 电机 | 闭环控制 |
| encoder.md | 编码器 QEI 解码 | 速度/位置 |
| k230.md | K230 API + 43条已知问题 | K230开发 |
| contest.md | 25E/24H/23E 真题方案 | 赛前准备 |
| tools.md | 烧录/SysConfig/VOFA+/WDT | 工具链 |

---

## PID 调参指南

### 速度 PI (增量式，20ms 周期)

| 步骤 | 操作 | 效果 |
|------|------|------|
| 1 | Kp=1.0, Ki=0 | 能跟上，有稳态误差 |
| 2 | Kp -> 3~5 | 响应加快 |
| 3 | Ki -> 0.5~1.5 | 消除稳态误差 |
| 4 | 如振荡，减小Kp/Ki | 稳定 |

### 转弯 PID (IMU601，原地旋转)

```c
#define TURN_KP     2.5f   // 比例: 响应速度
#define TURN_KI     0.0f   // 积分固定为0, 避免饱和
#define TURN_KD     1.2f   // 微分: 陀螺Z轴阻尼
#define TURN_MIN_PWM 800   // 最小PWM不能为0
#define TURN_TIMEOUT 3000  // 超时保护(ms)
```

### 蓝牙在线调参

```
手机 BLE -> JDY-31(9600) -> UART -> MSPM0G
发送 "KP 3.5" -> 修改速度Kp
发送 "KI 1.2" -> 修改速度Ki
```

---

## K230 视觉方案

### 开发铁律 Top 10

| # | 铁律 | 错误 | 正确 |
|---|------|------|------|
| 1 | Sensor(id=2) | Sensor(width=320,height=240) | Sensor(id=2) |
| 2 | Display优先 | 乱序 | Display.init->MediaManager.init->sensor.run |
| 3 | PWM仅2参数 | PWM(channel=2,freq=50) | PWM(2,50) |
| 4 | GPIO先FPIOA | Pin(46,OUT) | fpioa.set_function(); Pin(46,OUT) |
| 5 | Pin输出 | pin.high() | pin.value(1) |
| 6 | ADC仅1.8V | 直接测电池 | 必须分压 |
| 7 | Timer软定时 | Timer(0) | Timer(-1) |
| 8 | LAB现场校准 | 自然光阈值 | 场地灯光下重校准 |
| 9 | 帧率优化 | 800x480全帧 | ROI + stride + 隔帧 |
| 10 | f-string | f"x={x}" | "x=%d" % x |

> 完整 43 条已知问题见 `k230.md`

### 双芯通信帧 (Wheeltec 兼容)

```
K230 -> MSPM0G, 9600 8N1:
FF FE pan tilt 00 00 00 BCC
BCC = Byte0 ^ Byte1 ^ ... ^ Byte7
```

---

## 常见问题排查

| 现象 | 原因 | 排查 |
|------|------|------|
| 电机不转 | PWM未启动/方向错/电池没电 | DL_TimerG_startCounter(); 检查TB6612方向 |
| 小车跑偏 | 左右速差/漏脉冲/机械不对称 | OLED对比速度; 调BALANCE_KP |
| OLED不亮 | I2C地址错/引脚错 | 确认0x3C; PA28/PA31 |
| Yaw漂移 | 电源噪声/DMP未校准 | 加电容; 静置2秒; 换IMU601 |
| K230无数据 | 未共地/波特率/帧格式 | 必须共地; 必须9600 |
| Flash失败 | SWD松动/低功耗/RDP锁 | 检查PA19/20; RESET法; Mass Erase |

---

## API 安全黑名单

以下 API 在 SDK 2.10.00.04 中**不存在**：

| 不存在 API | 正确替代 |
|-----------|---------|
| DL_GPIO_setDirection() | SysConfig 配置 |
| DL_ADC12_readMemResult() | DL_ADC12_getMemResult() |
| DL_I2C_transmitBlocking() | DL_I2C_fillControllerTXFIFO() + startTransfer() |
| DL_I2C_isBusy() | DL_I2C_getControllerStatus() & BUSY |
| DL_I2C_startControllerTransfer(i2c,dir,len) | **缺addr!** 正确: (i2c,addr,dir,len) |
| DL_TimerG_setPeriod() | SysConfig 中设置 |
| DL_TimerG_getCounterValue() | DL_TimerG_getTimerCount() |
| DL_SPI_transferBlocking() | DL_SPI_transmitDataBlocking8/16/32() |
| DL_WDT_feed(WDT) | DL_WWDT_restart(WWDT0_INST) |

**可用定时器**: 仅 TIMG0, TIMG6, TIMG7, TIMG8, TIMG12, TIMA0

---

## 安全提醒

- 舵机独立供电, 不能从 XDS110/USB 取电
- K230 ADC 仅 1.8V, 超压烧芯片, 必须分压
- K230 <-> MSPM0G 通信必须共地
- 看门狗在主循环喂, 禁止在中断中喂
- PA10/PA11=UART0/I2C1二选一, PA2~6绝对勿用

---

## 依赖清单

| 依赖 | 版本 | 必需 |
|------|------|------|
| MSPM0 SDK | 2.10.00.04 | 是 |
| TI Arm Clang | 2.1.3+ | 是 |
| SysConfig | 1.20+ | 是 |
| XDS110 驱动 | -- | 是 |
| InvenSense eMPL | -- | 仅MPU6050 |
| CanMV | canmv_k230 | 仅K230 |

---

## 致谢

- [TI MSPM0 SDK](https://www.ti.com/tool/MSPM0-SDK) — MCU 驱动库
- [InvenSense eMPL](https://invensense.tdk.com/) — MPU6050 DMP
- [正点原子 IMU601](https://www.alientek.com/) — UART 无漂移 IMU
- [嘉楠科技 K230](https://developer.canaan-creative.com/) — RISC-V 视觉芯片
- [Wheeltec](https://www.wheeltec.net/) — 双芯通信协议参考
- 天猛星 MSPM0G3507 开发板 — 硬件平台

---

## License

MIT License — 详见 [LICENSE](LICENSE)

---

> **全国大学生电子设计竞赛加油！** 如果对你有帮助请给 Star
> 有问题欢迎提 Issue，或用 Claude Code 加载 Skill 直接提问。
