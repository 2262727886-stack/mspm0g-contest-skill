/**
 * imu601.h — 正点原子 ATK-IMU601 6轴姿态传感器 驱动
 *
 * 通信: UART0 (PA0=TX, PA1=RX) @ 115200 8N1
 * 协议: 0x55 0x55 帧头, 姿态角帧ID=0x01, 6字节数据(小端int16 ×3)
 *
 * 注意: PA0/PA1 是开漏引脚, 无外部上拉时启用内部弱上拉(~50kΩ)
 *       稳定通信建议补焊 4.7kΩ 上拉到 3.3V
 */
#ifndef IMU601_H
#define IMU601_H

#include <stdint.h>
#include <stdbool.h>

/* ========================= 数据结构 ========================= */

/** 姿态角 (欧拉角, 单位: 度) */
typedef struct {
    float roll;   /* 横滚角 X 轴, 范围 ±180° */
    float pitch;  /* 俯仰角 Y 轴, 范围 ±90°  */
    float yaw;    /* 偏航角 Z 轴, 范围 ±180° (6轴无磁力计, 会缓慢漂移) */
} imu601_attitude_t;

/* ========================= API ========================= */

/**
 * 初始化 IMU601 通信
 * - GPIO: PA0 → UART0_TX (IOMUX_PINCM1_PF_UART0_TX)
 * - GPIO: PA1 → UART0_RX (IOMUX_PINCM2_PF_UART0_RX)
 * - 波特率: 115200, 8N1
 * - 中断: UART0 RX 中断接收
 * - 上拉: PA1 RX 启用内部弱上拉 (无外部上拉时防止浮空)
 */
void imu601_init(void);

/**
 * 获取最新姿态角 (非阻塞, 返回是否有新数据)
 * @param att 输出: Roll/Pitch/Yaw (度)
 * @return true=有新数据, false=数据未更新
 */
bool imu601_get_attitude(imu601_attitude_t *att);

/**
 * 获取统计信息 (调试用)
 */
uint32_t imu601_get_frame_count(void);   /* 成功解析的帧数 */
uint32_t imu601_get_error_count(void);   /* 校验错误帧数 */
uint8_t  imu601_get_last_frame_id(void); /* 最近收到的帧ID */

#endif
