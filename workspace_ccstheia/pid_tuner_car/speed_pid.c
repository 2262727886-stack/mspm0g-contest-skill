/**
 * speed_pid.c — 速度 PID 控制器实现
 *
 * 位置式 PID + 前馈:
 *   output = target * pwm_per_pulse + Kp*e + Ki*Σe + Kd*Δe
 *
 * 前馈项的作用:
 *   不加前馈时, PID 需要从 PWM=0 开始爬升, 响应慢。
 *   加前馈后, 基础 PWM 直接等于 target * pwm_per_pulse,
 *   PID 只需要修正前馈不准的部分 (误差通常 <10 脉冲)。
 */
#include "speed_pid.h"

/**
 * 初始化 PID 控制器
 */
void speed_pid_init(SpeedPid *pid, float kp, float ki, float kd,
                    int16_t pwm_per_pulse, int16_t limit)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->integral = 0.0f;
    pid->last_error = 0.0f;
    pid->pwm_per_pulse = pwm_per_pulse;
    pid->output_limit = limit;
}

/**
 * 重置 PID 状态 (积分 + 微分清零)
 *
 * 必须在以下场景调用:
 *   - 启动/停止切换
 *   - 目标速度大幅变化
 *   - PC 下发 RESET 命令
 */
void speed_pid_reset(SpeedPid *pid)
{
    pid->integral = 0.0f;
    pid->last_error = 0.0f;
}

/**
 * PID 计算
 *
 * @param target   目标速度 (脉冲/20ms, 典型 40~80)
 * @param current  当前速度 (编码器读数)
 * @return         PWM 输出 (0~output_limit)
 *
 * 计算步骤:
 *   1. error = target - current
 *   2. integral += error (限幅 ±300)
 *   3. derivative = error - last_error
 *   4. output = target*pwm_per_pulse + Kp*error + Ki*integral + Kd*derivative
 *   5. output 限幅 0~limit
 */
int16_t speed_pid_update(SpeedPid *pid, int16_t target, int16_t current)
{
    float error = (float)(target - current);
    float derivative = error - pid->last_error;
    float output;

    /* 目标为 0 时直接停车, 清空 PID 状态 */
    if (target <= 0) {
        speed_pid_reset(pid);
        return 0;
    }

    /* 积分累加 (限幅 ±300, 防止饱和) */
    pid->integral += error;
    if (pid->integral > 300.0f) pid->integral = 300.0f;
    if (pid->integral < -300.0f) pid->integral = -300.0f;

    /* 前馈 + 位置式 PID */
    output = (float)(target * pid->pwm_per_pulse)   /* 前馈: 基础 PWM */
           + pid->kp * error                        /* 比例: 快速响应 */
           + pid->ki * pid->integral                /* 积分: 消除稳态误差 */
           + pid->kd * derivative;                  /* 微分: 抑制超调 */
    pid->last_error = error;

    /* 输出限幅 */
    if (output > (float)pid->output_limit) output = (float)pid->output_limit;
    if (output < 0.0f) output = 0.0f;

    return (int16_t)output;
}
