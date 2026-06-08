/**
 * delay.c — 毫秒延时 (基于 delay_cycles)
 */
#include "delay.h"

void delay_ms(uint32_t ms)
{
    uint32_t cycles = (CPUCLK_FREQ / 1000U) * ms;
    delay_cycles(cycles);
}
