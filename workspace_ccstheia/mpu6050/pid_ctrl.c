/**
 * pid_ctrl.c — 增量式 PI 速度控制器 + PD 航向控制器 实现
 *
 * 迁移自 ZLC_MSPM0_Peripheral_Library (ZLC_PID.c)
 * 原实现: Zhijian Li, Shandong University, 2024-07-30
 */

#include "pid_ctrl.h"

/* ================================================================
 * 速度 PI 控制器 — 增量式
 * ================================================================ */

/* 可调参数 (运行时可通过 OLED/串口在线修改) */
float g_speed_kp     = 2.5f;    /* 比例系数: 越大响应越快, 过大振荡 */
float g_speed_ki     = 1.0f;    /* 积分系数: 消除稳态误差, 过大超调 */
int16_t g_speed_limit = 1200;   /* 输出限幅: 防止 PWM 占空比超限 */

/**
 * 速度环内部状态
 *
 * 用 static 而非全局变量, 避免被外部误修改.
 * 增量式 PI 的核心: ControlVelocity 在函数调用间保持, 自然平滑.
 */
static int16_t  s_last_bias_l;       /* 左轮上次偏差 */
static int16_t  s_last_bias_r;       /* 右轮上次偏差 */
static int16_t  s_control_l;         /* 左轮控制量累加器 */
static int16_t  s_control_r;         /* 右轮控制量累加器 */

/* 重置所有内部状态 — 任务切换或停止时调用 */
void PID_Speed_Reset(void)
{
    s_last_bias_l = 0;
    s_last_bias_r = 0;
    s_control_l   = 0;
    s_control_r   = 0;
}

/**
 * 左轮增量式 PI
 *
 * @param target   目标速度 (编码器脉冲/20ms)
 * @param current  当前速度 (编码器脉冲/20ms)
 * @return         PWM 占空比值 (正=前进, 负=后退)
 *
 * 增量式公式 (与 ZLC 一致):
 *   Δu = Kp * (e(k) - e(k-1)) + Ki * e(k)
 *   u(k) = u(k-1) + Δu
 *
 * 为什么用增量式而不是位置式?
 *   - 输出自然平滑, 不会因 Ki*∑e 积分饱和突变
 *   - 切换目标速度时无需重置积分
 *   - Cortex-M0+ 计算量更小
 */
int16_t PID_Speed_L(int16_t target, int16_t current)
{
    int16_t bias = target - current;             /* 本次偏差 */

    /* 增量式 PI 核心 */
    s_control_l += (int16_t)(g_speed_kp * (float)(bias - s_last_bias_l)
                           + g_speed_ki * (float)bias);

    s_last_bias_l = bias;

    /* 输出限幅: 防止 PWM 溢出, 同时起到抗积分饱和作用 */
    if (s_control_l > g_speed_limit) {
        s_control_l = g_speed_limit;
    } else if (s_control_l < -g_speed_limit) {
        s_control_l = -g_speed_limit;
    }

    return s_control_l;
}

/* 右轮增量式 PI — 逻辑同左轮, 独立状态 */
int16_t PID_Speed_R(int16_t target, int16_t current)
{
    int16_t bias = target - current;

    s_control_r += (int16_t)(g_speed_kp * (float)(bias - s_last_bias_r)
                           + g_speed_ki * (float)bias);

    s_last_bias_r = bias;

    if (s_control_r > g_speed_limit) {
        s_control_r = g_speed_limit;
    } else if (s_control_r < -g_speed_limit) {
        s_control_r = -g_speed_limit;
    }

    return s_control_r;
}


/* ================================================================
 * 航向 PD 控制器
 * ================================================================ */

float g_dir_kp = 1.5f;    /* P: 偏差1°的差速修正量, 太大对yaw漂移过敏 */
float g_dir_kd = 0.8f;    /* D: 抑制突变, 对慢漂移无效 */
float g_dir_deadband = 3.0f; /* 死区: |偏差|<3°时不修正, 过滤yaw漂移 */

static float s_last_error;  /* 上次航向偏差 */

void PID_Dir_Reset(void)
{
    s_last_error = 0.0f;
}

/**
 * 航向 PD 控制 (带死区)
 *
 *   死区逻辑: yaw 漂移速度慢 (通常<1°/s), 产生的偏差在几度内。
 *   死区过滤掉这些慢漂移, 只有真正的转弯 (>3°偏差) 才触发修正。
 */
float PID_Dir_Calc(float error)
{
    /* 死区: 小偏差不修正 (过滤 yaw 慢漂移) */
    if (error < g_dir_deadband && error > -g_dir_deadband) {
        s_last_error = 0.0f;
        return 0.0f;
    }
    float result = g_dir_kp * error + g_dir_kd * (error - s_last_error);
    s_last_error = error;
    return result;
}


/* ================================================================
 * 目标速度 (全局, 由状态机/任务设定)
 * ================================================================ */
int16_t g_object_speed = 0;
