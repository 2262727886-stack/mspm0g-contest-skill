# PID 调试助手工程

MSPM0G3507 小车 PID 调试助手，支持 PA25 启停按键和 UART0 串口调参。

## 硬件配置

| 外设功能 | 芯片/模块型号 | 天猛星引脚 | IOMUX索引 | 片上复用功能 | 备注 |
|----------|--------------|-----------|-----------|-------------|------|
| 右轮 PWM | TB6612FNG | PB15 | PINCM43 | TIMG8_C0 | A 通道 |
| 左轮 PWM | TB6612FNG | PB16 | PINCM44 | TIMG8_C1 | B 通道 |
| 右轮 AIN1 | TB6612FNG | PA13 | PINCM10 | GPIO | 方向控制 |
| 右轮 AIN2 | TB6612FNG | PA12 | PINCM9 | GPIO | 方向控制 |
| 左轮 BIN1 | TB6612FNG | PB0 | PINCM19 | GPIO | 方向控制 |
| 左轮 BIN2 | TB6612FNG | PB1 | PINCM20 | GPIO | 方向控制 |
| 右轮编码器 A | MG310 | PA15 | PINCM37 | GPIO | 双边沿中断 |
| 左轮编码器 A | MG310 | PA17 | PINCM39 | GPIO | 双边沿中断 |
| OLED SDA | SSD1306 | PA28 | PINCM45 | I2C0_SDA | 0x3C |
| OLED SCL | SSD1306 | PA31 | PINCM48 | I2C0_SCL | 400kHz |
| 调试 TX | CH340 | PA10 | PINCM6 | UART0_TX | 115200 |
| 调试 RX | CH340 | PA11 | PINCM7 | UART0_RX | 115200 |
| 启动按键 | 轻触开关 | PA25 | PINCM42 | GPIO | 上拉输入 |
| LED | 板载 | PB22 | PINCM53 | GPIO | 状态指示 |

## 文件结构

```
pid_tuner_car/
├── main.c              ← 主程序
├── motor.h / motor.c   ← TB6612FNG 电机驱动
├── encoder.h / .c      ← 编码器测速
├── pid_ctrl.h / .c     ← PID 控制器 + 串口协议
├── oled.h / oled.c     ← SSD1306 OLED 驱动
├── i2c_utils.h / .c    ← I2C 工具函数
├── delay.h / delay.c   ← 延时函数
├── empty.syscfg        ← SysConfig 引脚配置
└── startup_mspm0g350x_ticlang.c ← 启动文件
```

## 串口调参协议

串口配置：COM5, 115200, 8N1

| 命令 | 含义 | 示例 |
|------|------|------|
| `SET P:3.0000 I:1.0000 D:0.0000` | 设置 PID 参数 | `SET P:5.0000 I:2.0000 D:0.0000` |
| `TARGET L:60 R:60` | 设置目标速度 | `TARGET L:80 R:80` |
| `STATUS` | 查询当前状态 | |
| `RESET` | 重置 PID | |
| `STOP` | 停止电机 | |

## CSV 输出格式

每 80ms 输出一次 CSV 数据（兼容 PID 调试助手）：

```
timestamp_ms,speed_L,speed_R,target_L,target_R,pwm_L,pwm_R,Kp,Ki
1200,58,59,60,60,780,790,3.0,1.0
```

## 调参建议

1. **测最大速度**: 发送 `TARGET L:999 R:999`
2. **设目标**: `T=上限*0.9`
3. **P-only**: `SET P:5.0000 I:0.0000 D:0.0000`
4. **加积分**: `SET P:5.0000 I:2.0000 D:0.0000`
5. **防振荡**: 降 P 或加 D
