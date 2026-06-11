#include "speed_pid.h"

void speed_pid_init(SpeedPid *pid, float kp, float ki, float kd,
                    int16_t feedforward, int16_t limit)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integral = 0.0f;
    pid->last_error = 0.0f;
    pid->feedforward = feedforward;
    pid->output_limit = limit;
}

void speed_pid_reset(SpeedPid *pid)
{
    pid->integral = 0.0f;
    pid->last_error = 0.0f;
}

int16_t speed_pid_update(SpeedPid *pid, int16_t target, int16_t current)
{
    float error = (float)(target - current);
    float derivative = error - pid->last_error;
    float output;

    if (target <= 0) {
        speed_pid_reset(pid);
        return 0;
    }

    /* 积分项用于消除稳态误差；目标速度很小，积分限幅必须保守。 */
    pid->integral += error;
    if (pid->integral > 300.0f) pid->integral = 300.0f;
    if (pid->integral < -300.0f) pid->integral = -300.0f;

    output = (float)pid->feedforward
           + pid->kp * error
           + pid->ki * pid->integral
           + pid->kd * derivative;
    pid->last_error = error;

    if (output > (float)pid->output_limit) output = (float)pid->output_limit;
    if (output < 0.0f) output = 0.0f;

    return (int16_t)output;
}
