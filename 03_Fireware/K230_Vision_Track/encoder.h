/**
 * @file encoder.h
 * @brief Polling quadrature encoder reader for motor channels.
 */
#ifndef ENCODER_H
#define ENCODER_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

void Encoder_Init(void);
void Encoder_Tick(void);
void Encoder_Update(void);
uint8_t Encoder_HasA(void);
int16_t Encoder_GetSpeedCountA(void);    /* 每周期增量(速度), int16_t */
int16_t Encoder_GetSpeedCountB(void);
int16_t Encoder_GetSpeedCount(void);
int32_t Encoder_GetPositionA(void);      /* 累积总脉冲(位置), int32_t */
int32_t Encoder_GetPositionB(void);
void Encoder_ResetPosition(void);        /* 位置清零 */

#endif
