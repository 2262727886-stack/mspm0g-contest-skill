#include "motor.h"
#include "ti_msp_dl_config.h"

/* 左轮接 TB6612FNG B 通道：BIN1=PB0, BIN2=PB1。 */
static void left_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(DIR_B_PORT, DIR_B_BIN1_PIN);
    else     DL_GPIO_clearPins(DIR_B_PORT, DIR_B_BIN1_PIN);

    if (in2) DL_GPIO_setPins(DIR_B_PORT, DIR_B_BIN2_PIN);
    else     DL_GPIO_clearPins(DIR_B_PORT, DIR_B_BIN2_PIN);
}

/* 右轮接 TB6612FNG A 通道：AIN1=PA13, AIN2=PA12。 */
static void right_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(DIR_A_PORT, DIR_A_AIN1_PIN);
    else     DL_GPIO_clearPins(DIR_A_PORT, DIR_A_AIN1_PIN);

    if (in2) DL_GPIO_setPins(DIR_A_PORT, DIR_A_AIN2_PIN);
    else     DL_GPIO_clearPins(DIR_A_PORT, DIR_A_AIN2_PIN);
}

/* 把有符号 PWM 命令限制到安全范围，避免比较值越界。 */
static uint16_t abs_limit_duty(int16_t duty)
{
    int16_t max_duty = (int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD);

    if (duty < 0) duty = (int16_t)(-duty);
    if (duty > max_duty) duty = max_duty;

    return (uint16_t)duty;
}

/* 左轮 PWM = PWMB = PB16 = TIMG8_C1。 */
static void left_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST,
        (uint16_t)(MOTOR_PWM_MAX - duty), DL_TIMER_CC_1_INDEX);
}

/* 右轮 PWM = PWMA = PB15 = TIMG8_C0。 */
static void right_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST,
        (uint16_t)(MOTOR_PWM_MAX - duty), DL_TIMER_CC_0_INDEX);
}

void motor_left_set(int16_t duty)
{
    if (duty >= 0) {
        left_dir(false, true);
    } else {
        left_dir(true, false);
    }

    left_pwm(abs_limit_duty(duty));
}

void motor_right_set(int16_t duty)
{
    if (duty >= 0) {
        right_dir(false, true);
    } else {
        right_dir(true, false);
    }

    right_pwm(abs_limit_duty(duty));
}

void motor_stop(void)
{
    left_dir(false, false);
    right_dir(false, false);
    left_pwm(0);
    right_pwm(0);
}

void motor_init(void)
{
    /* SysConfig 会生成 GPIO 端口/引脚宏，这里只确保上电后先停车。 */
    motor_stop();
    DL_TimerG_startCounter(MOTOR_PWM_INST);
}
