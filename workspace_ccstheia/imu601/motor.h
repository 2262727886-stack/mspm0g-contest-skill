/**
 * motor.h — TB6612FNG 双路直流电机驱动
 *
 * 硬件接线 (天猛星小车):
 *   A通道=右轮: PWMA=PB15/TIMG8_C0, AIN1=PA13, AIN2=PA12
 *   B通道=左轮: PWMB=PB16/TIMG8_C1, BIN1=PB0,  BIN2=PB1
 *
 * ⚠️ PWM 反逻辑: CC值 = MOTOR_PWM_MAX - duty
 *   CC=0 → 100% 占空比, CC=PERIOD → 0% 占空比
 */

#ifndef MOTOR_H
#define MOTOR_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define MOTOR_PWM_MAX   (2133U)     /* TIMG8 周期值 (SysConfig 配置) */
#define MOTOR_PWM_DEAD  (30U)       /* 死区, 避免 duty 碰到周期极限 */

/* ========================= 公开接口 ========================= */

/**
 * 电机初始化: 配置方向 GPIO + 启动 PWM 计数器
 * 必须在 SYSCFG_DL_init() 之后调用
 */
void Motor_Init(void);

/**
 * 设置左轮 duty (B通道, PWMB=PB16)
 * @param duty  正=前进, 负=后退, 0=刹车
 */
void Motor_LeftSet(int16_t duty);

/**
 * 设置右轮 duty (A通道, PWMA=PB15)
 * @param duty  正=前进, 负=后退, 0=刹车
 */
void Motor_RightSet(int16_t duty);

/**
 * 停车: 方向脚拉低 + PWM 清零
 */
void Motor_Stop(void);

#ifdef __cplusplus
}
#endif

#endif /* MOTOR_H */
