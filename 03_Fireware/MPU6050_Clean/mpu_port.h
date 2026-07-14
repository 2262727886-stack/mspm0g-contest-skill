/**
 * mpu_port.h — MPU6050 DMP MSPM0 移植层
 *
 * 天猛星引脚: I2C1 = PA10(SDA) + PA11(SCL), MPU6050 地址 0x68
 * ⚠️ PA10/PA11 与板载 CH340 (UART0) 共享 — 使用 MPU6050 时断开 CH340
 */
#ifndef MPU_PORT_H
#define MPU_PORT_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

int  MPU_Write_Len(unsigned char addr, unsigned char reg,
                   unsigned char len, unsigned char *buf);
int  MPU_Read_Len(unsigned char addr, unsigned char reg,
                  unsigned char len, unsigned char *buf);
void mget_ms(unsigned long *time);

int DMP_Init(void);
int DMP_Read_Data(float *pitch, float *roll, float *yaw);

#ifdef __cplusplus
}
#endif

#endif
