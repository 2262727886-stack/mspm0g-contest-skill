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

/* TIMG8 周期值。PWM 输出使用“PWM_MAX - duty”，所以 duty=0 时比较值为周期值。 */
#define PWM_MAX         2133

/* 留一点死区，避免 duty 接近周期极限时输出异常。 */
#define PWM_DEAD        30

/* 基础前进速度。速度越大车越快，调试阶段建议从 220~350 慢慢试。 */
#define RUN_DUTY        450

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

/* ========================= 小工具函数 ========================= */

/* PWM 缓启动/缓停止：把 current 每次向 target 靠近一点。 */
static int16_t ramp_to(int16_t current, int16_t target)
{
    if (current < target) {
        current = (int16_t)(current + DUTY_RAMP_STEP);
        if (current > target) current = target;
    } else if (current > target) {
        current = (int16_t)(current - DUTY_RAMP_STEP);
        if (current < target) current = target;
    }

    return current;
}

/* 按键为上拉输入，按下时被拉到 GND，所以读到 0 表示按下。 */
static bool button_pressed(uint32_t port, uint32_t pin)
{
    return (DL_GPIO_readPins((GPIO_Regs *)port, pin) == 0U);
}

/* 简单浮点转字符串，只保留 1 位小数，供 OLED 显示 yaw。 */
static void ftoa_1d(float val, char *out)
{
    uint8_t p = 0U;

    if (val < 0.0f) {
        out[p++] = '-';
        val = -val;
    }

    uint16_t iv = (uint16_t)val;
    if (iv >= 1000U) iv = 999U;

    if (iv >= 100U) out[p++] = (char)('0' + (iv / 100U));
    if (iv >= 10U || p > 0U) out[p++] = (char)('0' + ((iv / 10U) % 10U));
    out[p++] = (char)('0' + (iv % 10U));
    out[p++] = '.';
    out[p++] = (char)('0' + (uint8_t)((val - (float)iv) * 10.0f + 0.5f));
    out[p] = '\0';
}

/* 把角度约束到 -180~180，避免 OLED 显示跳到 300 多度。 */
static float wrap_180(float angle)
{
    while (angle > 180.0f) angle -= 360.0f;
    while (angle < -180.0f) angle += 360.0f;
    return angle;
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
