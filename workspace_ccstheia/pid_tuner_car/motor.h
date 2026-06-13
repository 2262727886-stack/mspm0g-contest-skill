/**
 * motor.h — TB6612FNG 电机驱动模块
 *
 * 硬件连接:
 *   左轮 = TB6612 B 通道: PWMB=PB16(TIMG8_C1), BIN1=PB0, BIN2=PB1
 *   右轮 = TB6612 A 通道: PWMA=PB15(TIMG8_C0), AIN1=PA13, AIN2=PA12
 *
 * PWM 配置:
 *   TIMG8, 20kHz, period=2133 (SysConfig 生成)
 *   比较值使用反逻辑: CC = PWM_MAX - duty (CC=0→100%, CC=2133→0%)
 *
 * 注意: 右轮方向与左轮相反 (两个电机面对面安装)
 */
#ifndef MOTOR_H
#define MOTOR_H

#include <stdbool.h>
#include <stdint.h>

/* TIMG8 周期值 (来自 SysConfig, 不要改) */
#define MOTOR_PWM_MAX   2133

/* 死区: duty 不碰周期极限, 保证 PWM 波形完整 */
#define MOTOR_PWM_DEAD  30

/* 初始化电机 GPIO 和 PWM 定时器 */
void motor_init(void);

/**
 * 设置左轮 PWM
 * @param duty  正=前进, 负=后退, 范围 ±(PWM_MAX-PWM_DEAD)
 */
void motor_left_set(int16_t duty);

/**
 * 设置右轮 PWM
 * @param duty  正=前进, 负=后退 (方向已翻转, 与左轮一致)
 */
void motor_right_set(int16_t duty);

/* 停车: 方向脚拉低, PWM 清零 */
void motor_stop(void);

#endif /* MOTOR_H */
