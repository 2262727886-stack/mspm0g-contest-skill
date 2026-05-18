/**
 * MSPM0G3507 25E 拓展板 — K230 UART3 接收 + 控制框架
 * ======================================================
 * SysConfig 外设配置:
 *   UART0: PA0=TX, PA1=RX (CH340调试, 115200)
 *   UART3: PB2=TX, PB3=RX (K230通信, 115200)  ✅ 已验证
 *   I2C0:  PA28=SDA, PA31=SCL (OLED SSD1306, 400kHz)
 *   I2C1:  PA10=SDA, PA11=SCL (MPU6050, 400kHz)
 *   TIMG8: PB15=CH0(PWMA), PB16=CH1(PWMB) (TB6612, 20kHz)
 *   TIMA0: PB8=CH0, PB9=CH1 (舵机, 50Hz)
 *   TIMG7: PA17=CH0(A相), PA24=CH1(B相) (编码器B, QEI)
 *   GPIO:  PA15(A相), PA16(B相) (编码器A, 双边沿中断)
 *   GPIO:  PA13(AIN1), PA12(AIN2), PB0(BIN1), PB1(BIN2) (TB6612方向)
 *   GPIO:  PA8(TRIG), PA9(ECHO) (超声波 HC-SR04)
 *   GPIO:  PB17(蜂鸣器), PB27(LED), PA26(K1), PA25(K2)
 *   ADC0:  8路 TCRT5000 (PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7)
 *   时钟:  SYSOSC 32MHz (默认)
 *   看门狗: 1s
 */

#include "ti_msp_dl_config.h"
#include <stdio.h>
#include <string.h>

/* ============================================================
 * 一、printf 重定向 (UART0 → CH340)
 * ============================================================ */
int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

/* ============================================================
 * 二、系统滴答 1ms
 * ============================================================ */
volatile uint32_t g_ms_ticks = 0;
void SysTick_Handler(void) { g_ms_ticks++; }
void delay_ms(uint32_t ms) {
    uint32_t start = g_ms_ticks;
    while ((g_ms_ticks - start) < ms) { __WFI(); }
}

/* ============================================================
 * 三、K230 UART3 10字节帧接收
 * ============================================================ */
#define FRAME_LEN   10
#define FRAME_HEAD1 0xA5
#define FRAME_HEAD2 0x5A

#define CMD_TARGET  0x01  // 靶心坐标, X/Y=0.1mm
#define CMD_LASER   0x02  // 激光光斑
#define CMD_DEVIATION 0x03 // 偏差
#define CMD_LOST    0x04  // 目标丢失

static uint8_t  rx_buf[FRAME_LEN];
static uint8_t  rx_idx  = 0;
static uint8_t  rx_state = 0;  // 0=等HEAD1, 1=等HEAD2, 2=收数据
static bool     rx_done = false;

typedef struct {
    uint8_t cmd;
    int16_t x_raw;    // 0.1mm
    int16_t y_raw;
    uint16_t extra;
    bool    valid;
} K230_Frame;

static K230_Frame k230 = {0};

/* UART3 中断接收 */
void UART3_INST_IRQHandler(void) {
    uint8_t byte = DL_UART_receiveData(UART3);

    switch (rx_state) {
    case 0:
        if (byte == FRAME_HEAD1) { rx_buf[0] = byte; rx_state = 1; rx_idx = 1; }
        break;
    case 1:
        if (byte == FRAME_HEAD2) { rx_buf[1] = byte; rx_state = 2; rx_idx = 2; }
        else rx_state = 0;
        break;
    case 2:
        rx_buf[rx_idx++] = byte;
        if (rx_idx >= FRAME_LEN) {
            uint8_t cs = 0;
            for (int i = 0; i < 9; i++) cs ^= rx_buf[i];
            if (cs == rx_buf[9]) {
                k230.cmd   = rx_buf[2];
                k230.x_raw = (int16_t)(rx_buf[3] | (rx_buf[4] << 8));
                k230.y_raw = (int16_t)(rx_buf[5] | (rx_buf[6] << 8));
                k230.extra = (uint16_t)(rx_buf[7] | (rx_buf[8] << 8));
                k230.valid = true;
            }
            rx_state = 0;
        }
        break;
    }
}

/* ============================================================
 * 四、电机A编码器 (PA15/PA16 GPIO双边沿中断)
 * ============================================================ */
volatile int32_t enc_a_count = 0;

void GROUP1_IRQHandler(void) {
    uint32_t st = DL_GPIO_getEnabledInterruptStatus(GPIOA,
                    DL_GPIO_PIN_15 | DL_GPIO_PIN_16);
    uint8_t a = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_15) != 0);
    uint8_t b = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16) != 0);

    if (st & DL_GPIO_PIN_15) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_15);
        if (a == b) enc_a_count++; else enc_a_count--;
    }
    if (st & DL_GPIO_PIN_16) {
        DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_16);
        if (a != b) enc_a_count++; else enc_a_count--;
    }
}

/* ============================================================
 * 五、电机B编码器 (TIMG7 QEI)
 * ============================================================ */
int32_t enc_b_read(void) {
    return (int32_t)DL_TimerG_getTimerCount(TIMG7);
}

/* ============================================================
 * 六、TB6612 电机控制
 * ============================================================ */
void motor_init(void) {
    // 方向引脚: PA13=AIN1, PA12=AIN2, PB0=BIN1, PB1=BIN2
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_13 | DL_GPIO_PIN_12);
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0  | DL_GPIO_PIN_1);
}

void motor_forward(void) {
    DL_GPIO_setPins(GPIOA, DL_GPIO_PIN_13);     // AIN1=1
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_12);   // AIN2=0
    DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_0);      // BIN1=1
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);    // BIN2=0
}

void motor_brake(void) {
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_13 | DL_GPIO_PIN_12);
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0  | DL_GPIO_PIN_1);
    DL_TimerG_setCaptureCompareValue(TIMG8, 0, 0);  // PWMA=0
    DL_TimerG_setCaptureCompareValue(TIMG8, 1, 0);  // PWMB=0
}

// left/right: 0.0~1.0 占空比
void motor_set_speed(float left, float right) {
    motor_forward();
    uint32_t period = 4000;  // 20kHz
    DL_TimerG_setCaptureCompareValue(TIMG8, 0, (uint32_t)(left  * period));
    DL_TimerG_setCaptureCompareValue(TIMG8, 1, (uint32_t)(right * period));
}

/* ============================================================
 * 七、舵机控制 (TIMA0, PB8=CH0, PB9=CH1)
 * ============================================================ */
#define SERVO_MIN  625
#define SERVO_MAX  3125

void servo_set(uint8_t ch, uint32_t angle_deg) {  // 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    if (ch == 0) DL_TimerG_setCaptureCompareValue(TIMA0, 0, pulse);  // PB8
    else         DL_TimerG_setCaptureCompareValue(TIMA0, 1, pulse);  // PB9
}

/* ============================================================
 * 八、蜂鸣器 + LED
 * ============================================================ */
#define BEEP_ON()   DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_17)
#define BEEP_OFF()  DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_17)
#define LED_ON()    DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_27)
#define LED_OFF()   DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_27)

void beep(uint32_t ms) { BEEP_ON(); delay_ms(ms); BEEP_OFF(); }

/* ============================================================
 * 九、主函数
 * ============================================================ */
int main(void)
{
    SYSCFG_DL_init();                    // SysConfig 外设初始化
    SysTick_Config(SystemCoreClock / 1000);
    NVIC_EnableIRQ(UART3_INST_INT_IRQN); // 使能K230中断
    __enable_irq();

    printf("\r\n========================================\r\n");
    printf("  MSPM0G3507 25E 拓展板\r\n");
    printf("  UART0(调试):PA0/PA1  UART3(K230):PB2/PB3\r\n");
    printf("  MCLK: %lu Hz\r\n", SystemCoreClock);
    printf("========================================\r\n\r\n");

    motor_init();
    beep(200);  // 启动提示音

    while (1)
    {
        /* ---- 处理 K230 视觉数据 ---- */
        if (k230.valid) {
            k230.valid = false;
            float x_cm = k230.x_raw / 100.0f;
            float y_cm = k230.y_raw / 100.0f;

            switch (k230.cmd) {
            case CMD_TARGET:
                printf("靶心: (%.1f, %.1f)cm r=%d\r\n", x_cm, y_cm, k230.extra);
                // TODO: 更新目标位置 → PID控制云台
                break;
            case CMD_LASER:
                printf("光斑: (%.1f, %.1f)cm\r\n", x_cm, y_cm);
                break;
            case CMD_DEVIATION:
                printf("偏差: dx=%.1f dy=%.1f\r\n", x_cm, y_cm);
                // TODO: 微调云台舵机
                break;
            case CMD_LOST:
                printf("视觉丢失!\r\n");
                break;
            }
        }

        /* ---- 按键 K1 (PA26) ---- */
        if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0) {
            delay_ms(20);
            if (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0) {
                printf("K1 pressed\r\n");
                while (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_26) == 0);
            }
        }

        /* ---- 喂狗 ---- */
        DL_WDT_feed(WDT);
    }
}
