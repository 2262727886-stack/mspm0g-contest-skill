/**
 * pid_tuner.c — PID 调试助手串口通信实现
 *
 * 功能:
 *   1. 接收 PC 命令 (SET/TARGET/STATUS/RESET/STOP)
 *   2. 解析并更新全局 PID 参数
 *   3. 发送 CSV 格式数据给 PC (速度/PWM/PID)
 *
 * 串口配置: UART0, 115200 8N1, PA10=TX, PA11=RX
 */
#include "pid_tuner.h"
#include "ti_msp_dl_config.h"
#include <stdio.h>
#include <string.h>

#define CMD_BUF_SIZE  64  /* 命令缓冲区大小 */

/**
 * 全局 PID 状态 (默认值)
 *
 * ╔══════════════════════════════════════════════════════════════╗
 * ║  ★★★ 在这里填入 PID 调参助手找到的最优值 ★★★              ║
 * ║                                                              ║
 * ║  从 GUI 的「推荐 PID」或「最终验证」结果中复制:             ║
 * ║    kp = P 值                                                 ║
 * ║    ki = I 值                                                 ║
 * ║    kd = D 值 (速度环通常为 0)                               ║
 * ║    target_left/right = 目标速度 (脉冲/20ms)                 ║
 * ╚══════════════════════════════════════════════════════════════╝
 */
PidTunerState g_pid_tuner = {
    5.4f,   /* kp — 比例系数 (调参助手结果填这里) */
    1.8f,   /* ki — 积分系数 (调参助手结果填这里) */
    0.0f,   /* kd — 微分系数 (速度环通常为 0) */
    20,     /* target_left  — 左轮目标速度 (脉冲/20ms) */
    20,     /* target_right — 右轮目标速度 (脉冲/20ms) */
    false   /* reset_request — PC 下发重置时置 true */
};

/* 命令接收缓冲区 */
static char g_cmd_buf[CMD_BUF_SIZE];
static uint8_t g_cmd_idx;

/**
 * UART 发送字符串 (阻塞, 等 FIFO 有空位)
 */
static void uart_send_text(const char *text)
{
    while (*text != '\0') {
        while (DL_UART_Main_isTXFIFOFull(DEBUG_UART_INST)) {
        }
        DL_UART_Main_transmitData(DEBUG_UART_INST, (uint8_t)*text);
        text++;
    }
}

/**
 * 浮点数限幅
 */
static float clamp_float(float value, float min_value, float max_value)
{
    if (value < min_value) return min_value;
    if (value > max_value) return max_value;
    return value;
}

/**
 * 目标速度限幅 (0~200, 防止电机失控)
 */
static int16_t clamp_target(int value)
{
    if (value > 200) return 200;
    if (value < 0) return 0;
    return (int16_t)value;
}

/**
 * 解析 PC 下发的命令
 *
 * 支持的命令:
 *   "SET P:2.5 I:1.0 D:0.0"  → 设置 PID 参数
 *   "SET P:2.5 I:1.0"         → 设置 PD (D 不变)
 *   "TARGET L:60 R:60"        → 设置左右轮目标速度
 *   "STATUS"                  → 查询当前参数
 *   "RESET"                   → 重置为默认值
 *   "STOP"                    → 停车
 */
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
        g_pid_tuner.kp = 2.0f;
        g_pid_tuner.ki = 0.0f;
        g_pid_tuner.kd = 0.0f;
        g_pid_tuner.target_left = 20;
        g_pid_tuner.target_right = 20;
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

/**
 * 轮询 UART 接收缓冲区, 收到完整行后解析命令
 *
 * 在主循环中高频调用 (每轮都检查), 避免 PC 命令被 CSV 输出阻塞。
 */
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
            g_cmd_idx = 0U;  /* 缓冲区溢出, 丢弃 */
        }
    }
}

/**
 * 初始化 PID 调试助手
 */
void pid_tuner_init(void)
{
    g_cmd_idx = 0U;
    uart_send_text("MSPM0G PID Tuner Car Ready\r\n");
}

/**
 * 发送 CSV 数据给 PC
 *
 * 格式: timestamp,speed_L,speed_R,target_L,target_R,pwm_L,pwm_R,Kp,Ki
 * PC PID 调试助手解析此数据计算误差/超调等指标。
 */
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
