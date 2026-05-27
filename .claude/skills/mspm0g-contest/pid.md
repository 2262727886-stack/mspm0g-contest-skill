# PID + 滤波器 + 电机控制

## 核心级联 PID 例程 — 小车直线行驶 (mpu6050_clean)

> **工程路径**: `workspace_ccstheia/mpu6050_clean/` — 完整的 CCS Theia 工程，可直接编译烧录。
> **核心思路**: 编码器速度均衡 PI (内环) 驱直，MPU6050 DMP yaw 仅显示不参与控制 (避免漂移带偏)。
> **备用**: 航向 PD (外环) 代码已就绪但默认不接入，只在陀螺仪校准良好时启用。

### ⚠️ 关键铁律：TB6612 A/B 通道与左右轮映射

```
TB6612 A 通道 (PWMA/PA13/PA12) → 右轮
TB6612 B 通道 (PWMB/PB0/PB1)   → 左轮
```

**每次生成小车代码前，必须先问用户**："你的车是 TB6612 A 通道接右轮、B 通道接左轮吗？如果不是请告诉我你的左右轮接线。"

**如果用户左右轮接反**（A=左/B=右），只需交换 `motor_left_set` / `motor_right_set` 的引脚映射即可，不影响 PID 算法。

**右轮方向陷阱**：差速小车轮，两个电机物理上面对面安装，所以 **右轮前进方向与左轮相反**：
- 左轮前进: `left_dir(false, true)` (BIN1=L, BIN2=H)
- 右轮前进: `right_dir(false, true)` (AIN1=L, AIN2=H) — 对右轮来说 AIN2=H 才是前进方向

### 工程结构

```
mpu6050_clean/
├── main.c                          ← main() + 速度均衡 PI + 电机驱动 + 编码器中断
├── pid_ctrl.h / pid_ctrl.c         ← 增量式 PI 速度控制器 + PD 航向控制器 (备用)
├── mpu_port.h / mpu_port.c         ← MPU6050 DMP I2C 移植层 + DMP 初始化/读取
├── inv_mpu.h / inv_mpu.c           ← InvenSense MPU6050 底层驱动 (官方移植)
├── inv_mpu_dmp_motion_driver.h/.c  ← InvenSense DMP 运动驱动 (官方固件)
├── dmpKey.h / dmpmap.h             ← DMP 固件数据
├── oled.h / oled.c                 ← SSD1306 128x64 I2C OLED 驱动
├── i2c_utils.h / i2c_utils.c       ← I2C 阻塞式读写工具 (OLED/MPU 共用)
├── delay.h / delay.c               ← 毫秒延时
├── empty.syscfg                    ← SysConfig 引脚/外设配置
└── startup_mspm0g350x_ticlang.c    ← 启动文件
```

### SysConfig 引脚配置 (empty.syscfg)

**完整外设引脚表：**

| 外设功能 | 芯片/模块型号 | 天猛星引脚 | IOMUX索引 | 片上复用功能 | 备注 |
|----------|--------------|-----------|-----------|-------------|------|
| OLED SDA | SSD1306 | PA28 | PINCM45 | I2C0_SDA | 硬件I2C0, 0x3C, 400kHz |
| OLED SCL | SSD1306 | PA31 | PINCM48 | I2C0_SCL | 同上 |
| MPU6050 SDA | MPU6050 | PA10 | PINCM7 | I2C1_SDA | 硬件I2C1, 0x68, 400kHz |
| MPU6050 SCL | MPU6050 | PA11 | PINCM8 | I2C1_SCL | 与CH340 UART0复用, 二选一 |
| **右轮** PWM | TB6612FNG | PB15 | PINCM35 | TIMG8_C0 | **A通道**=PWMA, 20kHz |
| **左轮** PWM | TB6612FNG | PB16 | PINCM36 | TIMG8_C1 | **B通道**=PWMB, 20kHz |
| **右轮** AIN1 (方向) | TB6612FNG | PA13 | PINCM10 | GPIO | A通道H桥IN1 |
| **右轮** AIN2 (方向) | TB6612FNG | PA12 | PINCM9 | GPIO | A通道H桥IN2 |
| **左轮** BIN1 (方向) | TB6612FNG | PB0 | PINCM19 | GPIO | B通道H桥IN1 |
| **左轮** BIN2 (方向) | TB6612FNG | PB1 | PINCM20 | GPIO | B通道H桥IN2 |
| 编码器A A相 | MG310(霍尔) | PA15 | PINCM37 | GPIO/TIMA1_CH0 | **右轮** 速度, 双边沿中断 |
| 编码器A B相 | MG310(霍尔) | PA16 | PINCM38 | GPIO/TIMA1_CH1 | **右轮** 方向(备用) |
| 编码器B A相 | MG310(霍尔) | PA17 | PINCM39 | TIMG7_CH0 | **左轮** 速度, QEI正交编码 |
| 编码器B B相 | MG310(霍尔) | PA24 | PINCM54 | TIMG7_CH1 | **左轮** 方向 |
| CAL 按键 | 轻触开关 | PA26 | PINCM43 | GPIO上拉输入 | yaw校零 |
| START 按键 | 轻触开关 | PA25 | PINCM42 | GPIO上拉输入 | 启动/停止 |
| LED | 板载 | PB22 | PINCM53 | GPIO输出 | 状态指示 |
| SWDIO | XDS110 | PA19 | — | SWD | 保留调试 |
| SWCLK | XDS110 | PA20 | — | SWCLK | 保留调试 |

**PWM 参数：**
- TIMG8, 20kHz, period=2133, edge-aligned up-count
- 比较值取反逻辑: `PWM_MAX - duty` (CC=0→100%, CC=period→0%)

### 控制架构

```
                  ┌──────────────┐
  RUN_DUTY ──────►│ 左轮 target  │──► ramp_to() ──► motor_left_set()
   (260)    │     └──────────────┘
            │
            │     ┌──────────────┐
            ├────►│ 右轮 target  │──► ramp_to() ──► motor_right_set()
            │     └──────────────┘
            │
            │     ┌──────────────────────┐
            └────►│ 速度均衡 PI (内环)    │
   LEFT_RIGHT_TRIM─┤ err = speed_L - R   │──► balance → 左右差速修正
   (0)             │ Kp=3, Ki=1          │
                   │ Limit: ±120         │
                   └──────────────────────┘

   MPU6050 DMP ───► yaw 仅 OLED 显示 ── 不参与电机控制 (避免漂移)
```

**为什么 yaw 不参与控制？** MPU6050 DMP yaw 角存在固有漂移 (上电后逐步累加)，如果直接用于航向修正会把车带偏。本版本用纯编码器速度均衡，天然无漂移。航向 PD 代码已预留 (`pid_ctrl.c`)，在场地磁力计/外部视觉航向可用时接入。

### 核心代码: 速度均衡 PI + 电机驱动 (main.c)

```c
/**
 * main.c - MSPM0G3507 小车底盘调试基线
 *
 * 当前版本的目标：
 *   1. 电机 A/B 与左右轮映射已经按实车修正：
 *        A 通道 = 右轮：PWMA=PB15, AIN1=PA13, AIN2=PA12
 *        B 通道 = 左轮：PWMB=PB16, BIN1=PB0,  BIN2=PB1
 *   2. MPU6050 只显示 Yaw，不参与方向控制。这样可以避免 yaw 漂移把车带偏。
 *   3. 编码器只用 A 相边沿计数做速度反馈，让左右轮速度自动一致。
 *
 * 按键：
 *   PA25: 启动/停止
 *   PA26: 当前 yaw 显示清零
 *
 * OLED：
 *   Y  = MPU6050 yaw 显示值，仅供观察
 *   SL = 左轮 20ms 内编码器 A 相边沿数
 *   SR = 右轮 20ms 内编码器 A 相边沿数
 *   L/R = 当前输出到左右轮的 PWM 占空比命令
 */

#include "ti_msp_dl_config.h"
#include "oled.h"
#include "mpu_port.h"
#include "delay.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

/* SysTick 由 DMP 延时/时间接口使用，每 1ms 加 1。 */
extern volatile uint32_t sys_tick_ms;
void SysTick_Handler(void) { sys_tick_ms++; }

/* ========================= 可调参数 ========================= */

/* PWM_TIMER 由 SysConfig 生成，当前为 TIMG8。 */
#define PWM_TIMER       MOTOR_PWM_INST

/* TIMG8 周期值。PWM 输出使用"PWM_MAX - duty"，所以 duty=0 时比较值为周期值。 */
#define PWM_MAX         2133

/* 留一点死区，避免 duty 接近周期极限时输出异常。 */
#define PWM_DEAD        30

/* 基础前进速度。速度越大车越快，调试阶段建议从 220~350 慢慢试。 */
#define RUN_DUTY        260

/* 斜坡步进。每 10ms 最多变化 5，避免电机突然冲击导致打滑或 MPU 抖动。 */
#define DUTY_RAMP_STEP  5

/* 速度闭环周期。20ms 读取一次编码器边沿数并修正左右轮速度。 */
#define SPEED_CTRL_PERIOD_MS 20U

/* 左右轮速度均衡 PI 参数。
 * Kp 太大：左右轮输出会抖。
 * Ki 太大：长时间误差会积累过猛，容易左右来回摆。
 */
#define SPEED_BALANCE_KP     3
#define SPEED_BALANCE_KI     1

/* 左右轮均衡修正最大值，防止某个编码器异常时把 PWM 拉爆。 */
#define SPEED_BALANCE_LIMIT  120

/* 开环微调量。
 * 正数：左轮 duty 增大、右轮 duty 减小。
 * 负数：左轮 duty 减小、右轮 duty 增大。
 * 现在编码器闭环能走直，默认保持 0。
 */
#define LEFT_RIGHT_TRIM 0


/* ========================= 编码器引脚 =========================
 * 右轮是 A 通道编码器：PA15/PA16。
 * 左轮是 B 通道编码器：PA17/PA24。
 *
 * 当前为了稳定和简单，只统计 A 相双边沿数量作为速度。
 * B 相暂时只初始化为输入，后续做方向/里程时再用。
 */
#define ENC_R_A_IOMUX    IOMUX_PINCM37
#define ENC_R_A_PIN      DL_GPIO_PIN_15
#define ENC_R_B_IOMUX    IOMUX_PINCM38
#define ENC_R_B_PIN      DL_GPIO_PIN_16
#define ENC_L_A_IOMUX    IOMUX_PINCM39
#define ENC_L_A_PIN      DL_GPIO_PIN_17
#define ENC_L_B_IOMUX    IOMUX_PINCM54
#define ENC_L_B_PIN      DL_GPIO_PIN_24

/* 编码器边沿计数在中断里更新，主循环每 20ms 读取并清零。 */
static volatile int16_t g_enc_l_edges = 0;
static volatile int16_t g_enc_r_edges = 0;


/* ========================= 电机底层控制 ========================= */

/* 左轮实际接 TB6612 的 B 通道：BIN1=PB0, BIN2=PB1。 */
static void left_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(DIR_R_PORT, DIR_R_BIN1_PIN);
    else     DL_GPIO_clearPins(DIR_R_PORT, DIR_R_BIN1_PIN);

    if (in2) DL_GPIO_setPins(DIR_R_PORT, DIR_R_BIN2_PIN);
    else     DL_GPIO_clearPins(DIR_R_PORT, DIR_R_BIN2_PIN);
}

/* 右轮实际接 TB6612 的 A 通道：AIN1=PA13, AIN2=PA12。 */
static void right_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(DIR_L_PORT, DIR_L_AIN1_PIN);
    else     DL_GPIO_clearPins(DIR_L_PORT, DIR_L_AIN1_PIN);

    if (in2) DL_GPIO_setPins(DIR_L_PORT, DIR_L_AIN2_PIN);
    else     DL_GPIO_clearPins(DIR_L_PORT, DIR_L_AIN2_PIN);
}

/* 把有符号 duty 转成 PWM 需要的正数，并限制到安全范围。 */
static uint16_t abs_limit_duty(int16_t duty)
{
    int16_t max_duty = (int16_t)(PWM_MAX - PWM_DEAD);

    if (duty < 0) duty = (int16_t)(-duty);
    if (duty > max_duty) duty = max_duty;

    return (uint16_t)duty;
}

/* 左轮 PWM = PWMB = PB16 = TIMG8_C1。 */
static void left_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(PWM_TIMER,
        (uint16_t)(PWM_MAX - duty), DL_TIMER_CC_1_INDEX);
}

/* 右轮 PWM = PWMA = PB15 = TIMG8_C0。 */
static void right_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(PWM_TIMER,
        (uint16_t)(PWM_MAX - duty), DL_TIMER_CC_0_INDEX);
}

/* 设置左轮速度。duty>0 前进，duty<0 后退。 */
static void motor_left_set(int16_t duty)
{
    if (duty >= 0) {
        left_dir(false, true);
    } else {
        left_dir(true, false);
    }

    left_pwm(abs_limit_duty(duty));
}

/* 设置右轮速度。右轮之前实测反了，所以这里的正转极性已翻转。 */
static void motor_right_set(int16_t duty)
{
    if (duty >= 0) {
        right_dir(false, true);
    } else {
        right_dir(true, false);
    }

    right_pwm(abs_limit_duty(duty));
}

/* 停车：方向脚全部拉低，PWM duty 清零。 */
static void motor_stop(void)
{
    left_dir(false, false);
    right_dir(false, false);
    left_pwm(0);
    right_pwm(0);
}

/* 初始化电机方向 GPIO，并确保上电后先停车。 */
static void motor_init(void)
{
    DL_GPIO_initDigitalOutput(DIR_L_AIN1_IOMUX);
    DL_GPIO_initDigitalOutput(DIR_L_AIN2_IOMUX);
    DL_GPIO_initDigitalOutput(DIR_R_BIN1_IOMUX);
    DL_GPIO_initDigitalOutput(DIR_R_BIN2_IOMUX);
    motor_stop();
}


/* ========================= 编码器计数 ========================= */

/* 初始化编码器输入。
 * A 相开启双边沿中断，用于速度计数。
 * B 相先作为普通输入保留，后续做方向或里程时再加入解码。
 */
static void encoder_init(void)
{
    DL_GPIO_initDigitalInputFeatures(ENC_R_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_R_B_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_L_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_L_B_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    /* PA15 在低 16 位边沿配置寄存器，PA17 在高 16 位寄存器。 */
    DL_GPIO_setLowerPinsPolarity(GPIOA, DL_GPIO_PIN_15_EDGE_RISE_FALL);
    DL_GPIO_setUpperPinsPolarity(GPIOA, DL_GPIO_PIN_17_EDGE_RISE_FALL);

    /* MSPM0G3507 的 GPIOA/GPIOB 共用 GROUP1 中断向量。 */
    DL_GPIO_clearInterruptStatus(GPIOA, ENC_R_A_PIN | ENC_L_A_PIN);
    DL_GPIO_enableInterrupt(GPIOA, ENC_R_A_PIN | ENC_L_A_PIN);
    NVIC_EnableIRQ(GPIOA_INT_IRQn);
}

/* GPIOA/GPIOB 共用 GROUP1_IRQHandler。
 * 只处理 PA15/PA17 两个编码器 A 相，其它 GPIO 中断不在这里使用。
 */
void GROUP1_IRQHandler(void)
{
    uint32_t status = DL_GPIO_getEnabledInterruptStatus(GPIOA,
        ENC_R_A_PIN | ENC_L_A_PIN);

    if ((status & ENC_R_A_PIN) != 0U) {
        g_enc_r_edges++;
    }
    if ((status & ENC_L_A_PIN) != 0U) {
        g_enc_l_edges++;
    }

    DL_GPIO_clearInterruptStatus(GPIOA, status);
}


/* ========================= 主程序 ========================= */

int main(void)
{
    /* SysConfig 生成的外设初始化：时钟、GPIO、PWM、I2C 等。 */
    SYSCFG_DL_init();

    /* PA26/PA25 按键手动配置上拉，避免悬空导致误触发。 */
    DL_GPIO_initDigitalInputFeatures(CAL_KEY_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(START_BTN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);

    motor_init();
    encoder_init();

    OLED_Init();
    OLED_Clear();
    OLED_Puts(0, 0, "CLEAN MOTOR TEST");
    OLED_Puts(1, 0, "DMP init...");

    /* DMP 只用于显示 yaw，不参与闭环控制。 */
    int dmp_ret = DMP_Init();
    if (dmp_ret != 0) {
        char buf[16];
        sprintf(buf, "DMP ERR:%d", dmp_ret);
        OLED_Puts(2, 0, buf);
        while (1) {
            motor_stop();
            delay_ms(100);
        }
    }

    OLED_Clear();
    OLED_Puts(0, 0, "PA25 RUN/STOP");
    OLED_Puts(1, 0, "PA26 ZERO Y");
    OLED_Puts(2, 0, "Y:");
    OLED_Puts(3, 0, "SL:");
    OLED_Puts(4, 0, "SR:");
    OLED_Puts(5, 0, "L:");
    OLED_Puts(6, 0, "R:");
    OLED_Puts(7, 0, "STOP");

    /* 运行状态与按键边沿检测变量。 */
    bool running = false;
    bool last_start = false;
    bool last_zero = false;

    /* 姿态显示变量。pitch/roll 当前不用，只是 DMP_Read_Data 需要传入。 */
    float pitch = 0.0f;
    float roll = 0.0f;
    float yaw = 0.0f;
    float yaw_zero = 0.0f;
    float yaw_show = 0.0f;

    /* 当前实际输出 PWM。通过 ramp_to 缓慢靠近目标值。 */
    int16_t duty_l = 0;
    int16_t duty_r = 0;

    /* 20ms 速度值：编码器 A 相边沿数，越大表示轮速越快。 */
    int16_t speed_l = 0;
    int16_t speed_r = 0;

    /* 左右轮速度均衡 PI 的输出和积分项。 */
    int16_t balance = 0;
    int16_t balance_i = 0;

    uint16_t ctrl_ms = 0;
    uint16_t oled_div = 0;
    char text[16];

    while (1) {
        /* 读取 yaw，仅用于 OLED 显示。电机闭环完全不依赖 MPU6050。 */
        if (DMP_Read_Data(&pitch, &roll, &yaw) == 0) {
            yaw_show = wrap_180(yaw - yaw_zero);
        }

        /* PA25 短按切换运行/停止。启动瞬间把 yaw 显示清零。 */
        bool start_now = button_pressed((uint32_t)START_PORT, START_BTN_PIN);
        if (!last_start && start_now) {
            running = !running;
            if (running) {
                yaw_zero = yaw;
                yaw_show = 0.0f;
            }
        }
        last_start = start_now;

        /* PA26 手动清零 yaw 显示。 */
        bool zero_now = button_pressed((uint32_t)CAL_PORT, CAL_KEY_PIN);
        if (!last_zero && zero_now) {
            yaw_zero = yaw;
            yaw_show = 0.0f;
        }
        last_zero = zero_now;

        /* 每 20ms 取一次编码器速度并计算左右均衡修正。 */
        ctrl_ms = (uint16_t)(ctrl_ms + 10U);
        if (ctrl_ms >= SPEED_CTRL_PERIOD_MS) {
            int16_t raw_l;
            int16_t raw_r;

            /* 读写中断变量时短暂关中断，避免读到一半被 ISR 修改。 */
            __disable_irq();
            raw_l = g_enc_l_edges;
            raw_r = g_enc_r_edges;
            g_enc_l_edges = 0;
            g_enc_r_edges = 0;
            __enable_irq();

            /* 当前只关心速度大小，不关心方向，所以取绝对值。 */
            speed_l = (raw_l < 0) ? (int16_t)(-raw_l) : raw_l;
            speed_r = (raw_r < 0) ? (int16_t)(-raw_r) : raw_r;

            if (running) {
                /* err>0 表示左轮更快，需要减左轮、加右轮。 */
                int16_t err = (int16_t)(speed_l - speed_r);
                balance_i = (int16_t)(balance_i + err);
                if (balance_i > SPEED_BALANCE_LIMIT) balance_i = SPEED_BALANCE_LIMIT;
                if (balance_i < -SPEED_BALANCE_LIMIT) balance_i = -SPEED_BALANCE_LIMIT;

                balance = (int16_t)(SPEED_BALANCE_KP * err +
                                    SPEED_BALANCE_KI * balance_i);
                if (balance > SPEED_BALANCE_LIMIT) balance = SPEED_BALANCE_LIMIT;
                if (balance < -SPEED_BALANCE_LIMIT) balance = -SPEED_BALANCE_LIMIT;
            } else {
                /* 停车时清掉 PI 状态，避免下次启动继承旧误差。 */
                balance = 0;
                balance_i = 0;
            }

            ctrl_ms = 0;
        }

        /* 目标 PWM：
         *   balance>0：左轮快，左轮目标降低、右轮目标提高。
         *   balance<0：右轮快，左轮目标提高、右轮目标降低。
         */
        int16_t target_l = 0;
        int16_t target_r = 0;
        if (running) {
            target_l = (int16_t)(RUN_DUTY + LEFT_RIGHT_TRIM - balance);
            target_r = (int16_t)(RUN_DUTY - LEFT_RIGHT_TRIM + balance);
        }

        duty_l = ramp_to(duty_l, target_l);
        duty_r = ramp_to(duty_r, target_r);

        if (duty_l == 0 && duty_r == 0) {
            motor_stop();
        } else {
            motor_left_set(duty_l);
            motor_right_set(duty_r);
        }

        /* OLED 约 10Hz 更新一次，避免频繁刷屏拖慢主循环。 */
        if (++oled_div >= 10U) {
            oled_div = 0;

            OLED_ClearPage(2);
            OLED_Puts(2, 0, "Y:");
            ftoa_1d(yaw_show, text);
            OLED_Puts(2, 20, text);

            OLED_ClearPage(3);
            OLED_Puts(3, 0, "SL:");
            sprintf(text, "%d", speed_l);
            OLED_Puts(3, 24, text);

            OLED_ClearPage(4);
            OLED_Puts(4, 0, "SR:");
            sprintf(text, "%d", speed_r);
            OLED_Puts(4, 24, text);

            OLED_ClearPage(5);
            OLED_Puts(5, 0, "L:");
            sprintf(text, "%d", duty_l);
            OLED_Puts(5, 20, text);

            OLED_ClearPage(6);
            OLED_Puts(6, 0, "R:");
            sprintf(text, "%d", duty_r);
            OLED_Puts(6, 20, text);

            OLED_ClearPage(7);
            OLED_Puts(7, 0, running ? "RUN SPEED PID" : "STOP");
        }

        /* 主循环周期约 10ms。速度闭环用 ctrl_ms 累计到 20ms 执行。 */
        delay_ms(10);
    }
}
```

### 可调参数速查表

| 参数 | 默认值 | 含义 | 调参建议 |
|------|--------|------|---------|
| `RUN_DUTY` | 260 | 基础前进速度 (PWM占空比) | 220~350, 电池电压高→低, 电压低→高 |
| `DUTY_RAMP_STEP` | 5 | 每10ms斜坡步进 | 2~10, 越小越平滑但启动慢 |
| `SPEED_CTRL_PERIOD_MS` | 20 | 速度闭环周期 | 10~20ms, 太短编码器脉冲太少 |
| `SPEED_BALANCE_KP` | 3 | 左右轮均衡 P | 1~5, 太大会左右摇摆 |
| `SPEED_BALANCE_KI` | 1 | 左右轮均衡 I | 0~3, 太大积分过猛 |
| `SPEED_BALANCE_LIMIT` | 120 | 均衡修正上限 | 80~200, 防止编码器异常拉爆PWM |
| `LEFT_RIGHT_TRIM` | 0 | 开环微调 | ±50, 编码器失效时的备用手动微调 |
| `PWM_MAX` | 2133 | TIMG8周期值 | SysConfig 中设置, 不要改 |
| `PWM_DEAD` | 30 | 死区 | 保证duty不碰周期极限 |

### 实测参数 (MG310 + TB6612 + 电池 7.4V)

| 电池电压 | RUN_DUTY | 20ms编码器脉冲 | 直线表现 |
|---------|---------|---------------|---------|
| 8.4V (满电) | 260 | 40~55 | 2m内偏差<5cm |
| 7.4V (标称) | 300 | 40~55 | 同上 |
| 6.5V (低电) | 350 | 35~45 | 速度下降, 仍能走直 |

> 编码器脉冲数取决于电池电压、地面摩擦力、电机个体差异，以上仅供参考。

### ⚠️ 关键陷阱 (来自实车调试)

| # | 陷阱 | 症状 | 正确做法 |
|---|------|------|---------|
| **1** | **yaw漂移参与控制** | 上电yaw慢慢变, 车越走越歪 | yaw仅显示不控制, 编码器均衡替代 |
| **2** | **右轮方向接反** | 左轮前进右轮后退, 原地打转 | 按代码注释: 右轮IN1=L时前进 (与左轮相反) |
| **3** | **CC比较值反逻辑** | duty=260但PWM输出≈0% | 必须 `PWM_MAX - duty`, CC=0→100% |
| **4** | **停车不清PI** | 停止后再启动, 车猛歪一下 | 停车时 `balance=0; balance_i=0` |
| **5** | **PWM=0未刹车** | 车停不住, 惯性滑行 | duty==0时调用 `motor_stop()` 拉低方向脚 |
| **6** | **编码器中断丢脉冲** | 高速时速度读数偏低 | 中断只做 `g_enc_edges++`, 不要调任何函数 |
| **7** | **按键无上拉** | 不按也触发 | 必须 `initDigitalInputFeatures(..., PULL_UP, ...)` |
| **8** | **OLED刷新太频繁** | 主循环变慢, 编码器丢数 | OLED每100ms(10帧)更新一次 |

---

## 增量式 PI 速度控制器 + PD 航向控制器 (pid_ctrl.c 备用库)

> 此库代码已就绪，但 `mpu6050_clean/main.c` 默认**不使用**。
> 当需要航向闭环时 (如 K230 视觉提供绝对航向，或磁力计校准后)，将航向 PD 输出叠加到左右轮差速即可。

### pid_ctrl.h

```c
/**
 * pid_ctrl.h — 增量式 PI 速度控制器 + PD 航向控制器
 *
 * 适配: MSPM0G3507 天猛星 + TB6612FNG + MG310 电机
 *
 * 使用前请在 SysConfig 中配置:
 *   - MOTOR_PWM: TIMG8, PB15=C0, PB16=C1 (PWM 频率 20kHz)
 *   - MOTOR_DIR: 4 个 GPIO 输出 (TB6612 AIN1/AIN2/BIN1/BIN2)
 *   - ENCODER: GPIO 双边沿中断 (PA15/PA16/PA17/PA24)
 *   - CONTROL_TIMER: 20ms 周期定时器 (用于速度环)
 */

#ifndef PID_CTRL_H
#define PID_CTRL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ================================================================
 * 速度 PI 控制器 (增量式)
 *
 * 公式: output += Kp*(err - last_err) + Ki*err
 *
 * 特点:
 *   - 增量式, 输出平滑不突变
 *   - static 变量保存状态, 无全局污染
 *   - 自动输出限幅 (防止积分饱和)
 *
 * 调用方式: 放在 20ms 定时中断中
 *   LC_Speed = Encoder_Get_L();  // 获取当前速度(编码器脉冲数)
 *   duty_L  = PID_Speed_L(Object_Speed, LC_Speed);
 *   Motor_SetLeft(duty_L);
 * ================================================================ */

extern float g_speed_kp;       /* 速度环比例系数 (默认 2.5) */
extern float g_speed_ki;       /* 速度环积分系数 (默认 1.0) */
extern int16_t g_speed_limit;  /* 速度环输出限幅 (默认 1200, 对应 PWM 最大占空比) */

/* 初始化速度环内部状态 (切换任务时调用, 清除历史积分) */
void PID_Speed_Reset(void);

/* 左轮速度 PI, 返回 PWM 占空比值 (有符号, 正=前进, 负=后退) */
int16_t PID_Speed_L(int16_t target, int16_t current);

/* 右轮速度 PI, 返回 PWM 占空比值 (有符号, 正=前进, 负=后退) */
int16_t PID_Speed_R(int16_t target, int16_t current);


/* ================================================================
 * 航向 PD 控制器
 *
 * 公式: output = Kp*error + Kd*(error - last_error)
 *
 * 用途: 根据航向偏差计算差速转向修正量
 *
 * 调用方式: 放在 20ms 主循环中
 *   float heading_err = wrap_180(target_heading - current_yaw);
 *   float steer = PID_Dir_Calc(heading_err);
 *   target_l = RUN_DUTY - (int16_t)steer;  // 右偏→减速左轮
 *   target_r = RUN_DUTY + (int16_t)steer;  // 右偏→加速右轮
 * ================================================================ */

extern float g_dir_kp;        /* 航向环比例系数 (默认 1.5) */
extern float g_dir_kd;        /* 航向环微分系数 (默认 0.8) */
extern float g_dir_deadband;  /* 死区: |偏差|<3°不修正, 过滤yaw漂移 */

/* 重置航向环 (切换任务时调用) */
void PID_Dir_Reset(void);

/* 航向 PD 计算, 返回差速修正值 (叠加到左右轮目标) */
float PID_Dir_Calc(float error);


/* ================================================================
 * 目标速度 (由状态机/遥控设定)
 * ================================================================ */
extern int16_t g_object_speed;  /* 目标速度 (编码器脉冲/20ms) */

#ifdef __cplusplus
}
#endif

#endif /* PID_CTRL_H */
```

### pid_ctrl.c — 增量式 PI + 航向 PD 实现

```c
/**
 * pid_ctrl.c — 增量式 PI 速度控制器 + PD 航向控制器 实现
 */

#include "pid_ctrl.h"

/* ================================================================
 * 速度 PI 控制器 — 增量式
 * ================================================================ */

/* 可调参数 (运行时可通过 OLED/串口在线修改) */
float g_speed_kp     = 2.5f;    /* 比例系数: 越大响应越快, 过大振荡 */
float g_speed_ki     = 1.0f;    /* 积分系数: 消除稳态误差, 过大超调 */
int16_t g_speed_limit = 1200;   /* 输出限幅: 防止 PWM 占空比超限 */

/**
 * 速度环内部状态
 *
 * 用 static 而非全局变量, 避免被外部误修改.
 * 增量式 PI 的核心: ControlVelocity 在函数调用间保持, 自然平滑.
 */
static int16_t  s_last_bias_l;       /* 左轮上次偏差 */
static int16_t  s_last_bias_r;       /* 右轮上次偏差 */
static int16_t  s_control_l;         /* 左轮控制量累加器 */
static int16_t  s_control_r;         /* 右轮控制量累加器 */

/* 重置所有内部状态 — 任务切换或停止时调用 */
void PID_Speed_Reset(void)
{
    s_last_bias_l = 0;
    s_last_bias_r = 0;
    s_control_l   = 0;
    s_control_r   = 0;
}

/**
 * 左轮增量式 PI
 *
 * @param target   目标速度 (编码器脉冲/20ms)
 * @param current  当前速度 (编码器脉冲/20ms)
 * @return         PWM 占空比值 (正=前进, 负=后退)
 *
 * 增量式公式:
 *   Δu = Kp * (e(k) - e(k-1)) + Ki * e(k)
 *   u(k) = u(k-1) + Δu
 *
 * 为什么用增量式而不是位置式?
 *   - 输出自然平滑, 不会因 Ki*∑e 积分饱和突变
 *   - 切换目标速度时无需重置积分
 *   - Cortex-M0+ 计算量更小
 */
int16_t PID_Speed_L(int16_t target, int16_t current)
{
    int16_t bias = target - current;             /* 本次偏差 */

    /* 增量式 PI 核心 */
    s_control_l += (int16_t)(g_speed_kp * (float)(bias - s_last_bias_l)
                           + g_speed_ki * (float)bias);

    s_last_bias_l = bias;

    /* 输出限幅: 防止 PWM 溢出, 同时起到抗积分饱和作用 */
    if (s_control_l > g_speed_limit) {
        s_control_l = g_speed_limit;
    } else if (s_control_l < -g_speed_limit) {
        s_control_l = -g_speed_limit;
    }

    return s_control_l;
}

/* 右轮增量式 PI — 逻辑同左轮, 独立状态 */
int16_t PID_Speed_R(int16_t target, int16_t current)
{
    int16_t bias = target - current;

    s_control_r += (int16_t)(g_speed_kp * (float)(bias - s_last_bias_r)
                           + g_speed_ki * (float)bias);

    s_last_bias_r = bias;

    if (s_control_r > g_speed_limit) {
        s_control_r = g_speed_limit;
    } else if (s_control_r < -g_speed_limit) {
        s_control_r = -g_speed_limit;
    }

    return s_control_r;
}


/* ================================================================
 * 航向 PD 控制器
 * ================================================================ */

float g_dir_kp = 1.5f;    /* P: 偏差1°的差速修正量, 太大对yaw漂移过敏 */
float g_dir_kd = 0.8f;    /* D: 抑制突变, 对慢漂移无效 */
float g_dir_deadband = 3.0f; /* 死区: |偏差|<3°时不修正, 过滤yaw漂移 */

static float s_last_error;  /* 上次航向偏差 */

void PID_Dir_Reset(void)
{
    s_last_error = 0.0f;
}

/**
 * 航向 PD 控制 (带死区)
 *
 *   死区逻辑: yaw 漂移速度慢 (通常<1°/s), 产生的偏差在几度内。
 *   死区过滤掉这些慢漂移, 只有真正的转弯 (>3°偏差) 才触发修正。
 */
float PID_Dir_Calc(float error)
{
    /* 死区: 小偏差不修正 (过滤 yaw 慢漂移) */
    if (error < g_dir_deadband && error > -g_dir_deadband) {
        s_last_error = 0.0f;
        return 0.0f;
    }
    float result = g_dir_kp * error + g_dir_kd * (error - s_last_error);
    s_last_error = error;
    return result;
}


/* ================================================================
 * 目标速度 (全局, 由状态机/任务设定)
 * ================================================================ */
int16_t g_object_speed = 0;
```

### 航向 PD 接入方法 (从编码器均衡升级到级联 PID)

```c
// === 在 main.c 中接入航向 PD (pid_ctrl.c 已包含此代码) ===

// 1. include 头文件
#include "pid_ctrl.h"

// 2. 在 20ms 控制周期中，将航向 PD 输出叠加到左右轮目标:
if (ctrl_ms >= SPEED_CTRL_PERIOD_MS) {
    // ... 编码器读取 (同上) ...

    if (running) {
        // 内环: 速度均衡 (同上)
        int16_t err = speed_l - speed_r;
        balance_i += err;
        // ... 限幅 ...
        balance = SPEED_BALANCE_KP * err + SPEED_BALANCE_KI * balance_i;

        // 外环: 航向 PD (新增)
        float heading_err = wrap_180(target_heading - yaw_show);
        float steer = PID_Dir_Calc(heading_err);
        // steer>0 → 车偏右 → 减速左轮加速右轮来纠正
    }

    // 3. 目标PWM合成 (新增 steer 项)
    if (running) {
        target_l = RUN_DUTY + LEFT_RIGHT_TRIM - balance - (int16_t)steer;
        target_r = RUN_DUTY - LEFT_RIGHT_TRIM + balance + (int16_t)steer;
    }
}
```

> **启用航向 PD 的代价**: DMP yaw 漂移 (~1°/s) 会被 P 项放大为持续的差速偏置，车反而走不直。
> **推荐**: 仅在 K230 视觉提供绝对航向时启用外环。编码器均衡内环已足够走直线。

---

## 简单位置式 PID (单电机速度闭环)

> 以下为较简单的单电机位置式 PID，适合只有一个编码器的场景。不适用于差速小车。

### PID 控制器 (⚠️ 重点章节 — 实测调参验证)

#### 架构铁律

```
前馈 PWM (Base) + PID 增量 — 不要从 0 起调!
┌──────────┐     ┌──────────┐     ┌───────────┐
│ SysTick  │ ──→ │ Encoder  │ ──→ │ PID calc  │ ──→ PWM = Base ± Δ
│ 10/20ms  │     │ Update() │     │ (position)│
└──────────┘     └──────────┘     └───────────┘
      ↑ 固定周期! 不能用主循环count!
```

#### 已验证的实现

```c
// pid.h — 位置式 PID (编码器脉冲计数域)
typedef struct {
    float kp, ki, kd;
    float target, error, last_error, integral;
    float max_integral, max_output, output;
} PID;

void pid_init(PID *pid, float kp, float ki, float kd,
              float max_integral, float max_output, float target);
float pid_calc(PID *pid, float current);  // PID_OUT = Kp*E + Ki*ΣE + Kd*dE

// 主循环框架 (SysTick 10ms)
#define PID_PERIOD_MS         (10U)
#define PID_SYSTICK_LOAD      (CPUCLK_FREQ / 1000U * PID_PERIOD_MS)
#define PID_MAX_INTEGRAL      (2500.0f)
#define PWM_STEP_LIMIT        (4)          // 每次调节不超过±4

volatile uint8_t g_pid_tick = 0;
void SysTick_Handler(void) { g_pid_tick = 1; }

int main(void) {
    SYSCFG_DL_init(); __enable_irq();
    Motor_Init(); Encoder_Init();
    DL_TimerG_startCounter(PWM_TB6612_INST);
    DL_SYSTICK_config(PID_SYSTICK_LOAD);  // 硬件定时器, 不是delay!

    pid_init(&pid, 0.5f, 0.08f, 0.0f, 2500, 1000, 42);
    int base_pwm = 800;  // 前馈! 不是从0开始

    while (1) {
        Encoder_Tick();  // 全速轮询

        if (g_pid_tick) {
            g_pid_tick = 0;
            Encoder_Update();
            int count = abs(Encoder_GetCount());

            int pwm = base_pwm + (int)pid_calc(&pid, (float)count);
            pwm = clamp(pwm, 0, 1000);
            pwm = step_limit(pwm, last_pwm, PWM_STEP_LIMIT);
            last_pwm = pwm;
            Motor_B(pwm);
        }
    }
}
```

#### ⚠️ 调参必读 (6 大陷阱)

| # | 陷阱 | 后果 | 正确做法 |
|---|------|------|---------|
| **1** | **PID 从 0 开始** | 电机不起转,积分饱和 | **前馈 Base PWM=800**,PID 只做 ±200 微调 |
| **2** | **主循环 delay 当采样** | UART 阻塞导致周期不准 | **SysTick 硬件定时器**, 10ms 固定周期 |
| **3** | **PWM 跳变太大** | 电机抽搐抖动 | **步进限幅 ±4/次**, 防突变 |
| **4** | **目标超过物理上限** | PID 永远在饱和 | 先满 PWM 测最大计数, 目标×0.95 |
| **5** | **编码器负值直入 PID** | error 方向反了 | **abs(count)** 取绝对值 |
| **6** | **`setCaptureCompareValue` 参数反** | PWM 写入错通道 | 正确: `(inst, VALUE, INDEX)` |

#### 实测参数 (MG310 + TB6612 + 电池 7.4V)

| 采样周期 | Base PWM | Kp | Ki | Kd | 目标 | 实测计数 |
|----------|---------|-----|-----|-----|------|---------|
| 10ms | 800 | 0.5 | 0.08 | 0 | 42 | 41~43 |
| 20ms | 800 | 0.5 | 0.08 | 0 | 80 | 82~86 |

> **调参顺序**: 先设 B800 T=实测最大值×0.9 → P=0.5 I=0 D=0 → 看是否稳定 → 微量加 I

---

## 滤波器

**一阶低通滤波器：**
```c
typedef struct {
    float alpha;   // 滤波系数 = dt/(RC+dt), 取值范围 (0,1]
    float output;
} LowPassFilter;

float lpf_update(LowPassFilter *f, float input) {
    f->output = f->alpha * input + (1.0f - f->alpha) * f->output;
    return f->output;
}
```

**滑动平均滤波：**
```c
#define MA_WINDOW 8
typedef struct {
    uint16_t buf[MA_WINDOW];
    uint8_t  idx;
    uint32_t sum;
    uint8_t  count;
} MovingAvg;

uint16_t ma_update(MovingAvg *ma, uint16_t val) {
    ma->sum -= ma->buf[ma->idx];
    ma->sum += val;
    ma->buf[ma->idx] = val;
    ma->idx = (ma->idx + 1) % MA_WINDOW;
    if (ma->count < MA_WINDOW) ma->count++;
    return (uint16_t)(ma->sum / ma->count);
}
```

**互补滤波 (IMU 姿态融合)：**
```c
// 陀螺仪积分 + 加速度计修正
typedef struct {
    float angle;     // 输出角度
    float alpha;     // 互补系数, 典型 0.98
    float dt;        // 采样周期
} ComplementaryFilter;

float cf_update(ComplementaryFilter *cf, float gyro_rate, float accel_angle) {
    // gyro_rate: 陀螺仪角速度 (°/s)
    // accel_angle: 加速度计推算的角度
    cf->angle = cf->alpha * (cf->angle + gyro_rate * cf->dt)
              + (1.0f - cf->alpha) * accel_angle;
    return cf->angle;
}
```

**卡尔曼滤波 (1D，适合单轴角度融合)：**
```c
typedef struct {
    float x;   // 状态估计
    float p;   // 估计协方差
    float q;   // 过程噪声
    float r;   // 测量噪声
    float k;   // 卡尔曼增益
} Kalman1D;

void kalman1d_init(Kalman1D *kf, float q, float r) {
    kf->x = 0; kf->p = 1; kf->q = q; kf->r = r; kf->k = 0;
}

float kalman1d_update(Kalman1D *kf, float measurement) {
    kf->p += kf->q;
    kf->k  = kf->p / (kf->p + kf->r);
    kf->x += kf->k * (measurement - kf->x);
    kf->p *= (1 - kf->k);
    return kf->x;
}

// 陀螺仪+加速度计角度融合示例：
// 每 dt 秒调用: angle = kalman1d_update(&kf,
//     accel_angle + (angle + gyro_rate*dt)  // 融合输入
// );
// 或直接用: 先用 gyro*dt 做预测，再用 accel 做更新
```

### 电机控制

**直流电机速度闭环 (PWM + 编码器)：**
```c
typedef struct {
    PID_Controller speed_pid;
    uint32_t pwm_channel;
    uint32_t pwm_period;
    int32_t  target_speed;   // 目标速度 (编码器脉冲/控制周期)
    int32_t  current_speed;
    // 编码器读数
    int32_t  last_encoder;
} DC_Motor;

void motor_speed_control(DC_Motor *motor, int32_t encoder_val, float dt) {
    motor->current_speed = encoder_val - motor->last_encoder;
    motor->last_encoder = encoder_val;

    float output = pid_update(&motor->speed_pid,
                              (float)motor->current_speed, dt);

    // 将 PID 输出映射到 PWM 占空比
    if (output > motor->pwm_period) output = motor->pwm_period;
    if (output < 0) output = 0;

    DL_TimerG_setCaptureCompareValue(TIMG0, motor->pwm_channel, (uint32_t)output);
}
```

**舵机控制 (TIMA0 50Hz PWM, 500~2500us)：**
```c
// 25E 拓展板: 舵机1=PB9(TIMA0_CH1), 舵机2=PB8(TIMA0_CH0)
// 20ms 周期 = 50Hz, 脉宽 0.5~2.5ms 对应 0°~180°
// SysConfig: TIMA0 → PWM → PB8=CH0, PB9=CH1, period=25000
#define SERVO_PERIOD  25000
#define SERVO_MIN     625    // 0.5ms 对应
#define SERVO_MAX     3125   // 2.5ms 对应
#define SERVO_MID     1875   // 1.5ms 对应 90°

void servo1_set_angle(uint32_t angle_deg) { // 舵机1 PB9=CH1, 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    DL_TimerA_setCaptureCompareValue(TIMA0, 1, pulse);
}
void servo2_set_angle(uint32_t angle_deg) { // 舵机2 PB8=CH0, 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    DL_TimerA_setCaptureCompareValue(TIMA0, 0, pulse);
}
```

**步进电机控制 (A4988/DRV8825 脉冲+方向)：**
```c
// STEP 引脚连接 GPIO, DIR 连接 GPIO
void stepper_step(int steps, uint8_t dir_pin_state, uint32_t step_delay_us) {
    // 设置方向
    if (dir_pin_state) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_8);
    else DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_8);

    for (int i = 0; i < steps; i++) {
        DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_9);   // STEP high
        delay_us(step_delay_us / 2);
        DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_9); // STEP low
        delay_us(step_delay_us / 2);
    }
}
```

---

## 串口实时调参 (✅ 实测可用)

串口发送命令修改 PID 参数，无需重编译烧录：

```c
// UART 命令解析 (主循环中调用)
static void uart_poll_params(void) {
    static int value = 0, mode = 0;  // 0=none 1=P 2=I 3=D 4=T 5=B

    while (!DL_UART_isRXFIFOEmpty(UART_0_INST)) {
        char c = (char)DL_UART_Main_receiveData(UART_0_INST);

        if (c >= '0' && c <= '9') {
            value = value * 10 + (c - '0');
        } else if (c == 'P') { mode = 1; value = 0; }
        else if (c == 'I')  { mode = 2; value = 0; }
        else if (c == 'D')  { mode = 3; value = 0; }
        else if (c == 'T')  { mode = 4; value = 0; }
        else if (c == 'B')  { mode = 5; value = 0; }
        else {
            if (mode == 1) g_kp_x10 = value;      // P50 = Kp 5.0
            if (mode == 2) g_ki_x100 = value;     // I8  = Ki 0.08
            if (mode == 3) g_kd_x100 = value;     // D5  = Kd 0.05
            if (mode == 4) g_target = value;      // T42 = 目标42
            if (mode == 5) g_base_pwm = value;    // B800= 前馈800
            if (mode) pid_apply_params();         // 复位PID
            mode = 0; value = 0;
        }
    }
}
```

**命令格式 (数值=实际值×10/100)：**

| 命令 | 含义 | 示例 |
|------|------|------|
| `P5` | Kp = 0.5 | Kp×10 = 5 |
| `I8` | Ki = 0.08 | Ki×100 = 8 |
| `D0` | Kd = 0 | |
| `T42` | target = 42 脉冲/周期 | |
| `B800` | base PWM = 800 (前馈) | |
| 回车 | **自动重置 PID，回显确认** | |

**CSV 输出格式 (兼容 VOFA+ / Excel / 串口绘图)：**
```
count,pwm,target,Kp_x10,Ki_x100,Kd_x100,base_pwm
62,590,42,5,8,0,800
```

> ⚠️ **VOFA+ 串口命令防丢**: CSV 输出频率降到每 4 个 PID 周期 (80ms)。`csv_skip` 计数器跳过不发 CSV 的周期，UART RX 空闲接收命令不丢包。

**VOFA+ 连接设置：**
| 参数 | 值 |
|------|-----|
| 端口 | COM5 |
| 波特率 | 115200 |
| 协议 | CSV |
| 分隔符 | `,` |
| 通道 | CH1=速度 CH2=PWM CH3=目标 |

**调参工作流：**
1. 先发 `B999 T999` 满功率跑 → 记下最大 count = 上限
2. `T=上限×0.9` → 设可达目标
3. `B=上限附近 PWM` → 设前馈
4. `P5 I0 D0` → P-only 看是否稳定
5. `I8` → 加微量积分消除静差
6. 振荡 → 降 P 或加 D

#### ⚠️ 串口调参自动配置

当用户说"调PID"时，自动执行以下配置：

**串口设置 (必须)：**

| 参数 | 值 |
|------|-----|
| 端口 | COM5 (CH340, PA10/PA11) |
| 波特率 | 115200 |
| 数据位 | 8 |
| 校验 | None |
| 停止位 | 1 |
| 工具 | 串口调试助手 / PuTTY / VS Code Serial Monitor |

**操作步骤：**
1. 打开串口助手 → **COM5, 115200**
2. 启动后自动输出 CSV: `count,pwm,target,Kp,Ki,Kd,base`
3. 在发送框输入命令 → 点发送
4. 每次改参数后自动回显确认 (如 `P5 I8 D0 T42 B800`)
5. 数据可**拷贝粘贴到 Excel**，插入折线图观察趋势

**PID 调参快捷命令：**
```
B800 T42 P5 I8 D0     ← 推荐起始值
B999 T999             ← 测最大计数(不要长时间满功率)
B800 T82 P5 I8 D0     ← 20ms采样用
```

---

## IMU601 Yaw 角转向 PID：PA26 一键顺时针 90 度

### 已验证场景

- MCU: MSPM0G3507 / Tianmengxing board
- IMU: ATK/正点原子 IMU601, UART0 on PA0/PA1
- Motor driver: TB6612FNG
- Start key: PA26, active low
- Gyro zero key: PA25, active low
- Result: PA26 pressed once -> robot turns clockwise 90 degrees -> stops without shaking

Note: older MPU6050 yaw examples in this file may use PA26 as yaw-zero key. For the verified IMU601 car setup, use **PA25 for gyro zero** and **PA26 for turn start**.

### 关键参数

```c
#define MOTOR_PWM_MAX           (2133U)
#define TURN_CONTROL_PERIOD_MS  (20U)
#define TURN_TARGET_DEG         (90.0f)
#define TURN_KP                 (9.0f)
#define TURN_KI                 (0.06f)     /* ⚠️ 建议设0, 积分导致来回摆 */
#define TURN_KD                 (0.7f)
#define TURN_PWM_MIN            (180)       /* ⚠️ 不能太低, 低于摩擦力会卡死 */
#define TURN_PWM_MAX            (620)
#define TURN_NEAR_ERR_DEG       (12.0f)
#define TURN_NEAR_PWM_MIN       (70)        /* ⚠️ 必须≥远区MIN, 否则进近区卡死 */
#define TURN_NEAR_PWM_MAX       (260)
#define TURN_STOP_ERR_DEG       (3.0f)
#define TURN_STOP_GYRO_DPS      (25.0f)
#define TURN_SETTLE_TICKS       (3U)
#define TURN_INTEGRAL_LIMIT     (600.0f)
#define TURN_TIMEOUT_MS         (3000U)     /* ⚠️ 超时保护: 防电机卡死系统挂起 */
```

### ⚠️ yaw 方向铁律

IMU601 yaw: **逆时针为正(+), 顺时针为负(-)**。

```c
/* ✅ 顺时针: 目标 = 当前 - 90 */
targetYaw = wrap_angle_180(currentYaw - 90.0f);

/* ❌ 逆时针: 这是 +90 */
targetYaw = wrap_angle_180(currentYaw + 90.0f);
```

### 控制公式

```c
targetYaw = wrap_angle_180(currentYaw - 90.0f);  /* ⚠️ 顺时针减 */
errorDeg = wrap_angle_180(currentYaw - targetYaw); /* ⚠️ 当前-目标 */
integral += errorDeg * 0.02f;
output = TURN_KP * errorDeg + TURN_KI * integral + TURN_KD * gyroZ; /* ⚠️ +Kd */
```

### ⚠️ 最小 PWM 陷阱

`TURN_PWM_MIN=0` → PID 输出降到摩擦力以下 → 电机停转 → 误差卡住 → 停车条件不满足 → **系统死锁**。

`TURN_NEAR_PWM_MIN < TURN_PWM_MIN` → 进近目标区时 PWM 突降 → 也可能卡死。

**规则**: 近目标区最小 PWM 必须 ≥ 远区最小 PWM，都必须大于电机摩擦死区。超时保护必须有。

输出到电机：

```c
motor_left_set(pwm);
motor_right_set(-pwm);
```

如果实车方向相反，优先把 `TURN_TARGET_DEG` 改成 `-90.0f`，或交换左右电机符号。

### 防抖停车经验

最容易出问题的是“已经到 90 度但还在抖”。原因通常是误差很小时仍然强制使用较大的最小 PWM，导致小车在目标附近反复追赶。

已验证解决方法：
- 进入近目标区后降低 PWM 下限和上限：`12 deg` 内使用 `70~260`
- 停止死区放宽到 `3 deg`
- 角速度阈值放宽到 `25 dps`
- 连续满足 3 个控制周期后停车
- 停车时必须清零积分项

调参顺序：
1. 若到 90 度附近抖动：先降低 `TURN_NEAR_PWM_MIN`，再增大 `TURN_STOP_ERR_DEG`
2. 若转不到角度就停：减小 `TURN_STOP_ERR_DEG` 或提高 `TURN_NEAR_PWM_MIN`
3. 若冲过头明显：降低 `TURN_KP` 或增大 `TURN_KD`
4. 若起步转不动：提高 `TURN_PWM_MIN`

### 工程注意

- OLED 必须非阻塞刷新，否则影响 IMU 接收和控制周期。
- IMU UART RX 用中断搬运到 ring buffer，主循环解析。
- SysTick 提供 1ms 时间基，PID 服务函数每 20ms 运行一次。
- TB6612 的 PWM compare 使用反相占空比：`compare = MOTOR_PWM_MAX - duty`。
- TIMG8 PWM 由 SysConfig 生成后，需要在代码里调用 `DL_TimerG_startCounter(MOTOR_PWM_INST)`。
- 实车首次测试必须架空车轮，先 PA25 静止校准，再 PA26 启动转向。

完整复用说明见 `examples/imu601_yaw_pid_90deg_turn.md`。
