/**
 * 编码器 — 轮询 + 周期清零
 */
#include "encoder.h"

static int enc_count = 0, enc_latched = 0;
static uint8_t la, lb;

void Encoder_Init(void) {
    la = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_A_PIN) != 0);
    lb = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_B_PIN) != 0);
}

void Encoder_Tick(void) {
    uint8_t a = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_A_PIN) != 0);
    uint8_t b = (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_B_PIN) != 0);
    if (a != la) { enc_count += (a == b) ? 1 : -1; la = a; }
    if (b != lb) { enc_count += (a != b) ? 1 : -1; lb = b; }
}

void Encoder_Update(void) {
    enc_latched = enc_count;
    enc_count = 0;
}

int Encoder_GetCount(void) {
    return enc_latched;
}
