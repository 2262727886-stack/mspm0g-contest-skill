/**
 * imu601.c — ATK/正点原子 IMU601 UART 姿态传感器驱动实现
 *
 * 硬件连接: IMU601 TX → PA1 (UART0_RX), IMU601 RX → PA0 (UART0_TX)
 * UART0 由 SysConfig 生成, 115200 8N1, FIFO 使能
 *
 * 工作流程:
 *   1. UART0 RX 中断将字节存入环形缓冲区
 *   2. 主循环调用 IMU601_ParseService() 解析 ATKP 帧
 *   3. 解析到姿态帧/陀螺仪帧时更新全局数据
 */

#include "imu601.h"
#include "ti_msp_dl_config.h"

/* ========================= 内部常量 ========================= */

#define RING_SIZE       (2048U)         /* 环形缓冲区大小, 必须是2的幂 */
#define RING_MASK       (RING_SIZE - 1U)

static const uint16_t sGyroFsrTable[4] = {250U, 500U, 1000U, 2000U};
static const uint8_t  sAccFsrTable[4]  = {2U, 4U, 8U, 16U};

/* ========================= 内部状态 ========================= */

/* UART 环形缓冲区 (中断写, 主循环读) */
static volatile uint8_t  sRxBuf[RING_SIZE];
static volatile uint16_t sRxHead;
static volatile uint16_t sRxTail;

/* IMU 数据 (中断更新, 主循环读取) */
static volatile IMU601_Data sData;

/* 陀螺仪零偏校准 */
static volatile Vector3f sGyroBias;
static Vector3f sGyroCalSum;
static volatile uint32_t sGyroCalCount;
static volatile bool sGyroCalibrating;
static volatile bool sGyroCalDone;

/* 调试计数 */
static volatile uint32_t sPktCount;
static volatile uint32_t sChkErrCount;
static volatile uint32_t sOverflowCount;

/* ========================= 环形缓冲区操作 ========================= */

static void ring_push(uint8_t byte)
{
    uint16_t next = (uint16_t)((sRxHead + 1U) & RING_MASK);
    if (next == sRxTail) {
        sOverflowCount++;
        return;
    }
    sRxBuf[sRxHead] = byte;
    sRxHead = next;
}

static bool ring_pop(uint8_t *byte)
{
    if (sRxTail == sRxHead) return false;
    *byte = sRxBuf[sRxTail];
    sRxTail = (uint16_t)((sRxTail + 1U) & RING_MASK);
    return true;
}

/* ========================= UART0 中断 ========================= */

/* 将 FIFO 中所有字节搬到环形缓冲区 */
static void drain_fifo(void)
{
    while (!DL_UART_Main_isRXFIFOEmpty(UART_0_INST)) {
        ring_push(DL_UART_Main_receiveData(UART_0_INST));
    }
}

/* UART0 中断服务函数 (SysConfig 生成弱符号, 此处覆盖) */
void UART_0_INST_IRQHandler(void)
{
    switch (DL_UART_Main_getPendingInterrupt(UART_0_INST)) {
    case DL_UART_MAIN_IIDX_RX:
    case DL_UART_MAIN_IIDX_RX_TIMEOUT_ERROR:
        drain_fifo();
        break;
    default:
        break;
    }
}

/* ========================= ATKP 发送 ========================= */

static void uart_send(const uint8_t *data, uint16_t len)
{
    for (uint16_t i = 0U; i < len; i++) {
        DL_UART_Main_transmitDataBlocking(UART_0_INST, data[i]);
    }
}

/* 向 IMU601 写寄存器 */
static void atkp_write_reg(uint8_t reg, uint16_t value, uint8_t len)
{
    uint8_t pkt[7];
    pkt[0] = ATKP_HEAD1;
    pkt[1] = ATKP_HEAD2_ACK;
    pkt[2] = reg;
    pkt[3] = len;
    pkt[4] = (uint8_t)value;

    if (len == 2U) {
        pkt[5] = (uint8_t)(value >> 8);
        pkt[6] = pkt[0] + pkt[1] + pkt[2] + pkt[3] + pkt[4] + pkt[5];
        uart_send(pkt, 7U);
    } else {
        pkt[5] = pkt[0] + pkt[1] + pkt[2] + pkt[3] + pkt[4];
        uart_send(pkt, 6U);
    }
}

/* 向 IMU601 发送读寄存器命令 (触发数据上传) */
static void atkp_read_reg(uint8_t reg)
{
    uint8_t pkt[6];
    pkt[0] = ATKP_HEAD1;
    pkt[1] = ATKP_HEAD2_ACK;
    pkt[2] = reg | 0x80U;
    pkt[3] = 1U;
    pkt[4] = 0U;
    pkt[5] = pkt[0] + pkt[1] + pkt[2] + pkt[3] + pkt[4];
    uart_send(pkt, 6U);
}

/* ========================= ATKP 解析 ========================= */

static int16_t decode_i16(uint8_t lo, uint8_t hi)
{
    return (int16_t)(((uint16_t)hi << 8) | lo);
}

/* 陀螺仪零偏采样 (校准模式下每收到一个样本调用一次) */
static void gyro_cal_sample(Vector3f raw)
{
    if (!sGyroCalibrating) return;

    sGyroCalSum.x += raw.x;
    sGyroCalSum.y += raw.y;
    sGyroCalSum.z += raw.z;
    sGyroCalCount++;

    if (sGyroCalCount >= GYRO_CAL_SAMPLES) {
        sGyroBias.x = sGyroCalSum.x / (float)GYRO_CAL_SAMPLES;
        sGyroBias.y = sGyroCalSum.y / (float)GYRO_CAL_SAMPLES;
        sGyroBias.z = sGyroCalSum.z / (float)GYRO_CAL_SAMPLES;
        sGyroCalibrating = false;
        sGyroCalDone = true;
    }
}

/* 解析一个完整的 ATKP 包 */
static void atkp_parse(const ATKP_Packet *pkt)
{
    int16_t x, y, z;

    if (pkt->head2 == ATKP_HEAD2_ACK) return; /* ACK 帧忽略 */

    switch (pkt->msg_id) {
    case ATKP_MSG_ATTITUDE:
        /* 姿态帧: roll(2B) + pitch(2B) + yaw(2B), 有符号, 单位=32768/180° */
        if (pkt->data_len < 6U) return;
        x = decode_i16(pkt->data[0], pkt->data[1]);
        y = decode_i16(pkt->data[2], pkt->data[3]);
        z = decode_i16(pkt->data[4], pkt->data[5]);
        sData.angle_deg.x = (float)x / 32768.0f * 180.0f;
        sData.angle_deg.y = (float)y / 32768.0f * 180.0f;
        sData.angle_deg.z = (float)z / 32768.0f * 180.0f;
        sData.attitude_count++;
        break;

    case ATKP_MSG_GYRO_ACC:
        /* 陀螺仪+加速度帧: ax(2B) ay(2B) az(2B) gx(2B) gy(2B) gz(2B) */
        if (pkt->data_len < 12U) return;
        /* 加速度 */
        x = decode_i16(pkt->data[0], pkt->data[1]);
        y = decode_i16(pkt->data[2], pkt->data[3]);
        z = decode_i16(pkt->data[4], pkt->data[5]);
        sData.accel_g.x = (float)x / 32768.0f * sAccFsrTable[ACC_FSR_INDEX];
        sData.accel_g.y = (float)y / 32768.0f * sAccFsrTable[ACC_FSR_INDEX];
        sData.accel_g.z = (float)z / 32768.0f * sAccFsrTable[ACC_FSR_INDEX];
        /* 陀螺仪原始值 */
        x = decode_i16(pkt->data[6],  pkt->data[7]);
        y = decode_i16(pkt->data[8],  pkt->data[9]);
        z = decode_i16(pkt->data[10], pkt->data[11]);
        {
            Vector3f raw;
            raw.x = (float)x / 32768.0f * sGyroFsrTable[GYRO_FSR_INDEX];
            raw.y = (float)y / 32768.0f * sGyroFsrTable[GYRO_FSR_INDEX];
            raw.z = (float)z / 32768.0f * sGyroFsrTable[GYRO_FSR_INDEX];
            /* 校准采样 */
            gyro_cal_sample(raw);
            /* 减去零偏 */
            sData.gyro_dps.x = raw.x - sGyroBias.x;
            sData.gyro_dps.y = raw.y - sGyroBias.y;
            sData.gyro_dps.z = raw.z - sGyroBias.z;
        }
        sData.gyro_acc_count++;
        break;

    default:
        break;
    }
}

/* 逐字节 ATKP 状态机 (从环形缓冲区取字节调用) */
static bool atkp_rx_byte(uint8_t byte)
{
    typedef enum {
        ST_HEAD1, ST_HEAD2, ST_MSGID, ST_LEN, ST_DATA, ST_CHK
    } State;

    static State st = ST_HEAD1;
    static ATKP_Packet pkt;
    static uint8_t chk, idx;

    switch (st) {
    case ST_HEAD1:
        if (byte == ATKP_HEAD1) { pkt.head1 = byte; chk = byte; st = ST_HEAD2; }
        break;
    case ST_HEAD2:
        if (byte == ATKP_HEAD2_UPLOAD || byte == ATKP_HEAD2_ACK) {
            pkt.head2 = byte; chk += byte; st = ST_MSGID;
        } else {
            st = ST_HEAD1;
        }
        break;
    case ST_MSGID:
        pkt.msg_id = byte; chk += byte; st = ST_LEN;
        break;
    case ST_LEN:
        if (byte <= ATKP_MAX_DATA_SIZE) {
            pkt.data_len = byte; chk += byte; idx = 0;
            st = (byte > 0U) ? ST_DATA : ST_CHK;
        } else {
            st = ST_HEAD1;
        }
        break;
    case ST_DATA:
        pkt.data[idx++] = byte; chk += byte;
        if (idx >= pkt.data_len) st = ST_CHK;
        break;
    case ST_CHK:
        pkt.checksum = byte; st = ST_HEAD1;
        if (chk == byte) {
            sPktCount++;
            atkp_parse(&pkt);
            return true;
        }
        sChkErrCount++;
        break;
    default:
        st = ST_HEAD1;
        break;
    }
    return false;
}

/* ========================= 公开接口实现 ========================= */

void IMU601_Init(void)
{
    /* 等待 IMU601 模块上电稳定 */
    delay_cycles(3200000U);

    /* 配置陀螺仪/加速度计量程 */
    atkp_write_reg(ATKP_REG_GYRO_FSR, GYRO_FSR_INDEX, 1U);
    delay_cycles(320000U);
    atkp_write_reg(ATKP_REG_ACC_FSR, ACC_FSR_INDEX, 1U);
    delay_cycles(320000U);

    /* 上传姿态帧 + 陀螺仪帧 */
    atkp_write_reg(ATKP_REG_UPSET, 0x0005U, 1U);
    delay_cycles(320000U);
    atkp_write_reg(ATKP_REG_UPRATE, 0x0002U, 1U);
    delay_cycles(320000U);
    atkp_write_reg(ATKP_REG_SAVE, 0U, 1U);

    /* 清空接收缓冲区, 丢弃配置期间的杂数据 */
    while (!DL_UART_Main_isRXFIFOEmpty(UART_0_INST)) {
        (void)DL_UART_Main_receiveData(UART_0_INST);
    }
    sRxHead = 0U;
    sRxTail = 0U;
    sChkErrCount = 0U;
    sOverflowCount = 0U;

    /* 使能 UART0 接收中断 */
    DL_UART_Main_enableInterrupt(UART_0_INST,
        DL_UART_MAIN_INTERRUPT_RX | DL_UART_MAIN_INTERRUPT_RX_TIMEOUT_ERROR);
    NVIC_EnableIRQ(UART_0_INST_INT_IRQN);
}

void IMU601_ParseService(void)
{
    uint8_t byte;
    /* 每次最多解析 64 字节, 避免阻塞过久 */
    uint8_t limit = 64U;
    while (limit-- > 0U && ring_pop(&byte)) {
        (void)atkp_rx_byte(byte);
    }
}

IMU601_Data IMU601_GetData(void)
{
    IMU601_Data copy;
    __disable_irq();
    copy = *(IMU601_Data *)&sData;
    __enable_irq();
    return copy;
}

float IMU601_GetYaw(void)
{
    return sData.angle_deg.z;
}

float IMU601_GetGyroZ(void)
{
    return sData.gyro_dps.z;
}

void IMU601_StartGyroCal(void)
{
    sGyroCalSum.x = 0.0f;
    sGyroCalSum.y = 0.0f;
    sGyroCalSum.z = 0.0f;
    sGyroCalCount = 0U;
    sGyroCalDone = false;
    sGyroCalibrating = true;
}

bool IMU601_IsGyroCalDone(void)
{
    return sGyroCalDone;
}

bool IMU601_IsGyroCalibrating(void)
{
    return sGyroCalibrating;
}

uint32_t IMU601_GetPacketCount(void)
{
    return sPktCount;
}

uint32_t IMU601_GetChecksumErrors(void)
{
    return sChkErrCount;
}
