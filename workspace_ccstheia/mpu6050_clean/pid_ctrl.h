/**
 * pid_ctrl.h — 增量式 PI 速度控制器 + PD 航向控制器
 *
 * 迁移自 ZLC_MSPM0_Peripheral_Library (ZLC_PID.c)
 * 适配: MSPM0G3507 天猛星 + TB6612FNG + MG310 电机
 *
 * 使用前请在 SysConfig 中配置:
 *   - MOTOR_PWM: TIMG8, PB15=C0, PB16=C1 (PWM 频率 20kHz)
 *   - MOTOR_DIR: 4 个 GPIO 输出 (TB6612 AIN1/AIN2/BIN1/BIN2)
 *   - ENCODER: GPIO 双边沿中断 (PA15/PA16/PA17/PA24)
 *   - CONTROL_TIMER: 20ms 周期定时器 (用于速度环)
 */

#ifndef PID_CTRL_H
#define PID_CTRL_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ================================================================
 * 速度 PI 控制器 (增量式)
 *
 * 公式: output += Kp*(err - last_err) + Ki*err
 *
 * 特点:
 *   - 增量式, 输出平滑不突变
 *   - static 变量保存状态, 无全局污染
 *   - 自动输出限幅 (防止积分饱和)
 *
 * 调用方式: 放在 20ms 定时中断中
 *   LC_Speed = Encoder_Get_L();  // 获取当前速度(编码器脉冲数)
 *   duty_L  = PID_Speed_L(Object_Speed, LC_Speed);
 *   Motor_SetLeft(duty_L);
 * ================================================================ */

extern float g_speed_kp;       /* 速度环比例系数 (默认 2.5) */
extern float g_speed_ki;       /* 速度环积分系数 (默认 1.0) */
extern int16_t g_speed_limit;  /* 速度环输出限幅 (默认 1200, 对应 PWM 最大占空比) */

/* 初始化速度环内部状态 (切换任务时调用, 清除历史积分) */
void PID_Speed_Reset(void);

/* 左轮速度 PI, 返回 PWM 占空比值 (有符号, 正=前进, 负=后退) */
int16_t PID_Speed_L(int16_t target, int16_t current);

/* 右轮速度 PI, 返回 PWM 占空比值 (有符号, 正=前进, 负=后退) */
int16_t PID_Speed_R(int16_t target, int16_t current);


/* ================================================================
 * 航向 PD 控制器
 *
 * 公式: output = Kp*error + Kd*(error - last_error)
 *
 * 用途: 根据航向偏差计算舵机转向修正量
 *
 * 调用方式: 放在 20ms 主循环中
 *   float heading_err = get_minor_arc(object_angle, current_heading);
 *   float steer = PID_Dir_Calc(heading_err);
 *   Servo_Set(STEER_MID + (int32_t)steer);  // 叠加到舵机中位
 * ================================================================ */

extern float g_dir_kp;        /* 航向环比例系数 (默认 4.0) */
extern float g_dir_kd;        /* 航向环微分系数 (默认 1.0) */

/* 重置航向环 (切换任务时调用) */
void PID_Dir_Reset(void);

/* 航向 PD 计算, 返回舵机修正值 (叠加到 SERVO_MID) */
float PID_Dir_Calc(float error);


/* ================================================================
 * 目标速度 (由状态机/遥控设定)
 * ================================================================ */
extern int16_t g_object_speed;  /* 目标速度 (编码器脉冲/20ms) */

#ifdef __cplusplus
}
#endif

#endif /* PID_CTRL_H */
