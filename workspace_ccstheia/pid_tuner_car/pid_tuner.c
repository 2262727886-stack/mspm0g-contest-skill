#include "pid_tuner.h"
#include "ti_msp_dl_config.h"
#include <stdio.h>
#include <string.h>

#define CMD_BUF_SIZE  64

PidTunerState g_pid_tuner = {
    3.0f,
    1.0f,
    0.0f,
    60,
    60,
    false
};

static char g_cmd_buf[CMD_BUF_SIZE];
static uint8_t g_cmd_idx;

static void uart_send_text(const char *text)
{
    while (*text != '\0') {
        while (DL_UART_Main_isTXFIFOFull(DEBUG_UART_INST)) {
        }
        DL_UART_Main_transmitData(DEBUG_UART_INST, (uint8_t)*text);
        text++;
    }
}

static float clamp_float(float value, float min_value, float max_value)
{
    if (value < min_value) return min_value;
    if (value > max_value) return max_value;
    return value;
}

static int16_t clamp_target(int value)
{
    if (value > 200) return 200;
    if (value < 0) return 0;
    return (int16_t)value;
}

static void parse_tuner_cmd(const char *cmd)
{
    float p, i, d;
    int left, right;
    char resp[96];

    if (sscanf(cmd, "SET P:%f I:%f D:%f", &p, &i, &d) == 3) {
        g_pid_tuner.kp = clamp_float(p, 0.1f, 50.0f);
        g_pid_tuner.ki = clamp_float(i, 0.0f, 20.0f);
        g_pid_tuner.kd = clamp_float(d, 0.0f, 5.0f);
        snprintf(resp, sizeof(resp), "OK P=%.3f I=%.3f D=%.3f\r\n",
            (double)g_pid_tuner.kp, (double)g_pid_tuner.ki,
            (double)g_pid_tuner.kd);
        uart_send_text(resp);
    } else if (sscanf(cmd, "SET P:%f I:%f", &p, &i) == 2) {
        g_pid_tuner.kp = clamp_float(p, 0.1f, 50.0f);
        g_pid_tuner.ki = clamp_float(i, 0.0f, 20.0f);
        snprintf(resp, sizeof(resp), "OK P=%.3f I=%.3f D=%.3f\r\n",
            (double)g_pid_tuner.kp, (double)g_pid_tuner.ki,
            (double)g_pid_tuner.kd);
        uart_send_text(resp);
    } else if (sscanf(cmd, "TARGET L:%d R:%d", &left, &right) == 2) {
        g_pid_tuner.target_left = clamp_target(left);
        g_pid_tuner.target_right = clamp_target(right);
        snprintf(resp, sizeof(resp), "OK TARGET L=%d R=%d\r\n",
            (int)g_pid_tuner.target_left, (int)g_pid_tuner.target_right);
        uart_send_text(resp);
    } else if (strncmp(cmd, "STATUS", 6) == 0) {
        snprintf(resp, sizeof(resp), "P=%.3f I=%.3f D=%.3f TL=%d TR=%d\r\n",
            (double)g_pid_tuner.kp, (double)g_pid_tuner.ki,
            (double)g_pid_tuner.kd, (int)g_pid_tuner.target_left,
            (int)g_pid_tuner.target_right);
        uart_send_text(resp);
    } else if (strncmp(cmd, "RESET", 5) == 0) {
        g_pid_tuner.kp = 3.0f;
        g_pid_tuner.ki = 1.0f;
        g_pid_tuner.kd = 0.0f;
        g_pid_tuner.target_left = 60;
        g_pid_tuner.target_right = 60;
        g_pid_tuner.reset_request = true;
        uart_send_text("OK RESET\r\n");
    } else if (strncmp(cmd, "STOP", 4) == 0) {
        g_pid_tuner.target_left = 0;
        g_pid_tuner.target_right = 0;
        g_pid_tuner.reset_request = true;
        uart_send_text("OK STOP\r\n");
    } else {
        uart_send_text("ERR CMD\r\n");
    }
}

void pid_tuner_poll(void)
{
    while (!DL_UART_Main_isRXFIFOEmpty(DEBUG_UART_INST)) {
        uint8_t ch = DL_UART_Main_receiveData(DEBUG_UART_INST);
        if (ch == '\r' || ch == '\n') {
            if (g_cmd_idx > 0U) {
                g_cmd_buf[g_cmd_idx] = '\0';
                parse_tuner_cmd(g_cmd_buf);
                g_cmd_idx = 0U;
            }
        } else if (g_cmd_idx < (CMD_BUF_SIZE - 1U)) {
            g_cmd_buf[g_cmd_idx++] = (char)ch;
        } else {
            g_cmd_idx = 0U;
        }
    }
}

void pid_tuner_init(void)
{
    g_cmd_idx = 0U;
    uart_send_text("MSPM0G PID Tuner Car Ready\r\n");
}

void pid_tuner_send_csv(uint32_t timestamp_ms,
                        int16_t speed_left, int16_t speed_right,
                        int16_t pwm_left, int16_t pwm_right)
{
    char line[128];

    snprintf(line, sizeof(line), "%lu,%d,%d,%d,%d,%d,%d,%.3f,%.3f\r\n",
        (unsigned long)timestamp_ms,
        (int)speed_left, (int)speed_right,
        (int)g_pid_tuner.target_left, (int)g_pid_tuner.target_right,
        (int)pwm_left, (int)pwm_right,
        (double)g_pid_tuner.kp, (double)g_pid_tuner.ki);

    uart_send_text(line);
}
