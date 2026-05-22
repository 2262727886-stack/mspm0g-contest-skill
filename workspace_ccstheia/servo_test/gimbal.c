#include "ti_msp_dl_config.h"
#include "gimbal.h"

#define PWM_PERIOD_TICKS 9999U
#define PWM_TICK_MIN     250U
#define PWM_TICK_MAX     1250U
#define PWM_TICK_RANGE   1000U
#define PWM_INST         SERVO_PWM_INST

static uint32_t angle_to_tick(uint16_t angle_deg, uint16_t range)
{
    uint32_t a = angle_deg;
    if (a > range) {
        a = range;
    }
    return PWM_TICK_MIN + (a * PWM_TICK_RANGE / range);
}

static uint32_t pulse_tick_to_compare(uint32_t pulse_ticks)
{
    if (pulse_ticks < PWM_TICK_MIN) {
        pulse_ticks = PWM_TICK_MIN;
    }
    if (pulse_ticks > PWM_TICK_MAX) {
        pulse_ticks = PWM_TICK_MAX;
    }
    return PWM_PERIOD_TICKS - pulse_ticks;
}

static uint32_t angle_to_tick_clamped(uint16_t angle_deg, uint16_t range,
                                      uint16_t limit_min, uint16_t limit_max)
{
    uint16_t a = angle_deg;
    if (limit_max > 0U && a > limit_max) {
        a = limit_max;
    }
    if (limit_min > 0U && a < limit_min) {
        a = limit_min;
    }
    return angle_to_tick(a, range);
}

uint16_t Gimbal_AngleToPwm(uint16_t angle_deg, uint16_t range)
{
    uint32_t a = angle_deg;
    if (a > range) {
        a = range;
    }
    return (uint16_t)(GIMBAL_PWM_MIN_US + (a * GIMBAL_PWM_RANGE_US / range));
}

void Gimbal_Init(void)
{
    DL_TimerA_startCounter(PWM_INST);
    Gimbal_Center();
}

void Gimbal_Center(void)
{
    DL_TimerA_setCaptureCompareValue(PWM_INST,
        pulse_tick_to_compare(angle_to_tick(135U, GIMBAL_PAN_RANGE)), GIMBAL_CH_PAN);
    DL_TimerA_setCaptureCompareValue(PWM_INST,
        pulse_tick_to_compare(angle_to_tick(90U, GIMBAL_TILT_RANGE)), GIMBAL_CH_TILT);
}

void Gimbal_SetPan(uint16_t angle_deg)
{
    uint32_t tick = angle_to_tick_clamped(angle_deg, GIMBAL_PAN_RANGE,
        GIMBAL_PAN_MIN_DEG, GIMBAL_PAN_MAX_DEG);
    DL_TimerA_setCaptureCompareValue(PWM_INST, pulse_tick_to_compare(tick), GIMBAL_CH_PAN);
}

void Gimbal_SetTilt(uint16_t angle_deg)
{
    uint32_t tick = angle_to_tick_clamped(angle_deg, GIMBAL_TILT_RANGE,
        GIMBAL_TILT_MIN_DEG, GIMBAL_TILT_MAX_DEG);
    DL_TimerA_setCaptureCompareValue(PWM_INST, pulse_tick_to_compare(tick), GIMBAL_CH_TILT);
}

void Gimbal_SetPanUs(uint16_t pulse_us)
{
    uint32_t us = pulse_us;
    if (us < GIMBAL_PWM_MIN_US) {
        us = GIMBAL_PWM_MIN_US;
    }
    if (us > GIMBAL_PWM_MAX_US) {
        us = GIMBAL_PWM_MAX_US;
    }
    DL_TimerA_setCaptureCompareValue(PWM_INST,
        pulse_tick_to_compare(PWM_TICK_MIN + (us - GIMBAL_PWM_MIN_US) / 2U), GIMBAL_CH_PAN);
}

void Gimbal_SetTiltUs(uint16_t pulse_us)
{
    uint32_t us = pulse_us;
    if (us < GIMBAL_PWM_MIN_US) {
        us = GIMBAL_PWM_MIN_US;
    }
    if (us > GIMBAL_PWM_MAX_US) {
        us = GIMBAL_PWM_MAX_US;
    }
    DL_TimerA_setCaptureCompareValue(PWM_INST,
        pulse_tick_to_compare(PWM_TICK_MIN + (us - GIMBAL_PWM_MIN_US) / 2U), GIMBAL_CH_TILT);
}
