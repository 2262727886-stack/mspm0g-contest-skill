# MSPM0G 电赛开发助手

MSPM0G3507 (天猛星) + K230 (庐山派) 双芯架构 25E 电赛完整参考。

## Skill 使用教程

在 Claude Code 中输入 `/mspm0g-contest` 加载完整电赛开发知识库。

### 常用指令

| 输入 | 功能 |
|------|------|
| `/mspm0g-contest 引脚分配` | 天猛星全引脚映射表 + 禁止使用引脚 |
| `/mspm0g-contest GPIO` | GPIO 输出/输入/中断代码模板 |
| `/mspm0g-contest PWM` | TIMG/TIMA PWM 配置+舵机+TB6612 |
| `/mspm0g-contest 编码器` | 编码器轮询+TIMG QEI |
| `/mspm0g-contest I2C` | OLED SSD1306 / MPU6050 驱动 |
| `/mspm0g-contest UART` | printf 重定向 / K230 通信 |
| `/mspm0g-contest ADC` | TCRT5000 循迹 8路采样 |
| `/mspm0g-contest PID` | **PID 速度闭环 + 串口调参 + VOFA+** |
| `/mspm0g-contest 舵机` | SG90/MG996R 50Hz 角度控制 |
| `/mspm0g-contest 电机` | TB6612 + MG310 速度闭环 |
| `/mspm0g-contest OLED驱动` | SSD1306 I2C 显示驱动 |
| `/mspm0g-contest K230` | K230 摄像头 + 视觉检测 + 双芯通信 |
| `/mspm0g-contest 25E方案` | 简易瞄准装置完整方案 |
| `/mspm0g-contest 24H方案` | 自动行驶小车方案 |
| `/mspm0g-contest 23E方案` | 运动目标追踪方案 |
| `/mspm0g-contest 烧录` | XDS110/J-Link/BSL 烧录方法 |
| `/mspm0g-contest VOFA+` | VOFA+ FireWater 实时调参 |
| `/mspm0g-contest Flash` | Flash 参数存储 |
| `/mspm0g-contest 看门狗` | WWDT 配置和喂狗 |

## Skill 安装配置

```bash
git clone https://github.com/2262727886-stack/mspm0g-contest-skill.git
cp -r mspm0g-contest-skill/.claude/skills/mspm0g-contest ~/.claude/skills/
cp mspm0g-contest-skill/.claude/CLAUDE.md ~/.claude/CLAUDE.md
```

## 验证状态

| 模块 | 子项 | 状态 |
|------|------|------|
| **K230** | GC2093 QVGA 采集 60fps | ✅ 实机 |
| **K230** | A4黑框 find_rects + A4几何中心 | ✅ 实机 |
| **K230** | OLED SSD1306 I2C0 逐页写入 | ✅ 实机 |
| **K230** | 自动Otsu阈值校准+验证回退 | ✅ 实机 |
| **K230** | UART2→M0G 10字节帧 | ✅ 代码就绪 |
| **M0G** | BSL 串口烧录 (UniFlash+CH340) | ✅ 实机 |
| **M0G** | UART0 printf (PA10/PA11 CH340) | ✅ 实机 |
| **M0G** | LED (PB22) | ✅ 实机 |
| **M0G** | OLED SSD1306 I2C0 (PA28/PA31) | ✅ 实机 |
| **M0G** | TB6612 电机驱动 (B通道) | ✅ 实机 |
| **M0G** | 编码器轮询 (GMR 500PPR) | ✅ 实机 |
| **M0G** | **PID 速度闭环 + 串口调参 + VOFA+** | ✅ 实机 |
| **M0G** | 拓展板全引脚 SysConfig | ✅ 验证 |
| **M0G** | SDK API 黑名单 17 条 | ✅ dl_xxx.h确认 |
| **M0G** | 12 个 G3507 裸机 driverlib 例程 | ✅ 已验证 |
| **M0G** | 舵机 TIMA0 PWM (PB8/PB9) | 🟡 SysConfig已配 |
| **M0G** | 按键 K1/K2 / 蜂鸣器 / ADC 循迹 | 🟡 待测 |
| **双芯** | K230→M0G UART 联调 | 🟡 待接线 |

## 关键引脚

| 外设 | 天猛星引脚 | 说明 |
|------|-----------|------|
| CH340 串口 | PA10(TX), PA11(RX) | UART0, 115200 |
| OLED I2C0 | PA28(SDA), PA31(SCL) | SSD1306 |
| TB6612 PWM | PB15(PWMA), PB16(PWMB) | TIMG8 |
| TB6612 方向 | PA13(AIN1), PA12(AIN2), PB0(BIN1), PB1(BIN2) | |
| 编码器B | PA17(A), PA24(B) | 轮询模式 |
| 舵机 | PB8(CH0), PB9(CH1) | TIMA0 |
| K230通信 | PB2(TX), PB3(RX) | UART3 |
| LED/蜂鸣器 | PB22/PB17 | GPIO |

## SDK API 黑名单 (17 条)

基于 TI MSPM0 SDK 2.10.00.04 dl_xxx.h 逐项确认，详见 SKILL.md。

## 模块例程

| 模块 | 目录 | 状态 |
|------|------|------|
| **PID 速度闭环** | Documents/model/PID_Speed/ | ✅ 完整可编译 |
| TB6612 电机 | Documents/model/TB6612_Verified/ | ✅ |
| 编码器轮询 | Documents/model/Encoder_Poll/ | ✅ |
| OLED I2C | workspace_ccstheia/test_1/ | ✅ |
