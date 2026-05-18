/**
 * PID 控制器
 */
#ifndef __PID_H
#define __PID_H

typedef struct {
    float Kp, Ki, Kd;
    float setpoint;        // 目标值
    float integral;        // 积分累加
    float prev_error;      // 上次误差
    float out_min, out_max; // 输出限幅
} PID_t;

void PID_Init(PID_t *pid, float kp, float ki, float kd, float out_min, float out_max);
float PID_Update(PID_t *pid, float measurement, float dt);

#endif
