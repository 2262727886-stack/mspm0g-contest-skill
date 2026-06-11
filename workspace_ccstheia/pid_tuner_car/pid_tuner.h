#ifndef PID_TUNER_H
#define PID_TUNER_H

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    volatile float kp;
    volatile float ki;
    volatile float kd;
    volatile int16_t target_left;
    volatile int16_t target_right;
    volatile bool reset_request;
} PidTunerState;

extern PidTunerState g_pid_tuner;

void pid_tuner_init(void);
void pid_tuner_poll(void);
void pid_tuner_send_csv(uint32_t timestamp_ms,
                        int16_t speed_left, int16_t speed_right,
                        int16_t pwm_left, int16_t pwm_right);

#endif
