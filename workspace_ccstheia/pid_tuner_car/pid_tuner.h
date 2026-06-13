/**
 * pid_tuner.h — PID 调试助手串口通信模块
 *
 * 功能:
 *   - 接收 PC 下发的 PID 参数 (SET P:xx I:xx D:xx)
 *   - 接收目标速度 (TARGET L:xx R:xx)
 *   - 发送 CSV 格式的速度/PWM/PID 数据给 PC
 *
 * 协议:
 *   PC→MCU: "SET P:2.5 I:1.0 D:0.0\n"  设置 PID 参数
 *   PC→MCU: "TARGET L:60 R:60\n"         设置目标速度
 *   PC→MCU: "STATUS\n"                    查询当前参数
 *   PC→MCU: "RESET\n"                     重置 PID
 *   PC→MCU: "STOP\n"                      停车
 *   MCU→PC: "ts,spdL,spdR,tgtL,tgtR,pwmL,pwmR,Kp,Ki\n"  CSV 数据
 *
 * 宏开关:
 *   PID_TUNER_ENABLE = 1  → 启用串口调试 (连接 PC PID 调参助手)
 *   PID_TUNER_ENABLE = 0  → 关闭串口调试 (比赛/运行时, 避免 UART 输出影响 MCU)
 */
#ifndef PID_TUNER_H
#define PID_TUNER_H

#include <stdbool.h>
#include <stdint.h>

/* ═══════════════════════════════════════════════════════════════
 * PID 调试助手开关
 *   1 = 启用 UART 通信 + CSV 输出 (调试用)
 *   0 = 关闭 UART 通信 (比赛时设为 0, 避免高频输出影响 MCU)
 * ═══════════════════════════════════════════════════════════════ */
#define PID_TUNER_ENABLE   0

/**
 * PID 调试助手全局状态
 *
 * 主循环每 20ms 读取 kp/ki/kd 和 target, 应用到速度 PID。
 * PC 通过串口命令实时修改这些值。
 */
typedef struct {
    volatile float kp;              /* 比例系数 (PC 可实时修改) */
    volatile float ki;              /* 积分系数 */
    volatile float kd;              /* 微分系数 */
    volatile int16_t target_left;   /* 左轮目标速度 (脉冲/20ms) */
    volatile int16_t target_right;  /* 右轮目标速度 (脉冲/20ms) */
    volatile bool reset_request;    /* PC 下发 RESET 命令时置 true */
} PidTunerState;

/* 全局 PID 状态 (main.c 和 pid_tuner.c 共用) */
extern PidTunerState g_pid_tuner;

/* 初始化 UART 和命令缓冲区 */
void pid_tuner_init(void);

/* 主循环调用: 轮询 UART 接收并解析命令 */
void pid_tuner_poll(void);

/* 发送 CSV 数据给 PC (每 CSV_PERIOD_MS 调用一次) */
void pid_tuner_send_csv(uint32_t timestamp_ms,
                        int16_t speed_left, int16_t speed_right,
                        int16_t pwm_left, int16_t pwm_right);

#endif /* PID_TUNER_H */
