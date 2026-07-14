/**
 * @file main_servo.c
 * @brief K230视觉追踪 → MSPM0G舵机控制 主程序
 *
 * 系统架构:
 *   K230摄像头(GC2093) → find_blobs检测色块 → UART2发送坐标帧
 *       ↓
 *   MSPM0G UART3(PB2/PB3) → 解析帧 → TIMA0 PWM(PB9/PB8) → 舵机跟踪
 *
 * 显示屏: SSD1306 OLED (I2C0, PA28=SCL, PA31=SDA, 0x3C)
 *   Row 0-1: 标题 + 连接状态
 *   Row 2-3: Pan 角度 + Tilt 角度
 *   Row 4-5: 目标坐标 X/Y (0.1°)
 *   Row 6-7: 帧率 + 丢失指示
 *
 * 指示灯: PB22 板载LED, 收到帧时闪烁
 *
 * 编译: 此文件替代 empty.c 作为主程序入口
 */
#include "ti_msp_dl_config.h"
#include "oled.h"
#include "servo_k230.h"
#include <stdint.h>

/* ================================================================
 * 定时参数
 * ================================================================ */
#define LOOP_DELAY_MS         1U    /* 主循环 1ms */
#define OLED_UPDATE_MS        100U  /* OLED 每100ms刷新 */
#define SERVO_TICK_MS         10U   /* 舵机模块滴答 10ms */

/* ================================================================
 * 前向声明
 * ================================================================ */

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0; i < ms; i++) {
        delay_cycles(CPUCLK_FREQ / 1000U);
    }
}

static void int32_to_str(int32_t value, char *buf)
{
    char tmp[12];
    uint8_t i = 0U, out = 0U;
    int32_t v = value;
    if (v < 0) { buf[out++] = '-'; v = -v; }
    do {
        tmp[i++] = (char)('0' + (uint8_t)(v % 10));
        v /= 10;
    } while (v != 0);
    while (i > 0U) { buf[out++] = tmp[--i]; }
    buf[out] = '\0';
}

static void make_line(char *line, const char *prefix, int32_t value)
{
    uint8_t i = 0U;
    while (*prefix) line[i++] = *prefix++;
    int32_to_str(value, &line[i]);
}

/* ================================================================
 * 主程序
 * ================================================================ */

int main(void)
{
    char line[18];
    int oled_ret;
    uint16_t oled_ms = 0U;
    uint16_t tick_ms = 0U;
    uint8_t  led_state = 0U;
    uint8_t  frames_received = 0U;
    uint8_t  was_lost = 1U;

    /* ---- 初始化 ---- */
    SYSCFG_DL_init();
    __enable_irq();

    oled_ret = OLED_Init();
    ServoK230_Init();

    if (oled_ret == 0) {
        OLED_Clear();
        OLED_Puts(0, 0, "K230 SERVO TRACK");
        OLED_Puts(1, 0, "WAITING K230...");
        OLED_Puts(4, 0, "PB9=PAN PB8=TILT");
        OLED_Puts(5, 0, "PB3=RX<-K230 UART");
    }

    /* LED 初始亮 */
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_22);

    /* ---- 主循环 ---- */
    while (1) {
        /* UART3 轮询: 高频调用, 逐字节处理 */
        int8_t r = ServoK230_Poll();

        if (r == 1) {
            /* 收到新坐标帧: 更新舵机角度 */
            uint16_t pan  = Servo_GetTargetPan();
            uint16_t tilt = Servo_GetTargetTilt();
            Servo_SetPanRaw(pan);
            Servo_SetTiltRaw(tilt);
            frames_received++;

            /* LED 闪烁: 每收到帧翻转一次 */
            led_state = !led_state;
            if (led_state) {
                DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_22);
            } else {
                DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_22);
            }
        } else if (r == -1) {
            /* 急停: 舵机保持当前位置, LED快闪 */
            DL_GPIO_togglePins(GPIOB, DL_GPIO_PIN_22);
        }

        /* 舵机模块滴答 10ms */
        tick_ms++;
        if (tick_ms >= SERVO_TICK_MS) {
            tick_ms = 0U;
            ServoK230_Tick10ms();
        }

        /* OLED 更新 100ms */
        oled_ms++;
        if ((oled_ms >= OLED_UPDATE_MS) && (oled_ret == 0)) {
            oled_ms = 0U;

            uint8_t lost = Servo_IsTargetLost();
            uint16_t pan  = Servo_GetTargetPan();
            uint16_t tilt = Servo_GetTargetTilt();
            uint8_t fps = Servo_GetFrameRate();

            OLED_ClearPage(1);
            if (lost) {
                OLED_Puts(1, 0, "TARGET: LOST");
            } else {
                OLED_Puts(1, 0, "TARGET: LOCKED");
            }

            OLED_ClearPage(2);
            make_line(line, "PAN:", (int32_t)(pan / 10));
            OLED_Puts(2, 0, line);
            make_line(line, "deg", 0);
            OLED_Puts(2, 60, line);

            OLED_ClearPage(3);
            make_line(line, "TILT:", (int32_t)(tilt / 10));
            OLED_Puts(3, 0, line);
            make_line(line, "deg", 0);
            OLED_Puts(3, 60, line);

            OLED_ClearPage(4);
            make_line(line, "X:", (int32_t)pan);
            OLED_Puts(4, 0, line);
            make_line(line, "x0.1", 0);
            OLED_Puts(4, 60, line);

            OLED_ClearPage(5);
            make_line(line, "Y:", (int32_t)tilt);
            OLED_Puts(5, 0, line);
            make_line(line, "x0.1", 0);
            OLED_Puts(5, 60, line);

            OLED_ClearPage(6);
            make_line(line, "FPS:", (int32_t)fps);
            OLED_Puts(6, 0, line);
            make_line(line, "FR:", (int32_t)frames_received);
            OLED_Puts(6, 54, line);

            /* 状态切换时刷新 */
            if (lost != was_lost) {
                was_lost = lost;
                OLED_ClearPage(7);
                if (lost) {
                    OLED_Puts(7, 0, ">> TARGET LOST <<");
                } else {
                    OLED_Puts(7, 0, ">> TRACKING OK  <<");
                }
            }

            /* 无目标超时: LED 常亮 */
            if (lost) {
                DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_22);
            }
        }

        delay_ms(LOOP_DELAY_MS);
    }
}
