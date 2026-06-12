/**
 * @file encoder.c
 * @brief 编码器测速实现
 */

#include "encoder.h"
#include "ti_msp_dl_config.h"

/* 编码器引脚定义 */
#define ENC_R_A_IOMUX    IOMUX_PINCM37   /* PA15 */
#define ENC_R_A_PIN      DL_GPIO_PIN_15
#define ENC_R_B_IOMUX    IOMUX_PINCM38   /* PA16 */
#define ENC_R_B_PIN      DL_GPIO_PIN_16
#define ENC_L_A_IOMUX    IOMUX_PINCM39   /* PA17 */
#define ENC_L_A_PIN      DL_GPIO_PIN_17
#define ENC_L_B_IOMUX    IOMUX_PINCM54   /* PA24 */
#define ENC_L_B_PIN      DL_GPIO_PIN_24

/* 边沿计数变量 */
static volatile int16_t g_enc_l_edges = 0;
static volatile int16_t g_enc_r_edges = 0;

void encoder_init(void)
{
    DL_GPIO_initDigitalInputFeatures(ENC_R_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_R_B_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_L_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_L_B_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    DL_GPIO_setLowerPinsPolarity(GPIOA, DL_GPIO_PIN_15_EDGE_RISE_FALL);
    DL_GPIO_setUpperPinsPolarity(GPIOA, DL_GPIO_PIN_17_EDGE_RISE_FALL);

    DL_GPIO_clearInterruptStatus(GPIOA, ENC_R_A_PIN | ENC_L_A_PIN);
    DL_GPIO_enableInterrupt(GPIOA, ENC_R_A_PIN | ENC_L_A_PIN);
    NVIC_EnableIRQ(GPIOA_INT_IRQn);
}

int16_t encoder_left_get(void)
{
    int16_t val;
    __disable_irq();
    val = g_enc_l_edges;
    g_enc_l_edges = 0;
    __enable_irq();
    return (val < 0) ? (int16_t)(-val) : val;
}

int16_t encoder_right_get(void)
{
    int16_t val;
    __disable_irq();
    val = g_enc_r_edges;
    g_enc_r_edges = 0;
    __enable_irq();
    return (val < 0) ? (int16_t)(-val) : val;
}

void GROUP1_IRQHandler(void)
{
    uint32_t status = DL_GPIO_getEnabledInterruptStatus(GPIOA,
        ENC_R_A_PIN | ENC_L_A_PIN);
    if ((status & ENC_R_A_PIN) != 0U) g_enc_r_edges++;
    if ((status & ENC_L_A_PIN) != 0U) g_enc_l_edges++;
    DL_GPIO_clearInterruptStatus(GPIOA, status);
}
