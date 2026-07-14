# 03_Fireware

MSPM0G3507 固件工程（Cortex-M0+ 裸机开发，TI Arm Clang 编译）。

## 目录结构

### 核心竞赛工程

| 目录 | 说明 | 状态 |
|------|------|------|
| `MPU6050_Clean/` | 底盘控制基线工程（推荐入门） | 已验证 |
| `IMU601/` | IMU601 UART 方案 + 90度原地旋转 | 已验证 |
| `K230_Vision_Track/` | K230 视觉追踪双芯全功能方案 | 已验证 |
| `PID_Tuner_Car/` | PID 调试助手实车工程 | 已验证 |
| `Servo_Test/` | 舵机云台 MPU6050 姿态随动 | 已验证 |
| `JDY31_PID_Test/` | 蓝牙 BLE PID 在线调参 | 已验证 |
| `Basic_Periph/` | 基础外设测试工程 | 参考 |
| `MPU6050_Base/` | MPU6050 原始工程（未清理版本） | 参考 |

### 竞赛方案

| 目录 | 说明 |
|------|------|
| `Contest/25E_Receiver/` | 2025 全国大学生电子设计竞赛 E 题接收端方案 |

### 外设参考驱动

| 目录 | 说明 |
|------|------|
| `Periph_Ref/` | 逐个外设的独立驱动参考（非完整竞赛工程） |

## 开发环境

- **IDE**: TI CCS Theia（推荐）或 VS Code
- **SDK**: MSPM0 SDK 2.10.00.04
- **编译工具链**: TI Arm Clang 2.1.3+
- **调试器**: XDS110 (SWD)

每个子目录是独立的 CCS Theia 工程，可在 IDE 中直接导入。
