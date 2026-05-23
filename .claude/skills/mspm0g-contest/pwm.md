# PWM (TIMG/TIMA) + 舵机控制

## ⚠️ SDK 铁律

- 定时器周期/模式/引脚全在 SysConfig 配置，**`DL_TimerG_setPeriod()` 不存在**！
- **TIMA0 是 TimerA 实例，必须用 `DL_TimerA_xxx()` 系列，不是 `DL_TimerG_xxx()`**！
- TIMA0 `DL_TimerA_setCaptureCompareValue` 参数顺序: **(inst, value, index)** — 与 TIMG 的 `(inst, index, value)` 不同！
- TIMG PWM 默认 edge-aligned **up-count**: CC=0→输出100%, CC=period→输出0%
- 可用定时器白名单: 仅 TIMG0, TIMG6, TIMG7, TIMG8, TIMG12, TIMA0

## ⚠️ TB6612 通道与左右轮铁律

```
TB6612 A 通道 (PWMA/PB15/PA13/PA12) → 右轮
TB6612 B 通道 (PWMB/PB16/PB0/PB1)   → 左轮

每次生成小车代码前必须先问用户确认左右轮接线！
```

## SysConfig 配置 PWM (TB6612 电机, TIMG8)

```
ADD → Timer G → Name: TIMG_8 → Mode: PWM
  → PWM Pin0: PB15 (TIMG8_C0) → PWMA (右轮)
  → PWM Pin1: PB16 (TIMG8_C1) → PWMB (左轮)
  → Period: 4000 (32MHz/4000=8kHz 或 PLL 80MHz/4000=20kHz)
  → 保存
```

## TIMG PWM 运行时代码

```c
// PWM 启动和占空比调整
// ⚠️ A通道(PB15, CH0)=右轮, B通道(PB16, CH1)=左轮
DL_TimerG_startCounter(TIMG8);
DL_TimerG_setCaptureCompareValue(TIMG8, DL_TIMER_CC_0_INDEX, duty_a);  // CH0=PB15=右轮
DL_TimerG_setCaptureCompareValue(TIMG8, DL_TIMER_CC_1_INDEX, duty_b);  // CH1=PB16=左轮

// 刹车: 占空比设为 period (输出常低)
DL_TimerG_setCaptureCompareValue(TIMG8, DL_TIMER_CC_0_INDEX, 4000);
```

## SysConfig 配置 TIMA0 舵机 PWM

```
ADD → PWM → Name: SERVO_PWM → Timer: TIMA0
  → CCP0 Pin: PB8 → CCP1 Pin: PB9
  → timerCount: 9999 (32MHz/64/50Hz=10000, period=9999)
  → 保存
```

MCLK=32MHz, prescaler=64: 32M/64 = 500kHz, 500k/50Hz = 10000 ticks → period=9999
1 tick = 2μs, 500μs = 250 ticks, 2500μs = 1250 ticks

## 舵机控制 — 众灵 PM 系列 PWM 舵机 (TIMA0 50Hz, 500~2500μs)

> 众灵 PM 系列 PWM 舵机与 SG90/MG996R 使用相同的 50Hz PWM 协议。PM 默认 270° 范围。不同型号详见规格表。

```c
// 通用舵机 PWM 参数
#define SERVO_PWM_MIN    500     // 0° = 500μs
#define SERVO_PWM_MID    1500    // 中位 (PM270=135°, PM180=90°)
#define SERVO_PWM_MAX    2500    // 最大 (PM270=270°, PM180=180°)
#define SERVO_PWM_RANGE  2000    // 2500-500

/* === 角度→PWM μs === */

/* PM 系列 270° 舵机: 角度→PWM */
static uint32_t servo_angle_to_pwm_270(int angle_deg) {
    if (angle_deg < 0)   angle_deg = 0;
    if (angle_deg > 270) angle_deg = 270;
    return SERVO_PWM_MIN + (uint32_t)angle_deg * SERVO_PWM_RANGE / 270U;
}

/* 标准 180° 舵机 (SG90/MG996R/PM180): 角度→PWM */
static uint32_t servo_angle_to_pwm_180(int angle_deg) {
    if (angle_deg < 0)   angle_deg = 0;
    if (angle_deg > 180) angle_deg = 180;
    return SERVO_PWM_MIN + (uint32_t)angle_deg * SERVO_PWM_RANGE / 180U;
}

/* === 精确延时 (us/ms 级) === */
// 使用 TIMG 周期中断做系统滴答
volatile uint32_t g_ms_ticks = 0;

void TICK_IRQHandler(void) { g_ms_ticks++; }

void delay_ms(uint32_t ms) {
    uint32_t start = g_ms_ticks;
    while ((g_ms_ticks - start) < ms) { __WFI(); }
}

void delay_us(uint32_t us) {
    uint32_t start = SysTick->VAL;
    uint32_t ticks = us * (SystemCoreClock / 1000000);
    while ((start - SysTick->VAL) < ticks);
}
```

## TIMA0 舵机设置 (PWM tick 方式, 最高精度)

```c
// TIMA0 period=9999, MCLK=32MHz/64=500kHz, 1tick=2μs
// 0°=250ticks(0.5ms), 90°=750ticks(1.5ms), 180°=1250ticks(2.5ms)
#define SERVO_TICK_MIN  250U
#define SERVO_TICK_MAX  1250U

static void servo_set_pwm_us(uint8_t ch, uint32_t pulse_us) {
    // ch: 0=PB8(CC0), 1=PB9(CC1); pulse_us: 500~2500
    if (pulse_us < 500U)  pulse_us = 500U;
    if (pulse_us > 2500U) pulse_us = 2500U;
    uint32_t tick = 250U + (pulse_us - 500U) / 2U;
    // TIMA0 API: (inst, value, index)
    DL_TimerA_setCaptureCompareValue(TIMA0, tick,
        (ch == 0U) ? DL_TIMERA_CAPTURE_COMPARE_0_INDEX
                   : DL_TIMERA_CAPTURE_COMPARE_1_INDEX);
}

// 便捷函数
void servo1_set_us(uint32_t us)   { servo_set_pwm_us(1, us); } // PB9=CH1
void servo2_set_us(uint32_t us)   { servo_set_pwm_us(0, us); } // PB8=CH0
void servo1_set_270(int angle)   { servo_set_pwm_us(1, servo_angle_to_pwm_270(angle)); }
void servo2_set_270(int angle)   { servo_set_pwm_us(0, servo_angle_to_pwm_270(angle)); }
void servo1_set_180(int angle)   { servo_set_pwm_us(1, servo_angle_to_pwm_180(angle)); }
void servo2_set_180(int angle)   { servo_set_pwm_us(0, servo_angle_to_pwm_180(angle)); }
```

## 众灵 PM 系列舵机规格速查

| 型号 | 类型 | 电压 | 角度 | 堵转扭矩 | 壳体 |
|------|------|------|------|----------|------|
| PM10S/D | PWM 单/双轴 | 4~6V | 180° | 10 kg·cm | 塑料 |
| PM15S/D | PWM 单/双轴 | 5~8.4V | 270° | 15 kg·cm | 塑料 |
| PM20S/D | PWM 单/双轴 | 5~8.4V | 270° | 20 kg·cm | 半金属 |
| PM25S/D | PWM 单/双轴 | 5~8.4V | 270° | 25 kg·cm | 半金属 |
| PM30S/D | PWM 单/双轴 | 5~8.4V | 270° | 30 kg·cm | 半金属/全金属 |
| PM35S/D | PWM 单/双轴 | 5~8.4V | 270° | 35 kg·cm | 全金属 |
| PM45S | PWM 单轴 | 5~8.4V | 270° | 45 kg·cm | 全金属 |
| PM60S | PWM 单轴 | 5~13V | 270° | 60 kg·cm | 全金属 |
| PM80S | PWM 单轴 | 5~13V | 270° | 80 kg·cm | 全金属 |

> S=单轴, D=双轴。三线接口: 棕=GND, 红=VCC(5~8.4V/13V), 黄/白=信号。

**PM 系列 PWM 参数：**
- 周期: 20ms (50Hz), 脉宽: 500~2500μs
- 中心位置: 1500μs (始终为中位)
- 270°: 500μs=0°, 1500μs=135°, 2500μs=270°
- 180°: 500μs=0°, 1500μs=90°, 2500μs=180°
- 分辨率: 270/2000=0.135°/μs; 180/2000=0.09°/μs

## 众灵 ZP 系列串行总线舵机 (UART 单线半双工)

> ZP 系列内置 MCU，通过单线 UART 串行通信控制。支持 255 个舵机共享一条总线。
> 以下协议来自众灵官方 Arduino/STM32 控制器源码 (2017-08 V2.0)。

| 型号 | 电压 | 角度 | 堵转扭矩 |
|------|------|------|----------|
| ZP10S/D~ZP35S/D | 5~8.4V | 270° | 10~35 kg·cm |
| ZP45S~ZP80S | 5~13V | 270° | 45~80 kg·cm |

**ZP 接线：** 棕=GND, 红=VCC(5~8.4V/13V), 黄/白=半双工数据线 → M0G UART TX (115200)

### 串行协议格式 (官方源码验证)

**单舵机指令：** `#XXXPYYYYTZZZZ!`

| 字段 | 含义 | 范围 |
|------|------|------|
| `#` | 帧头 | 固定 |
| `XXX` | 舵机 ID | 000~254 (255=广播全部) |
| `P` | PWM 分隔符 | 固定 |
| `YYYY` | PWM 值 (μs) | 0500~2500 |
| `T` | 时间分隔符 | 固定 |
| `ZZZZ` | 执行时间 (ms) | 0000~65535 |
| `!` | 帧尾 | 固定 |

**多舵机动作组指令：** `{#0P1500T1000!#1P2000T0500!#2P1200T1000!}`

> 将多条单舵机指令用大括号 `{ }` 包裹，一次发送整组动作。

**停止指令：** `$DST!` — 立即停止所有舵机

### 官方源码验证的命令

| 命令 | 功能 | 来源 |
|------|------|------|
| `#000P1500T1000!` | ID0 舵机 1s 内转到中位 (1500μs) | ✅ 官方源码 |
| `#255P1500T1000!` | 广播：全部舵机同步转到中位 | ✅ 官方源码 |
| `{#0P1500T1000!#1P2000T0500!}` | 多舵机动作组 (大括号包裹) | ✅ 官方源码 |
| `$DST!` | 立即停止所有舵机 | ✅ 官方源码 |

### 官方源码中未出现的命令 (固件版本差异, 谨慎使用)

以下命令来自网络文档/其他固件版本，官方 Arduino/STM32 控制器源码中**未找到**，可能不可用：

| 命令 | 声称功能 | 状态 |
|------|---------|------|
| `#000PRAD!` | 读当前位置 | ⚠️ 官方源码中不存在 |
| `#000PULK!` | 释放扭矩 | ⚠️ 官方源码中不存在 |
| `#000PMOD!` | 读工作模式 | ⚠️ 官方源码中不存在 |
| `#000PVER!` | 读固件版本 | ⚠️ 官方源码中不存在 |

> **实测前务必用 `#000P1500T1000!` 和 `$DST!` 验证基本通信**，确认固件版本后再尝试扩展命令。

### MSPM0G 发送函数

```c
#include <stdio.h>

/* 单舵机控制 (官方格式) */
void zp_servo_cmd(uint8_t id, uint16_t pwm, uint16_t time_ms) {
    char buf[24];
    snprintf(buf, sizeof(buf), "#%03dP%04dT%04d!", id, pwm, time_ms);
    for (int i = 0; buf[i]; i++) {
        DL_UART_transmitDataBlocking(UART1, (uint8_t)buf[i]);
    }
}

/* 多舵机动作组 */
void zp_servo_group(const char *cmds) {
    // cmds: "{#0P1500T1000!#1P2000T0500!}"
    for (int i = 0; cmds[i]; i++) {
        DL_UART_transmitDataBlocking(UART1, (uint8_t)cmds[i]);
    }
}

/* 停止全部 */
void zp_servo_stop_all(void) {
    const char *stop = "$DST!";
    for (int i = 0; stop[i]; i++) {
        DL_UART_transmitDataBlocking(UART1, (uint8_t)stop[i]);
    }
}
```

## 旧版舵机参考 (SG90/MG996R, 备用)

```c
// 旧版 period=25000 配置 (不推荐, 仅作参考)
// #define SERVO_PERIOD  25000
// #define SERVO_MIN     625    // 0.5ms
// #define SERVO_MAX     3125   // 2.5ms
// #define SERVO_MID     1875   // 1.5ms=90°

// void servo_set_angle_180(uint8_t ch, uint32_t angle_deg) {
//     uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
//     DL_TimerA_setCaptureCompareValue(TIMA0, pulse,
//         (ch == 0) ? DL_TIMERA_CAPTURE_COMPARE_0_INDEX
//                   : DL_TIMERA_CAPTURE_COMPARE_1_INDEX);
// }
```

## 步进电机控制 (A4988/DRV8825, 参考)

```c
// STEP/DIR 方式
void stepper_step(int steps, uint8_t dir, uint32_t step_delay_us) {
    if (dir) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_8);
    else     DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_8);

    for (int i = 0; i < steps; i++) {
        DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_9);   // STEP high
        delay_us(step_delay_us / 2);
        DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_9); // STEP low
        delay_us(step_delay_us / 2);
    }
}
```
