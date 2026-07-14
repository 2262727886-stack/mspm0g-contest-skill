/**
 * mpu_port.h — MPU6050 DMP MSPM0 移植层
 *
 * 适配天猛星引脚: I2C1 = PA10(SDA), PA11(SCL), MPU6050 地址 0x68
 * ⚠️ PA10/PA11 与板载 CH340 UART0 共享 — 使用 MPU6050 时需断开 CH340
 *
 * 基于: 地猛星电赛控制题配套资料 12_MPU6050_DMP读取角度
 * DMP 库: InvenSense 官方 inv_mpu + inv_mpu_dmp_motion_driver
 */
#ifndef MPU_PORT_H
#define MPU_PORT_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * 底层 I2C 读写函数 — inv_mpu.c 通过宏映射调用
 * i2c_write → MPU_Write_Len
 * i2c_read  → MPU_Read_Len
 * get_ms    → mget_ms
 */
int  MPU_Write_Len(unsigned char addr, unsigned char reg,
                   unsigned char len, unsigned char *buf);
int  MPU_Read_Len(unsigned char addr, unsigned char reg,
                  unsigned char len, unsigned char *buf);
void mget_ms(unsigned long *time);

/**
 * DMP 初始化和读取 — 应用层直接调用
 * DMP_Init() 返回 0 = 成功, 非 0 = 失败
 * DMP_Read_Data() 返回 0 = 有新数据, -1 = FIFO 空
 */
int DMP_Init(void);
int DMP_Read_Data(float *pitch, float *roll, float *yaw);

#ifdef __cplusplus
}
#endif

#endif /* MPU_PORT_H */
