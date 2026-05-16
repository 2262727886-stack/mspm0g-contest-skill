# MSPM0G 电赛开发助手

Claude Code skill，面向 TI 杯电子设计竞赛控制类题目，基于 MSPM0G3507 MCU 快速生成初始化代码、控制算法、外设驱动和硬件连接方案。

## 安装

将 `skills/mspm0g-contest.md` 复制到 Claude Code 的用户级 skills 目录：

```powershell
# Windows PowerShell
mkdir -Force "$env:USERPROFILE\.claude\skills"
Copy-Item "skills\mspm0g-contest.md" "$env:USERPROFILE\.claude\skills\"
```

安装后重启 Claude Code 会话，skill 自动注册。使用时直接描述需求即可触发，或输入 `/mspm0g-contest` 手动激活。

## 覆盖内容

### 外设驱动
| 外设 | 内容 |
|------|------|
| GPIO | 输出/输入/中断配置 |
| Timer | PWM 输出、输入捕获、编码器模式、精确延时 |
| ADC | 单通道/多通道/DMA 采样 |
| UART | 调试串口、printf 重定向、协议帧解析 |
| I2C | OLED SSD1306 驱动、MPU6050 读取 |
| SPI | 主机模式传输 |
| OPA | 内部运放射随器/差分放大 |
| HC-SR04 | 超声波测距 (输入捕获) |
| EC11 | 旋转编码器 (双边沿中断) |
| 矩阵按键 | 4×4 扫描 |

### 控制算法
- PID 控制器 (位置式/增量式, 积分分离, 抗饱和)
- 一阶低通 / 滑动平均 / 互补滤波
- 卡尔曼滤波 (1D)
- Mahony AHRS 姿态解算 (MPU6050)
- 直流电机速度闭环 / 舵机 / 步进电机控制

### 调试工具
- VOFA+ FireWater 协议 (实时多变量波形)
- SerialPlot 兼容格式
- 串口文本协议在线调 PID 参数
- 按键短按/长按/双击识别
- OLED 实时数据显示

### 硬件连接
- TB6612 电机驱动模块接线
- MPU6050 / SSD1306 OLED / HC-05 蓝牙接线
- 电源设计注意事项

## 开发环境

- **MCU:** TI MSPM0G3507 (LQFP48)
- **IDE:** Code Composer Studio (CCS) + SysConfig
- **SDK:** TI MSPM0 SDK (DriverLib)
- **调试器:** XDS110 / 板载 SWD

## 快速开始

```c
#include "ti_msp_dl_config.h"

int main(void) {
    SYSCFG_DL_init();   // SysConfig 自动生成
    __enable_irq();

    while (1) {
        // 你的控制逻辑
    }
}
```

## 许可

MIT License — 随意用于竞赛和项目中。
