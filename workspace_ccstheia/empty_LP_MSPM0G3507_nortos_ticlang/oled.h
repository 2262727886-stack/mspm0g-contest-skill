/**
 * OLED SSD1306 128x64 I2C 驱动
 * 硬件: MSPM0G3507 + I2C0 (PA28=SDA, PA31=SCL)
 */
#ifndef __OLED_H
#define __OLED_H

#include "ti_msp_dl_config.h"

#define OLED_CMD  0
#define OLED_DATA 1

void OLED_WR_Byte(unsigned char dat, unsigned char mode);
void OLED_Init(void);
void OLED_Clear(void);
void OLED_DrawPoint(unsigned char x, unsigned char y, unsigned char t);
void OLED_Refresh(void);
void OLED_ShowChar(unsigned char x, unsigned char y, unsigned char chr, unsigned char mode);
void OLED_ShowStr(unsigned char x, unsigned char y, const char *s, unsigned char mode);

#endif
