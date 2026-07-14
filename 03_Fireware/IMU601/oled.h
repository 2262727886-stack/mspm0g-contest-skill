/**
 * @file oled.h
 * @brief SSD1306 128x64 I2C OLED driver, address 0x3C.
 */
#ifndef OLED_H
#define OLED_H

#include <stdint.h>

int OLED_Init(void);
void OLED_Clear(void);
void OLED_ClearPage(uint8_t page);
void OLED_Puts(uint8_t page, uint8_t col, const char *s);
void OLED_PutsLine(uint8_t page, const char *s);
void OLED_RequestLine(uint8_t page, const char *s);
void OLED_Service(void);

#endif
