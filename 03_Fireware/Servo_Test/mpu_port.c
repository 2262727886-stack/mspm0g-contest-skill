/**
 * mpu_port.c — MPU6050 DMP MSPM0 移植层 实现
 *
 * 适配: 天猛星 MSPM0G3507, I2C1 = PA10(SDA) + PA11(SCL), 32MHz
 *
 * 基于: 地猛星电赛控制题配套资料 12_MPU6050_DMP读取角度
 * DMP 库: InvenSense 官方 inv_mpu.c + inv_mpu_dmp_motion_driver.c
 *
 * ⚠️ PA10/PA11 与板载 CH340 (UART0) 共享物理引脚!
 *    使用 MPU6050 DMP 期间 printf/UART0 调试输出不可用.
 *    调试建议: 用 OLED 代替串口输出.
 */

#include "mpu_port.h"
#include "inv_mpu.h"
#include "inv_mpu_dmp_motion_driver.h"
#include "i2c_utils.h"
#include <math.h>

/* ================================================================
 * SysTick 毫秒时钟 — DMP 库通过 mget_ms() 获取时间戳
 *
 * SysTick 配置为 1ms 周期中断, SysTick_Handler 在 main.c 中实现.
 * 不占用定时器外设 (TIMG0/6/7/8/12 留给 PWM/编码器/PID).
 * ================================================================ */
volatile uint32_t sys_tick_ms = 0;

void mget_ms(unsigned long *time)
{
    if (time != 0) {
        *time = sys_tick_ms;
    }
}

/* ================================================================
 * I2C 读写 — inv_mpu.c 通过宏 i2c_write / i2c_read 调用
 *
 * i2c_write(slave_addr, reg_addr, length, data):
 *   向器件 slave_addr 的 reg_addr 寄存器连续写入 length 字节
 *   → i2c_write_bytes(i2c, addr, {reg, data[0..len-1]}, len+1)
 *
 * i2c_read(slave_addr, reg_addr, length, data):
 *   从器件 slave_addr 的 reg_addr 寄存器连续读取 length 字节
 *   → i2c_read_reg_bytes(i2c, addr, reg, data, len)
 * ================================================================ */

int MPU_Write_Len(unsigned char addr, unsigned char reg,
                  unsigned char len, unsigned char *buf)
{
    /*
     * i2c_write_bytes 要求 buf 前部包含寄存器地址,
     * 所以构造一个临时缓冲区: [reg] [data...].
     * 对于 MPU6050 单寄存器写: len=1, 发送 2 字节 = reg + 1 字节数据
     */
    uint8_t tmp[32];  /* MPU6050 寄存器操作不会超过此长度 */
    if (len > sizeof(tmp) - 1U) {
        return -10;
    }

    tmp[0] = reg;
    for (uint8_t i = 0; i < len; i++) {
        tmp[i + 1U] = buf[i];
    }

    return i2c_write_bytes(I2C_MPU_INST, addr, tmp, (uint8_t)(len + 1U));
}

int MPU_Read_Len(unsigned char addr, unsigned char reg,
                 unsigned char len, unsigned char *buf)
{
    return i2c_read_reg_bytes(I2C_MPU_INST, addr, reg, buf, len);
}

/* ================================================================
 * 陀螺仪安装方向矩阵 — 单位矩阵 (默认安装方向)
 *
 * 如果你的 MPU6050 安装方向与车身坐标系不一致,
 * 修改 gyro_orientation 矩阵来重新映射轴.
 *
 * 矩阵格式 (row-major 3×3):
 *   {X轴映射, Y轴映射, Z轴映射} 各 3 个分量
 *   单位矩阵 {1,0,0, 0,1,0, 0,0,1} = 不重映射
 * ================================================================ */
static signed char gyro_orientation[9] = { 1, 0, 0,
                                           0, 1, 0,
                                           0, 0, 1 };

/* DMP 库内部辅助函数 — 方向矩阵 → 标量编码 */
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
    unsigned short scalar;
    scalar  = inv_row_2_scale(mtx);
    scalar |= inv_row_2_scale(mtx + 3) << 3;
    scalar |= inv_row_2_scale(mtx + 6) << 6;
    return scalar;
}

/* ================================================================
 * DMP_Init — 完整初始化序列
 *
 * 流程:
 *   1. 配置 SysTick 1ms (DMP 库需要毫秒时间戳)
 *   2. mpu_init() — 复位 MPU6050 + 检查 WHO_AM_I
 *   3. 设置传感器 + FIFO + 采样率 100Hz
 *   4. dmp_load_motion_driver_firmware() — 加载 DMP 固件
 *   5. 设置方向 + 使能 6 轴四元数 + 启动 DMP
 *
 * 返回 0 = 成功, 非 0 = 失败 (排查: 检查 I2C 接线/地址/电源)
 * ================================================================ */
int DMP_Init(void)
{
    int res;

    /* 1. SysTick: 1ms 周期, CPU 时钟源, 使能中断 */
    SysTick->LOAD  = (CPUCLK_FREQ / 1000U) - 1U;
    SysTick->VAL   = 0U;
    SysTick->CTRL  = SysTick_CTRL_CLKSOURCE_Msk   /* 使用 CPU 时钟 */
                   | SysTick_CTRL_TICKINT_Msk      /* 使能中断 */
                   | SysTick_CTRL_ENABLE_Msk;      /* 使能 SysTick */
    __enable_irq();

    /* 等待 MPU6050 上电稳定 (100ms) */
    delay_cycles(CPUCLK_FREQ / 10U);

    /* 2. 初始化 MPU6050 基础驱动 */
    res = mpu_init();
    if (res != 0) return res;

    /* 3. 配置传感器 + FIFO + 采样率 */
    mpu_set_sensors(INV_XYZ_GYRO | INV_XYZ_ACCEL);
    mpu_configure_fifo(INV_XYZ_GYRO | INV_XYZ_ACCEL);
    mpu_set_sample_rate(100);  /* 100Hz */

    /* 4. 加载 DMP 固件 (从 dmpKey.h / dmpmap.h) */
    res = dmp_load_motion_driver_firmware();
    if (res != 0) return res;

    /* 5. 设置安装方向 + 使能功能 */
    dmp_set_orientation(
        inv_orientation_matrix_to_scalar(gyro_orientation));

    dmp_enable_feature(DMP_FEATURE_6X_LP_QUAT       /* 6 轴四元数 */
                     | DMP_FEATURE_TAP               /* 敲击检测 */
                     | DMP_FEATURE_ANDROID_ORIENT    /* Android 方向 */
                     | DMP_FEATURE_SEND_RAW_ACCEL    /* 原始加速度 */
                     | DMP_FEATURE_SEND_CAL_GYRO     /* 校准后陀螺 */
                     | DMP_FEATURE_GYRO_CAL);        /* 陀螺校准 */

    dmp_set_fifo_rate(100);  /* FIFO 输出 100Hz */
    res = mpu_set_dmp_state(1);  /* 启动 DMP */

    return res;
}

/* ================================================================
 * DMP_Read_Data — 读取欧拉角
 *
 * 从 DMP FIFO 读取四元数 → 转为 pitch/roll/yaw (度)
 *
 * q30 格式: 四元数 = quat[i] / 1073741824.0f
 *
 * 注意: yaw 是相对角度 (无磁力计修正, 会随时间漂移).
 *       pitch/roll 由重力修正, 稳定不漂.
 *       上电时 yaw=0, 相对该初始方向.
 * ================================================================ */
#define Q30  1073741824.0f

int DMP_Read_Data(float *pitch, float *roll, float *yaw)
{
    short gyro[3], accel[3], sensors;
    unsigned char more;
    long quat[4];

    /* 从 DMP FIFO 读取一帧数据 */
    if (dmp_read_fifo(gyro, accel, quat, NULL, &sensors, &more) != 0) {
        return -1;  /* FIFO 空或读取失败 */
    }

    /* 检查是否包含四元数数据 */
    if (!(sensors & INV_WXYZ_QUAT)) {
        return -1;
    }

    /* q30 定点数 → 浮点四元数 */
    float q0 = (float)quat[0] / Q30;
    float q1 = (float)quat[1] / Q30;
    float q2 = (float)quat[2] / Q30;
    float q3 = (float)quat[3] / Q30;

    /* 四元数 → 欧拉角 (InvenSense 标准公式) */
    *pitch = asinf(-2.0f * q1 * q3 + 2.0f * q0 * q2) * 57.3f;
    *roll  = atan2f(2.0f * q2 * q3 + 2.0f * q0 * q1,
                    -2.0f * q1 * q1 - 2.0f * q2 * q2 + 1.0f) * 57.3f;
    *yaw   = atan2f(2.0f * (q1 * q2 + q0 * q3),
                    q0 * q0 + q1 * q1 - q2 * q2 - q3 * q3) * 57.3f;

    return 0;
}
