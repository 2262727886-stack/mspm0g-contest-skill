/**
 * @file motor.c
 * @brief TB6612FNG motor output layer.
 */
#include "motor.h"

#define MOTOR_PWM_PERIOD 4000U

static uint16_t compare_from_duty(int16_t duty)
{
    int32_t abs_duty = duty;

    if (abs_duty < 0) {
        abs_duty = -abs_duty;
    }
    if (abs_duty > MOTOR_DUTY_MAX) {
        abs_duty = MOTOR_DUTY_MAX;
    }

    return (uint16_t) (MOTOR_PWM_PERIOD -
        ((abs_duty * (int32_t) MOTOR_PWM_PERIOD) / MOTOR_DUTY_MAX));
}

void Motor_Init(void)
{
    Motor_Stop();
    DL_TimerG_startCounter(PWM_TB6612_INST);
}

void Motor_SetA(int16_t duty)
{
    if (duty > 0) {
        DL_GPIO_setPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
        DL_GPIO_clearPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    } else if (duty < 0) {
        DL_GPIO_clearPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
        DL_GPIO_setPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    } else {
        DL_GPIO_clearPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
        DL_GPIO_clearPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    }

    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST,
        compare_from_duty(duty), GPIO_PWM_TB6612_C0_IDX);
}

void Motor_SetB(int16_t duty)
{
    if (duty > 0) {
        DL_GPIO_setPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
        DL_GPIO_clearPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    } else if (duty < 0) {
        DL_GPIO_clearPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
        DL_GPIO_setPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    } else {
        DL_GPIO_clearPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
        DL_GPIO_clearPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    }

    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST,
        compare_from_duty(duty), GPIO_PWM_TB6612_C1_IDX);
}

void Motor_Stop(void)
{
    DL_GPIO_clearPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
    DL_GPIO_clearPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    DL_GPIO_clearPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
    DL_GPIO_clearPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, MOTOR_PWM_PERIOD, GPIO_PWM_TB6612_C0_IDX);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, MOTOR_PWM_PERIOD, GPIO_PWM_TB6612_C1_IDX);
}

void Motor_Brake(void)
{
    DL_GPIO_setPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
    DL_GPIO_setPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    DL_GPIO_setPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
    DL_GPIO_setPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, MOTOR_PWM_PERIOD, GPIO_PWM_TB6612_C0_IDX);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, MOTOR_PWM_PERIOD, GPIO_PWM_TB6612_C1_IDX);
}
