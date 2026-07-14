/**
 * mpu_port.c — MPU6050 DMP MSPM0 移植层 (与例程 API 完全一致)
 *
 * 直接使用 DL_I2C 原始 API, 与地猛星 12_MPU6050_DMP 例程完全相同的 I2C 操作顺序:
 *   写: reg → startTransfer(TX, len+1) → 逐字节填 TXFIFO
 *   读: reg → startTransfer(TX, 1) → startTransfer(RX, len) → 逐字节读 RXFIFO
 */

#include "mpu_port.h"
#include "inv_mpu.h"
#include "inv_mpu_dmp_motion_driver.h"
#include "delay.h"
#include <math.h>

/* ---- SysTick ---- */
volatile uint32_t sys_tick_ms = 0;

void mget_ms(unsigned long *time)
{
    if (time != 0) { *time = sys_tick_ms; }
}

/* ---- I2C 写: 与原始例程完全一致的时序 ---- */
int MPU_Write_Len(unsigned char addr, unsigned char reg,
                  unsigned char len, unsigned char *buf)
{
    volatile uint32_t timeout = 100000;

    /* 等待总线空闲 */
    while (!(DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--timeout == 0) return -1;
    }

    /* 先发寄存器地址 (1 字节入 TXFIFO) */
    DL_I2C_transmitControllerData(I2C_MPU_INST, reg);

    /* 启动发送: addr + 方向 = TX, 总长度 = reg(1) + data(len) */
    DL_I2C_startControllerTransfer(I2C_MPU_INST, addr,
        DL_I2C_CONTROLLER_DIRECTION_TX, (uint8_t)(len + 1U));

    /* 传输进行中逐字节填数据 */
    for (uint16_t i = 0; i < len; i++) {
        timeout = 100000;
        while (DL_I2C_isControllerTXFIFOFull(I2C_MPU_INST)) {
            if (--timeout == 0) return -2;
        }
        DL_I2C_transmitControllerData(I2C_MPU_INST, buf[i]);
    }

    /* 等待传输完成 (BUSY 清零) */
    timeout = 100000;
    while (DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_BUSY) {
        if (--timeout == 0) return -3;
    }

    /* 等待总线回到 IDLE */
    timeout = 100000;
    while (!(DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--timeout == 0) return -4;
    }

    return 0;
}

/* ---- I2C 读: 与原始例程完全一致的时序 ---- */
int MPU_Read_Len(unsigned char addr, unsigned char reg,
                 unsigned char len, unsigned char *buf)
{
    volatile uint32_t timeout;

    /* 1. 写寄存器地址 */
    timeout = 100000;
    while (!(DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--timeout == 0) return -1;
    }

    DL_I2C_transmitControllerData(I2C_MPU_INST, reg);
    DL_I2C_startControllerTransfer(I2C_MPU_INST, addr,
        DL_I2C_CONTROLLER_DIRECTION_TX, 1);

    /* 等 TX 完成 */
    timeout = 100000;
    while (DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_BUSY) {
        if (--timeout == 0) return -2;
    }
    timeout = 100000;
    while (!(DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--timeout == 0) return -3;
    }

    /* 2. 启动接收 */
    DL_I2C_startControllerTransfer(I2C_MPU_INST, addr,
        DL_I2C_CONTROLLER_DIRECTION_RX, len);

    /* 3. 逐字节读 RXFIFO */
    for (uint16_t i = 0; i < len; i++) {
        timeout = 100000;
        while (DL_I2C_isControllerRXFIFOEmpty(I2C_MPU_INST)) {
            if (DL_I2C_getControllerStatus(I2C_MPU_INST)
                & DL_I2C_CONTROLLER_STATUS_ERROR) {
                return -4;
            }
            if (--timeout == 0) return -5;
        }
        buf[i] = DL_I2C_receiveControllerData(I2C_MPU_INST);
    }

    /* 等接收完成 */
    timeout = 100000;
    while (DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_BUSY) {
        if (--timeout == 0) return -6;
    }
    timeout = 100000;
    while (!(DL_I2C_getControllerStatus(I2C_MPU_INST)
           & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--timeout == 0) return -7;
    }

    return 0;
}

/* ---- 陀螺仪方向矩阵 ---- */
static signed char gyro_orientation[9] = {1,0,0, 0,1,0, 0,0,1};

unsigned short inv_row_2_scale(const signed char *row)
{
    unsigned short b;
    if      (row[0] > 0) b = 0;
    else if (row[0] < 0) b = 4;
    else if (row[1] > 0) b = 1;
    else if (row[1] < 0) b = 5;
    else if (row[2] > 0) b = 2;
    else if (row[2] < 0) b = 6;
    else                 b = 7;
    return b;
}

unsigned short inv_orientation_matrix_to_scalar(const signed char *mtx)
{
    unsigned short s;
    s  = inv_row_2_scale(mtx);
    s |= inv_row_2_scale(mtx + 3) << 3;
    s |= inv_row_2_scale(mtx + 6) << 6;
    return s;
}

/* ---- DMP 初始化: 与例程完全一致 ---- */
int DMP_Init(void)
{
    int res;

    /* SysTick 1ms */
    SysTick->LOAD  = (CPUCLK_FREQ / 1000U) - 1U;
    SysTick->VAL   = 0U;
    SysTick->CTRL  = SysTick_CTRL_CLKSOURCE_Msk
                   | SysTick_CTRL_TICKINT_Msk
                   | SysTick_CTRL_ENABLE_Msk;
    __enable_irq();
    delay_cycles(CPUCLK_FREQ / 10U);

    res = mpu_init();
    if (res) return res;

    mpu_set_sensors(INV_XYZ_GYRO | INV_XYZ_ACCEL);
    mpu_configure_fifo(INV_XYZ_GYRO | INV_XYZ_ACCEL);
    mpu_set_sample_rate(100);

    res = dmp_load_motion_driver_firmware();
    if (res) return res;

    dmp_set_orientation(inv_orientation_matrix_to_scalar(gyro_orientation));
    dmp_enable_feature(DMP_FEATURE_6X_LP_QUAT | DMP_FEATURE_TAP
                     | DMP_FEATURE_ANDROID_ORIENT | DMP_FEATURE_SEND_RAW_ACCEL
                     | DMP_FEATURE_SEND_CAL_GYRO | DMP_FEATURE_GYRO_CAL);
    dmp_set_fifo_rate(100);
    return mpu_set_dmp_state(1);
}

/* ---- 读取欧拉角 ---- */
#define Q30 1073741824.0f

int DMP_Read_Data(float *pitch, float *roll, float *yaw)
{
    short gyro[3], accel[3], sensors;
    unsigned char more;
    long quat[4];

    if (dmp_read_fifo(gyro, accel, quat, NULL, &sensors, &more) != 0)
        return -1;
    if (!(sensors & INV_WXYZ_QUAT))
        return -1;

    float q0 = (float)quat[0] / Q30;
    float q1 = (float)quat[1] / Q30;
    float q2 = (float)quat[2] / Q30;
    float q3 = (float)quat[3] / Q30;

    *pitch = asinf(-2.0f * q1 * q3 + 2.0f * q0 * q2) * 57.3f;
    *roll  = atan2f(2.0f * q2 * q3 + 2.0f * q0 * q1,
                    -2.0f * q1 * q1 - 2.0f * q2 * q2 + 1.0f) * 57.3f;
    *yaw   = atan2f(2.0f * (q1 * q2 + q0 * q3),
                    q0 * q0 + q1 * q1 - q2 * q2 - q3 * q3) * 57.3f;
    return 0;
}
