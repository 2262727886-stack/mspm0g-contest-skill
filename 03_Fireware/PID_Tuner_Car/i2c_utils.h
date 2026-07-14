/**
 * @file i2c_utils.h
 * @brief MSPM0G DriverLib I2C polling helpers.
 *
 * The helpers keep all low-level timeout and FIFO handling in one place, so
 * OLED, MPU6050 and later sensors can share the same bus code.
 */
#ifndef I2C_UTILS_H
#define I2C_UTILS_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#define I2C_TIMEOUT 100000U

int i2c_wait_idle(I2C_Regs *i2c);
int i2c_wait_done(I2C_Regs *i2c);
int i2c_write_bytes(I2C_Regs *i2c, uint8_t addr, const uint8_t *buf, uint8_t len);
int i2c_read_reg_bytes(I2C_Regs *i2c, uint8_t addr, uint8_t reg, uint8_t *buf, uint8_t len);
int i2c_probe_reg(I2C_Regs *i2c, uint8_t addr, uint8_t reg);

#endif
