/**
 * TB6612 直流电机驱动 — MSPM0G3507
 * PWM:  TIMG8 PB15(PWMA) PB16(PWMB) 20kHz
 * DIR:  PA13(AIN1) PA12(AIN2) PB0(BIN1) PB1(BIN2)
 */
#ifndef __MOTOR_H
#define __MOTOR_H
#include "ti_msp_dl_config.h"

void Motor_Init(void);
void Motor_A(int16_t speed);   // -1000~1000
void Motor_B(int16_t speed);
void Motor_Brake(void);

#endif
