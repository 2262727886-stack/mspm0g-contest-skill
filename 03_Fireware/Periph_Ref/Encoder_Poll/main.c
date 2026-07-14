/**
 * 编码器B — 高速轮询 + 电机 + SysTick 定时打印
 */
#include "ti_msp_dl_config.h"
#include "motor.h"
#include "encoder.h"

volatile uint32_t g_ms = 0;
void SysTick_Handler(void) { g_ms++; }

void uart_num(int32_t n) {
    if (n < 0) { DL_UART_Main_transmitDataBlocking(UART_0_INST, '-'); n = -n; }
    if (n == 0) { DL_UART_Main_transmitDataBlocking(UART_0_INST, '0'); return; }
    char buf[12]; int i = 0;
    while (n) { buf[i++] = '0' + (n % 10); n /= 10; }
    while (i) DL_UART_Main_transmitDataBlocking(UART_0_INST, buf[--i]);
}

int main(void) {
    SYSCFG_DL_init();
    SysTick_Config(CPUCLK_FREQ / 1000);
    __enable_irq();
    Motor_Init();
    Encoder_Init();
    DL_TimerG_startCounter(PWM_TB6612_INST);

    DL_UART_Main_transmitDataBlocking(UART_0_INST, 'S');
    Motor_B(400);

    uint32_t last_print = 0;
    while (1) {
        Encoder_Tick();                    // 高速轮询编码器
        if (g_ms - last_print > 200) {     // 每200ms打印
            last_print = g_ms;
            uart_num(Encoder_Read());
            DL_UART_Main_transmitDataBlocking(UART_0_INST, '\n');
            DL_GPIO_togglePins(GPIO_PORT, GPIO_LED_PIN);
        }
    }
}
