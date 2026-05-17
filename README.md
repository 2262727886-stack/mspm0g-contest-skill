# 电赛开发助手 — MSPM0G + K230 双芯方案

Claude Code skill，覆盖 **2023-2025 年三道 TI 杯电赛控制类真题**，基于 **MSPM0G3507 (天猛星)** + **立创庐山派 K230** 双芯架构，提供从外设驱动、控制算法到视觉检测、双芯通信的完整代码模板。

> **引脚来源**: 天猛星官方引脚配置表 (`docs/pinout_tmx_mspm0g3507.md`)，已验证确认。

## 安装

将 `CLAUDE.md` 复制到 Claude Code 的用户级配置目录：

```powershell
# 方式1: CLAUDE.md (推荐, 每次对话自动注入)
Copy-Item "CLAUDE.md" "$env:USERPROFILE\.claude\CLAUDE.md"

# 方式2: Skill 文件 (需 / 命令手动激活)
mkdir -Force "$env:USERPROFILE\.claude\skills"
Copy-Item "skills\mspm0g-contest.md" "$env:USERPROFILE\.claude\skills\"
```

安装后重启 Claude Code，用自然语言描述需求即可触发。Skill 会**先询问你的实际引脚接线**再生成代码，不写死引脚号。

## 覆盖内容 (~3200 行, 16 章)

### 控制算法 (MSPM0G)
| 算法 | 特性 |
|------|------|
| **PID 控制器** | 积分分离、抗饱和、位置式/增量式 |
| **滤波器** | 一阶低通、滑动平均、互补滤波、**卡尔曼滤波** |
| **电机控制** | 直流电机速度闭环、舵机、步进电机 |

### 外设驱动 (MSPM0G · TI DriverLib)
| 外设 | 内容 |
|------|------|
| GPIO | 输入/输出/中断、按键消抖、长按/短按/双击 |
| Timer | PWM(20kHz)、输入捕获(超声波/编码器)、正交编码 |
| ADC | 单通道/多通道/DMA 采样 |
| UART | printf重定向、**帧协议解析** |
| I2C | SSD1306 OLED 全功能驱动、MPU6050 读取 |
| SPI | 主机模式、SPI LCD |
| OPA | 内部运放射随器/差分放大 |

### 传感器/外设驱动
- **HC-SR04** 超声波测距 (输入捕获)
- **MPU6050** 完整驱动 + Mahony AHRS 姿态解算
- **SSD1306 OLED** framebuffer / 画点画线 / 中文显示
- **EC11** 旋转编码器 (双边沿中断)
- **4×4 矩阵按键** 扫描
- **TCRT5000 ×5** 循迹阵列 (自动校准+加权位置)

### 视觉模块 (K230 CanMV · 立创庐山派)
| 功能 | API |
|------|-----|
| 红光/绿光斑检测 | `find_blobs(LAB阈值)` |
| 靶心红色圆环检测 | `find_circles()` |
| AprilTag 3D 定位 | `find_apriltags()` |
| 黑线中线检测 | `get_regression()` |
| 矩形/A4纸检测 | `find_rects()` |
| 二维码识别 | `find_qrcodes()` |
| YOLO 自定义检测 | `YOLOv5/v8/11` |
| 图像处理 | `binary/histeq/erode/dilate/gaussian` 等 105 个方法 |
| 全功能管道 | `VisionPipeline` 类 (可切换 blob/circle/apriltag) |

### 电赛真题方案
| 年份 | 题号 | 核心方案 | 双芯分工 |
|------|------|----------|----------|
| **2025** | E — 自行瞄准 | 巡线+编码器定位+瞄准几何+同步画圆 | K230 靶心验证 / M0G 巡线云台 |
| **2024** | H — 自动行驶 | 圆弧循迹+弯直道自适应PID+定点刹车 | K230 辅助 / M0G 主导 |
| **2023** | E — 运动追踪 | 红绿双MCU+红光斑检测+视觉伺服PID | K230 视觉检测 / M0G 舵机追踪 |

### 双芯通信
- **10 字节定长帧协议** — 帧头+命令+坐标+校验
- **K230 GPIO11(UART2_TXD) ↔ M0G PA0(UART0_RX)** | 竞赛时拔 USB
- **K230 GPIO12(UART2_RXD) ↔ M0G PA1(UART0_TX)**
- **FPIOA 配置示例**

### 烧录与调试
| 方式 | 状态 | 推荐度 |
|------|------|--------|
| **XDS110** (SWD) | CLI 一键烧录 `dslite flash` | ⭐⭐⭐ 强烈推荐 |
| **J-Link** (SWD) | 同上 | ⭐⭐⭐ |
| **串口 BSL** (CH340) | ⚠️ 烧录成功但程序可能不运行 | ⭐ 不推荐 |

## 开发环境

| 芯片 | IDE/SDK | 版本 |
|------|---------|------|
| **MSPM0G3507** (天猛星) | CCS 20.x + SysConfig | MSPM0 SDK v2.10.00.04 |
| **K230** (庐山派) | CanMV IDE + MicroPython | canmv_k230 v1.0+ |

## 引脚参考

| 外设 | 天猛星引脚 | 来源 |
|------|-----------|------|
| CH340 UART0 | **PA0(TX), PA1(RX)** | 板载固定 |
| I2C0 (OLED/MPU) | **PA28(SDA), PA31(SCL)** | 官方引脚表 |
| 电机 PWM (TB6612) | **PB0, PB1** (TIMA0_C2/C3) | 官方引脚表 |
| 编码器 (MG310) | **PB2, PB3** (TIMG6) | 官方引脚表 |
| TCRT5000 ×5 | **PA24~PA27, PA29** (ADC12) | 官方引脚表 |
| 舵机 ×2 | **PA8, PA9** (TIMA1_C0/C1) | 官方引脚表 |
| EC11 | **PA16, PA17, PB4** | 避开编码器 |
| 激光/蜂鸣器 | **PA10, PA11** | GPIO |
| 矩阵按键 4×4 | **PB8~PB15** | 避开 PA 时钟区 |
| 板载 LED | **PB22** | 测试用 |
| ⚠️ 禁用 | **PA2~PA6** | 时钟引脚/未引出 |

完整引脚表见 [CLAUDE.md 第一章](CLAUDE.md) 或 [官方存档](docs/pinout_tmx_mspm0g3507.md)。

## 快速开始

### M0G 端
```c
#include "ti_msp_dl_config.h"
int main(void) {
    SYSCFG_DL_init();   // SysConfig 自动生成 (先配 UART0/GPIO/I2C0)
    __enable_irq();
    while (1) {
        // 控制逻辑
    }
}
```

### K230 端
```python
from machine import FPIOA, UART
# 必须先配 FPIOA
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

import sensor, image
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)  # 320x240, 90fps
sensor.run()
while True:
    img = sensor.snapshot()
    blobs = img.find_blobs([(30,100,15,127,0,127)], pixels_threshold=5, merge=True)
    if blobs:
        b = blobs[0]
        # 发送坐标给 M0G (10字节帧协议)
        pass
```

## 文件结构

```
mspm0g-contest-skill/
├── README.md                          # 本文件
├── CLAUDE.md                          # 用户级项目文档 (~3200行, 16章)
├── skills/
│   └── mspm0g-contest.md              # Skill 文件 (带 frontmatter)
├── docs/
│   └── pinout_tmx_mspm0g3507.md       # 天猛星官方引脚配置 (审查用)
└── modules/
    └── README.md                      # 模块索引 (13个逻辑模块)
```

## 已知问题与踩坑

| 问题 | 原因 | 解决 |
|------|------|------|
| BSL 烧录成功但程序不运行 | CRC 验证失败, 协议不可靠 | 用 XDS110/J-Link |
| PA0/PA1 开漏无串口输出 | 需外部上拉电阻 | 外接 4.7kΩ 或等 XDS110 |
| SysTick 频率错 | 默认 32MHz 非 80MHz | 配 SYSPLL 或改代码 |
| `fputs` 重复定义 | 标准库已有 | 删自定义 fputs |
| TIMA1 确认存在 | 之前误标为不存在 | 已修正为可用 |

## 参考资源

- **天猛星 Wiki**: https://wiki.lckfb.com/zh-hans/tmx-mspm0g3507/
- **庐山派 K230 Wiki**: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/
- **K230 CanMV 固件**: https://github.com/kendryte/canmv_k230
- **MSPM0 SDK**: TI Resource Explorer
- **VOFA+ 串口调试**: https://www.vofa.plus/

## 许可

MIT License — 随意用于竞赛和项目中。
