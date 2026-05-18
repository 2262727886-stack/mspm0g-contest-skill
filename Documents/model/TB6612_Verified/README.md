# TB6612 直流电机驱动例程 (✅ 实测验证)

## 硬件连接

| TB6612 | MSPM0G3507 | 说明 |
|--------|-----------|------|
| PWMA | PB15 | TIMG8 CH0 PWM, 8kHz |
| PWMB | PB16 | TIMG8 CH1 PWM |
| AIN1 | PA13 | A通道方向1 |
| AIN2 | PA12 | A通道方向2 |
| BIN1 | PB0 | B通道方向1 |
| BIN2 | PB1 | B通道方向2 |
| STBY | 3.3V | 使能(必须接高) |
| VM | 电池 7.4V | 电机电源 |
| VCC | 3.3V | 逻辑电源 |
| GND | GND | 必须共地 |

## SysConfig 配置

- TIMG8 PWM: PB15=CH0, PB16=CH1, Period=4000 (8kHz@32MHz)
- GPIO_TB6612: PA13(AIN1), PA12(AIN2), PB0(BIN1), PB1(BIN2)

## 文件

- `motor.h` — 电机驱动接口
- `motor.c` — 电机驱动实现
- `main.c` — 测试程序
- `empty.syscfg` — SysConfig 参考

## 验证状态

| 项目 | 状态 |
|------|------|
| B通道正反转 | ✅ 实测通过 |
| B通道刹车 | ✅ 实测通过 |
| A通道 | ❌ TB6612硬件故障(待换模块) |

## 使用方法

```c
#include "motor.h"

Motor_Init();
DL_TimerG_startCounter(PWM_TB6612_INST);

Motor_A(500);   // A正转 50%占空比
Motor_B(-400);  // B反转 40%占空比
Motor_Brake();  // 刹车
```
