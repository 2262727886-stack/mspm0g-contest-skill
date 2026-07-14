/**
 * @file pid_ctrl.c
 * @brief PID 控制器实现
 */

#include "pid_ctrl.h"
#include "motor.h"
#include "ti_msp_dl_config.h"
#include <string.h>
#include <stdio.h>
#include <stdarg.h>

/* 默认 PID 参数 */
#define SPEED_BALANCE_KP     3.0f
#define SPEED_BALANCE_KI     1.0f
#define SPEED_BALANCE_KD     0.0f
#define INTEGRAL_MAX         1000.0f
#define OUTPUT_MAX           120.0f
#define DUTY_RAMP_STEP       5

/* 全局 PID 参数 */
float g_kp = SPEED_BALANCE_KP;
float g_ki = SPEED_BALANCE_KI;
float g_kd = SPEED_BALANCE_KD;
int16_t g_target_l = 60;
int16_t g_target_r = 60;

/* PID 控制器实例 */
static PID_Controller g_pid;

void pid_ctrl_init(void)
{
    g_pid.kp = g_kp;
    g_pid.ki = g_ki;
    g_pid.kd = g_kd;
    g_pid.integral = 0.0f;
    g_pid.integral_max = INTEGRAL_MAX;
    g_pid.output_max = OUTPUT_MAX;
}

void pid_ctrl_reset(void)
{
    g_pid.integral = 0.0f;
}

int16_t pid_speed_balance(int16_t speed_l, int16_t speed_r)
{
    float err = (float)(speed_l - speed_r);
    g_pid.integral += err;
    if (g_pid.integral > g_pid.integral_max) g_pid.integral = g_pid.integral_max;
    if (g_pid.integral < -g_pid.integral_max) g_pid.integral = -g_pid.integral_max;
    float output = g_pid.kp * err + g_pid.ki * g_pid.integral;
    if (output > g_pid.output_max) output = g_pid.output_max;
    if (output < -g_pid.output_max) output = -g_pid.output_max;
    return (int16_t)output;
}

int16_t ramp_to(int16_t current, int16_t target)
{
    if (current < target) {
        current = (int16_t)(current + DUTY_RAMP_STEP);
        if (current > target) current = target;
    } else if (current > target) {
        current = (int16_t)(current - DUTY_RAMP_STEP);
        if (current < target) current = target;
    }
    return current;
}

static void uart_send_string(const char *str)
{
    while (*str) {
        DL_UART_Main_transmitData(UART_0_INST, *str);
        str++;
        while (DL_UART_isTXFIFOFull(UART_0_INST)) {}
    }
}

static void uart_printf(const char *fmt, ...)
{
    char buf[128];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);
    uart_send_string(buf);
}

void pid_tuner_parse_command(char *cmd)
{
    if (strncmp(cmd, "SET P:", 6) == 0) {
        sscanf(cmd + 6, "%f", &g_kp);
        char *i_pos = strstr(cmd, "I:");
        if (i_pos) sscanf(i_pos + 2, "%f", &g_ki);
        char *d_pos = strstr(cmd, "D:");
        if (d_pos) sscanf(d_pos + 2, "%f", &g_kd);
        g_pid.kp = g_kp;
        g_pid.ki = g_ki;
        g_pid.kd = g_kd;
        uart_printf("OK SET P:%.4f I:%.4f D:%.4f\r\n", g_kp, g_ki, g_kd);
    }
    else if (strncmp(cmd, "TARGET L:", 9) == 0) {
        sscanf(cmd + 9, "%d", &g_target_l);
        char *r_pos = strstr(cmd, "R:");
        if (r_pos) sscanf(r_pos + 2, "%d", &g_target_r);
        uart_printf("OK TARGET L=%d R=%d\r\n", g_target_l, g_target_r);
    }
    else if (strcmp(cmd, "STATUS") == 0) {
        uart_printf("OK STATUS P:%.4f I:%.4f D:%.4f TL:%d TR:%d\r\n",
                    g_kp, g_ki, g_kd, g_target_l, g_target_r);
    }
    else if (strcmp(cmd, "RESET") == 0) {
        pid_ctrl_reset();
        uart_printf("OK RESET\r\n");
    }
    else if (strcmp(cmd, "STOP") == 0) {
        motor_stop();
        pid_ctrl_reset();
        uart_printf("OK STOP\r\n");
    }
}

void pid_tuner_output_csv(uint32_t timestamp_ms,
                           int16_t speed_l, int16_t speed_r,
                           int16_t pwm_l, int16_t pwm_r)
{
    uart_printf("%lu,%d,%d,%d,%d,%d,%d,%.1f,%.1f\r\n",
                timestamp_ms, speed_l, speed_r,
                g_target_l, g_target_r, pwm_l, pwm_r,
                g_kp, g_ki);
}
