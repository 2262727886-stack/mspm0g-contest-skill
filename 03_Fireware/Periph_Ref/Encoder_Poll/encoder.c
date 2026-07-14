/**
 * 编码器B — 高速轮询模式 (不依赖中断)
 * PA17(A相) PA24(B相), 主循环全速采样
 */
#include "encoder.h"

static volatile int32_t enc_count = 0;
static uint8_t last_a = 0, last_b = 0;

void Encoder_Init(void) {
    last_a = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_A_PIN) != 0);
    last_b = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_B_PIN) != 0);
}

int32_t Encoder_Read(void) {
    return enc_count;
}

void Encoder_Tick(void) {
    uint8_t a = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_A_PIN) != 0);
    uint8_t b = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_B_PIN) != 0);
    if (a != last_a) {
        enc_count += (a == b) ? 1 : -1;
        last_a = a;
    }
    if (b != last_b) {
        enc_count += (a != b) ? 1 : -1;
        last_b = b;
    }
}
