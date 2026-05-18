/**
 * 25E 拓展板主程序 — MSPM0G3507
 * SysConfig 外设: LED(PB22) + UART0(PA10/PA11) + I2C0(PA28/PA31) + TIMA0(PB8/PB9)
 */
#include "ti_msp_dl_config.h"
#include "oled.h"

int main(void) {
    SYSCFG_DL_init();
    OLED_Init();
    OLED_Clear();

    OLED_ShowStr(0, 0,  "MSPM0G3507", 1);
    OLED_ShowStr(0, 10, "OLED SSD1306", 1);
    OLED_ShowStr(0, 20, "I2C0 PA28/31", 1);
    OLED_ShowStr(0, 30, "25E Contest", 1);
    OLED_ShowStr(0, 45, "UART PA10/11", 1);
    OLED_ShowStr(0, 55, "Hello World!", 1);
    OLED_Refresh();

    while (1);
}
