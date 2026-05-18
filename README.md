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
| `/mspm0g-contest 编码器` | TIMG QEI + GPIO 双边沿中断 |
| `/mspm0g-contest I2C` | OLED SSD1306 / MPU6050 驱动 |
| `/mspm0g-contest UART` | printf 重定向 / K230 通信 |
| `/mspm0g-contest ADC` | TCRT5000 循迹 8路采样 |
| `/mspm0g-contest 超声波` | HC-SR04 输入捕获测距 |
| `/mspm0g-contest PID` | PID控制器 + 滤波器 + 卡尔曼 |
| `/mspm0g-contest 舵机` | SG90/MG996R 50Hz 角度控制 |
| `/mspm0g-contest 电机` | TB6612 + MG310 速度闭环 |
| `/mspm0g-contest OLED驱动` | SSD1306 I2C 显示驱动 |
| `/mspm0g-contest K230` | K230 摄像头 + 视觉检测 + 双芯通信 |
| `/mspm0g-contest 25E方案` | 简易瞄准装置完整方案 |
| `/mspm0g-contest 24H方案` | 自动行驶小车方案 |
| `/mspm0g-contest 23E方案` | 运动目标追踪方案 |
| `/mspm0g-contest 烧录` | XDS110/J-Link/BSL 烧录方法 |
| `/mspm0g-contest VOFA+` | VOFA+ FireWater 实时调参 |
| `/mspm0g-contest Flash` | Flash 参数存储 (校准值持久化) |
| `/mspm0g-contest 看门狗` | WWDT 配置和喂狗 |
| `/mspm0g-contest MPU6050` | 陀螺仪 DMP 姿态解算 |
| `/mspm0g-contest 矩阵按键` | 4×4 矩阵键盘扫描 |
| `/mspm0g-contest 蓝牙` | HC-05/06 UART1 无线调参 |

### 正确提问姿势

```
❌ "帮我写个电机控制"          → 不知道什么电机、什么驱动、什么引脚
✅ "TB6612驱动MG310电机，PWMA=PB15，AIN1=PA13，编码器=PA15/PA16"
```

**所有问题请带上实际引脚号**，Skill 会根据拓展板引脚生成直接可用的代码。

## 项目结构

```
├── k230_cam_test.py              # K230 视觉端 (GC2093 + A4检测 + OLED + UART)
├── k230_sensor_diag.py           # K230 摄像头诊断脚本
├── m0g_25e_receiver.c            # MSPM0G 拓展板接收框架
├── bsl_flash.py                  # BSL 串口烧录工具
├── .claude/
│   ├── CLAUDE.md                 # 开发规范
│   └── skills/mspm0g-contest/
│       └── SKILL.md              # 完整参考资料 (引脚/API/算法/真题)
└── Documents/model/              # MSPM0G 模块例程 (TB6612/SG90/OLED/MPU6050/Tracking)
```

## 验证状态

| 模块 | 子项 | 状态 |
|------|------|------|
| **K230** | GC2093 QVGA 采集 60fps | ✅ 实机 |
| **K230** | A4黑框 find_rects + OLED SSD1306 | ✅ 实机 |
| **K230** | 自动Otsu阈值校准+验证回退 | ✅ 实机 |
| **K230** | UART2→M0G 10字节帧协议 | ✅ 代码就绪 |
| **M0G** | BSL串口烧录 (UniFlash+CH340) | ✅ 实机验证 |
| **M0G** | UART0 printf (PA10/PA11 CH340) | ✅ 实机验证 |
| **M0G** | 拓展板全引脚 SysConfig | ✅ 验证 |
| **M0G** | API黑名单17条 (SDK 2.10.00.04) | ✅ dl_xxx.h逐项确认 |
| **M0G** | 11个G3507裸机driverlib例程 | ✅ 已验证 |
| **M0G** | TB6612 / 编码器 / 舵机 / ADC | 🟡 待实机 |
| **双芯** | K230→M0G UART通信联调 | 🟡 待仿真器/接线 |

## 关键引脚

### 天猛星 MSPM0G3507

| 外设 | 引脚 | 说明 |
|------|------|------|
| CH340 串口 | PA10(TX), PA11(RX) | UART0, 115200, printf调试 |
| SWD 调试 | PA19(SWDIO), PA20(SWCLK) | XDS110/J-Link |
| BSL 烧录 | PA0(TX), PA1(RX) | 开漏, BSL+UniFlash |
| OLED I2C0 | PA28(SDA), PA31(SCL) | SSD1306 |
| TB6612 PWM | PB15(PWMA), PB16(PWMB) | TIMG8, 20kHz |
| TB6612 方向 | PA13(AIN1), PA12(AIN2), PB0(BIN1), PB1(BIN2) | GPIO |
| 编码器A | PA15(A相), PA16(B相) | GPIO双边沿中断 |
| 编码器B | PA17(A相), PA24(B相) | TIMG7 QEI |
| 舵机 | PB8(CH0), PB9(CH1) | TIMA0, 50Hz |
| 超声波 | PA8(TRIG), PA9(ECHO) | TIMG12输入捕获 |
| K230通信 | PB2(TX), PB3(RX) | UART3, 115200 |
| 蓝牙 | PB6(RX), PB7(TX) | UART1 |
| 循迹 ×8 | PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7 | ADC0 |
| LED/蜂鸣器/按键 | PB22(LED), PB17(Buzzer), PA26(K1), PA25(K2) | GPIO |

### K230 庐山派

| 外设 | 引脚 | 说明 |
|------|------|------|
| 摄像头 | GPIO48(SCL), GPIO49(SDA) | I2C0, GC2093 |
| UART2→M0G | GPIO11(TXD), GPIO12(RXD) | 需 FPIOA 预配 |
| OLED | GPIO48(SCL), GPIO49(SDA) | 与GC2093共用I2C0 |
| 按键 | GPIO53 | 下拉,按下=高 |

## SDK API 黑名单 (17条, SDK 2.10.00.04 验证)

| 不存在的API | 正确替代 |
|-----------|---------|
| `DL_GPIO_setDirection()` | SysConfig配置 |
| `DL_GPIO_setInternalResistor()` | `DL_GPIO_setDigitalInternalResistor(PINCMxx, ...)` |
| `DL_TimerG_setPeriod()` | SysConfig中设Period |
| `DL_TimerG_getCounterValue()` | `DL_TimerG_getTimerCount()` |
| `DL_I2C_transmitBlocking()` | `DL_I2C_fillControllerTXFIFO()` + `startControllerTransfer()` |
| `DL_I2C_receiveBlocking()` | 同上 |
| `DL_I2C_isBusy()` | `DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_BUSY` |
| `DL_I2C_sendControllerStop()` | STOP由 `startControllerTransfer` 自动生成 |
| `DL_I2C_startControllerTransfer(i2c, dir, len)` | 缺地址! 正确: `(i2c, addr, dir, len)` |
| `DL_I2C_getControllerStatus(i2c, MASK)` | 只1参数! 正确: `getControllerStatus(i2c) & MASK` |
| `DL_I2C_CONTROLLER_STATUS_ARB_LOST` | `DL_I2C_CONTROLLER_STATUS_ARBITRATION_LOST` |
| `DL_ADC12_readMemResult()` | `DL_ADC12_getMemResult()` |
| `DL_SPI_transferBlocking()` | `DL_SPI_transmitDataBlocking8/16/32()` |
| `DL_WDT_feed/enable/setPeriod/getCount(WDT)` | `DL_WWDT_restart(WWDT0_INST)`, 配置在SysConfig |
| `DL_FlashCTL_eraseSector()` | `DL_FlashCTL_eraseMemoryFromRAM(FLASHCTL, addr, size)` |
| `DL_FlashCTL_programMemory()` | `DL_FlashCTL_programMemoryFromRAM32/64WithECCGenerated()` |
| `DL_TimerG_setCaptureCompareValue(inst, value, index)` | 参数反了! 正确: `(inst, INDEX, VALUE)` |

## 烧录方法

### BSL 串口 (已验证可用)

```
1. CCS编译 Ctrl+B
2. tiarmhex --ti_txt firmware.out -o firmware.txt
3. UniFlash → MSPM0G3507 → UART → COM5 → Load Image
4. 按住BSL键 → 按RST → 1秒松BSL → Start
5. 报错无视: "Image Loading Failed" / "Verification Failed" 均为误报
6. 拔插Type-C冷启动
```

### CCS Post-build 自动生成 .txt

```
${CCS_INSTALL_ROOT}/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/bin/tiarmhex --ti_txt ${ProjName}.out
```

## 快速开始

### K230 视觉端
1. `k230_cam_test.py` → SD卡 `/sdcard/main.py`
2. 上电 → OLED启动 → 自动Otsu校准 → A4检测 → UART发坐标

### M0G 控制端
1. CCS新建工程 → SysConfig配外设 (按 `m0g_25e_receiver.c` 注释)
2. 合并代码 → 编译 → BSL或XDS110烧录

### 已验证的CCS工程路径
```
C:/Users/Administrator/workspace_ccstheia/empty_LP_MSPM0G3507_nortos_ticlang/
```
当前已配: GPIO(LED PB22) + UART0(PA10/PA11 CH340) + TIMA0(PB8/PB9舵机)

## 模块例程 (Documents/model)

| 模块 | 目录 | 备注 |
|------|------|------|
| OLED I2C | IIC SCREEN/ | API用法完全正确 ✅ |
| MPU6050 | MPU6050/ | 软件I2C, 含DMP库 |
| TB6612 | TB6612/ | **已修正**: setCaptureCompareValue参数顺序+刹车逻辑 |
| SG90舵机 | SG90/ | **已修正**: 同参数顺序 |
| 循迹 | Tracking sensor/ | **已简化**: ADC读写从6行减到3行 |
