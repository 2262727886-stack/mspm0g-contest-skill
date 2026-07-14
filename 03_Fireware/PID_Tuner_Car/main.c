/**
 * @file main.c
 * @brief MSPM0G3507 小车 PID 调试助手主程序
 *
 * 功能：
 *   1. PA25 启动/停止按键（边沿检测）
 *   2. 编码器速度闭环 PI 控制
 *   3. UART0 串口调参协议（兼容 PID 调试助手）
 *   4. OLED 实时显示状态
 *
 * 串口协议：
 *   SET P:3.0000 I:1.0000 D:0.0000  -> 设置 PID 参数
 *   TARGET L:60 R:60                -> 设置目标速度
 *   STATUS                          -> 查询当前状态
 *   RESET                           -> 重置 PID
 *   STOP                            -> 停止电机
 *
 * CSV 输出格式：
 *   timestamp_ms,speed_L,speed_R,target_L,target_R,pwm_L,pwm_R,Kp,Ki
 */

#include "ti_msp_dl_config.h"
#include "motor.h"
#include "encoder.h"
#include "pid_ctrl.h"
#include "oled.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* 时间基准 */
volatile uint32_t sys_tick_ms = 0;

void SysTick_Handler(void)
{
    sys_tick_ms++;
}

/* 延时函数 */
static void delay_ms(uint32_t ms)
{
    uint32_t start = sys_tick_ms;
    while ((sys_tick_ms - start) < ms) {
        __NOP();
    }
}

/* PA25 按键 IOMUX */
#define START_BTN_IOMUX    IOMUX_PINCM42

/* 按键检测 */
static bool button_pressed(uint32_t port, uint32_t pin)
{
    return (DL_GPIO_readPins((GPIO_Regs *)port, pin) == 0U);
}

/* 串口命令缓冲区 */
#define CMD_BUF_SIZE    64
static char g_cmd_buf[CMD_BUF_SIZE];
static int g_cmd_idx = 0;

static void uart_rx_process(char c)
{
    if (c == '\n' || c == '\r') {
        if (g_cmd_idx > 0) {
            g_cmd_buf[g_cmd_idx] = '\0';
            pid_tuner_parse_command(g_cmd_buf);
            g_cmd_idx = 0;
        }
    } else if (g_cmd_idx < CMD_BUF_SIZE - 1) {
        g_cmd_buf[g_cmd_idx++] = c;
    }
}

/* 浮点转字符串 */
static void ftoa_1d(float val, char *out)
{
    uint8_t p = 0U;
    if (val < 0.0f) {
        out[p++] = '-';
        val = -val;
    }
    uint16_t iv = (uint16_t)val;
    if (iv >= 1000U) iv = 999U;
    if (iv >= 100U) out[p++] = (char)('0' + (iv / 100U));
    if (iv >= 10U || p > 0U) out[p++] = (char)('0' + ((iv / 10U) % 10U));
    out[p++] = (char)('0' + (iv % 10U));
    out[p++] = '.';
    out[p++] = (char)('0' + (uint8_t)((val - (float)iv) * 10.0f + 0.5f));
    out[p] = '\0';
}

/* 主程序 */
int main(void)
{
    /* 系统初始化 */
    SYSCFG_DL_init();

    /* GPIO 初始化 */
    DL_GPIO_initDigitalInputFeatures(START_BTN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);

    /* 模块初始化 */
    motor_init();
    encoder_init();
    pid_ctrl_init();

    /* OLED 初始化 */
    OLED_Init();
    OLED_Clear();
    OLED_Puts(0, 0, "PID Tuner Car");
    OLED_Puts(1, 0, "PA25: RUN/STOP");
    OLED_Puts(2, 0, "UART0: 115200");
    OLED_Puts(3, 0, "Ready...");
    delay_ms(1000);

    /* 主循环变量 */
    bool running = false;
    bool last_start = false;
    int16_t speed_l = 0, speed_r = 0;
    int16_t duty_l = 0, duty_r = 0;
    int16_t balance = 0;
    uint32_t last_ctrl_time = 0;
    uint32_t last_csv_time = 0;
    uint32_t last_oled_time = 0;
    uint8_t csv_skip = 0;
    char text[16];

    /* 主循环 */
    while (1) {
        uint32_t now = sys_tick_ms;

        /* 读取串口命令 */
        while (!DL_UART_isRXFIFOEmpty(UART_0_INST)) {
            char c = (char)DL_UART_Main_receiveData(UART_0_INST);
            uart_rx_process(c);
        }

        /* PA25 按键边沿检测 */
        bool start_now = button_pressed(GPIOA, DL_GPIO_PIN_25);
        if (!last_start && start_now) {
            running = !running;
            if (!running) {
                pid_ctrl_reset();
                duty_l = 0;
                duty_r = 0;
            }
        }
        last_start = start_now;

        /* 速度闭环控制 (每 20ms) */
        if ((now - last_ctrl_time) >= 20U) {
            last_ctrl_time = now;
            speed_l = encoder_left_get();
            speed_r = encoder_right_get();

            if (running) {
                balance = pid_speed_balance(speed_l, speed_r);
                int16_t target_l = g_target_l - balance;
                int16_t target_r = g_target_r + balance;
                duty_l = ramp_to(duty_l, target_l);
                duty_r = ramp_to(duty_r, target_r);
            } else {
                duty_l = ramp_to(duty_l, 0);
                duty_r = ramp_to(duty_r, 0);
                pid_ctrl_reset();
            }

            if (duty_l == 0 && duty_r == 0) {
                motor_stop();
            } else {
                motor_left_set(duty_l);
                motor_right_set(duty_r);
            }
        }

        /* CSV 输出 (每 20ms，跳过 4 次) */
        if ((now - last_csv_time) >= 20U) {
            last_csv_time = now;
            if (++csv_skip >= 4) {
                csv_skip = 0;
                pid_tuner_output_csv(now, speed_l, speed_r, duty_l, duty_r);
            }
        }

        /* OLED 显示 (每 100ms) */
        if ((now - last_oled_time) >= 100U) {
            last_oled_time = now;

            OLED_ClearPage(0);
            OLED_Puts(0, 0, running ? "RUN" : "STOP");

            OLED_ClearPage(1);
            sprintf(text, "TL:%d TR:%d", g_target_l, g_target_r);
            OLED_Puts(1, 0, text);

            OLED_ClearPage(2);
            sprintf(text, "SL:%d SR:%d", speed_l, speed_r);
            OLED_Puts(2, 0, text);

            OLED_ClearPage(3);
            sprintf(text, "PL:%d PR:%d", duty_l, duty_r);
            OLED_Puts(3, 0, text);

            OLED_ClearPage(4);
            sprintf(text, "P:%.1f I:%.1f", g_kp, g_ki);
            OLED_Puts(4, 0, text);

            OLED_ClearPage(5);
            sprintf(text, "BAL:%d", balance);
            OLED_Puts(5, 0, text);

            OLED_ClearPage(6);
            OLED_Puts(6, 0, "UART: 115200");

            OLED_ClearPage(7);
            sprintf(text, "T:%lu", now / 1000);
            OLED_Puts(7, 0, text);
        }

        delay_ms(1);
    }
}
