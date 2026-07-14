/**
 * @file servo_k230.c
 * @brief K230视觉追踪→MSPM0G舵机控制 实现
 *
 * 舵机: TIMA0 50Hz PWM, PB9=CH1(Pan水平), PB8=CH0(Tilt俯仰)
 * 通信: UART3 115200, PB3=RX←K230(GPIO5排针11), PB2=TX→K230(GPIO6排针13)
 *
 * 帧协议(10字节):
 *   [0xA5][0x5A][CMD][PAN_L][PAN_H][TILT_L][TILT_H][EXTRA_L][EXTRA_H][CHK]
 *   PAN/TILT 单位 0.1°, 小端序(int16)
 *   CHK = 前9字节异或
 */
#include "ti_msp_dl_config.h"
#include "servo_k230.h"

/* ================================================================
 * 舵机 PWM 参数 (TIMA0, 50Hz)
 * 32MHz / 64(prescaler) / 50Hz = 10000 ticks → period = 9999
 * 0°=0.5ms→250,  90°=1.5ms→750,  180°=2.5ms→1250
 * TIMA0.setCaptureCompareValue 参数顺序: (inst, value, index)
 * ================================================================ */
#define SERVO_PERIOD   9999U
#define SERVO_MIN      250U
#define SERVO_MAX      1250U
#define SERVO_MID      750U
#define SERVO_CH_PAN   1U     /* PB9 = TIMA0_CH1 = Pan 水平 */
#define SERVO_CH_TILT  0U     /* PB8 = TIMA0_CH0 = Tilt 俯仰 */

/* ================================================================
 * UART3 帧协议常量
 * ================================================================ */
#define FRAME_HEAD1  0xA5U
#define FRAME_HEAD2  0x5AU
#define CMD_TARGET   0x01U   /* 目标坐标帧 */
#define CMD_LOST     0x04U   /* 目标丢失 */
#define CMD_STOP     0xFFU   /* 急停, 舵机保持当前位置 */

/* 目标丢失超时: 500ms 无新帧则标记丢失 */
#define TARGET_LOST_TIMEOUT_MS  500U

/* ================================================================
 * 模块静态变量
 * ================================================================ */

/* UART3 帧解析状态机 */
static uint8_t  g_rx_state = 0U;    /* 0=等HEAD1, 1=等HEAD2, 2=收数据 */
static uint8_t  g_rx_idx = 0U;
static uint8_t  g_rx_buf[10];

/* 目标状态 */
static uint16_t g_target_pan = 900U;    /* 默认90.0° */
static uint16_t g_target_tilt = 900U;
static uint8_t  g_target_lost = 1U;     /* 初始状态=丢失 */
static uint32_t g_last_frame_ms = 0U;

/* 帧率统计 */
static uint8_t  g_frame_count = 0U;
static uint32_t g_frame_rate_ms = 0U;
static uint8_t  g_frame_rate = 0U;

/* 系统滴答(ms) — 由调用方周期性更新 */
static volatile uint32_t g_sys_ms = 0U;

/* ================================================================
 * 初始化
 * ================================================================ */

void ServoK230_Init(void)
{
    /* TIMA0 已在 SysConfig 中完成引脚+时钟+周期配置, 这里只需启动 */
    DL_TimerA_startCounter(SERVO_PWM_INST);

    /* 舵机归中 */
    DL_TimerA_setCaptureCompareValue(SERVO_PWM_INST, SERVO_MID, SERVO_CH_PAN);
    DL_TimerA_setCaptureCompareValue(SERVO_PWM_INST, SERVO_MID, SERVO_CH_TILT);
}

/* ================================================================
 * 舵机控制
 * ================================================================ */

void Servo_SetPan(uint8_t angle_deg)
{
    uint32_t pulse;
    if (angle_deg > 180U) angle_deg = 180U;
    pulse = SERVO_MIN + (uint32_t)(SERVO_MAX - SERVO_MIN) * angle_deg / 180U;
    DL_TimerA_setCaptureCompareValue(SERVO_PWM_INST, pulse, SERVO_CH_PAN);
}

void Servo_SetTilt(uint8_t angle_deg)
{
    uint32_t pulse;
    if (angle_deg > 180U) angle_deg = 180U;
    pulse = SERVO_MIN + (uint32_t)(SERVO_MAX - SERVO_MIN) * angle_deg / 180U;
    DL_TimerA_setCaptureCompareValue(SERVO_PWM_INST, pulse, SERVO_CH_TILT);
}

void Servo_SetPanRaw(uint16_t angle_x10)
{
    uint32_t pulse;
    if (angle_x10 > 1800U) angle_x10 = 1800U;
    pulse = SERVO_MIN + (uint32_t)(SERVO_MAX - SERVO_MIN) * angle_x10 / 1800U;
    DL_TimerA_setCaptureCompareValue(SERVO_PWM_INST, pulse, SERVO_CH_PAN);
}

void Servo_SetTiltRaw(uint16_t angle_x10)
{
    uint32_t pulse;
    if (angle_x10 > 1800U) angle_x10 = 1800U;
    pulse = SERVO_MIN + (uint32_t)(SERVO_MAX - SERVO_MIN) * angle_x10 / 1800U;
    DL_TimerA_setCaptureCompareValue(SERVO_PWM_INST, pulse, SERVO_CH_TILT);
}

/* ================================================================
 * UART3 帧接收与解析
 * 在主循环中高频调用, 从 RX FIFO 逐字节读取
 * ================================================================ */

int8_t ServoK230_Poll(void)
{
    int8_t result = 0;

    while (!DL_UART_Main_isRXFIFOEmpty(UART_K230_INST)) {
        uint8_t b = DL_UART_Main_receiveData(UART_K230_INST);

        switch (g_rx_state) {
        case 0U:  /* 等待帧头1 */
            if (b == FRAME_HEAD1) {
                g_rx_buf[0] = b;
                g_rx_state = 1U;
            }
            break;

        case 1U:  /* 等待帧头2 */
            if (b == FRAME_HEAD2) {
                g_rx_buf[1] = b;
                g_rx_idx = 2U;
                g_rx_state = 2U;
            } else if (b != FRAME_HEAD1) {
                g_rx_state = 0U;  /* 不是帧头2也不是帧头1, 丢弃 */
            } else {
                /* b == 0xA5, 可能是下一帧开头, 保持 state=1 重新开始 */
                g_rx_buf[0] = b;
            }
            break;

        case 2U:  /* 收数据(body共7字节: CMD+PAN2+TILT2+EXTRA2) */
            g_rx_buf[g_rx_idx++] = b;
            if (g_rx_idx >= 10U) {
                g_rx_state = 0U;
                /* 校验: 前9字节异或应等于第10字节 */
                uint8_t chk = 0U;
                for (uint8_t i = 0U; i < 9U; i++) {
                    chk ^= g_rx_buf[i];
                }
                if (chk == g_rx_buf[9]) {
                    uint8_t cmd = g_rx_buf[2];
                    if (cmd == CMD_TARGET) {
                        /* 小端序: PAN在[3][4], TILT在[5][6] */
                        g_target_pan  = (uint16_t)g_rx_buf[3]
                                     | ((uint16_t)g_rx_buf[4] << 8);
                        g_target_tilt = (uint16_t)g_rx_buf[5]
                                     | ((uint16_t)g_rx_buf[6] << 8);
                        g_target_lost = 0U;
                        g_last_frame_ms = g_sys_ms;
                        g_frame_count++;
                        result = 1;
                    } else if (cmd == CMD_LOST) {
                        g_target_lost = 1U;
                        g_last_frame_ms = g_sys_ms;
                    } else if (cmd == CMD_STOP) {
                        g_target_lost = 1U;
                        result = -1;
                    }
                    /* 其他CMD忽略 */
                }
                /* 校验失败: 丢弃整帧, 等下一帧头 */
            }
            break;

        default:
            g_rx_state = 0U;
            break;
        }
    }

    return result;
}

/* ================================================================
 * 状态查询
 * ================================================================ */

uint16_t Servo_GetTargetPan(void)
{
    return g_target_pan;
}

uint16_t Servo_GetTargetTilt(void)
{
    return g_target_tilt;
}

uint8_t Servo_IsTargetLost(void)
{
    /* 超时检测: 超过阈值无新帧则标记丢失 */
    if ((g_sys_ms - g_last_frame_ms) > TARGET_LOST_TIMEOUT_MS) {
        g_target_lost = 1U;
    }
    return g_target_lost;
}

uint8_t Servo_GetFrameRate(void)
{
    return g_frame_rate;
}

/* ================================================================
 * 系统滴答 — 由主循环周期性(如10ms)调用, 用于超时和帧率统计
 * ================================================================ */

void ServoK230_Tick10ms(void)
{
    g_sys_ms += 10U;

    /* 每500ms更新帧率 */
    if ((g_sys_ms - g_frame_rate_ms) >= 500U) {
        g_frame_rate = g_frame_count * 2U;  /* frames/s = count * 2 */
        g_frame_count = 0U;
        g_frame_rate_ms = g_sys_ms;
    }
}
