/**
 * @file empty.c
 * @brief MSPM0G3507 contest-board smoke test.
 *
 * SysConfig peripherals:
 * - LED: PB22
 * - UART0: PA10 TX, PA11 RX, 115200 baud
 * - OLED: SSD1306 on I2C0, PA28 SDA, PA31 SCL, address 0x3C
 * - Servo PWM reserve: TIMA0 on PB8/PB9
 */
#include "ti_msp_dl_config.h"
#include "oled.h"

int main(void)
{
    SYSCFG_DL_init();

    /*
     * Initialize the display after SysConfig has enabled I2C0. The driver
     * clears both framebuffer and panel so the following text is deterministic.
     */
    OLED_Init();
    OLED_Clear();

    OLED_ShowStr(0, 0,  "MSPM0G3507", 1);
    OLED_ShowStr(0, 8,  "OLED SSD1306", 1);
    OLED_ShowStr(0, 16, "I2C0 PA28/PA31", 1);
    OLED_ShowStr(0, 24, "ADDR 0x3C", 1);
    OLED_ShowStr(0, 40, "UART0 PA10/PA11", 1);
    OLED_ShowStr(0, 56, "Contest Ready", 1);
    OLED_Refresh();

    while (1) {
        /*
         * Keep the main loop intentionally light. Future motor, sensor, or
         * control modules can be called here without blocking OLED recovery.
         */
        __WFI();
    }
}
