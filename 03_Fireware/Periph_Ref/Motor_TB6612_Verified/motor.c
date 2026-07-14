/**
 * TB6612 直流电机驱动实现
 */
#include "motor.h"

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
    if (speed > 1000) speed = 1000;
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, GPIO_PWM_TB6612_C0_IDX, speed);
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
    if (speed > 1000) speed = 1000;
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, GPIO_PWM_TB6612_C1_IDX, speed);
}

void Motor_Brake(void) {
    DL_GPIO_setPins(GPIO_TB6612_AIN1_PORT, GPIO_TB6612_AIN1_PIN);
    DL_GPIO_setPins(GPIO_TB6612_AIN2_PORT, GPIO_TB6612_AIN2_PIN);
    DL_GPIO_setPins(GPIO_TB6612_BIN1_PORT, GPIO_TB6612_BIN1_PIN);
    DL_GPIO_setPins(GPIO_TB6612_BIN2_PORT, GPIO_TB6612_BIN2_PIN);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, GPIO_PWM_TB6612_C0_IDX, 0);
    DL_TimerG_setCaptureCompareValue(PWM_TB6612_INST, GPIO_PWM_TB6612_C1_IDX, 0);
}
