/**
 * @file mpu6050.c
 * @brief MPU6050 driver for the expansion-board I2C1 bus.
 *
 * Wiring used by this project:
 *   MPU6050 SDA -> PA10 / I2C1_SDA
 *   MPU6050 SCL -> PA11 / I2C1_SCL
 *   MPU6050 AD0 -> GND, address 0x68. AD0 high is also detected as 0x69.
 */
#include "mpu6050.h"
#include "i2c_utils.h"

#ifndef I2C_MPU_INST
int MPU6050_Init(void)
{
    return -99;
}

int MPU6050_ReadRaw(MPU6050_RawData *data)
{
    (void)data;
    return -99;
}

int MPU6050_ReadScaled(MPU6050_ScaledData *data)
{
    (void)data;
    return -99;
}
#else

#define MPU6050_I2C        I2C_MPU_INST
#define MPU6050_ADDR_LOW   0x68U
#define MPU6050_ADDR_HIGH  0x69U

#define REG_SMPLRT_DIV     0x19U
#define REG_CONFIG         0x1AU
#define REG_GYRO_CONFIG    0x1BU
#define REG_ACCEL_CONFIG   0x1CU
#define REG_ACCEL_XOUT_H   0x3BU
#define REG_PWR_MGMT_1     0x6BU
#define REG_WHO_AM_I       0x75U

#define ACCEL_LSB_PER_G    4096.0f
#define GYRO_LSB_PER_DPS   16.4f

static uint8_t g_mpu_addr = MPU6050_ADDR_LOW;

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0; i < ms; i++) {
        delay_cycles(CPUCLK_FREQ / 1000U);
    }
}

static int mpu_write_reg(uint8_t reg, uint8_t val)
{
    uint8_t buf[2] = {reg, val};
    return i2c_write_bytes(MPU6050_I2C, g_mpu_addr, buf, sizeof(buf));
}

static int mpu_probe_addr(uint8_t addr)
{
    uint8_t who = 0U;
    int ret = i2c_read_reg_bytes(MPU6050_I2C, addr, REG_WHO_AM_I, &who, 1U);

    if (ret != 0) {
        return ret;
    }
    if (who != 0x68U) {
        return -30;
    }

    g_mpu_addr = addr;
    return 0;
}

int MPU6050_Init(void)
{
    int ret;

    ret = mpu_probe_addr(MPU6050_ADDR_LOW);
    if (ret != 0) {
        ret = mpu_probe_addr(MPU6050_ADDR_HIGH);
        if (ret != 0) {
            return -1;
        }
    }

    if (mpu_write_reg(REG_PWR_MGMT_1, 0x00U) != 0) {
        return -2;
    }
    delay_ms(100U);

    if (mpu_write_reg(REG_SMPLRT_DIV, 0x07U) != 0) {
        return -3;
    }
    if (mpu_write_reg(REG_CONFIG, 0x03U) != 0) {
        return -4;
    }
    if (mpu_write_reg(REG_GYRO_CONFIG, 0x18U) != 0) {
        return -5;
    }
    if (mpu_write_reg(REG_ACCEL_CONFIG, 0x10U) != 0) {
        return -6;
    }

    return 0;
}

int MPU6050_ReadRaw(MPU6050_RawData *data)
{
    uint8_t buf[14] = {0};

    if (data == 0) {
        return -4;
    }

    int ret = i2c_read_reg_bytes(MPU6050_I2C, g_mpu_addr, REG_ACCEL_XOUT_H, buf, sizeof(buf));
    if (ret != 0) {
        return ret;
    }

    data->ax   = (int16_t) (((uint16_t) buf[0] << 8) | buf[1]);
    data->ay   = (int16_t) (((uint16_t) buf[2] << 8) | buf[3]);
    data->az   = (int16_t) (((uint16_t) buf[4] << 8) | buf[5]);
    data->temp = (int16_t) (((uint16_t) buf[6] << 8) | buf[7]);
    data->gx   = (int16_t) (((uint16_t) buf[8] << 8) | buf[9]);
    data->gy   = (int16_t) (((uint16_t) buf[10] << 8) | buf[11]);
    data->gz   = (int16_t) (((uint16_t) buf[12] << 8) | buf[13]);

    return 0;
}

int MPU6050_ReadScaled(MPU6050_ScaledData *data)
{
    MPU6050_RawData raw;
    int ret;

    if (data == 0) {
        return -4;
    }

    ret = MPU6050_ReadRaw(&raw);
    if (ret != 0) {
        return ret;
    }

    data->ax_g = (float) raw.ax / ACCEL_LSB_PER_G;
    data->ay_g = (float) raw.ay / ACCEL_LSB_PER_G;
    data->az_g = (float) raw.az / ACCEL_LSB_PER_G;
    data->temp_c = ((float) raw.temp / 340.0f) + 36.53f;
    data->gx_dps = (float) raw.gx / GYRO_LSB_PER_DPS;
    data->gy_dps = (float) raw.gy / GYRO_LSB_PER_DPS;
    data->gz_dps = (float) raw.gz / GYRO_LSB_PER_DPS;

    return 0;
}

#endif
