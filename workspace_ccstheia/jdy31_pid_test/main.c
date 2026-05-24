/**
 * main.c — JDY-31 蓝牙 PID 调参 最小测试单元
 *
 * 硬件: MSPM0G3507 + JDY-31 (UART1 PB6/PB7) + OLED (I2C0 PA28/PA31)
 *
 * 功能:
 *   1. UART1 9600 收发 — 上位机(PC蓝牙/手机)发PID命令
 *   2. OLED 实时回显 — 收到的命令 + PID参数值
 *   3. 蓝牙回声 — 把收到的命令原样发回, 确认通信正常
 *   4. 按键:
 *        PA25: 发送测试帧 "P5\r\n" (设Kp=0.5)
 *        PA26: 发送测试帧 "I8\r\n" (设Ki=0.08)
 *
 * PID 命令格式 (与串口调参完全一致):
 *   P5  = Kp = 0.5   (值÷10)
 *   I8  = Ki = 0.08  (值÷100)
 *   D5  = Kd = 0.05  (值÷100)
 *   T42 = 目标速度 42 (编码器脉冲/周期)
 *   B800= 前馈PWM 800
 *   回车 = 自动回显确认
 *
 * JDY-31 接线:
 *   JDY-31 TXD → PB7 (M0G UART1_RX)
 *   JDY-31 RXD → PB6 (M0G UART1_TX)
 *   JDY-31 VCC → 3.3V
 *   JDY-31 GND → GND
 *   JDY-31 STATE → PA14 (可选, 高=已连接)
 *
 * JDY-31 V1.3 AT 预设 (默认9600, 直接用不配AT):
 *   1. 出厂默认 9600 8N1, 密码1234, 名称JDY-31-SPP
 *   2. 如需改名: AT+NAME小车主控     (最长18字节)
 *   3. 如需关状态日志: AT+ENLOG0     (推荐, 避免连接时乱码)
 *   4. 串口助手/蓝牙COM口 9600 8N1 即可通信
 */

#include "ti_msp_dl_config.h"
#include "oled.h"
#include "delay.h"
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* ========================= 外设引用 ========================= */
#define BT_UART            UART_JDY31_INST
#define BT_BAUD            9600U

/* ========================= PID 参数 (全局, 蓝牙实时修改) ========================= */
float    g_kp       = 2.5f;    /* Kp ×0.1 → 实际值0.25 (发送P25=2.5) */
float    g_ki       = 0.08f;   /* Ki ×0.01 → 实际值0.0008 (发送I8=0.08) */
float    g_kd       = 0.0f;    /* Kd ×0.01 */
int16_t  g_target   = 42;      /* 目标速度 (编码器脉冲/周期) */
int16_t  g_base_pwm = 800;     /* 前馈 PWM 占空比 */

/* ========================= 接收缓冲区 ========================= */
#define RX_BUF_SIZE   64
static char   rx_buf[RX_BUF_SIZE];
static uint8_t rx_idx = 0;

/* 上次收到的完整命令行 (用于 OLED 显示) */
static char   last_cmd[32];
static bool   cmd_updated = false;

/* LED 状态 (PB22) */
static bool   led_on = false;

/* ========================= 按键读取 ========================= */
static bool button_pressed(uint32_t port, uint32_t pin)
{
    return (DL_GPIO_readPins((GPIO_Regs *)port, pin) == 0U);
}

/* ========================= 蓝牙 UART 底层 ========================= */

/* 发送单字节 (阻塞) */
static void bt_tx_byte(char c)
{
    while (DL_UART_isTXFIFOFull(BT_UART));
    DL_UART_Main_transmitData(BT_UART, (uint8_t)c);
}

/* 发送字符串 */
static void bt_tx_str(const char *s)
{
    while (*s) bt_tx_byte(*s++);
}

/* 发送整数 + 换行 */
static void bt_tx_intln(const char *label, int16_t val)
{
    char buf[24];
    int len = sprintf(buf, "%s%d\r\n", label, val);
    for (int i = 0; i < len; i++) bt_tx_byte(buf[i]);
}

/* 发送确认帧 (回显当前所有参数) */
static void bt_tx_ack(void)
{
    char buf[64];
    int len = sprintf(buf,
        "P%d I%d D%d T%d B%d\r\n",
        (int)(g_kp * 10.0f + 0.5f),
        (int)(g_ki * 100.0f + 0.5f),
        (int)(g_kd * 100.0f + 0.5f),
        g_target, g_base_pwm);
    for (int i = 0; i < len; i++) bt_tx_byte(buf[i]);
}

/* ========================= PID 命令解析 ========================= */

/* 解析蓝牙命令 (与串口调参协议完全一致) */
static void bt_parse_cmd(const char *cmd, int len)
{
    static int  value = 0;
    static int  mode  = 0;  /* 0=none 1=P 2=I 3=D 4=T 5=B */

    for (int i = 0; i < len; i++) {
        char c = cmd[i];

        /* 收到回车/换行 → 确认并回显 */
        if (c == '\r' || c == '\n') {
            if (mode != 0) {
                /* 应用参数 */
                if (mode == 1) {
                    g_kp = (float)value / 10.0f;
                } else if (mode == 2) {
                    g_ki = (float)value / 100.0f;
                } else if (mode == 3) {
                    g_kd = (float)value / 100.0f;
                } else if (mode == 4) {
                    g_target = (int16_t)value;
                } else if (mode == 5) {
                    g_base_pwm = (int16_t)value;
                }

                /* 通过蓝牙回显确认 */
                bt_tx_ack();

                mode  = 0;
                value = 0;
            }
            continue;
        }

        /* 命令头 */
        if (c == 'P' || c == 'p') { mode = 1; value = 0; }
        else if (c == 'I' || c == 'i') { mode = 2; value = 0; }
        else if (c == 'D' || c == 'd') { mode = 3; value = 0; }
        else if (c == 'T' || c == 't') { mode = 4; value = 0; }
        else if (c == 'B' || c == 'b') { mode = 5; value = 0; }
        /* 数字累加 */
        else if (c >= '0' && c <= '9') {
            value = value * 10 + (c - '0');
        }
    }
}

/* ========================= OLED 显示 ========================= */

/* 刷新 OLED (调用开销小, 放在主循环) */
static void oled_update(void)
{
    char text[22];

    /* 第0行: 标题 */
    OLED_ClearPage(0);
    OLED_Puts(0, 0, "JDY31 BT PID TEST");

    /* 第1行: 蓝牙状态 + LED */
    OLED_ClearPage(1);
    OLED_Puts(1, 0, led_on ? "RX:ON " : "RX:   ");

    /* 第2-3行: 最近收到的命令 */
    OLED_ClearPage(2);
    OLED_Puts(2, 0, "CMD:");
    if (cmd_updated) {
        OLED_Puts(2, 30, last_cmd);
    }

    /* 第4-6行: 当前 PID 参数 */
    OLED_ClearPage(4);
    sprintf(text, "P=%.1f I=%.2f", (double)g_kp, (double)g_ki);
    OLED_Puts(4, 0, text);

    OLED_ClearPage(5);
    sprintf(text, "D=%.2f T=%d", (double)g_kd, g_target);
    OLED_Puts(5, 0, text);

    OLED_ClearPage(6);
    sprintf(text, "BASE=%d", g_base_pwm);
    OLED_Puts(6, 0, text);

    /* 第7行: 操作提示 */
    OLED_ClearPage(7);
    OLED_Puts(7, 0, "PA25:P5 PA26:I8");
}

/* ========================= 主程序 ========================= */

int main(void)
{
    /* SysConfig 初始化: 时钟 GPIO I2C UART */
    SYSCFG_DL_init();

    /* 按键上拉 */
    DL_GPIO_initDigitalInputFeatures(CAL_KEY_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(START_BTN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_DISABLE, DL_GPIO_WAKEUP_DISABLE);

    /* OLED 初始化 */
    OLED_Init();
    OLED_Clear();
    OLED_Puts(0, 0, "JDY31 BT INIT...");
    OLED_Puts(1, 0, "UART1 9600");

    /* LED 初始状态: 亮起表示上电 */
    DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN);
    delay_ms(500);
    DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN);

    /* 上电问候帧 → 蓝牙 (上位机看到表示通信OK) */
    bt_tx_str("JDY31 PID Ready\r\n");
    bt_tx_str("CMD: Px Ix Dx Tx Bx\r\n");
    bt_tx_ack();

    OLED_Clear();
    oled_update();

    /* 按键边沿检测 */
    bool last_pa25 = false;
    bool last_pa26 = false;

    /* 主循环 */
    while (1) {
        /* ---- 蓝牙接收 ---- */
        bool rx_activity = false;
        while (!DL_UART_isRXFIFOEmpty(BT_UART)) {
            rx_activity = true;
            char c = (char)DL_UART_Main_receiveData(BT_UART);

            /* 缓存到行缓冲区 */
            if (rx_idx < RX_BUF_SIZE - 1) {
                rx_buf[rx_idx++] = c;
                rx_buf[rx_idx] = '\0';

                /* 遇到换行 → 解析本条命令 */
                if (c == '\n' || c == '\r') {
                    /* 保存到显示缓冲 */
                    int copy_len = (rx_idx < 31) ? rx_idx : 30;
                    memcpy(last_cmd, rx_buf, copy_len);
                    last_cmd[copy_len] = '\0';
                    cmd_updated = true;

                    /* 解析PID命令 */
                    bt_parse_cmd(rx_buf, rx_idx);
                    rx_idx = 0;
                }
            } else {
                /* 缓冲区满 → 丢弃并重置 */
                rx_idx = 0;
            }

            /* 回声: 收什么发什么 (方便串口助手验证) */
            bt_tx_byte(c);
        }

        /* LED 跟随 RX 活动 (有数据时闪烁) */
        if (rx_activity) {
            led_on = !led_on;
            if (led_on) DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN);
            else        DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN);
        }

        /* ---- 按键 PA25: 发送 P5 (Kp=0.5) ---- */
        bool pa25 = button_pressed((uint32_t)START_PORT, START_BTN_PIN);
        if (!last_pa25 && pa25) {
            bt_tx_str("P5\r\n");
            g_kp = 0.5f;
            bt_tx_ack();
        }
        last_pa25 = pa25;

        /* ---- 按键 PA26: 发送 I8 (Ki=0.08) ---- */
        bool pa26 = button_pressed((uint32_t)CAL_PORT, CAL_KEY_PIN);
        if (!last_pa26 && pa26) {
            bt_tx_str("I8\r\n");
            g_ki = 0.08f;
            bt_tx_ack();
        }
        last_pa26 = pa26;

        /* ---- OLED 刷新 (约 5Hz) ---- */
        static uint8_t oled_div = 0;
        if (++oled_div >= 200U) {  /* 200 × 10ms = 2s 刷新一次 */
            oled_div = 0;
            oled_update();
            cmd_updated = false;
        }

        delay_ms(10);
    }
}
