/**
 * delay.h — 毫秒延时模块
 *
 * 基于 delay_cycles() 实现, 使用 CPU 时钟周期计数。
 * 阻塞式延时, 不使用定时器中断。
 */
#ifndef DELAY_H
#define DELAY_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 阻塞延时指定毫秒数
 * @param ms  延时毫秒数
 */
void delay_ms(uint32_t ms);

#ifdef __cplusplus
}
#endif

#endif /* DELAY_H */
