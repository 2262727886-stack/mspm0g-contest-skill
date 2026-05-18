/**
 * PID 速度闭环 v5 — SysTick 100Hz 定时采集+PID
 */
#include "ti_msp_dl_config.h"
#include "motor.h"
#include "encoder.h"
#include "pid.h"

volatile uint32_t g_ms = 0;
volatile uint8_t  ctrl_flag = 0;

void SysTick_Handler(void) {
    g_ms++;
    if ((g_ms % 10) == 0) ctrl_flag = 1;  // 10ms 标记
}

PID_t pid;
int32_t target = 20, speed = 0, spd = 0, pwm_out = 400;

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

    PID_Init(&pid, 0.005f, 0.01f, 0.0f, -300, 300);
    pid.setpoint = (float)target;

    static int32_t last_enc = 0;
    uint32_t last_prn = 0;

    while (1) {
        Encoder_Tick();  // 高速轮询不丢脉冲

        if (ctrl_flag) {
            ctrl_flag = 0;

            int32_t cur_enc = Encoder_Read();
            speed = cur_enc - last_enc;
            last_enc = cur_enc;

            spd = speed < 0 ? -speed : speed;
            float out = PID_Update(&pid, (float)spd, 0.01f);
            pwm_out += (int32_t)out;
            if (pwm_out < 0)    pwm_out = 0;
            if (pwm_out > 1000) pwm_out = 1000;
            if (pwm_out < 80)   pwm_out = 80;

            Motor_B(pwm_out);
        }

        // 200ms UART (不干扰控制)
        if (g_ms - last_prn >= 200) {
            last_prn = g_ms;
            uart_num(spd);  DL_UART_Main_transmitDataBlocking(UART_0_INST, ',');
            uart_num(pwm_out); DL_UART_Main_transmitDataBlocking(UART_0_INST, ',');
            uart_num(target); DL_UART_Main_transmitDataBlocking(UART_0_INST, '\n');
        }
    }
}
