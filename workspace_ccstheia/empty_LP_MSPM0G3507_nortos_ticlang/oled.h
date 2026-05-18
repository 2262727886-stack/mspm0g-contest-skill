/**
 * @file oled.h
 * @brief SSD1306 0.96 inch 128x64 I2C OLED driver for MSPM0G3507.
 *
 * Hardware contract from SysConfig:
 * - MCU: MSPM0G3507
 * - OLED: SSD1306, 7-bit I2C address 0x3C
 * - Bus: I2C0, PA28 = SDA, PA31 = SCL
 *
 * Keep pin assignment in SysConfig. This module only uses the generated
 * I2C_OLED_* symbols so the driver does not duplicate pinmux decisions.
 */
#ifndef __OLED_H
#define __OLED_H

#include "ti_msp_dl_config.h"
#include <stdbool.h>
#include <stdint.h>

#define OLED_CMD  0
#define OLED_DATA 1

bool OLED_WR_Byte(uint8_t dat, uint8_t mode);
void OLED_Init(void);
void OLED_Clear(void);
void OLED_DrawPoint(uint8_t x, uint8_t y, uint8_t t);
void OLED_Refresh(void);
void OLED_ShowChar(uint8_t x, uint8_t y, char chr, uint8_t mode);
void OLED_ShowStr(uint8_t x, uint8_t y, const char *s, uint8_t mode);

#endif
