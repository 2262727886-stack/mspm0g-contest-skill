/**
 * @file motor.c
 * @brief TB6612FNG 电机驱动实现
 */

#include "motor.h"
#include "ti_msp_dl_config.h"

/* 方向引脚 IOMUX */
#define DIR_L_BIN1_IOMUX    IOMUX_PINCM19   /* PB0 */
#define DIR_L_BIN2_IOMUX    IOMUX_PINCM20   /* PB1 */
#define DIR_R_AIN1_IOMUX    IOMUX_PINCM10   /* PA13 */
#define DIR_R_AIN2_IOMUX    IOMUX_PINCM9    /* PA12 */

/* 左轮方向控制 */
static void left_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_0);
    else     DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0);
    if (in2) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_1);
    else     DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);
}

/* 右轮方向控制 */
static void right_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(GPIOA, DL_GPIO_PIN_13);
    else     DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_13);
    if (in2) DL_GPIO_setPins(GPIOA, DL_GPIO_PIN_12);
    else     DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_12);
}

/* 左轮 PWM */
static void left_pwm(int16_t duty)
{
    if (duty < 0) duty = 0;
    if (duty > MOTOR_PWM_MAX) duty = MOTOR_PWM_MAX;
    uint32_t compare = (uint32_t)(MOTOR_PWM_MAX - duty);
    DL_TimerG_setCaptureCompareValue(PWM_MOTOR_INST, compare, GPIO_TIMG8_C0_IDX);
}

/* 右轮 PWM */
static void right_pwm(int16_t duty)
{
    if (duty < 0) duty = 0;
    if (duty > MOTOR_PWM_MAX) duty = MOTOR_PWM_MAX;
    uint32_t compare = (uint32_t)(MOTOR_PWM_MAX - duty);
    DL_TimerG_setCaptureCompareValue(PWM_MOTOR_INST, compare, GPIO_TIMG8_C1_IDX);
}

void motor_init(void)
{
    DL_GPIO_initDigitalOutput(DIR_L_BIN1_IOMUX);
    DL_GPIO_initDigitalOutput(DIR_L_BIN2_IOMUX);
    DL_GPIO_initDigitalOutput(DIR_R_AIN1_IOMUX);
    DL_GPIO_initDigitalOutput(DIR_R_AIN2_IOMUX);
    motor_stop();
    DL_TimerG_startCounter(PWM_MOTOR_INST);
}

void motor_stop(void)
{
    left_dir(false, false);
    right_dir(false, false);
    left_pwm(0);
    right_pwm(0);
}

void motor_left_set(int16_t duty)
{
    if (duty > 0) {
        left_dir(false, true);
        left_pwm(duty);
    } else if (duty < 0) {
        left_dir(true, false);
        left_pwm(-duty);
    } else {
        left_dir(false, false);
        left_pwm(0);
    }
}

void motor_right_set(int16_t duty)
{
    if (duty > 0) {
        right_dir(false, true);
        right_pwm(duty);
    } else if (duty < 0) {
        right_dir(true, false);
        right_pwm(-duty);
    } else {
        right_dir(false, false);
        right_pwm(0);
    }
}
