/**
 * imu601.h — ATK/正点原子 IMU601 UART 姿态传感器驱动
 *
 * 硬件: IMU601 → UART0 (PA0=TX, PA1=RX), 115200 8N1
 * 协议: ATKP 帧, 上传帧头 55 55, 姿态 msg_id=0x01, 陀螺仪 msg_id=0x03
 */

#ifndef IMU601_H
#define IMU601_H

#include <stdbool.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ========================= ATKP 协议常量 ========================= */
#define ATKP_HEAD1              (0x55U)     /* 帧头第1字节 */
#define ATKP_HEAD2_UPLOAD       (0x55U)     /* 上传帧头第2字节 */
#define ATKP_HEAD2_ACK          (0xAFU)     /* ACK帧头第2字节 */
#define ATKP_MAX_DATA_SIZE      (28U)       /* 数据域最大长度 */

#define ATKP_MSG_ATTITUDE       (0x01U)     /* 姿态帧: roll/pitch/yaw */
#define ATKP_MSG_QUATERNION     (0x02U)     /* 四元数帧(未使用) */
#define ATKP_MSG_GYRO_ACC       (0x03U)     /* 陀螺仪+加速度计帧 */

#define ATKP_REG_SAVE           (0x00U)     /* 保存配置寄存器 */
#define ATKP_REG_GYRO_FSR       (0x03U)     /* 陀螺仪满量程 */
#define ATKP_REG_ACC_FSR        (0x04U)     /* 加速度计满量程 */
#define ATKP_REG_UPSET          (0x08U)     /* 上传内容选择 */
#define ATKP_REG_UPRATE         (0x0AU)     /* 上传速率 */

/* ========================= 配置参数 ========================= */
#define GYRO_FSR_INDEX          (3U)        /* 0=250, 1=500, 2=1000, 3=2000 dps */
#define ACC_FSR_INDEX           (1U)        /* 0=2g, 1=4g, 2=8g, 3=16g */
#define GYRO_CAL_SAMPLES        (128U)      /* 零偏校准采样数 */

/* ========================= 数据结构 ========================= */

/* 三维浮点向量 */
typedef struct {
    float x;
    float y;
    float z;
} Vector3f;

/* ATKP 接收包 */
typedef struct {
    uint8_t head1;
    uint8_t head2;
    uint8_t msg_id;
    uint8_t data_len;
    uint8_t data[ATKP_MAX_DATA_SIZE];
    uint8_t checksum;
} ATKP_Packet;

/* IMU601 完整数据 */
typedef struct {
    Vector3f accel_g;           /* 加速度 (g) */
    Vector3f gyro_dps;          /* 角速度 (°/s), 已减零偏 */
    Vector3f angle_deg;         /* 姿态角 (°), yaw=z轴 */
    uint32_t attitude_count;    /* 姿态帧计数 */
    uint32_t gyro_acc_count;    /* 陀螺仪帧计数 */
} IMU601_Data;

/* ========================= 公开接口 ========================= */

/**
 * IMU601 初始化: 配置 ATKP 寄存器 + 等待模块就绪
 * 必须在 SYSCFG_DL_init() 之后调用, 会阻塞约 600ms
 */
void IMU601_Init(void);

/**
 * 从 UART 环形缓冲区取出字节, 解析 ATKP 帧
 * 在主循环中调用, 非阻塞
 */
void IMU601_ParseService(void);

/**
 * 获取当前 IMU 数据 (中断安全的副本)
 */
IMU601_Data IMU601_GetData(void);

/**
 * 获取 yaw 角 (度), 已减去零偏
 */
float IMU601_GetYaw(void);

/**
 * 获取 Z 轴角速度 (°/s), 已减去零偏
 */
float IMU601_GetGyroZ(void);

/**
 * 启动陀螺仪零偏校准 (静止状态调用, 采集 128 个样本)
 */
void IMU601_StartGyroCal(void);

/**
 * 陀螺仪是否已完成校准
 */
bool IMU601_IsGyroCalDone(void);

/**
 * 陀螺仪是否正在校准中
 */
bool IMU601_IsGyroCalibrating(void);

/**
 * 获取已接收的 ATKP 包数 (调试用)
 */
uint32_t IMU601_GetPacketCount(void);

/**
 * 获取校验和错误计数 (调试用)
 */
uint32_t IMU601_GetChecksumErrors(void);

#ifdef __cplusplus
}
#endif

#endif /* IMU601_H */
