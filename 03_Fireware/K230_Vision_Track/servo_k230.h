/**
 * @file servo_k230.h
 * @brief K230视觉追踪→舵机控制模块
 *
 * 通信链路: K230 UART2(TX=GPIO5排针11, RX=GPIO6排针13) → MSPM0G UART3(RX=PB3, TX=PB2)
 * 舵机输出: PB9=TIMA0_CH1(Pan水平), PB8=TIMA0_CH0(Tilt俯仰), 50Hz PWM
 *
 * 帧协议(10字节):
 *   [0xA5][0x5A][CMD][PAN_L][PAN_H][TILT_L][TILT_H][EXTRA_L][EXTRA_H][CHK]
 *   PAN/TILT 单位 0.1°, 小端序
 *   CHK = 前9字节异或
 *   CMD: 0x01=目标坐标, 0x04=目标丢失, 0xFF=急停
 */
#ifndef SERVO_K230_H
#define SERVO_K230_H

#include <stdint.h>

/* 初始化舵机PWM(TIMA0)和UART3 */
void ServoK230_Init(void);

/* 设置舵机角度 0~180° */
void Servo_SetPan(uint8_t angle_deg);
void Servo_SetTilt(uint8_t angle_deg);

/* 设置舵机角度 (0.1°精度, 0~1800) */
void Servo_SetPanRaw(uint16_t angle_x10);
void Servo_SetTiltRaw(uint16_t angle_x10);

/* 轮询UART3, 解析K230坐标帧
 * 返回: 1=收到新坐标帧, 0=无新帧, -1=急停 */
int8_t ServoK230_Poll(void);

/* 获取最新目标角度(0.1°单位, 0~1800) */
uint16_t Servo_GetTargetPan(void);
uint16_t Servo_GetTargetTilt(void);

/* 目标是否丢失 (>500ms 无新帧) */
uint8_t Servo_IsTargetLost(void);

/* 获取帧率 (帧/秒, 每500ms更新) */
uint8_t Servo_GetFrameRate(void);

/* 系统滴答(10ms) — 主循环周期性调用, 用于超时检测和帧率统计 */
void ServoK230_Tick10ms(void);

#endif /* SERVO_K230_H */
