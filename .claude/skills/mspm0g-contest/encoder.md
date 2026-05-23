# 编码器

## MG310 编码器参数

| 参数 | 霍尔编码器 | GMR编码器 |
|------|-----------|----------|
| 输出轴 PPR | 13×20.409≈265 | 500×20.409≈10204 |
| 减速比 | 1:20.409 | 1:20.409 |
| 车轮周长 | π×4.8cm≈15.08cm | 同 |
| 供电 | 3.3V/5V | 3.3V/5V |

## ⚠️ 编码器与左右轮映射铁律

| 编码器 | 电机/车轮 | A相引脚 | B相引脚 | 片上功能 | 方案 |
|--------|----------|---------|---------|---------|------|
| **编码器A** | **右轮** | PA15 | PA16 | TIMA1_CH0/CH1 (不支持QEI) | GPIO双边沿中断 |
| **编码器B** | **左轮** | PA17 | PA24 | TIMG7_CH0/CH1 (支持QEI) | TIMG7正交编码 |

> TIMA1 不支持 Encoder Mode (QEI)，所以右轮编码器只能用 GPIO 中断软件解码。
> 每次生成代码前先问用户编码器A/B分别对应哪个轮子。

## 编码器 A (右轮) — GPIO 双边沿中断 (PA15/PA16)

```c
// PA15=A相, PA16=B相 — GPIO 双边沿中断, 4倍频
volatile int32_t enc_a_count = 0;  // 右轮编码器 (PA15=A相, PA16=B相)

// SysConfig: GPIO_ENC_A → PA15/PA16 → INPUT + PULL_UP + 双边沿中断
void GROUP1_IRQHandler(void) {
    uint32_t st = DL_GPIO_getEnabledInterruptStatus(GPIOA,
                    DL_GPIO_PIN_15 | DL_GPIO_PIN_16);
    uint8_t a = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_15) != 0);
    uint8_t b = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16) != 0);

    if (st & DL_GPIO_PIN_15) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_15);
        if (a == b) enc_a_count++; else enc_a_count--;
    }
    if (st & DL_GPIO_PIN_16) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_16);
        if (a != b) enc_a_count++; else enc_a_count--;
    }
}

int32_t encoder_a_read(void) {
    int32_t v;
    __disable_irq(); v = enc_a_count; __enable_irq();
    return v;
}
void encoder_a_reset(void) { enc_a_count = 0; }
```

## 编码器 B (左轮) — TIMG7 QEI 正交编码 (PA17/PA24)

```c
// 左轮编码器: PA17=TIMG7_CH0, PA24=TIMG7_CH1 — 硬件QEI自动计数
// SysConfig: TIMG7 → Encoder Mode → 双边沿4倍频

int32_t encoder_b_read(void) {
    return (int32_t)DL_TimerG_getTimerCount(TIMG7);
}

void encoder_b_reset(void) {
    DL_TimerG_setTimerCount(TIMG7, 0);
}
```

## 距离换算

```c
#define WHEEL_CIRCUMFERENCE  15.08f  // π×4.8cm (MG310 48mm轮胎)
#define ENCODER_PPR_A        265     // 霍尔编码器: 13×20.409
// #define ENCODER_PPR_A    10204   // GMR编码器版(高精度)

float pulses_to_cm(int32_t pulses, uint16_t ppr) {
    return (float)pulses / ppr * WHEEL_CIRCUMFERENCE;
}

// 速度计算 (在1ms定时中断中):
// static int32_t last_enc;
// int32_t diff = enc - last_enc;
// float speed_cm_s = pulses_to_cm(diff, PPR) / 0.001f;
// last_enc = enc;
```

## 编码器轮询示例 (无中断方案)

```c
// 适用于编码器无中断引脚时的轮询方案
// 注意: 需 ≥1kHz 轮询频率, 否则高速丢脉冲

typedef struct {
    uint8_t  last_a, last_b;
    int32_t  count;
} EncoderPoll;

void encoder_poll_update(EncoderPoll *enc, uint32_t port, uint32_t pin_a, uint32_t pin_b) {
    uint8_t a = (DL_GPIO_readPins(port, pin_a) != 0);
    uint8_t b = (DL_GPIO_readPins(port, pin_b) != 0);
    if (a != enc->last_a) { enc->count += (a == b) ? 1 : -1; }
    else if (b != enc->last_b) { enc->count += (a != b) ? 1 : -1; }
    enc->last_a = a; enc->last_b = b;
}
```

## EC11 旋转编码器 (拓展板未使用, 仅供参考)

```c
// EC11: A/B 相输出, 20脉冲/圈, 带按键
void EC11_Init(void) {
    DL_GPIO_initDigitalInputFeatures(PIN_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(PIN_B_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
}

int8_t EC11_GetRotation(void) {
    static uint8_t last_a = 0;
    uint8_t a = DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_xx) ? 1 : 0;
    uint8_t b = DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_xx) ? 1 : 0;
    int8_t dir = 0;
    if (a != last_a) {
        dir = (a == b) ? 1 : -1;
        last_a = a;
    }
    return dir;
}
```
