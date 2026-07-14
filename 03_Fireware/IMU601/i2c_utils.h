/**
 * @file i2c_utils.h
 * @brief Polling I2C helpers for MSPM0 DriverLib.
 */
#ifndef I2C_UTILS_H
#define I2C_UTILS_H

#include "ti_msp_dl_config.h"
#include <stdint.h>

#define I2C_TIMEOUT 100000U

int i2c_wait_idle(I2C_Regs *i2c);
int i2c_wait_done(I2C_Regs *i2c);
int i2c_write_bytes(I2C_Regs *i2c, uint8_t addr, const uint8_t *buf, uint8_t len);
int i2c_try_write_bytes(I2C_Regs *i2c, uint8_t addr, const uint8_t *buf, uint8_t len);

#endif
