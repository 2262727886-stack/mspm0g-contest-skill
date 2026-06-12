/**
 * @file motor.h
 * @brief TB6612FNG 电机驱动模块
 *
 * 硬件连接：
 *   右轮 (A 通道): PWMA=PB15(TIMG8_C0), AIN1=PA13, AIN2=PA12
 *   左轮 (B 通道): PWMB=PB16(TIMG8_C1), BIN1=PB0,  BIN2=PB1
 *
 * PWM 参数：
 *   TIMG8, 20kHz, period=2133
 *   比较值取反逻辑: CC=0->100%, CC=period->0%
 */

#ifndef MOTOR_H
#define MOTOR_H

#include <stdint.h>
#include <stdbool.h>

/* PWM 参数 */
#define MOTOR_PWM_MAX       2133
#define MOTOR_PWM_DEAD      30

/* 函数声明 */
void motor_init(void);
void motor_stop(void);
void motor_left_set(int16_t duty);
void motor_right_set(int16_t duty);

#endif /* MOTOR_H */
