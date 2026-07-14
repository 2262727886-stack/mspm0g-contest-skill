/**
 * imu601.c — 正点原子 ATK-IMU601 驱动实现
 *
 * - 手动初始化 UART0 (PA0=TX, PA1=RX) @ 115200
 * - 中断接收 + 帧解析 (0x55 0x55 协议)
 * - 姿态角提取 (帧ID=0x01, Roll/Pitch/Yaw int16 小端)
 *
 * ⚠️ PA0/PA1 是开漏引脚, 内部弱上拉(~50kΩ)可能不够
 *    稳定通信请补焊 4.7kΩ~10kΩ 外部上拉到 3.3V
 */
#include "imu601.h"
#include "ti_msp_dl_config.h"
#include <ti/devices/msp/msp.h>

/* ========================= UART0 硬件常量 ========================= */

/* IOMUX: PA0=DIO0=IOMUX_PINCM1, PA1=DIO1=IOMUX_PINCM2 (来自 mspm0g350x.h) */
#define IMU_UART_IO_TX    IOMUX_PINCM1_PF_UART0_TX  /* PA0 → UART0_TX, function 2 */
#define IMU_UART_IO_RX    IOMUX_PINCM2_PF_UART0_RX  /* PA1 → UART0_RX, function 2 */

/* 波特率分频: 32,000,000 / (16 × 115200) = 17.361 → IBRD=17, FBRD=23 */
#define IMU_IBRD_32M_115200  (17U)
#define IMU_FBRD_32M_115200  (23U)

/* ========================= 帧协议常量 ========================= */

#define FRAME_HEADER1       0x55U     /* 数据帧 帧头1 */
#define FRAME_HEADER2       0x55U     /* 数据帧 帧头2 (0xAF=指令帧, 暂不处理) */
#define FRAME_ID_ATTITUDE   0x01U     /* 姿态角帧ID (Roll/Pitch/Yaw) */
#define ATTITUDE_DATA_LEN   6U        /* 6字节: RollL RollH PitchL PitchH YawL YawH */
#define MAX_DATA_LEN        32U       /* 最大数据段长度 */

/* 角度换算因子: int16 → 度 (value / 32768 * 180) */
#define ANGLE_SCALE         (180.0f / 32768.0f)

/* ========================= 帧解析状态机 ========================= */

typedef enum {
    STATE_IDLE = 0,   /* 等待 0x55 */
    STATE_H1,         /* 收到第一个 0x55, 等第二个 */
    STATE_ID,         /* 等帧ID */
    STATE_LEN,        /* 等数据长度 */
    STATE_DATA,       /* 读数据字节 */
    STATE_SUM,        /* 等校验和 */
} parse_state_t;

/* ========================= 模块静态变量 ========================= */

static parse_state_t g_state      = STATE_IDLE;
static uint8_t       g_data_buf[MAX_DATA_LEN];  /* 当前帧数据段 */
static uint8_t       g_data_idx;                /* 已读数据字节数 */
static uint8_t       g_data_len;                /* 数据段长度 */
static uint8_t       g_frame_id;                /* 当前帧ID */
static uint8_t       g_csum;                    /* 累加校验和 */

/* 最新解析的姿态角 */
static imu601_attitude_t g_attitude;
static volatile bool     g_data_ready = false;

/* 统计 */
static volatile uint32_t g_frame_count = 0;
static volatile uint32_t g_error_count = 0;
static volatile uint8_t  g_last_frame_id = 0;

/* ========================= 内部: 帧解析 ========================= */

/**
 * 解析单个字节 (在 UART0 ISR 中调用)
 * 状态机自动识别 0x55 0x55 帧头并提取数据
 */
static void imu601_feed_byte(uint8_t byte)
{
    switch (g_state) {

    case STATE_IDLE:
        if (byte == FRAME_HEADER1) {
            g_csum  = byte;       /* 累加帧头1 */
            g_state = STATE_H1;
        }
        break;

    case STATE_H1:
        if (byte == FRAME_HEADER2) {
            /* 数据帧: 0x55 0x55 */
            g_csum += byte;       /* 累加帧头2 */
            g_state = STATE_ID;
        } else {
            /* 非法帧头, 回到 IDLE (0x55 0xAF 指令帧暂不处理) */
            g_state = STATE_IDLE;
        }
        break;

    case STATE_ID:
        g_frame_id = byte;
        g_csum    += byte;
        g_state    = STATE_LEN;
        break;

    case STATE_LEN:
        g_data_len = byte;
        g_csum    += byte;
        g_data_idx = 0;
        if (g_data_len == 0 || g_data_len > MAX_DATA_LEN) {
            /* 长度异常, 丢弃 */
            g_error_count++;
            g_state = STATE_IDLE;
        } else {
            g_state = STATE_DATA;
        }
        break;

    case STATE_DATA:
        g_data_buf[g_data_idx] = byte;
        g_csum                 += byte;
        g_data_idx++;
        if (g_data_idx >= g_data_len) {
            g_state = STATE_SUM;
        }
        break;

    case STATE_SUM: {
        /* 校验和: 帧中除SUM外所有字节之和的低8位 */
        if (g_csum == byte) {
            /* 校验通过 → 按帧ID分发 */
            g_last_frame_id = g_frame_id;
            if (g_frame_id == FRAME_ID_ATTITUDE && g_data_len >= ATTITUDE_DATA_LEN) {
                /* 小端 int16: Roll/Pitch/Yaw */
                int16_t roll_raw  = (int16_t)((g_data_buf[1] << 8) | g_data_buf[0]);
                int16_t pitch_raw = (int16_t)((g_data_buf[3] << 8) | g_data_buf[2]);
                int16_t yaw_raw   = (int16_t)((g_data_buf[5] << 8) | g_data_buf[4]);

                g_attitude.roll  = (float)roll_raw  * ANGLE_SCALE;
                g_attitude.pitch = (float)pitch_raw * ANGLE_SCALE;
                g_attitude.yaw   = (float)yaw_raw   * ANGLE_SCALE;
                g_data_ready     = true;
            }
            g_frame_count++;
        } else {
            g_error_count++;
        }
        g_state = STATE_IDLE;
        break;
    }

    default:
        g_state = STATE_IDLE;
        break;
    }
}

/* ========================= UART0 中断服务 ========================= */

/** 覆写弱定义 Default_Handler → 真正的 UART0 ISR */
void UART0_IRQHandler(void)
{
    uint8_t rx_byte;

    switch (DL_UART_Main_getPendingInterrupt(UART0)) {

    case DL_UART_MAIN_IIDX_RX:
        /* RX FIFO 非空 → 读一个字节喂给解析器 */
        rx_byte = DL_UART_Main_receiveData(UART0);
        imu601_feed_byte(rx_byte);
        break;

    case DL_UART_MAIN_IIDX_RX_TIMEOUT:
        /* 超时: 清标志, 不处理 */
        DL_UART_clearInterruptStatus(UART0, DL_UART_MAIN_IIDX_RX_TIMEOUT);
        break;

    default:
        break;
    }
}

/* ========================= 公开 API ========================= */

/**
 * 初始化 IMU601 通信
 *
 * 执行: UART0 时钟使能 → 引脚配置(PA0/PA1 开漏+内部上拉) → 波特率115200
 *       → RX中断使能 → NVIC使能
 *
 * 注意: 此函数应在 SYSCFG_DL_init() 之后调用
 *       因为 GPIOA 的 reset/power 已在 SYSCFG_DL_initPower() 中完成
 */
void imu601_init(void)
{
    /* ---- 1. UART0 外设复位 + 上电 ---- */
    DL_UART_Main_reset(UART0);
    DL_UART_Main_enablePower(UART0);
    delay_cycles(16);  /* 等待电源稳定 (与 POWER_STARTUP_DELAY 一致) */

    /* ---- 2. 引脚: PA0 → UART0_TX (内置弱上拉, 开漏引脚必需) ---- */
    DL_GPIO_initPeripheralOutputFunctionFeatures(
        IOMUX_PINCM1,                       /* PA0 (IOMUX index 1) */
        IMU_UART_IO_TX,                     /* UART0_TX function */
        DL_GPIO_INVERSION_DISABLE,
        DL_GPIO_RESISTOR_PULL_UP,           /* 内部弱上拉 ~50kΩ */
        DL_GPIO_DRIVE_STRENGTH_HIGH,        /* 高驱动补偿开漏 */
        DL_GPIO_HIZ_DISABLE);               /* 非高阻: 外设驱动引脚 */

    /* ---- 3. 引脚: PA1 → UART0_RX (输入 + 内部弱上拉, 防浮空) ---- */
    DL_GPIO_initPeripheralInputFunctionFeatures(
        IOMUX_PINCM2,                       /* PA1 */
        IMU_UART_IO_RX,                     /* UART0_RX */
        DL_GPIO_INVERSION_DISABLE,
        DL_GPIO_RESISTOR_PULL_UP,           /* 内部弱上拉 ~50kΩ */
        DL_GPIO_HYSTERESIS_DISABLE,
        DL_GPIO_WAKEUP_DISABLE);

    /* ---- 4. UART0 时钟: BUSCLK (32MHz) ---- */
    static const DL_UART_Main_ClockConfig clock_cfg = {
        .clockSel    = DL_UART_MAIN_CLOCK_BUSCLK,
        .divideRatio = DL_UART_MAIN_CLOCK_DIVIDE_RATIO_1,
    };
    DL_UART_Main_setClockConfig(UART0,
        (DL_UART_Main_ClockConfig *)&clock_cfg);

    /* ---- 5. UART0 参数: 115200 8N1 ---- */
    static const DL_UART_Main_Config uart_cfg = {
        .mode        = DL_UART_MAIN_MODE_NORMAL,
        .direction   = DL_UART_MAIN_DIRECTION_TX_RX,
        .flowControl = DL_UART_MAIN_FLOW_CONTROL_NONE,
        .parity      = DL_UART_MAIN_PARITY_NONE,
        .wordLength  = DL_UART_MAIN_WORD_LENGTH_8_BITS,
        .stopBits    = DL_UART_MAIN_STOP_BITS_ONE,
    };
    DL_UART_Main_init(UART0, (DL_UART_Main_Config *)&uart_cfg);

    DL_UART_Main_setOversampling(UART0,
        DL_UART_OVERSAMPLING_RATE_16X);
    DL_UART_Main_setBaudRateDivisor(UART0,
        IMU_IBRD_32M_115200, IMU_FBRD_32M_115200);

    /* ---- 6. 使能 RX 中断 ---- */
    DL_UART_Main_enableInterrupt(UART0,
        DL_UART_MAIN_INTERRUPT_RX);
    NVIC_EnableIRQ(UART0_INT_IRQn);

    /* ---- 7. 使能 UART0 ---- */
    DL_UART_Main_enable(UART0);

    /* 初始化状态机 */
    g_state      = STATE_IDLE;
    g_data_ready = false;
    g_frame_count = 0;
    g_error_count = 0;
}

bool imu601_get_attitude(imu601_attitude_t *att)
{
    if (att == NULL) return false;

    __disable_irq();
    bool ready = g_data_ready;
    if (ready) {
        att->roll  = g_attitude.roll;
        att->pitch = g_attitude.pitch;
        att->yaw   = g_attitude.yaw;
        g_data_ready = false;
    }
    __enable_irq();
    return ready;
}

uint32_t imu601_get_frame_count(void)
{
    return g_frame_count;
}

uint32_t imu601_get_error_count(void)
{
    return g_error_count;
}

uint8_t imu601_get_last_frame_id(void)
{
    return g_last_frame_id;
}
