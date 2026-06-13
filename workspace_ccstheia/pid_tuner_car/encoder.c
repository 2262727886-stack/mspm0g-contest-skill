/**
 * encoder.c — 霍尔编码器实现
 *
 * 编码器 A 相双边沿中断计数:
 *   PA15 (右轮): 上升沿 + 下降沿都计数 → 2 倍频
 *   PA17 (左轮): 上升沿 + 下降沿都计数 → 2 倍频
 *
 * 中断服务函数: GROUP1_IRQHandler (GPIOA/GPIOB 共用)
 *   只处理 PA15 和 PA17, 其他 GPIO 中断不在此使用
 */
#include "encoder.h"
#include "ti_msp_dl_config.h"

/* 编码器边沿计数 (中断写, 主循环读+清零) */
static volatile int16_t g_left_edges;
static volatile int16_t g_right_edges;

/* 编码器引脚定义 */
#define ENC_RIGHT_A_IOMUX  IOMUX_PINCM37   /* PA15 = 右轮 A 相 */
#define ENC_RIGHT_A_PIN    DL_GPIO_PIN_15
#define ENC_LEFT_A_IOMUX   IOMUX_PINCM39   /* PA17 = 左轮 A 相 */
#define ENC_LEFT_A_PIN     DL_GPIO_PIN_17

/**
 * 初始化编码器:
 *   1. 配置 PA15/PA17 为上拉输入 + 滞回
 *   2. 设置双边沿触发
 *   3. 使能 GPIOA GROUP1 中断
 */
void encoder_init(void)
{
    /* 右轮 A 相 (PA15) */
    DL_GPIO_initDigitalInputFeatures(ENC_RIGHT_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    /* 左轮 A 相 (PA17) */
    DL_GPIO_initDigitalInputFeatures(ENC_LEFT_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    /* 双边沿触发: 上升沿 + 下降沿都产生中断 */
    DL_GPIO_setLowerPinsPolarity(GPIOA, DL_GPIO_PIN_15_EDGE_RISE_FALL);
    DL_GPIO_setUpperPinsPolarity(GPIOA, DL_GPIO_PIN_17_EDGE_RISE_FALL);

    /* 清除中断标志, 使能中断 */
    DL_GPIO_clearInterruptStatus(GPIOA, ENC_RIGHT_A_PIN | ENC_LEFT_A_PIN);
    DL_GPIO_enableInterrupt(GPIOA, ENC_RIGHT_A_PIN | ENC_LEFT_A_PIN);
    NVIC_EnableIRQ(GPIOA_INT_IRQn);
}

/**
 * 读取编码器计数并清零 (原子操作)
 *
 * 在主循环每 20ms 调用一次:
 *   __disable_irq();
 *   *left_speed = g_left_edges;   // 读取
 *   g_left_edges = 0;             // 清零
 *   __enable_irq();
 */
void encoder_sample_and_clear(int16_t *left_speed, int16_t *right_speed)
{
    __disable_irq();
    *left_speed = g_left_edges;
    *right_speed = g_right_edges;
    g_left_edges = 0;
    g_right_edges = 0;
    __enable_irq();
}

/**
 * GPIOA GROUP1 中断服务函数
 *
 * PA15 和 PA17 共用此中断向量。
 * 只做 g_xxx_edges++, 不调用任何函数 (保持 ISR 短小)。
 */
void GROUP1_IRQHandler(void)
{
    uint32_t status = DL_GPIO_getEnabledInterruptStatus(GPIOA,
        ENC_RIGHT_A_PIN | ENC_LEFT_A_PIN);

    if ((status & ENC_RIGHT_A_PIN) != 0U) {
        g_right_edges++;
    }
    if ((status & ENC_LEFT_A_PIN) != 0U) {
        g_left_edges++;
    }

    DL_GPIO_clearInterruptStatus(GPIOA, status);
}
