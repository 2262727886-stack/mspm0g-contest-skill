/**
 * MSPM0G3507 — 25E 接收 K230 视觉数据
 * ======================================
 * UART0 (PA0=RX, PA1=TX) 接收 K230 10字节帧
 * 使用方法: 将此文件内容合并到你的 main.c 中
 *
 * 竞赛用 K230 通信时拔掉 M0G 的 USB 线
 * 此时 PA0/PA1 直接连 K230 GPIO12/GPIO11
 */

#include "ti_msp_dl_config.h"
#include <string.h>
#include <stdio.h>

/* ---- 10字节帧协议 ---- */
#define FRAME_LEN    10
#define FRAME_HEAD1  0xA5
#define FRAME_HEAD2  0x5A

/* K230 命令码 */
#define CMD_BLOB_POS   0x01   // 靶心坐标, X/Y 有效
#define CMD_LASER_POS  0x02   // 激光光斑坐标
#define CMD_LASER_DEV  0x03   // 激光→靶心偏差
#define CMD_LOST       0x04   // 目标丢失

/* 接收状态机 */
static uint8_t  rx_buf[FRAME_LEN];
static uint8_t  rx_idx = 0;
static uint8_t  rx_state = 0;  // 0=等HEAD1, 1=收数据
static bool     rx_done = false;

/* 解析后的数据 */
typedef struct {
    uint8_t cmd;
    int16_t x_raw;      // 单位: 0.1mm
    int16_t y_raw;
    uint16_t extra;
    bool    valid;
} K230_Frame;

static K230_Frame vision_frame = {0};

/* ---- UART 中断接收 (SysConfig 启用 UART0 RX Interrupt) ---- */
void UART0_INST_IRQHandler(void) {
    uint8_t byte = DL_UART_receiveData(UART0);

    switch (rx_state) {
    case 0:
        /* 等待帧头 0xA5 */
        if (byte == FRAME_HEAD1) {
            rx_buf[0] = byte;
            rx_state = 1;
            rx_idx = 1;
        }
        break;
    case 1:
        /* 等 0x5A */
        if (byte == FRAME_HEAD2) {
            rx_buf[1] = byte;
            rx_state = 2;
            rx_idx = 2;
        } else {
            rx_state = 0;  // 不是0x5A, 重新等
        }
        break;
    case 2:
        /* 收剩余 8 字节 */
        rx_buf[rx_idx++] = byte;
        if (rx_idx >= FRAME_LEN) {
            /* 校验 XOR (前9字节 XOR == 第10字节) */
            uint8_t checksum = 0;
            for (int i = 0; i < 9; i++) {
                checksum ^= rx_buf[i];
            }
            if (checksum == rx_buf[9]) {
                vision_frame.cmd   = rx_buf[2];
                vision_frame.x_raw = (int16_t)(rx_buf[3] | (rx_buf[4] << 8));
                vision_frame.y_raw = (int16_t)(rx_buf[5] | (rx_buf[6] << 8));
                vision_frame.extra = (uint16_t)(rx_buf[7] | (rx_buf[8] << 8));
                vision_frame.valid = true;
            }
            rx_state = 0;  /* 准备收下一帧 */
        }
        break;
    }
}

/* ---- 主循环中调用: 解析视觉数据 → 执行控制 ---- */
void handle_vision_data(void) {
    if (!vision_frame.valid) return;
    vision_frame.valid = false;

    float x_cm = vision_frame.x_raw / 100.0f;  /* 0.1mm → cm */
    float y_cm = vision_frame.y_raw / 100.0f;

    switch (vision_frame.cmd) {

    case CMD_BLOB_POS:
        /* 接收到靶心坐标 */
        printf("靶心: (%.1f, %.1f) r=%d\r\n", x_cm, y_cm, vision_frame.extra);
        /* 在这里更新靶心目标位置变量 */
        // target_x_cm = x_cm;
        // target_y_cm = y_cm;
        break;

    case CMD_LASER_POS:
        /* 接收到激光光斑坐标 */
        printf("光斑: (%.1f, %.1f) 偏差=%.1fcm\r\n",
               x_cm, y_cm, vision_frame.extra / 10.0f);
        /* 在这里做闭环微调云台 */
        break;

    case CMD_LASER_DEV:
        /* 接收到激光→靶心偏差 */
        printf("偏差: X=%.1f Y=%.1f 靶r=%d\r\n",
               x_cm, y_cm, vision_frame.extra);
        /* 用偏差做 PID 修正舵机角度 */
        break;

    case CMD_LOST:
        /* 目标丢失 */
        printf("视觉: 目标丢失!\r\n");
        /* 启动扫描搜索或保持最后位置 */
        break;

    default:
        break;
    }
}

/* ---- 主函数框架 ---- */
/*
int main(void) {
    SYSCFG_DL_init();
    NVIC_EnableIRQ(UART0_INST_INT_IRQN);
    __enable_irq();

    printf("M0G 25E 启动, 等待 K230 数据...\r\n");

    while (1) {
        handle_vision_data();

        // === 你的巡线+瞄准控制代码 ===
        // tcrt巡线 → PID转向
        // 接收 vision_frame 坐标 → 云台瞄准
        // 编码器累计 → 圈数检测 → 画圆同步
    }
}
*/
