/**
 * TB6612 直流电机驱动实现
 */
#include "motor.h"

#define MOTOR_PWM_PERIOD   (4000)
#define MOTOR_PWM_MAX      (1000)

static uint16_t Motor_CompareFromDuty(int16_t duty)
{
    if (duty < 0) {
        duty = -duty;
    }
    if (duty > MOTOR_PWM_MAX) {
        duty = MOTOR_PWM_MAX;
    }

    return (uint16_t)(MOTOR_PWM_PERIOD -
                      ((int32_t)duty * MOTOR_PWM_PERIOD / MOTOR_PWM_MAX));
}

void Motor_Init(void) {
    DL_GPIO_clearPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
    DL_GPIO_clearPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    DL_GPIO_clearPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
    DL_GPIO_clearPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
}

void Motor_A(int16_t speed) {
    if (speed > 0) {
        DL_GPIO_setPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
        DL_GPIO_clearPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    } else {
        DL_GPIO_clearPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
        DL_GPIO_setPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
        speed = -speed;
    }
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST,
                                     Motor_CompareFromDuty(speed),
                                     GPIO_PWM_TB6612_C0_IDX);
}

void Motor_B(int16_t speed) {
    if (speed > 0) {
        DL_GPIO_setPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
        DL_GPIO_clearPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    } else {
        DL_GPIO_clearPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
        DL_GPIO_setPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
        speed = -speed;
    }
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST,
                                     Motor_CompareFromDuty(speed),
                                     GPIO_PWM_TB6612_C1_IDX);
}

void Motor_Brake(void) {
    DL_GPIO_setPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
    DL_GPIO_setPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    DL_GPIO_setPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
    DL_GPIO_setPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, MOTOR_PWM_PERIOD,
                                     GPIO_PWM_TB6612_C0_IDX);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, MOTOR_PWM_PERIOD,
                                     GPIO_PWM_TB6612_C1_IDX);
}
