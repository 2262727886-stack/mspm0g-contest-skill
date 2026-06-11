#include "encoder.h"
#include "ti_msp_dl_config.h"

/* 编码器 A 相计数。主循环每 20ms 取一次，所以单位是脉冲/20ms。 */
static volatile int16_t g_left_edges;
static volatile int16_t g_right_edges;

#define ENC_RIGHT_A_IOMUX  IOMUX_PINCM37
#define ENC_RIGHT_A_PIN    DL_GPIO_PIN_15
#define ENC_LEFT_A_IOMUX   IOMUX_PINCM39
#define ENC_LEFT_A_PIN     DL_GPIO_PIN_17

void encoder_init(void)
{
    DL_GPIO_initDigitalInputFeatures(ENC_RIGHT_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_LEFT_A_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    DL_GPIO_setLowerPinsPolarity(GPIOA, DL_GPIO_PIN_15_EDGE_RISE_FALL);
    DL_GPIO_setUpperPinsPolarity(GPIOA, DL_GPIO_PIN_17_EDGE_RISE_FALL);

    DL_GPIO_clearInterruptStatus(GPIOA, ENC_RIGHT_A_PIN | ENC_LEFT_A_PIN);
    DL_GPIO_enableInterrupt(GPIOA, ENC_RIGHT_A_PIN | ENC_LEFT_A_PIN);
    NVIC_EnableIRQ(GPIOA_INT_IRQn);
}

void encoder_sample_and_clear(int16_t *left_speed, int16_t *right_speed)
{
    __disable_irq();
    *left_speed = g_left_edges;
    *right_speed = g_right_edges;
    g_left_edges = 0;
    g_right_edges = 0;
    __enable_irq();
}

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
