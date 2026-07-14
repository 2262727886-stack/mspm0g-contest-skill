/**
 * 编码器B — TIMG7 QEI 正交编码
 * 引脚: PA17(A相) PA24(B相)
 */
#ifndef __ENCODER_H
#define __ENCODER_H
#include "ti_msp_dl_config.h"

void Encoder_Init(void);
int32_t Encoder_Read(void);
void Encoder_Tick(void);   // 高速轮询, 主循环中每迭代调用

#endif
