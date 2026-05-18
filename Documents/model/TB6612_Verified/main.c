/**
 * TB6612 电机测试
 * SysConfig: LED(PB22) + UART0(PA10/PA11) + TIMG8 PWM(PB15/PB16) + GPIO_TB6612
 */
#include "ti_msp_dl_config.h"
#include "motor.h"

int main(void) {
    SYSCFG_DL_init();
    Motor_Init();
    DL_TimerG_startCounter(PWM_TB6612_INST);

    DL_UART_Main_transmitDataBlocking(UART_0_INST, '0');

    // 电机A正转3秒
    Motor_A(500);
    DL_UART_Main_transmitDataBlocking(UART_0_INST, '1');
    for (volatile uint32_t d=0; d<8000000; d++);
    DL_UART_Main_transmitDataBlocking(UART_0_INST, 'a');

    Motor_Brake();
    DL_UART_Main_transmitDataBlocking(UART_0_INST, '2');
    for (volatile uint32_t d=0; d<4000000; d++);
    DL_UART_Main_transmitDataBlocking(UART_0_INST, 'b');

    Motor_B(-400);
    DL_UART_Main_transmitDataBlocking(UART_0_INST, '3');
    for (volatile uint32_t d=0; d<8000000; d++);
    DL_UART_Main_transmitDataBlocking(UART_0_INST, 'c');

    Motor_Brake();
    DL_UART_Main_transmitDataBlocking(UART_0_INST, '4');

    while (1) {
        DL_GPIO_togglePins(GPIO_PORT, GPIO_LED_PIN);
        delay_cycles(16000000);
    }
}
