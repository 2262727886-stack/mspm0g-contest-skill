/**
 * main.c — 小车 PID 直线运行 + DMP 航向修正
 *
 * PA25 启动/停止, PA26 yaw 校零, OLED 显示状态
 *
 * 控制逻辑:
 *   停止态 → PA25 按下 → 锁定当前航向 → 两轮差速 PD 修正 → 直走
 *   运行中 → PA25 再按 → 停车
 */

#include "ti_msp_dl_config.h"
#include "oled.h"
#include "mpu_port.h"
#include "delay.h"
#include "pid_ctrl.h"
#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

extern volatile uint32_t sys_tick_ms;
void SysTick_Handler(void) { sys_tick_ms++; }

/* ================================================================
 * TB6612 电机引脚 — 用户实际接线
 *
 *   电机A (右轮): PWMA=PB15(C0), AIN1=PA13, AIN2=PA12
 *   电机B (左轮): PWMB=PB16(C1), BIN1=PB0,  BIN2=PB1
 * ================================================================ */
/* 右轮 (Motor A): PWMA + AIN1/AIN2 */
/*
 * Active motor map used by this file:
 *   left  wheel = DIR_L(AIN1/AIN2) + TIMG8 C0 / PB15
 *   right wheel = DIR_R(BIN1/BIN2) + TIMG8 C1 / PB16
 */
#define M_R1_PORT   DIR_R_PORT
#define M_R1_PIN    DIR_R_BIN1_PIN
#define M_R1_IOMUX  DIR_R_BIN1_IOMUX
#define M_R2_PORT   DIR_R_PORT
#define M_R2_PIN    DIR_R_BIN2_PIN
#define M_R2_IOMUX  DIR_R_BIN2_IOMUX

/* 左轮 (Motor B): PWMB + BIN1/BIN2 */
#define M_L1_PORT   DIR_L_PORT
#define M_L1_PIN    DIR_L_AIN1_PIN
#define M_L1_IOMUX  DIR_L_AIN1_IOMUX
#define M_L2_PORT   DIR_L_PORT
#define M_L2_PIN    DIR_L_AIN2_PIN
#define M_L2_IOMUX  DIR_L_AIN2_IOMUX

/* PWM: TIMG8, PB15=C0(左), PB16=C1(右) — SysConfig 生成 */
#define PWM_TIMER    MOTOR_PWM_INST
#define PWM_MAX      2133
#define PWM_DEAD     30

/* 速度参数 — 改这里调节快慢 */
#define TARGET_SPEED  300     /* 基础速度 (PWM占空比/2133, 120≈5.6%, 很慢) */
#define MAX_CORRECT   180     /* 最大差速修正 */

/* ================================================================
 * 电机底层操作
 * ================================================================ */
static void motor_l_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(M_L1_PORT, M_L1_PIN);
    else    DL_GPIO_clearPins(M_L1_PORT, M_L1_PIN);
    if (in2) DL_GPIO_setPins(M_L2_PORT, M_L2_PIN);
    else    DL_GPIO_clearPins(M_L2_PORT, M_L2_PIN);
}

static void motor_r_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(M_R1_PORT, M_R1_PIN);
    else    DL_GPIO_clearPins(M_R1_PORT, M_R1_PIN);
    if (in2) DL_GPIO_setPins(M_R2_PORT, M_R2_PIN);
    else    DL_GPIO_clearPins(M_R2_PORT, M_R2_PIN);
}

static void motor_pwm_l(uint16_t duty)
{
    /* Active: left PWM = TIMG8 C0 / PB15. */
    /* 左轮 = Motor B = PWMB = PB16 = TIMG8 C1, CC=PERIOD-duty */
    DL_TimerG_setCaptureCompareValue(PWM_TIMER, (uint16_t)(PWM_MAX - duty), DL_TIMER_CC_0_INDEX);
}

static void motor_pwm_r(uint16_t duty)
{
    /* Active: right PWM = TIMG8 C1 / PB16. */
    /* 右轮 = Motor A = PWMA = PB15 = TIMG8 C0, CC=PERIOD-duty */
    DL_TimerG_setCaptureCompareValue(PWM_TIMER, (uint16_t)(PWM_MAX - duty), DL_TIMER_CC_1_INDEX);
}

/**
 * 左轮速度: duty>0=前进, <0=后退
 */
static void motor_set_l(int16_t duty)
{
    int16_t max_d = (int16_t)(PWM_MAX - PWM_DEAD);
    if (duty > max_d) duty = max_d;
    if (duty < -max_d) duty = -max_d;
    if (duty >= 0) { motor_l_dir(0, 1); motor_pwm_l((uint16_t)duty); }
    else           { motor_l_dir(1, 0); motor_pwm_l((uint16_t)(-duty)); }
}

static void motor_set_r(int16_t duty)
{
    /* 右电机与左电机物理安装方向相反, 前进时方向控制翻转 */
    int16_t max_d = (int16_t)(PWM_MAX - PWM_DEAD);
    if (duty > max_d) duty = max_d;
    if (duty < -max_d) duty = -max_d;
    if (duty >= 0) { motor_r_dir(1, 0); motor_pwm_r((uint16_t)duty); }
    else           { motor_r_dir(0, 1); motor_pwm_r((uint16_t)(-duty)); }
}

static void motor_stop(void)
{
    motor_l_dir(0, 0); motor_r_dir(0, 0);  /* 短接制动 */
    motor_pwm_l(0);    motor_pwm_r(0);
}

static void motor_init(void)
{
    DL_GPIO_initDigitalOutput(M_L1_IOMUX);
    DL_GPIO_initDigitalOutput(M_L2_IOMUX);
    DL_GPIO_initDigitalOutput(M_R1_IOMUX);
    DL_GPIO_initDigitalOutput(M_R2_IOMUX);
    motor_stop();
}

/* ================================================================
 * LED, 按键, OLED 辅助
 * ================================================================ */
static void led_on(void)  { DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN); }
static void led_off(void) { DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN); }

static int btn_cal(void)   { return DL_GPIO_readPins(CAL_PORT, CAL_KEY_PIN) ? 0 : 1; }
static int btn_start(void) { return DL_GPIO_readPins(START_PORT, START_BTN_PIN) ? 0 : 1; }

static void ftoa_1d(float val, char *out)
{
    uint8_t p = 0U;
    if (val < 0.0f) { out[p++] = '-'; val = -val; }
    uint8_t iv = (uint8_t)val;
    uint8_t i100 = iv / 100U, i10 = (iv / 10U) % 10U, i1 = iv % 10U;
    if (i100 > 0U) out[p++] = (char)('0' + i100);
    if (i100 > 0U || i10 > 0U || p > 0U) out[p++] = (char)('0' + i10);
    out[p++] = (char)('0' + i1); out[p++] = '.';
    float frac_f = (val - (float)iv) * 10.0f + 0.5f;
    uint8_t frac = (uint8_t)frac_f;
    if (frac > 9U) frac = 9U;
    out[p++] = (char)('0' + frac); out[p] = '\0';
}

/* ================================================================
 * 最短弧偏差 (ZLC 算法)
 *   导航坐标 0-360°, 返回 ±180° 范围内的最小偏差
 *   正值 = 目标在右 (需右转), 负值 = 目标在左 (需左转)
 * ================================================================ */
static float minor_arc(float target, float current)
{
    float err = target - current;
    while (err >  180.0f) err -= 360.0f;
    while (err < -180.0f) err += 360.0f;
    return err;
}

/* ================================================================
 * 主程序
 * ================================================================ */
int main(void)
{
    SYSCFG_DL_init();

    /* 按键上拉 (SysConfig 只设了 INPUT, 加 PULL_UP) */
    DL_GPIO_initDigitalInputFeatures(CAL_KEY_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(START_BTN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);

    /* 电机初始化 */
    motor_init();
    led_on();

    /* OLED */
    if (OLED_Init() != 0) {
        for (uint8_t i = 0; i < 3; i++) { led_off(); delay_ms(150); led_on(); delay_ms(150); }
    }
    OLED_Puts(0, 0, "MPU+DMP Init...");

    /* DMP 初始化 */
    int dmp_ret;
    uint8_t retry = 0;
    do { dmp_ret = DMP_Init(); if (dmp_ret == 0) break; retry++; delay_ms(100); }
    while (retry < 100);
    if (dmp_ret != 0) {
        char buf[22]; sprintf(buf, "DMP ERR:%d", dmp_ret);
        OLED_Puts(2, 0, buf); while (1) { led_off(); delay_ms(200); led_on(); delay_ms(200); }
    }

    /* 5s 静止校准 */
    float startup_yaw_zero = 0.0f;
    OLED_Puts(0, 0, "Calibrating...");
    {
        float d = 0.0f; for (uint8_t i = 0; i < 50; i++) {
            for (uint8_t j = 0; j < 10; j++) {
                if (DMP_Read_Data(&d, &d, &d) == 0) { startup_yaw_zero = d; }
                delay_ms(10);
            }
        }
    }

    /* 就绪 */
    motor_stop();
    led_off();
    OLED_Clear();
    OLED_Puts(0, 0, "READY");
    OLED_Puts(1, 0, "PA26=ZERO PA25=GO");
    OLED_Puts(5, 0, "Y:");

    /* ================================================================
     * 状态变量
     * ================================================================ */
    bool    running     = false;    /* 运行/停止 */
    float   target_yaw  = 0.0f;    /* 启动时锁定的航向 */
    float   yaw_zero    = 0.0f;    /* PA26 校零偏移 */
    float   pitch, roll, yaw;
    uint8_t cal_prev    = 0;
    uint8_t start_prev  = 0;
    char    str[10];
    uint16_t loop_cnt   = 0;
    int16_t base_speed   = TARGET_SPEED;
    int16_t max_correct  = MAX_CORRECT;

    yaw_zero = startup_yaw_zero;

    while (1)
    {
        /* ---- 读 DMP ---- */
        if (DMP_Read_Data(&pitch, &roll, &yaw) != 0) continue;
        float yaw_deg = yaw - yaw_zero;  /* 校零后的航向 */
        while (yaw_deg >  180.0f) yaw_deg -= 360.0f;
        while (yaw_deg < -180.0f) yaw_deg += 360.0f;

        if (!running) {
            yaw_zero = yaw;
            yaw_deg = 0.0f;
        }

        /* ---- PA26 校零 ---- */
        uint8_t cal_now = (uint8_t)btn_cal();
        if (cal_prev == 0 && cal_now == 1) {
            yaw_zero = yaw;  /* 记录偏移, 之后 yaw_deg=0 */
            OLED_ClearPage(4); OLED_Puts(4, 0, "ZEROED!");
            delay_ms(100); OLED_ClearPage(4);
        }
        cal_prev = cal_now;

        /* ---- PA25 启动/停止 ---- */
        uint8_t start_now = (uint8_t)btn_start();
        if (start_prev == 0 && start_now == 1) {
            if (!running) {
                /* 启动: 锁定当前航向, 存储为目标 */
                running = true;
                yaw_zero = yaw;
                target_yaw = 0.0f;
                PID_Speed_Reset();
                PID_Dir_Reset();
                OLED_ClearPage(1); OLED_Puts(1, 0, "RUNNING...");
            } else {
                /* 停止 */
                running = false;
                motor_stop();
                OLED_ClearPage(1); OLED_Puts(1, 0, "STOPPED");
            }
        }
        start_prev = start_now;

        /* ---- 运行态: PID 控制 ---- */
        if (running) {
            /* 航向 PD: 偏差 → 差速修正 */
            float heading_err = minor_arc(target_yaw, yaw_deg);
            float correction  = PID_Dir_Calc(heading_err);

            /* 限幅后分配到左右轮 */
            if (correction >  (float)max_correct) correction =  (float)max_correct;
            if (correction < -(float)max_correct) correction = -(float)max_correct;

            int16_t duty_l = (int16_t)((float)base_speed + correction);
            int16_t duty_r = (int16_t)((float)base_speed - correction);

            motor_set_l(duty_l);
            motor_set_r(duty_r);
        }

        /* ---- OLED 更新 (10Hz) ---- */
        loop_cnt++;
        if (loop_cnt >= 10U) {
            loop_cnt = 0;
            ftoa_1d(yaw_deg,         str); OLED_Puts(5, 20, str);
            if (running) {
                OLED_Puts(6, 0,  "Z:");
                ftoa_1d(target_yaw,                     str); OLED_Puts(6, 20, str);
                OLED_Puts(7, 0,  "D:");
                ftoa_1d(minor_arc(target_yaw, yaw_deg), str); OLED_Puts(7, 20, str);
            } else {
                OLED_ClearPage(6);
                OLED_ClearPage(7);
            }
            led_on(); delay_cycles(CPUCLK_FREQ / 400U); led_off();
        }
    }
}
