/**
 * PID 控制器实现
 */
#include "pid.h"

void PID_Init(PID_t *pid, float kp, float ki, float kd, float out_min, float out_max) {
    pid->Kp = kp; pid->Ki = ki; pid->Kd = kd;
    pid->setpoint = 0;
    pid->integral = 0;
    pid->prev_error = 0;
    pid->out_min = out_min;
    pid->out_max = out_max;
}

float PID_Update(PID_t *pid, float measurement, float dt) {
    float error = pid->setpoint - measurement;
    float p_out = pid->Kp * error;

    pid->integral += error * dt;
    // 积分限幅
    if (pid->integral > pid->out_max)  pid->integral = pid->out_max;
    if (pid->integral < pid->out_min)  pid->integral = pid->out_min;
    float i_out = pid->Ki * pid->integral;

    float d_out = pid->Kd * (measurement - pid->prev_error) / dt;
    pid->prev_error = measurement;

    float out = p_out + i_out + d_out;
    if (out > pid->out_max)  out = pid->out_max;
    if (out < pid->out_min)  out = pid->out_min;
    return out;
}
