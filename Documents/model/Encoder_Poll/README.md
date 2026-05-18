# GMR 编码器高速轮询方案 (✅ 实测验证)

## 背景

MSPM0G3507 GPIO 双边沿中断在编码器场景下不稳定（实测不触发）。改用主循环高速轮询方案，采样率 >1MHz，GMR 500PPR 编码器满速不漏脉冲。

## 硬件连接

| 编码器 | MSPM0G3507 |
|--------|-----------|
| E2A | PA17 |
| E2B | PA24 |
| VCC | 3.3V |
| GND | GND |

## 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| **高速轮询 (采用)** | 稳定可靠, 不依赖中断 | 占用 CPU 周期 |
| GPIO 双边沿中断 | 省 CPU | MSPM0G3507 实测不触发 |
| QEI 硬件模式 | 最省 CPU | SysConfig 仅支持 TIMG8(已被PWM占用) |

## 实测数据

- 编码器: GMR 500PPR × 20.409 减速比
- 电机: 30% 占空比, 约 0.5 转/秒
- 脉冲速率: ~5100 脉冲/秒
- 采样精度: 200ms 打印, 连续无丢脉冲

## 使用方法

```c
#include "encoder.h"

Encoder_Init();

while (1) {
    Encoder_Tick();                          // 高速轮询, 每循环调用
    int32_t count = Encoder_Read();          // 读取累计值
    // count 每 200ms 打印或用于 PID 控制
}
```

## 文件

- `encoder.h` — 编码器接口
- `encoder.c` — 高速轮询实现
- `motor.h/motor.c` — TB6612 电机驱动
- `main.c` — 编码器+电机联动测试
- `empty.syscfg` — SysConfig 参考
