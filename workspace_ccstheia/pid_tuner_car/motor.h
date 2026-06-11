#ifndef MOTOR_H
#define MOTOR_H

#include <stdbool.h>
#include <stdint.h>

/* TIMG8 周期值来自 SysConfig。PWM 比较值使用 PWM_MAX - duty。 */
#define MOTOR_PWM_MAX   2133
#define MOTOR_PWM_DEAD  30

void motor_init(void);
void motor_left_set(int16_t duty);
void motor_right_set(int16_t duty);
void motor_stop(void);

#endif
