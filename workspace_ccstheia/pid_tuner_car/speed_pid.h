#ifndef SPEED_PID_H
#define SPEED_PID_H

#include <stdint.h>

typedef struct {
    float kp;
    float ki;
    float kd;
    float integral;
    float last_error;
    int16_t pwm_per_pulse;
    int16_t output_limit;
} SpeedPid;

void speed_pid_init(SpeedPid *pid, float kp, float ki, float kd,
                    int16_t pwm_per_pulse, int16_t limit);
void speed_pid_reset(SpeedPid *pid);
int16_t speed_pid_update(SpeedPid *pid, int16_t target, int16_t current);

#endif
