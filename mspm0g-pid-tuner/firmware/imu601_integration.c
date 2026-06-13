/**
 * imu601_integration.c — 插入 IMU601/empty.c 的 PID Tuner 对接代码
 *
 * 集成步骤:
 *   1. SysConfig → 添加 UART: PA10=TX, PA11=RX, 115200 8N1, 命名 UART_PID_TUNER
 *   2. empty.c 顶部 #include 区: #include <stdlib.h>
 *   3. 替换 PID 宏定义为变量 (见下方 【步骤3】)
 *   4. 插入 CSV 输出函数 (见下方 【步骤4】)
 *   5. 插入 UART 命令解析 (见下方 【步骤5】)
 *   6. while(1) 中调用 pid_tuner_poll()
 *   7. speed PI 中使用 g_tuner_Kp/g_tuner_Ki 替代 STRAIGHT_KP/STRAIGHT_KI
 *
 * 编译烧录 → PC 端 PID Tuner 顶部端口选择 XDS110 Class Application/User UART
 */

/* ======================================================================== */
/* 【步骤3】替换 empty.c 中的 PID 宏定义:
 *
 * 删除:
 *   #define STRAIGHT_KP  (3)
 *   #define STRAIGHT_KI  (1)
 *
 * 替换为:
 *   volatile float g_tuner_Kp = 3.0f;
 *   volatile float g_tuner_Ki = 1.0f;
 *
 * 然后将所有使用 STRAIGHT_KP/STRAIGHT_KI 的地方改为 g_tuner_Kp/g_tuner_Ki
 * ======================================================================== */

/* ======================================================================== */
/* 【步骤4】CSV 输出函数 — 插入到 empty.c 中
 * 在 SysTick_Handler 或 TIMG 中断中调用, 每 40ms 一次
 * ======================================================================== */

#if 0  /* 复制以下代码到 empty.c, 去掉 #if 0 */

#define TUNER_CSV_INTERVAL_MS  40    /* CSV 输出间隔 */
static uint32_t g_csv_last_ms = 0;

/** 通过 UART 发送一行 CSV 数据 (调用时机: 每 40ms) */
static void pid_tuner_csv_output(int16_t spd_l, int16_t spd_r,
                                  int16_t tgt_l, int16_t tgt_r,
                                  int16_t duty_l, int16_t duty_r)
{
    char line[128];
    uint32_t now = g_millis;

    if (now - g_csv_last_ms < TUNER_CSV_INTERVAL_MS) return;
    g_csv_last_ms = now;

    snprintf(line, sizeof(line),
             "%lu,%d,%d,%d,%d,%d,%d,%.3f,%.3f\r\n",
             (unsigned long)now,
             (int)spd_l, (int)spd_r,      /* 实际速度 */
             (int)tgt_l, (int)tgt_r,      /* 目标速度 */
             (int)duty_l, (int)duty_r,    /* PWM 占空比 */
             (double)g_tuner_Kp, (double)g_tuner_Ki);
    DL_UART_Main_transmitDataBlocking(UART_PID_TUNER_INST, (uint8_t *)line, strlen(line));
}

#endif

/* ======================================================================== */
/* 【步骤5】UART 命令解析 — 插入到 empty.c 中
 * ======================================================================== */

#if 0  /* 复制以下代码到 empty.c */

#define TUNER_CMD_BUF_SIZE  32
static char  g_tuner_cmd[TUNER_CMD_BUF_SIZE];
static uint8_t g_tuner_cmd_idx = 0;

/** UART RX 中断 — 已经在 SysConfig 配置 UART_PID_TUNER 时自动生成 ISR 框架 */
void UART_PID_TUNER_INST_IRQHandler(void)
{
    switch (DL_UART_Main_getPendingInterrupt(UART_PID_TUNER_INST)) {
    case DL_UART_MAIN_IIDX_RX: {
        uint8_t ch = DL_UART_Main_receiveData(UART_PID_TUNER_INST);
        if (ch == '\r' || ch == '\n') {
            if (g_tuner_cmd_idx > 0) {
                g_tuner_cmd[g_tuner_cmd_idx] = '\0';
                pid_tuner_parse(g_tuner_cmd);
                g_tuner_cmd_idx = 0;
            }
        } else if (g_tuner_cmd_idx < TUNER_CMD_BUF_SIZE - 1) {
            g_tuner_cmd[g_tuner_cmd_idx++] = (char)ch;
        }
        break;
    }
    default: break;
    }
}

/** 解析 PC 发来的命令 */
static void pid_tuner_parse(const char *cmd)
{
    float p, i; int16_t tl, tr; char resp[64];

    if (sscanf(cmd, "SET P:%f I:%f", &p, &i) == 2) {
        if (p > 0.1f && p <= 50.0f) g_tuner_Kp = p;
        if (i >= 0.0f && i <= 20.0f) g_tuner_Ki = i;
        snprintf(resp, sizeof(resp), "OK P=%.3f I=%.3f\r\n",
                 (double)g_tuner_Kp, (double)g_tuner_Ki);
    }
    else if (sscanf(cmd, "TARGET L:%hd R:%hd", &tl, &tr) == 2) {
        /* g_target_L = tl; g_target_R = tr; — 需要定义这两个变量 */
        snprintf(resp, sizeof(resp), "OK TARGET L=%d R=%d\r\n", (int)tl, (int)tr);
    }
    else if (strncmp(cmd, "STATUS", 6) == 0) {
        snprintf(resp, sizeof(resp), "PID P=%.3f I=%.3f\r\n",
                 (double)g_tuner_Kp, (double)g_tuner_Ki);
    }
    else if (strncmp(cmd, "RESET", 5) == 0) {
        g_tuner_Kp = 3.0f; g_tuner_Ki = 1.0f;
        snprintf(resp, sizeof(resp), "OK RESET P=3.0 I=1.0\r\n");
    }
    else { return; }  /* 未知命令, 不应答 */

    DL_UART_Main_transmitDataBlocking(UART_PID_TUNER_INST, (uint8_t *)resp, strlen(resp));
}

#endif

/* ======================================================================== */
/* 【步骤6】主循环中调用 pid_tuner_csv_output()
 *
 * 在 while(1) 主循环中某处 (或 speed PI 计算完成后) 添加:
 *
 *   pid_tuner_csv_output(speed_l, speed_r,
 *                        g_target_l, g_target_r,
 *                        duty_l, duty_r);
 *
 * 其中 speed_l/r 是当前编码器脉冲计数, duty_l/r 是当前 PWM 占空比
 * ======================================================================== */
