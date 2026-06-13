/**
 * motor.c — TB6612FNG 电机驱动实现
 *
 * TB6612FNG 引脚:
 *   A 通道 (右轮): PWMA=PB15, AIN1=PA13, AIN2=PA12
 *   B 通道 (左轮): PWMB=PB16, BIN1=PB0,  BIN2=PB1
 *
 * PWM 反逻辑:
 *   TIMG8 比较值 = PWM_MAX - duty
 *   duty=0   → CC=2133 → 输出 0%   (电机停)
 *   duty=2103 → CC=30  → 输出 ~100% (电机满速)
 */
#include "motor.h"
#include "ti_msp_dl_config.h"

/**
 * 左轮方向控制 (B 通道: BIN1=PB0, BIN2=PB1)
 *
 * BIN1=L, BIN2=H → 前进
 * BIN1=H, BIN2=L → 后退
 */
static void left_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(DIR_B_PORT, DIR_B_BIN1_PIN);
    else     DL_GPIO_clearPins(DIR_B_PORT, DIR_B_BIN1_PIN);

    if (in2) DL_GPIO_setPins(DIR_B_PORT, DIR_B_BIN2_PIN);
    else     DL_GPIO_clearPins(DIR_B_PORT, DIR_B_BIN2_PIN);
}

/**
 * 右轮方向控制 (A 通道: AIN1=PA13, AIN2=PA12)
 *
 * ⚠️ 右轮与左轮物理方向相反, 所以:
 *   AIN1=L, AIN2=H → 前进 (对右轮来说)
 */
static void right_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(DIR_A_PORT, DIR_A_AIN1_PIN);
    else     DL_GPIO_clearPins(DIR_A_PORT, DIR_A_AIN1_PIN);

    if (in2) DL_GPIO_setPins(DIR_A_PORT, DIR_A_AIN2_PIN);
    else     DL_GPIO_clearPins(DIR_A_PORT, DIR_A_AIN2_PIN);
}

/**
 * 限幅: 把有符号 duty 转为无符号, 限制到安全范围
 */
static uint16_t abs_limit_duty(int16_t duty)
{
    int16_t max_duty = (int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD);

    if (duty < 0) duty = (int16_t)(-duty);
    if (duty > max_duty) duty = max_duty;

    return (uint16_t)duty;
}

/**
 * 左轮 PWM 输出 (PB16 = TIMG8_C1)
 * 反逻辑: CC = PWM_MAX - duty
 */
static void left_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST,
        (uint16_t)(MOTOR_PWM_MAX - duty), DL_TIMER_CC_1_INDEX);
}

/**
 * 右轮 PWM 输出 (PB15 = TIMG8_C0)
 * 反逻辑: CC = PWM_MAX - duty
 */
static void right_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST,
        (uint16_t)(MOTOR_PWM_MAX - duty), DL_TIMER_CC_0_INDEX);
}

/**
 * 设置左轮速度
 * @param duty  正=前进, 负=后退
 */
void motor_left_set(int16_t duty)
{
    if (duty >= 0) {
        left_dir(false, true);   /* 前进 */
    } else {
        left_dir(true, false);   /* 后退 */
    }
    left_pwm(abs_limit_duty(duty));
}

/**
 * 设置右轮速度 (方向已翻转)
 * @param duty  正=前进, 负=后退
 */
void motor_right_set(int16_t duty)
{
    if (duty >= 0) {
        right_dir(false, true);  /* 前进 */
    } else {
        right_dir(true, false);  /* 后退 */
    }
    right_pwm(abs_limit_duty(duty));
}

/**
 * 停车: 方向脚全部拉低, PWM 清零
 */
void motor_stop(void)
{
    left_dir(false, false);
    right_dir(false, false);
    left_pwm(0);
    right_pwm(0);
}

/**
 * 电机初始化: 启动 PWM 定时器, 上电先停车
 */
void motor_init(void)
{
    motor_stop();
    DL_TimerG_startCounter(MOTOR_PWM_INST);
}
