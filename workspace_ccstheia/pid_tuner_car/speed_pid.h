/**
 * speed_pid.h — 速度 PID 控制器 (位置式 + 前馈)
 *
 * 算法:
 *   output = target * pwm_per_pulse    (前馈: 基础 PWM)
 *          + Kp * error                (比例: 快速响应)
 *          + Ki * integral             (积分: 消除稳态误差)
 *          + Kd * derivative           (微分: 抑制超调)
 *
 * 特点:
 *   - 前馈项让 PID 只做小修正, 不需要从 0 爬升
 *   - 积分限幅 ±300, 防止积分饱和
 *   - 输出限幅 0~output_limit, 防止 PWM 越界
 */
#ifndef SPEED_PID_H
#define SPEED_PID_H

#include <stdint.h>

/**
 * PID 控制器状态
 */
typedef struct {
    float kp;               /* 比例系数 */
    float ki;               /* 积分系数 */
    float kd;               /* 微分系数 */
    float integral;         /* 积分累加器 */
    float last_error;       /* 上次误差 (用于微分计算) */
    int16_t pwm_per_pulse;  /* 前馈系数: 每个脉冲对应的 PWM */
    int16_t output_limit;   /* PWM 输出上限 */
} SpeedPid;

/**
 * 初始化 PID 控制器
 *
 * @param pid            PID 状态指针
 * @param kp/ki/kd       PID 参数
 * @param pwm_per_pulse  前馈系数 (典型 5~15)
 * @param limit          PWM 输出上限 (典型 1000~2000)
 */
void speed_pid_init(SpeedPid *pid, float kp, float ki, float kd,
                    int16_t pwm_per_pulse, int16_t limit);

/**
 * 重置 PID 状态 (积分和微分清零)
 * 切换运行/停止时必须调用, 否则旧积分会导致 PWM 突变
 */
void speed_pid_reset(SpeedPid *pid);

/**
 * PID 计算 (每 SPEED_PERIOD_MS 调用一次)
 *
 * @param pid      PID 状态指针
 * @param target   目标速度 (脉冲/20ms)
 * @param current  当前速度 (脉冲/20ms)
 * @return         PWM 输出值 (0~output_limit)
 */
int16_t speed_pid_update(SpeedPid *pid, int16_t target, int16_t current);

#endif /* SPEED_PID_H */
