/**
 * @file pid_ctrl.h
 * @brief PID 控制器模块
 */

#ifndef PID_CTRL_H
#define PID_CTRL_H

#include <stdint.h>

/* PID 参数结构体 */
typedef struct {
    float kp;
    float ki;
    float kd;
    float integral;
    float integral_max;
    float output_max;
} PID_Controller;

/* 全局 PID 参数 */
extern float g_kp;
extern float g_ki;
extern float g_kd;
extern int16_t g_target_l;
extern int16_t g_target_r;

/* 函数声明 */
void pid_ctrl_init(void);
void pid_ctrl_reset(void);
int16_t pid_speed_balance(int16_t speed_l, int16_t speed_r);
int16_t ramp_to(int16_t current, int16_t target);
void pid_tuner_parse_command(char *cmd);
void pid_tuner_output_csv(uint32_t timestamp_ms,
                           int16_t speed_l, int16_t speed_r,
                           int16_t pwm_l, int16_t pwm_r);

#endif /* PID_CTRL_H */
