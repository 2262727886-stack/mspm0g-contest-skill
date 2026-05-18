/*
 * Quadrature encoder polling interface.
 */
#ifndef __ENCODER_H
#define __ENCODER_H

#include "ti_msp_dl_config.h"

void Encoder_Init(void);
void Encoder_Tick(void);
void Encoder_Update(void);
int Encoder_GetCount(void);

#endif
