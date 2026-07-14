/**
 * @file motor.h
 * @brief TB6612FNG two-channel DC motor driver.
 *
 * Current pin plan:
 *   PWMA -> PB15 / TIMG8_C0
 *   PWMB -> PB16 / TIMG8_C1
 *   AIN1 -> PA13, AIN2 -> PA12
 *   BIN1 -> PB0,  BIN2 -> PB1
 */
#ifndef MOTOR_H
#define MOTOR_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#define MOTOR_DUTY_MAX 1000

void Motor_Init(void);
void Motor_SetA(int16_t duty);
void Motor_SetB(int16_t duty);
void Motor_Stop(void);
void Motor_Brake(void);

#endif
