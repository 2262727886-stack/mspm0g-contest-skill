/**
 * @file encoder.h
 * @brief 编码器测速模块
 *
 * 硬件连接：
 *   右轮编码器: A 相=PA15(PINCM37), B 相=PA16(PINCM38)
 *   左轮编码器: A 相=PA17(PINCM39), B 相=PA24(PINCM54)
 */

#ifndef ENCODER_H
#define ENCODER_H

#include <stdint.h>

void encoder_init(void);
int16_t encoder_left_get(void);
int16_t encoder_right_get(void);

#endif /* ENCODER_H */
