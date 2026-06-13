/**
 * encoder.h — 霍尔编码器模块
 *
 * 硬件:
 *   右轮 A 相: PA15 (双边沿中断, GPIOA GROUP1)
 *   左轮 A 相: PA17 (双边沿中断, GPIOA GROUP1)
 *
 * 采样方式:
 *   主循环每 20ms 调用 encoder_sample_and_clear() 读取并清零。
 *   单位: 脉冲数/20ms (典型值 40~80)
 *
 * 分辨率:
 *   MG310 编码器 ~240 脉冲/转, 减速比 ~30:1
 *   实际 ~7200 脉冲/转输出轴
 */
#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

/**
 * 初始化编码器 GPIO + 中断
 * PA15/PA17 设为双边沿中断, 启用 GPIOA GROUP1 中断
 */
void encoder_init(void);

/**
 * 读取编码器计数并清零 (原子操作)
 *
 * @param left_speed   输出: 左轮脉冲数 (20ms 内)
 * @param right_speed  输出: 右轮脉冲数 (20ms 内)
 *
 * 注意: 调用时会短暂关中断, 避免读写冲突
 */
void encoder_sample_and_clear(int16_t *left_speed, int16_t *right_speed);

#endif /* ENCODER_H */
