# MSPM0G 电赛开发助手

MSPM0G3507 (天猛星) + K230 (庐山派) 双芯架构 25E 电赛完整参考。

## Skill 使用教程

在 Claude Code 中输入 `/mspm0g-contest` 加载完整电赛开发知识库。

### 常用指令

| 输入 | 功能 |
|------|------|
| `/mspm0g-contest 引脚分配` | 天猛星全引脚映射表 + 禁止使用引脚 |
| `/mspm0g-contest GPIO` | GPIO 输出/输入/中断代码模板 |
| `/mspm0g-contest PWM` | TIMG/TIMA PWM 配置 + 舵机 + TB6612 |
| `/mspm0g-contest 编码器` | 编码器轮询 + TIMG QEI |
| `/mspm0g-contest I2C` | OLED SSD1306 / MPU6050 驱动 |
| `/mspm0g-contest UART` | printf 重定向 / K230 通信 |
| `/mspm0g-contest ADC` | TCRT5000 循迹 8路采样 |
| `/mspm0g-contest PID` | PID 速度闭环 + 串口调参 + VOFA+ |
| `/mspm0g-contest 舵机` | 众灵PM/ZP系列 + SG90/MG996R 50Hz 角度控制 |
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
| **K230** | find_blobs 色块追踪 + LAB自动校准 | ✅ 实机 |
| **K230** | shape_detect 形状分类(矩/三角/圆) | ✅ 实机 |
| **K230** | UART→M0G FF FE 8字节帧 (9600) | ✅ 实机 |
| **K230** | TOUCH 触摸屏校准/菜单/调参 | ✅ 实机 |
| **M0G** | BSL 串口烧录 (UniFlash+CH340) | ✅ 实机 |
| **M0G** | UART0 printf (PA10/PA11 CH340) | ✅ 实机 |
| **M0G** | LED (PB22) | ✅ 实机 |
| **M0G** | OLED SSD1306 I2C0 (PA28/PA31) | ✅ 实机 |
| **M0G** | TB6612 电机驱动 (双通道) | ✅ 实机 |
| **M0G** | 编码器轮询 (GMR 500PPR) | ✅ 实机 |
| **M0G** | PID 速度闭环 + 串口调参 + VOFA+ | ✅ 实机 |
| **M0G** | **PID 位置-速度级联 + 航向PD 直线行走** | ✅ 实机 |
| **M0G** | 舵机 TIMA0 PWM (PB8/PB9) | ✅ 实机 |
| **M0G** | 拓展板全引脚 SysConfig | ✅ 验证 |
| **M0G** | SDK API 黑名单 17 条 | ✅ dl_xxx.h确认 |
| **M0G** | 12 个 G3507 裸机 driverlib 例程 | ✅ 已验证 |
| **M0G** | 按键 K1/K2 / 蜂鸣器 / ADC 循迹 | 🟡 待测 |
| **双芯** | K230→M0G UART FF FE 帧联调 (9600) | ✅ 实机 |
| **双芯** | K230色块追踪 → M0G舵机随动 | ✅ 实机 |

## 关键引脚

| 外设 | 天猛星引脚 | 说明 |
|------|-----------|------|
| CH340 串口 | PA10(TX), PA11(RX) | UART0, 115200 |
| OLED I2C0 | PA28(SDA), PA31(SCL) | SSD1306 |
| TB6612 PWM | PB15(PWMA), PB16(PWMB) | TIMG8, 20kHz |
| TB6612 方向 | PA13(AIN1), PA12(AIN2), PB0(BIN1), PB1(BIN2) | GPIO |
| 编码器A | PA15(A), PA16(B) | GPIO 双边沿中断 |
| 编码器B | PA17(A), PA24(B) | TIMG7 QEI |
| 舵机 | PB8(CH0), PB9(CH1) | TIMA0, 50Hz PWM |
| K230通信 | PB2(TX), PB3(RX) | UART3, 9600 |
| LED/蜂鸣器 | PB22/PB17 | GPIO |

## SDK API 黑名单 (17 条)

基于 TI MSPM0 SDK 2.10.00.04 dl_xxx.h 逐项确认，详见 SKILL.md。

| 禁用 API | 正确替代 |
|----------|---------|
| `DL_GPIO_setDirection()` | `DL_GPIO_initDigitalOutput/Input(PINCMxx)` |
| `DL_GPIO_setInternalResistor()` | `DL_GPIO_setDigitalInternalResistor(PINCMxx, ...)` |
| `DL_ADC12_readMemResult()` | `DL_ADC12_getMemResult()` |
| `DL_I2C_transmitBlocking()` | `DL_I2C_fillControllerTXFIFO()` + `DL_I2C_startControllerTransfer()` |
| `DL_TimerG_getCounterValue()` | `DL_TimerG_getTimerCount()` |
| `DL_TimerG_setCaptureCompareValue(TIMA0, ...)` | `DL_TimerA_setCaptureCompareValue(TIMA0, ...)` — TIMA0 是 TimerA 实例 |

## K230→MSPM0G UART 通信协议

FF FE WHEELTEC, 9600 8N1, 8字节帧。

```
[0xFF][0xFE][PAN][TILT][0x00][0x00][0x00][BCC]
 PAN: 1字节, TILT: 1字节, BCC = 前7字节 XOR
```

| 链路 | K230 引脚 | MSPM0G 引脚 |
|------|----------|------------|
| TX→RX | GPIO3 (排针8, UART1_TXD，实测稳定) | PB3 (UART3_RX) |
| GND | 任意 GND | GND |

> OLED 调试应显示 `HEAD` 和 `FRAME` 持续递增，`RAW` 含 `FF FE`。先用 `k230_uart_all_test.py` 识别物理 TX 引脚，再用 `k230_wheeltec_track.py` 跑追踪。

## 模块例程

| 模块 | 路径 | 状态 |
|------|------|------|
| K230 UART全通道测试 | `workspace_ccstheia/test_2/k230_uart_all_test.py` | ✅ 引脚识别 |
| K230 WHEELTEC追踪 | `workspace_ccstheia/test_2/k230_wheeltec_track.py` | ✅ FF FE 9600 |
| K230 形状检测 | `k230_shape_detect.py` | ✅ 触屏菜单 |
| K230 触屏调参 | `k230_touch_tuner.py` | ✅ |
| M0G 云台接收 | `workspace_ccstheia/servo_test/main.c` | ✅ FF FE解析 |
| M0G 云台驱动 | `workspace_ccstheia/servo_test/gimbal.c` | ✅ PM270/180 |
| M0G 25E接收 | `m0g_25e_receiver.c` | ✅ UART3中断 |
| PID 速度闭环 | `Documents/model/PID_Speed/` | ✅ 完整可编译 |
| PID 级联控制 | `workspace_ccstheia/test_2/` | ✅ 位置-速度+航向PD |
| TB6612 电机 | `Documents/model/TB6612_Verified/` | ✅ |
| 编码器轮询 | `Documents/model/Encoder_Poll/` | ✅ |
| OLED I2C | `workspace_ccstheia/test_2/` | ✅ |

## 舵机选型

| 型号 | 类型 | 角度 | 协议 | 扭矩范围 |
|------|------|------|------|----------|
| 众灵 PM 系列 | **纯 PWM 舵机** | 270° (默认) / 180° | 50Hz PWM, 500~2500μs | 10~80 kg·cm |
| 众灵 ZP 系列 | **串行总线舵机** | 270° | UART 115200, `#XXXPYYYYTZZZZ!` | 10~80 kg·cm |
| SG90 | PWM 舵机 | 180° | 50Hz PWM, 500~2500μs | 1.5 kg·cm |
| MG996R | PWM 舵机 | 180° | 50Hz PWM, 500~2500μs | 10 kg·cm |

**PM 系列 (PWM 舵机)**：三线接口（棕=GND, 红=VCC, 黄/白=信号），与 SG90/MG996R 相同的 50Hz PWM 协议，可直接替换。电压: PM10=4~6V, PM15-45=5~8.4V, PM60-80=5~13V。

**ZP 系列 (串行总线舵机)**：内置 MCU，单线 UART 半双工，255 个舵机共享一条总线。协议格式: `#XXXPYYYYTZZZZ!`（XXX=ID, YYYY=PWM值500~2500, ZZZZ=执行时间0~65535ms）。多舵机动作组: `{#0P1500T1000!#1P2000T0500!}`。停止: `$DST!`。波特率 115200。官方控制器源码(2017-08 V2.0)仅含基本角度/时间/停止指令，`PRAD/PULK/PMOD` 等扩展命令因固件版本差异可能不可用，实测前先用基础指令验证。
