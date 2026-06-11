# MSPM0G3507 电赛智能小车开发套件

> 基于 TI MSPM0G3507 的电赛控制类题目完整开发方案，涵盖底盘控制、IMU 姿态、视觉追踪、蓝牙遥控等全栈功能。

[![MCU](https://img.shields.io/badge/MCU-MSPM0G3507-blue)](https://www.ti.com/product/MSPM0G3507)
[![SDK](https://img.shields.io/badge/SDK-mspm0_sdk__2__10__00__04-green)](https://software-dl.ti.com/msp430/esd/MSPM0-SDK/)
[![IDE](https://img.shields.io/badge/IDE-CCS%20Theia%20/%20VS%20Code-orange)](https://www.ti.com/tool/CCSTHEIA)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

## 项目简介

本仓库是一套面向 **全国大学生电子设计竞赛（电赛）控制类题目** 的嵌入式开发方案。核心 MCU 为 TI MSPM0G3507 (Cortex-M0+, 80MHz)，搭配天猛星开发板，提供从底盘运动控制到视觉识别的完整解决方案。

### 核心能力

| 能力 | 说明 | 状态 |
|------|------|------|
| 🚗 差速底盘控制 | TB6612 + MG310 + 编码器速度闭环 | ✅ 实机验证 |
| 🧭 IMU 姿态解码 | MPU6050 DMP / IMU601 UART 双方案 | ✅ 实机验证 |
| 📐 PID 运动控制 | 增量式速度 PI + 航向 PD + 转弯 PID | ✅ 实机验证 |
| 📷 K230 视觉追踪 | 庐山派 GC2093 + LAB 色块识别 + 双芯通信 | ✅ 实机验证 |
| 📱 蓝牙遥控调参 | JDY-31 BLE + PID 在线调参 | ✅ 实机验证 |
| 🖥️ OLED 实时调试 | SSD1306 128×64 多页显示 | ✅ 实机验证 |
| 🎯 舵机云台 | TIMA0 PWM + 众灵 PM 系列舵机 | ✅ 实机验证 |

## 工程目录

```
workspace_ccstheia/
├── mpu6050_clean/      ⭐ 底盘控制基线 (推荐入门)
│   ├── main.c            主程序 + 编码器 PI + MPU6050 显示
│   ├── pid_ctrl.c        增量式速度 PI + 航向 PD 控制器
│   ├── oled.c            SSD1306 OLED 驱动
│   ├── mpu_port.c        MPU6050 DMP 移植层
│   └── ...
│
├── imu601/             🧭 IMU601 版本 (增加 90° 转弯)
│   ├── empty.c           主程序：直行 + 原地旋转
│   ├── imu601.c          IMU601 UART 驱动 (ATKP 协议)
│   ├── motor.c           电机控制模块
│   └── oled.c            OLED 驱动 (增强版)
│
├── jdy31_pid_test/     📱 蓝牙 PID 调参测试
│   ├── main.c            JDY-31 蓝牙通信 + PID 在线调参
│   ├── imu601.c          IMU601 驱动
│   └── _jdy31_docs/      JDY-31 技术文档
│
├── pid_tuner_car/      🖥️ PID 调试助手实车工程
│   ├── main.c            PA25 启停 + 20ms 速度闭环
│   ├── pid_tuner.c       UART0 CSV/SET/TARGET/STATUS 协议
│   ├── motor.c           TB6612FNG A=右轮/B=左轮
│   └── encoder.c         PA15/PA17 编码器边沿测速
│
├── servo_test/         🎯 舵机云台测试
│   ├── main.c            MPU6050 姿态 → 舵机随动
│   ├── gimbal.c          云台控制逻辑
│   └── mpu_port.c        MPU6050 移植层
│
├── test_2/             📷 K230 视觉追踪 (双芯方案)
│   ├── empty.c           MSPM0G 主控：UART 接收 + 舵机跟踪
│   ├── servo_k230.c      K230 数据解析 + 舵机控制
│   ├── k230_servo_track.py    K230 色块追踪脚本
│   ├── k230_shape_detect.py   K230 形状检测脚本
│   ├── docs/             技术文档
│   └── wheeltec_ref/     Wheeltec STM32 参考代码 (42MB)
│
├── mpu6050/            📦 MPU6050 原始工程 (未清理)
├── my_TI/              🧪 基础外设测试
│
└── .vscode/            VS Code 工作区配置
    └── c_cpp_properties.json
```

### 推荐学习路径

```
1. mpu6050_clean  ← 入门：理解底盘控制 + 编码器 + PID
2. imu601         ← 进阶：IMU601 + 转弯控制
3. jdy31_pid_test ← 调试：蓝牙遥控 + 参数整定
4. pid_tuner_car  ← 上位机：PID 调试助手 + 实车闭环
5. test_2         ← 高级：K230 视觉 + 双芯通信
```

## 硬件平台

### 核心组件

| 组件 | 型号 | 规格 |
|------|------|------|
| MCU | MSPM0G3507 | Cortex-M0+, 80MHz, 128KB Flash, 32KB SRAM |
| 电机驱动 | TB6612FNG | 双 H 桥, 1.2A 持续 / 3.2A 峰值 |
| 电机 | MG310 | 带霍尔编码器的直流减速电机 |
| IMU (方案一) | MPU6050 | 6 轴, I2C, DMP 硬件姿态解码 |
| IMU (方案二) | IMU601 (正点原子) | 6 轴, UART, 无漂移问题 |
| 视觉 | K230 庐山派 | RISC-V, GC2093 摄像头, MicroPython |
| 显示 | SSD1306 | 0.96" 128×64 OLED, I2C |
| 蓝牙 | JDY-31 | BLE 4.2, 9600 baud |
| 舵机 | 众灵 PM 系列 | 500~2500μs, 50Hz, 10-80KG |
| 调试器 | XDS110 | SWD 接口 |

### 引脚分配速查

详细引脚表见各工程的 `PINMAP.md`，核心分配如下：

| 功能 | 引脚 | 外设 |
|------|------|------|
| 右轮 PWM | PB15 | TIMG8_C0 |
| 左轮 PWM | PB16 | TIMG8_C1 |
| 右轮编码器 | PA15/PA16 | GPIO 中断 |
| 左轮编码器 | PA17/PA24 | GPIO 中断 |
| MPU6050 | PA10 (SDA), PA11 (SCL) | I2C1 |
| OLED | PA28 (SDA), PA31 (SCL) | I2C0 |
| K230 UART | PB2 (TX), PB3 (RX) | UART3, 9600 |
| 舵机 PWM | PB8, PB9 | TIMA0_C0/C1 |
| 按键 | PA25, PA26 | GPIO 上拉 |
| SWD | PA19, PA20 | 调试接口 |

> **⚠️ 禁用引脚**：PA2~PA6 (时钟)、PA19/PA20 (SWD) 不可分配给外设。

## 开发环境搭建

### 1. 安装工具链

```
TI CCS Theia    → https://www.ti.com/tool/CCSTHEIA
MSPM0 SDK       → https://software-dl.ti.com/msp430/esd/MSPM0-SDK/
XDS110 驱动     → 随 CCS Theia 自动安装
```

### 2. 克隆仓库

```bash
git clone <your-repo-url>
cd workspace_ccstheia
```

### 3. 打开工程

- **CCS Theia**: File → Open Folder → 选择 `mpu6050_clean` 等子目录
- **VS Code**: 直接打开 `workspace_ccstheia` 根目录，已配置好 `c_cpp_properties.json`

### 4. 编译烧录

```bash
# CCS Theia 中
# 1. 打开工程后自动识别 .ccsproject
# 2. Ctrl+B 编译
# 3. 连接 XDS110 → Debug 按钮烧录
```

### 5. 命令行烧录 (DSLite)

```bash
# 核心命令 (需根据实际路径修改)
C:\ti\uniflash_9.5.0\dslite.bat flash \
    -c <工程>/targetConfigs/MSPM0G3507.ccxml \
    -s "AutoResetOnConnect=true" \
    -s "VerifyAfterProgramLoad=2" \
    <工程>/Debug/<工程名>.out
```

> 完整烧录脚本 (fast_flash.bat / fast_flash.sh) 和 BSL 串口烧录方法见 `.claude/skills/mspm0g-contest/tools.md` 第十三章。

> **⚠️ 每次拿到新工程后，必须先打开 `.syscfg` 检查引脚配置是否与你的实际接线一致！**

## SysConfig 配置

每个工程包含 `.syscfg` 文件，可用 TI SysConfig 图形工具配置：

- **时钟**：SYSOSC 32MHz (默认) 或 PLL 80MHz
- **GPIO**：按键、LED、编码器、电机方向
- **PWM**：TIMG8 (电机)、TIMA0 (舵机)
- **I2C**：I2C0 (OLED)、I2C1 (MPU6050)
- **UART**：UART0 (调试)、UART3 (K230)

> **重要**：每次修改 `.syscfg` 后需重新编译，SysConfig 会自动更新 `ti_msp_dl_config.c/h`。

## PID 调参指南

### 速度环 PI (增量式)

```
适用场景：左右轮速度均衡，直线行驶
调用频率：20ms
公式：Δu = Kp × (e(k) - e(k-1)) + Ki × e(k)
```

| 步骤 | 操作 | 预期效果 |
|------|------|---------|
| 1 | `Kp=1, Ki=0` | 能跟上但有稳态误差 |
| 2 | 逐步增大 `Kp` (→3~5) | 响应加快，接近无差 |
| 3 | 加入 `Ki` (→0.5~1.5) | 消除稳态误差 |
| 4 | 如果振荡，减小 `Kp` 或 `Ki` | 稳定运行 |

### 航向环 PD (可选)

```
适用场景：保持直线不偏航
前提：MPU6050 Yaw 漂移可接受
公式：output = Kp × error + Kd × (error - last_error)
```

### 转弯 PID (IMU601 工程)

```
适用场景：原地旋转指定角度
公式：output = Kp × yaw_error + Ki × integral - Kd × gyroZ
注意：Ki 通常设为 0，避免积分饱和
```

## K230 视觉方案

### 双芯通信协议

```
K230 (庐山派)  ←—UART 9600 8N1—→  MSPM0G3507 (天猛星)
     ↓                                      ↓
  视觉识别                            舵机/电机执行
```

**FF FE WHEELTEC 帧格式**：

```
FF FE pan tilt 00 00 00 BCC
BCC = 前 7 字节 XOR 校验
```

### K230 已知问题 (Top 10)

| # | 问题 | 解决 |
|---|------|------|
| 1 | LAB 阈值不准 | 必须在场地灯光下重校准 |
| 2 | 硬件定时器不可用 | 仅 `Timer(-1)` 软件定时器 |
| 3 | PWM 构造器不支持关键字 | `PWM(2, 50)` 仅 2 个位置参数 |
| 4 | Pin 无 high()/low() | 用 `pin.value(1)` / `pin.value(0)` |
| 5 | FPIOA 必配 | 所有外设前必须 `fpioa.set_function()` |
| 6 | ADC 仅 1.8V 输入 | 超压烧毁芯片 |
| 7 | Sensor 必须 `id=2` | 庐山派 GC2093 在 CSI 2 |
| 8 | Display 初始化顺序 | Display.init → MediaManager.init → sensor.run |
| 9 | 800×480 帧率 | 用 ROI + stride + 隔帧检测 |
| 10 | f-string 不支持 | 用 `%` 格式化替代 |

> 完整 43 条已知问题见 `.claude/skills/mspm0g-contest/k230.md`

## 调试技巧

### OLED 实时监控

```c
// 显示格式示例
OLED_Puts(0, 0, "Y:12.3");     // Yaw 角度
OLED_Puts(1, 0, "SL:45 SR:47"); // 左右轮速度
OLED_Puts(2, 0, "L:450 R:452"); // PWM 占空比
OLED_Puts(3, 0, "RUN");         // 运行状态
```

### VOFA+ 波形调试

通过 UART0 (PA0/PA1) 输出数据到 VOFA+：

```c
// JustFloat 协议
float data[4] = {speed_l, speed_r, duty_l, duty_r};
DL_UART_Main_transmitData(UART0, (uint8_t*)data, 16);
```

### 常见问题排查

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| 电机不转 | PWM 未启动 | `DL_TimerG_startCounter(MOTOR_PWM_INST)` |
| 单轮反转 | 方向脚接反 | 交换 AIN1/AIN2 或 BIN1/BIN2 |
| 小车跑偏 | 左右轮速差 | 调 `SPEED_BALANCE_KP` / 检查编码器 |
| Yaw 漂移快 | MPU6050 问题 | 检查焊接/供电，或换 IMU601 |
| OLED 不亮 | I2C 地址错 | 确认 0x3C，检查 PA28/PA31 |
| K230 无数据 | 接线/波特率 | 确认 9600，检查 PB3↔GPIO3，共地 |

## Claude Code Skill

本仓库配套了一个 Claude Code Skill（位于 `.claude/skills/mspm0g-contest/`），提供：

- **完整引脚映射表**：所有外设引脚 + IOMUX + 复用功能
- **12 个外设驱动模板**：GPIO / PWM / ADC / UART / I2C / SPI / 编码器 / PID / OLED / MPU6050 / Flash / WDT
- **K230 API 速查**：43 条已知问题 + 正确用法
- **电赛真题方案**：25E 瞄准装置 / 24H 自动小车 / 23E 运动追踪
- **烧录与调试**：SysConfig / VOFA+ / Flash 烧录 / 看门狗

使用方式：

```
/mspm0g-contest 引脚分配
/mspm0g-contest PID参数
/mspm0g-contest K230找色块
/mspm0g-contest 25E方案
```

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| MSPM0 SDK | 2.10.00.04 | TI 官方 SDK |
| TI Arm Clang | 2.1.3+ | 编译工具链 |
| SysConfig | 1.20+ | 图形配置工具 |
| InvenSense eMPL | — | MPU6050 DMP 驱动 (已包含) |
| CanMV | canmv_k230 | K230 MicroPython 固件 |

## 致谢

- [TI MSPM0 SDK](https://www.ti.com/tool/MSPM0-SDK) — MCU 驱动库
- [InvenSense eMPL](https://github.com/)] — MPU6050 DMP 固件驱动
- [ZLC_MSPM0_Peripheral_Library](https://github.com/) — PID 控制器参考实现
- 天猛星 MSPM0G3507 开发板 — 硬件参考设计

## 许可证

MIT License - 详见各工程目录下的 [LICENSE](LICENSE)

---

> **全国大学生电子设计竞赛加油！** 🏆🚗💨
>
> 如果这个项目对你有帮助，请给个 Star ⭐
