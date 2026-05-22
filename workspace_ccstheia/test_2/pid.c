/**
 * @file pid.c
 * @brief Small PID implementation with integral and output limiting.
 */
#include "pid.h"

static float clamp_float(float value, float min_value, float max_value)
{
    if (value > max_value) {
        return max_value;
    }
    if (value < min_value) {
        return min_value;
    }
    return value;
}

void pid_init(PID *pid, float kp, float ki, float kd,
              float max_integral, float max_output, float target)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->max_integral = max_integral;
    pid->max_output = max_output;
    pid->target = target;
    pid_reset(pid);
}

void pid_reset(PID *pid)
{
    pid->error = 0.0f;
    pid->last_error = 0.0f;
    pid->integral = 0.0f;
    pid->output = 0.0f;
}

void pid_set_target(PID *pid, float target)
{
    pid->target = target;
}

float pid_calc(PID *pid, float current)
{
    float derivative;

    pid->last_error = pid->error;
    pid->error = pid->target - current;
    pid->integral += pid->error;
    pid->integral = clamp_float(pid->integral, -pid->max_integral, pid->max_integral);

    derivative = pid->error - pid->last_error;
    pid->output = (pid->kp * pid->error) +
                  (pid->ki * pid->integral) +
                  (pid->kd * derivative);
    pid->output = clamp_float(pid->output, -pid->max_output, pid->max_output);

    return pid->output;
}
