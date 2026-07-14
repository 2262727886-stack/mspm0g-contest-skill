/**
 * @file oled.h
 * @brief SSD1306 128x64 I2C OLED driver, address 0x3C.
 */
#ifndef OLED_H
#define OLED_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

int OLED_Init(void);
void OLED_Clear(void);
void OLED_ClearPage(uint8_t page);
void OLED_Puts(uint8_t page, uint8_t col, const char *s);

#endif
