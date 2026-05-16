# 电赛开发助手 — MSPM0G + K230 双芯方案

Claude Code skill，覆盖 **2023-2025 年三道 TI 杯电赛控制类真题**，基于 **MSPM0G3507 (控制)** + **立创庐山派 K230 (视觉)** 双芯架构，提供从外设驱动、控制算法到视觉检测、双芯通信的完整代码模板。

## 安装

将 `skills/mspm0g-contest.md` 或 `CLAUDE.md` 复制到 Claude Code 的用户级配置目录：

```powershell
# Windows PowerShell — 使用 skill 文件
mkdir -Force "$env:USERPROFILE\.claude\skills"
Copy-Item "skills\mspm0g-contest.md" "$env:USERPROFILE\.claude\skills\"

# 或使用 CLAUDE.md (每次对话自动注入)
Copy-Item "CLAUDE.md" "$env:USERPROFILE\.claude\CLAUDE.md"
```

安装后重启 Claude Code，用自然语言描述需求即可触发。

## 覆盖内容

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
| UART | printf重定向、**帧协议解析**(帧头+长度+校验) |
| I2C | SSD1306 OLED 全功能驱动、MPU6050 读取 |
| SPI | 主机模式、SPI LCD |
| OPA | 内部运放射随器/差分放大 |

### 传感器/外设驱动 (MSPM0G)
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

### 调试工具
- **VOFA+ FireWater 协议** — 实时多变量波形调参
- **SerialPlot 兼容格式**
- **串口文本协议 PID 在线调参** — PC 端发 `P 1.5` 即改 Kp

### 电赛真题方案
| 年份 | 题号 | 核心方案 |
|------|------|----------|
| **2025** | E — 简易自行瞄准 | 巡线+编码器定位+云台瞄准几何解算+同步画圆 |
| **2024** | H — 自动行驶小车 | 圆弧循迹+弯直道自适应PID+路径规划+定点刹车 |
| **2023** | E — 运动目标追踪 | 红绿双MCU+摄像头红光斑检测+视觉伺服PID |

### K230 + M0G 双芯通信
- **10 字节定长帧协议** — 帧头+命令+坐标+校验
- **引脚连接表** — K230 GPIO11/12 ↔ M0G PA10/11
- **FPIOA 配置示例**

## 开发环境

| 芯片 | IDE/SDK |
|------|---------|
| **TI MSPM0G3507** | Code Composer Studio + SysConfig + MSPM0 SDK |
| **嘉楠 K230** (庐山派) | CanMV IDE + MicroPython + canmv_k230 固件 |

## 快速开始

### M0G 端
```c
#include "ti_msp_dl_config.h"
int main(void) {
    SYSCFG_DL_init();   // SysConfig 自动生成
    __enable_irq();
    while (1) {
        // 控制逻辑
    }
}
```

### K230 端
```python
import sensor, image
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.run()
while True:
    img = sensor.snapshot()
    blobs = img.find_blobs([(30,100,15,127,0,127)], pixels_threshold=5, merge=True)
    if blobs:
        # 发送坐标给 M0G
        pass
```

## 文件结构

```
mspm0g-contest-skill/
├── README.md                          # 本文件
├── CLAUDE.md                          # 用户级 Claude Code 项目文档 (2800+行)
└── skills/
    └── mspm0g-contest.md              # Skill 文件 (带 frontmatter)
```

## 参考资源

- **立创庐山派 K230 文档**: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/
- **K230 CanMV 固件下载**: https://github.com/kendryte/canmv_k230
- **MSPM0G SDK**: TI Resource Explorer
- **VOFA+ 串口调试**: https://www.vofa.plus/

## 许可

MIT License — 随意用于竞赛和项目中。
