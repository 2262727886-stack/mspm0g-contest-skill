/*
 * Position PID controller for encoder-speed closed loop.
 */
#ifndef __PID_H
#define __PID_H

typedef struct {
    float kp;
    float ki;
    float kd;

    float target;
    float error;
    float last_error;
    float integral;

    float max_integral;
    float max_output;
    float output;
} PID;

void pid_init(PID *pid, float kp, float ki, float kd,
              float max_integral, float max_output, float target);
void pid_reset(PID *pid);
void pid_set_target(PID *pid, float target);
float pid_calc(PID *pid, float current);

#endif
