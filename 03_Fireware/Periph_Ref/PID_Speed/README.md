# PID 速度闭环 — 完整例程 (✅ 实测验证)

## 功能

- 位置式 PID + 前馈 (Base PWM)
- SysTick 10/20ms 硬件定时控制周期
- UART 串口实时调参 (P/I/D/T/B 命令)
- VOFA+ CSV 实时曲线
- PWM 步进限幅 ±4 防振荡

## 文件

| 文件 | 说明 |
|------|------|
| main.c | 主循环 + UART 命令解析 + PID 控制 |
| pid.h/c | 位置式 PID (积分限幅 + 输出限幅) |
| encoder.h/c | 编码器轮询 + 周期锁存清零 |
| motor.h/c | TB6612 直流电机驱动 |
| empty.syscfg | SysConfig 参考 |

## 硬件连接

| TB6612 | MSPM0G3507 | 编码器 | MSPM0G3507 |
|--------|-----------|--------|-----------|
| PWMA | PB15 | E2A | PA17 |
| PWMB | PB16 | E2B | PA24 |
| AIN1 | PA13 | VCC | 3.3V |
| AIN2 | PA12 | GND | GND |
| BIN1 | PB0 | | |
| BIN2 | PB1 | | |
| STBY | 3.3V | | |
| VM | 7.4V | | |

## 使用方法

1. CCS 新建工程 → 复制 empty.syscfg → SysConfig 生成
2. 添加 main.c, pid.c, encoder.c, motor.c 到工程
3. 编译 → BSL 烧录
4. 串口 COM5 115200 → 自动输出 CSV

## 调参命令

| 命令 | 含义 |
|------|------|
| `P5` | Kp = 0.5 |
| `I8` | Ki = 0.08 |
| `T42` | 目标 42 脉冲/10ms |
| `B800` | 前馈 PWM 800 |
| 回车 | 重置 PID |

## 实测参数

| 电源 | 采样 | Kp | Ki | Kd | Base | 目标 | 速度范围 |
|------|------|-----|-----|-----|------|------|---------|
| USB 5V | 20ms | 0.5 | 0.08 | 0 | 800 | 80 | 82~86 |
| 7.4V | 10ms | 0.5 | 0.08 | 0 | 800 | 42 | 41~62 |
