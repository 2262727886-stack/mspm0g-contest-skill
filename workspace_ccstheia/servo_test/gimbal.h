#ifndef GIMBAL_H
#define GIMBAL_H

#include <stdint.h>

#define GIMBAL_PWM_MIN_US    500U
#define GIMBAL_PWM_MID_US    1500U
#define GIMBAL_PWM_MAX_US    2500U
#define GIMBAL_PWM_RANGE_US  2000U

#define GIMBAL_CH_TILT       0U
#define GIMBAL_CH_PAN        1U

#define GIMBAL_PAN_RANGE     270U
#define GIMBAL_TILT_RANGE    180U

#define GIMBAL_PAN_MIN_DEG   0U
#define GIMBAL_PAN_MAX_DEG   180U
#define GIMBAL_TILT_MIN_DEG  0U
#define GIMBAL_TILT_MAX_DEG  0U

void Gimbal_Init(void);
void Gimbal_Center(void);
void Gimbal_SetPan(uint16_t angle_deg);
void Gimbal_SetTilt(uint16_t angle_deg);
void Gimbal_SetPanUs(uint16_t pulse_us);
void Gimbal_SetTiltUs(uint16_t pulse_us);
uint16_t Gimbal_AngleToPwm(uint16_t angle_deg, uint16_t range);

#endif
