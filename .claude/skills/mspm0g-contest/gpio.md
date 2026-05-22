# GPIO 输出/输入/中断

> **SDK 铁律: GPIO 方向/上下拉/中断全在 SysConfig 配置，代码只做运行时操作**

## SysConfig 配置 GPIO 输出 (LED/蜂鸣器)

```
ADD → GPIO → Pin: PB22 → Direction: Output → Initial Value: HIGH → Name: LED → 保存
ADD → GPIO → Pin: PB17 → Direction: Output → Initial Value: LOW  → Name: BUZZER → 保存
```

## SysConfig 配置 GPIO 输入 (按键)

```
ADD → GPIO → Pin: PA25 → Direction: Input → Internal Resistor: Pull-up → Name: KEY1 → 保存
```

## 运行时代码

```c
// GPIO 输出 — 必须在 PinCM 索引上初始化
DL_GPIO_initDigitalOutput(GPIO_LED_IOMUX);     // PB22
DL_GPIO_initDigitalOutput(GPIO_BUZZER_IOMUX);  // PB17

DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_22);        // LED 亮 (高电平)
DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_22);      // LED 灭
DL_GPIO_togglePins(GPIOB, DL_GPIO_PIN_22);     // LED 翻转
DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_17);        // 蜂鸣器开

// GPIO 输入 — 读取按键状态
DL_GPIO_initDigitalInputFeatures(GPIO_KEY_IOMUX,
    DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
    DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);

uint8_t key_pressed = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_25) == 0); // 上拉, 按下=0
```

## GPIO 中断配置

```c
// SysConfig: PA25 → Input + Pull-up + Interrupt (Falling Edge)
// NVIC 和中断函数自动生成, 只需使能
NVIC_EnableIRQ(GPIO_KEY_INST_INT_IRQN);

void GROUP1_IRQHandler(void) {
    uint32_t st = DL_GPIO_getEnabledInterruptStatus(GPIOA, DL_GPIO_PIN_25);
    if (st & DL_GPIO_PIN_25) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_25);
        // 处理按键, 只置标志位, 不做耗时操作!
        g_key_flag = 1;
    }
}
```

## HC-SR04 超声波测距

```c
// 25E 拓展板: PA8=TRIG, PA9=ECHO
// 原理: TRIG发10μs高脉冲 → ECHO回响高电平 → 计时高电平时长 → 距离=时间×0.017cm/μs

void hcsr04_init(void) {
    DL_GPIO_initDigitalOutput(GPIO_TRIG_IOMUX);   // PA8
    DL_GPIO_initDigitalInput(GPIO_ECHO_IOMUX);    // PA9
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_8);
}

float hcsr04_get_distance_cm(void) {
    // 发送 10μs 触发脉冲
    DL_GPIO_setPins(GPIOA, DL_GPIO_PIN_8);
    delay_us(10);
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_8);

    // 等待 ECHO 上升沿 (超时 30ms)
    uint32_t timeout = 30000;
    while (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_9) == 0) {
        if (--timeout == 0) return -1.0f;
    }

    // 计时高电平脉宽 (DWT 或定时器微秒计数)
    uint32_t start_us = micros();

    timeout = 30000;
    while (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_9) != 0) {
        if (--timeout == 0) return -1.0f;
    }

    uint32_t elapsed_us = micros() - start_us;
    return elapsed_us * 0.017f;  // 声速 340m/s → 0.017cm/μs (往返/2)
}

// 实现 micros() 用 SysTick 或 DWT:
uint32_t micros(void) {
    return g_ms_ticks * 1000 + (SystemCoreClock / 1000 - SysTick->VAL) / (SystemCoreClock / 1000000);
}
```

## 按键长按/短按/双击识别

```c
typedef struct {
    uint8_t  state;       // 0=空闲, 1=按下, 2=长按, 3=释放等待
    uint32_t press_ms;    // 按下时刻
    uint32_t release_ms;  // 释放时刻
    uint8_t  click_count;
    uint8_t  event;       // 0=无, 1=短按, 2=长按, 3=双击
} ButtonState;

#define LONG_PRESS_MS   800
#define DOUBLE_CLICK_MS 400

ButtonState btn = {0};

void button_tick(void) {
    uint8_t pressed = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_25) == 0);
    uint32_t now = g_ms_ticks;

    switch (btn.state) {
    case 0: // 空闲
        if (pressed) { btn.state = 1; btn.press_ms = now; }
        break;
    case 1: // 按下
        if (!pressed) {
            btn.state = 3; btn.release_ms = now;
        } else if (now - btn.press_ms > LONG_PRESS_MS) {
            btn.state = 2; btn.event = 2; // 长按
        }
        break;
    case 2: // 长按
        if (!pressed) btn.state = 0;
        break;
    case 3: // 释放等待
        if (pressed) {
            btn.click_count++;
            if (btn.click_count >= 2) { btn.event = 3; btn.state = 0; } // 双击
            else { btn.state = 1; btn.press_ms = now; }
        } else if (now - btn.release_ms > DOUBLE_CLICK_MS) {
            btn.event = 1; btn.state = 0; // 短按
        }
        break;
    }
}
```
