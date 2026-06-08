/**
 * main.c — OLED + MPU6050 DMP 联合测试
 *
 * 硬件: 天猛星 MSPM0G3507, 32MHz
 *   I2C0 OLED:  PA28=SDA, PA31=SCL (0x3C)
 *   I2C1 MPU:   PA10=SDA, PA11=SCL (0x68)
 *
 * ⚠️ PA10/PA11 与板载 CH340 (UART0) 共享!
 *    使用 MPU6050 DMP 期间不可用 printf 调试.
 *    调试信息全部显示在 OLED 上.
 *
 * 测试流程:
 *   1. OLED 显示 "MPU6050 DMP" 标题
 *   2. 初始化 DMP (LED 闪烁 = 进行中, OLED 显示状态)
 *   3. 循环读取姿态角, OLED 实时显示 Pitch / Roll / Yaw
 */

#include "ti_msp_dl_config.h"
#include "oled.h"
#include "mpu_port.h"
#include "delay.h"
#include <stdint.h>
#include <stdio.h>

/* ================================================================
 * 全局变量
 * ================================================================ */
extern volatile uint32_t sys_tick_ms;  /* mpu_port.c 中定义 */

/* ================================================================
 * SysTick 中断 — 每 1ms 触发, 供 DMP 库时间戳
 * ================================================================ */
void SysTick_Handler(void)
{
    sys_tick_ms++;
}

/* ================================================================
 * LED 辅助 (PB22, 低电平亮)
 * ================================================================ */
static void led_on(void)
{
    DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN);
}

static void led_off(void)
{
    DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN);
}

/* ================================================================
 * 浮点数 → 字符串 (用于 OLED 显示, 避免 sprintf 过大)
 *
 * 格式: "XX.X" (整数部分 3 位 + 小数点 + 小数 1 位)
 * 例如: pitch=-45.3 → "-45.3"
 * ================================================================ */
static void ftoa_1d(float val, char *out)
{
    uint8_t pos = 0U;
    uint8_t start = 0U;

    /* 处理负号 */
    if (val < 0.0f) {
        out[pos++] = '-';
        val = -val;
        start = 1U;  /* 数字从索引 1 开始 */
    }

    /* 整数部分 (最多 3 位: 0-180) */
    uint8_t ival = (uint8_t)val;
    uint8_t i100 = ival / 100U;
    uint8_t i10  = (ival / 10U) % 10U;
    uint8_t i1   = ival % 10U;

    /* 百位 (如果 >=100) */
    if (i100 > 0U) {
        out[pos++] = (char)('0' + i100);
    }
    /* 十位 (至少输出 1 位, 负数时补 0) */
    if (i100 > 0U || i10 > 0U || start > 0U) {
        out[pos++] = (char)('0' + i10);
    }
    /* 个位 (始终输出) */
    out[pos++] = (char)('0' + i1);

    /* 小数点 */
    out[pos++] = '.';

    /* 小数 1 位 (四舍五入) */
    float frac_f = (val - (float)ival) * 10.0f + 0.5f;
    uint8_t frac = (uint8_t)frac_f;
    if (frac > 9U) frac = 9U;
    out[pos++] = (char)('0' + frac);

    out[pos] = '\0';
}

/* ================================================================
 * 主程序
 * ================================================================ */
int main(void)
{
    /* ---- 硬件初始化 ---- */
    SYSCFG_DL_init();
    led_on();  /* LED 亮 = 启动中 */

    /* ---- OLED 初始化 ---- */
    int ret = OLED_Init();
    if (ret != 0) {
        /* OLED 失败: LED 快闪 3 次 */
        for (uint8_t i = 0; i < 3; i++) {
            led_off(); delay_ms(150);
            led_on();  delay_ms(150);
        }
        while (1) {}  /* 死循环, 等待复位 */
    }
    OLED_Puts(0, 0, "MPU6050 DMP");
    OLED_Puts(1, 0, "I2C1 PA10/PA11");
    OLED_Puts(2, 0, "Initializing...");
    delay_ms(500);

    /* ---- DMP 初始化 (阻塞重试) ---- */
    int dmp_ret;
    uint8_t retry = 0;
    do {
        dmp_ret = DMP_Init();
        if (dmp_ret == 0) break;

        /* 失败: LED 闪, OLED 显示错误码 */
        led_off();
        char err[20];
        sprintf(err, "DMP ERR:%d R%d", dmp_ret, retry);
        OLED_ClearPage(3);
        OLED_Puts(3, 0, err);
        OLED_Puts(4, 0, "Check I2C1 wire");
        OLED_Puts(5, 0, "PA10=SDA PA11=SCL");
        OLED_Puts(6, 0, "Retrying...");

        delay_ms(500);
        led_on();
        retry++;
    } while (retry < 100);  /* 最多重试 100 次 (~50s) */

    if (dmp_ret != 0) {
        /* 彻底失败 */
        OLED_Clear();
        OLED_Puts(0, 0, "DMP FAILED!");
        OLED_Puts(1, 0, "Check:");
        OLED_Puts(2, 0, "1.MPU6050 power");
        OLED_Puts(3, 0, "2.PA10/PA11 wire");
        OLED_Puts(4, 0, "3.Addr=0x68");
        while (1) {
            led_off(); delay_ms(200);
            led_on();  delay_ms(200);
        }
    }

    /* ---- DMP 就绪 ---- */
    led_off();
    OLED_Clear();
    OLED_Puts(0, 0, "MPU6050 DMP OK");
    OLED_Puts(1, 0, "P:");
    OLED_Puts(2, 0, "R:");
    OLED_Puts(3, 0, "Y:");
    OLED_Puts(7, 0, "Press reset->");

    /* ---- 主循环: 读取并显示姿态角 ---- */
    float pitch = 0.0f, roll = 0.0f, yaw = 0.0f;
    char  str[10];
    uint16_t loop_cnt = 0;

    while (1) {
        /* 尝试读取 DMP 数据 (非阻塞) */
        if (DMP_Read_Data(&pitch, &roll, &yaw) == 0) {
            /* 更新 OLED (只更新数值部分, 标签不动) */
            ftoa_1d(pitch, str);
            OLED_Puts(1, 20, str);

            ftoa_1d(roll, str);
            OLED_Puts(2, 20, str);

            ftoa_1d(yaw, str);
            OLED_Puts(3, 20, str);

            /* LED 随数据更新闪烁 */
            loop_cnt++;
            if (loop_cnt == 0U) {  /* 每 256 次约 2.5s */
                led_on();
                delay_cycles(CPUCLK_FREQ / 100U);  /* 10ms 脉冲 */
                led_off();
            }
        }

        /* 喂看门狗 (如果使能) */
        /* DL_WDTCLR_clearCounter(); */
    }
}
