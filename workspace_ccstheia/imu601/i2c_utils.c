/**
 * @file i2c_utils.c
 * @brief Blocking I2C transfer helpers used by the OLED driver.
 */
#include "i2c_utils.h"

int i2c_wait_idle(I2C_Regs *i2c)
{
    uint32_t timeout = I2C_TIMEOUT;

    while (!(DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--timeout == 0U) {
            return -1;
        }
    }
    return 0;
}

int i2c_wait_done(I2C_Regs *i2c)
{
    uint32_t timeout = I2C_TIMEOUT;

    while (DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_BUSY) {
        if (DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_ERROR) {
            return -2;
        }
        if (--timeout == 0U) {
            return -1;
        }
    }

    if (DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_ERROR) {
        return -2;
    }
    return 0;
}

int i2c_write_bytes(I2C_Regs *i2c, uint8_t addr, const uint8_t *buf, uint8_t len)
{
    if ((buf == 0) || (len == 0U)) {
        return -4;
    }
    if (i2c_wait_idle(i2c) != 0) {
        return -1;
    }

    DL_I2C_flushControllerTXFIFO(i2c);
    DL_I2C_flushControllerRXFIFO(i2c);
    DL_I2C_fillControllerTXFIFO(i2c, (uint8_t *) buf, len);
    DL_I2C_startControllerTransfer(i2c, addr, DL_I2C_CONTROLLER_DIRECTION_TX, len);

    delay_cycles(16);
    return i2c_wait_done(i2c);
}

int i2c_try_write_bytes(I2C_Regs *i2c, uint8_t addr, const uint8_t *buf, uint8_t len)
{
    uint32_t status;

    if ((buf == 0) || (len == 0U)) {
        return -4;
    }

    status = DL_I2C_getControllerStatus(i2c);
    if (status & DL_I2C_CONTROLLER_STATUS_ERROR) {
        DL_I2C_flushControllerTXFIFO(i2c);
        DL_I2C_flushControllerRXFIFO(i2c);
        return -2;
    }
    if (!(status & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        return 1;
    }

    DL_I2C_flushControllerTXFIFO(i2c);
    DL_I2C_flushControllerRXFIFO(i2c);
    DL_I2C_fillControllerTXFIFO(i2c, (uint8_t *) buf, len);
    DL_I2C_startControllerTransfer(i2c, addr, DL_I2C_CONTROLLER_DIRECTION_TX, len);

    return 0;
}
