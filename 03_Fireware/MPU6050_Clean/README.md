# MSPM0G3507 智能小车底盘控制基线

> 基于 TI MSPM0G3507 的差速驱动小车底盘，集成 MPU6050 DMP 姿态解码、编码器速度闭环、PID 运动控制和 OLED 实时调试显示。

## 项目简介

这是一个面向 **TI 电赛控制类题目** 的嵌入式底盘控制基线工程。目标硬件为 **天猛星 MSPM0G3507 开发板 + TB6612FNG 电机驱动 + MG310 减速电机 + MPU6050 IMU + SSD1306 OLED**。

工程提供了一套 **开箱即用** 的小车底盘控制框架：

- **编码器速度均衡 PI**：左右轮独立增量式 PI 控制，自动修正轮径差异，实现直线行驶
- **MPU6050 DMP 姿态显示**：实时读取 Yaw 角度，仅用于观察（不参与闭环，避免漂移带偏）
- **PWM 缓启动/缓停止**：斜坡函数避免电机突变打滑
- **OLED 实时调试**：Yaw、左右轮速度、PWM 占空比一目了然
- **模块化架构**：各驱动独立 .h/.c 文件，便于移植和组合

## 硬件平台

| 组件 | 型号 | 说明 |
|------|------|------|
| MCU | MSPM0G3507 | Cortex-M0+, 80MHz, 128KB Flash / 32KB SRAM |
| 电机驱动 | TB6612FNG | 双 H 桥, A 通道=右轮, B 通道=左轮 |
| 电机 | MG310 | 带霍尔编码器的减速电机 |
| IMU | MPU6050 | 6 轴 IMU, DMP 姿态解码, I2C 接口 |
| OLED | SSD1306 | 0.96" 128×64, I2C 接口 (地址 0x3C) |
| 开发环境 | CCS Theia / VS Code | TI 官方 IDE + SysConfig 图形配置 |

## 引脚接线

### 电机与编码器

| 功能 | MSPM0G 引脚 | 外设/复用 | 备注 |
|------|-------------|----------|------|
| 右轮 PWM (PWMA) | PB15 | TIMG8_C0 | TB6612 A 通道 |
| 右轮方向 AIN1 | PA13 | GPIO | TB6612 A 通道 |
| 右轮方向 AIN2 | PA12 | GPIO | TB6612 A 通道 |
| 左轮 PWM (PWMB) | PB16 | TIMG8_C1 | TB6612 B 通道 |
| 左轮方向 BIN1 | PB0 | GPIO | TB6612 B 通道 |
| 左轮方向 BIN2 | PB1 | GPIO | TB6612 B 通道 |
| 右轮编码器 A 相 | PA15 | GPIO 双边沿中断 | 速度计数 |
| 右轮编码器 B 相 | PA16 | GPIO 输入 | 预留方向 |
| 左轮编码器 A 相 | PA17 | GPIO 双边沿中断 | 速度计数 |
| 左轮编码器 B 相 | PA24 | GPIO 输入 | 预留方向 |

### IMU、OLED 与按键

| 功能 | MSPM0G 引脚 | 外设/复用 | 备注 |
|------|-------------|----------|------|
| MPU6050 SDA | PA10 | I2C1_SDA | ⚠️ 与 UART0 TX 复用，二选一 |
| MPU6050 SCL | PA11 | I2C1_SCL | ⚠️ 与 UART0 RX 复用，二选一 |
| OLED SDA | PA28 | I2C0_SDA | 地址 0x3C |
| OLED SCL | PA31 | I2C0_SCL | 400kHz |
| 启动/停止按键 | PA25 | GPIO 上拉输入 | 按下=低电平 |
| Yaw 清零按键 | PA26 | GPIO 上拉输入 | 按下=低电平 |
| SWD 调试 | PA19 (SWDIO), PA20 (SWCLK) | SWD | 保留调试接口 |

### 禁用引脚

| 引脚 | 原因 |
|------|------|
| PA2~PA6 | 时钟引脚 (ROSC/LFXIN/HFXIN)，默认未焊接 |
| PA19 / PA20 | SWD 调试接口 |

> **⚠️ TB6612 通道映射铁律**：天猛星小车 **A 通道 = 右轮，B 通道 = 左轮**。如果你的接线相反，修改 `motor_left_set()` / `motor_right_set()` 的引脚映射即可。

## 工程结构

```
mpu6050_clean/
├── main.c                              ← 主程序：系统初始化 + 主循环 + 按键逻辑
├── pid_ctrl.h / pid_ctrl.c             ← PID 控制器：增量式速度 PI + 航向 PD
├── oled.h / oled.c                     ← SSD1306 OLED 驱动 (I2C0)
├── mpu_port.h / mpu_port.c             ← MPU6050 DMP 移植层 (I2C1)
├── i2c_utils.h / i2c_utils.c           ← I2C 底层读写封装
├── delay.h / delay.c                   ← 延时函数
├── inv_mpu.h / inv_mpu.c               ← InvenSense MPU 驱动库
├── inv_mpu_dmp_motion_driver.h / .c    ← InvenSense DMP 固件驱动
├── dmpKey.h / dmpmap.h                 ← DMP 固件数据
├── empty.syscfg                        ← SysConfig 外设配置文件
├── PINMAP.md                           ← 完整引脚映射表
├── targetConfigs/MSPM0G3507.ccxml      ← XDS110 烧录配置
└── .vscode/c_cpp_properties.json       ← VS Code 代码补全配置
```

## 模块说明

### PID 控制器 (`pid_ctrl.h` / `pid_ctrl.c`)

提供两个独立的控制器：

**1. 增量式速度 PI** — 左右轮各一个实例

```
Δu = Kp × (e(k) - e(k-1)) + Ki × e(k)
u(k) = u(k-1) + Δu
```

- 为什么用增量式？输出平滑不突变，无积分饱和突变问题，Cortex-M0+ 计算量小
- 默认参数：`Kp=2.5`, `Ki=1.0`, 输出限幅 `±1200`
- 调用方式：放在 20ms 定时循环中

**2. 航向 PD** — 带死区的 Yaw 偏差修正

```
output = Kp × error + Kd × (error - last_error)
```

- 死区 `±3°`：过滤 MPU6050 DMP 的慢漂移，只有真正转弯才触发修正
- 默认参数：`Kp=1.5`, `Kd=0.8`
- 当前版本默认不启用（DMP yaw 漂移会带偏），需要时在主循环中调用

### MPU6050 DMP (`mpu_port.h` / `mpu_port.c`)

- 通过 I2C1 (PA10/PA11) 与 MPU6050 通信
- 使用 InvenSense DMP 固件进行硬件姿态解码，CPU 开销极低
- `DMP_Init()` 初始化 DMP，`DMP_Read_Data()` 读取 Pitch/Roll/Yaw
- **注意**：PA10/PA11 与板载 CH340 (UART0) 复用，使用 MPU6050 时需断开 CH340

### OLED 显示 (`oled.h` / `oled.c`)

- SSD1306 128×64, I2C0 接口 (PA28=SDA, PA31=SCL)
- `OLED_Puts(page, col, str)` 按页显示文本
- 主循环约 10Hz 刷新，避免频繁刷屏拖慢控制

### 电机控制 (main.c 内)

- TB6612FNG 双 H 桥驱动，PWM 频率 20kHz (TIMG8)
- **PWM 反逻辑**：`compare = PWM_MAX - duty`，duty 越大转速越快
- 斜坡缓启动：每 10ms 最多变化 5 个 duty，避免突然冲击

## 快速开始

### 环境准备

1. 安装 [TI CCS Theia](https://www.ti.com/tool/CCSTHEIA) 或 VS Code + TI 插件
2. 安装 MSPM0 SDK (`mspm0_sdk_2_10_00_04` 或更高版本)
3. 安装 XDS110 调试器驱动

### 编译与烧录

> **⚠️ 烧录前必须检查引脚配置！** 打开 `empty.syscfg`，逐项确认每个外设的引脚是否与你的实际接线一致。引脚错了也能烧进去，但外设不会工作。

**方式一：CCS Theia IDE (推荐)**
1. 用 CCS Theia 打开 `mpu6050_clean` 文件夹
2. 确认 SysConfig 配置与你的硬件接线一致（特别是 I2C 和 PWM 引脚）
3. 编译：`Ctrl+B`
4. 烧录：连接 XDS110 → 点击 Debug 按钮 (F5)

**方式二：命令行 DSLite**
```bash
C:\ti\uniflash_9.5.0\dslite.bat flash \
    -c targetConfigs/MSPM0G3507.ccxml \
    -s "AutoResetOnConnect=true" \
    -s "VerifyAfterProgramLoad=2" \
    Debug/mpu6050_clean.out
```

**方式三：串口 BSL (无需调试器)**
```bash
# 1. 先生成 .txt
tiarmhex --ti_txt Debug/mpu6050_clean.out -o Debug/mpu6050_clean.txt
# 2. UniFlash → Device: MSPM0G3507 → Connection: UART → COM口 → 烧录
# 3. 按住 BSL 键 → 按 RST → 1秒后松 BSL → UniFlash 点 Start
```

### 操作说明

| 按键 | 功能 |
|------|------|
| PA25 短按 | 启动/停止小车（切换运行模式） |
| PA26 短按 | 手动清零 Yaw 显示 |

### OLED 显示

```
Y:  12.3          ← MPU6050 Yaw 角度（仅供观察）
SL: 45            ← 左轮 20ms 编码器边沿数
SR: 47            ← 右轮 20ms 编码器边沿数
L:  450           ← 左轮当前 PWM 占空比
R:  452           ← 右轮当前 PWM 占空比
RUN SPEED PID     ← 运行状态
```

## 参数调优

### 速度环 PI

| 参数 | 默认值 | 调整建议 |
|------|--------|---------|
| `SPEED_BALANCE_KP` | 3 | 太大→左右轮输出抖动，太小→速度均衡慢 |
| `SPEED_BALANCE_KI` | 1 | 太大→长时间左右摆，太小→稳态误差 |
| `SPEED_BALANCE_LIMIT` | 120 | 修正量上限，防止编码器异常时 PWM 拉爆 |
| `RUN_DUTY` | 450 | 基础前进速度，调试阶段从 220 起步 |
| `DUTY_RAMP_STEP` | 5 | 斜坡步进，越小启动越平滑 |

### 航向环 PD（可选启用）

| 参数 | 默认值 | 调整建议 |
|------|--------|---------|
| `g_dir_kp` | 1.5 | 太大→对 yaw 漂移过敏，太小→转弯修正慢 |
| `g_dir_kd` | 0.8 | 抑制突变，对慢漂移无效 |
| `g_dir_deadband` | 3.0° | 死区，过滤 yaw 慢漂移 |

## 调试建议

1. **先悬空轮子**：上电前把车架起来，避免失控冲出去
2. **编码器方向确认**：如果某轮反转，交换该通道的 BIN1/BIN2 或 AIN1/AIN2
3. **MPU6050 校准**：静止状态下观察 Yaw 是否漂移，漂移过快检查焊接和供电
4. **PWM 死区**：如果电机在低 duty 不转，增大 `PWM_DEAD`
5. **VOFA+ 调试**：通过 PA0/PA1 (UART0) 输出波形数据，波特率 115200

## 相关工程

本工程是 `workspace_ccstheia` 工作区中的核心基线，其他工程在此基础上扩展：

| 工程 | 说明 | 状态 |
|------|------|------|
| `mpu6050_clean` | **本工程** — 底盘控制基线 | ✅ 实机验证 |
| `imu601` | IMU601 UART 模块版，增加 90° 原地转弯 | ✅ 实机验证 |
| `jdy31_pid_test` | JDY-31 蓝牙遥控 + PID 在线调参 | ✅ 实机验证 |
| `servo_test` | 舵机云台 + MPU6050 姿态随动 | 🟡 开发中 |
| `test_2` | K230 视觉追踪 + 双芯 UART 通信 | ✅ 实机验证 |

## 依赖

- **MSPM0 SDK**: `mspm0_sdk_2_10_00_04` (TI 官方)
- **InvenSense eMPL**: MPU6050 DMP 固件驱动 (已包含在工程中)
- **工具链**: TI Arm Clang (`tiarmclang`)
- **调试器**: XDS110 (SWD)

## 已知限制

1. **MPU6050 DMP Yaw 漂移**：DMP 输出的 Yaw 会随时间缓慢漂移（约 1°/s），因此当前版本 Yaw 仅用于显示，不参与闭环控制。如需航向闭环，建议使用 IMU601（UART 输出，无漂移问题）。
2. **PA10/PA11 复用冲突**：MPU6050 (I2C1) 与 CH340 调试串口 (UART0) 共用 PA10/PA11，不能同时使用。调试时可用 PA0/PA1 做软件 UART。
3. **编码器仅计数不判向**：当前只统计 A 相双边沿数量，不区分正反转。后续可加入 B 相解码实现方向判断。

## 致谢

- PID 控制器迁移自 [ZLC_MSPM0_Peripheral_Library](https://github.com/) (ZLC_PID.c)，原作者 Zhijian Li, Shandong University
- MPU6050 DMP 驱动基于 InvenSense eMPL 开源库
- 硬件参考天猛星 MSPM0G3507 开发板设计

## 许可证

MIT License - 详见 [LICENSE](LICENSE)

---

> **电赛加油！** 🚗💨
