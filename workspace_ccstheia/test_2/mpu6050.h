/**
 * @file mpu6050.h
 * @brief MPU6050 six-axis IMU driver, I2C address 0x68 when AD0 is GND.
 */
#ifndef MPU6050_H
#define MPU6050_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

typedef struct {
    int16_t ax;
    int16_t ay;
    int16_t az;
    int16_t temp;
    int16_t gx;
    int16_t gy;
    int16_t gz;
} MPU6050_RawData;

typedef struct {
    float ax_g;
    float ay_g;
    float az_g;
    float temp_c;
    float gx_dps;
    float gy_dps;
    float gz_dps;
} MPU6050_ScaledData;

int MPU6050_Init(void);
int MPU6050_ReadRaw(MPU6050_RawData *data);
int MPU6050_ReadScaled(MPU6050_ScaledData *data);

#endif
