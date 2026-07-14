/**
 * delay.h — 毫秒延时 (供 DMP 库和用户代码共用)
 */
#ifndef DELAY_H
#define DELAY_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

void delay_ms(uint32_t ms);

#ifdef __cplusplus
}
#endif

#endif /* DELAY_H */
