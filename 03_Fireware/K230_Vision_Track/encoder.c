/**
 * @file encoder.c
 * @brief Simple quadrature polling decoder.
 */
#include "encoder.h"

typedef struct {
    int16_t count;       /* 本周期增量(边沿计数), 每次 Update 后清零 */
    int16_t latched;     /* 上一周期的增量快照, 即速度值 */
    int32_t position;    /* 累积总脉冲数, 只增不减(方向由符号表示) */
    uint8_t last_a;
    uint8_t last_b;
} EncoderChannel;

static EncoderChannel g_enc_b;

#ifdef GPIO_ENC_A_PORT
static EncoderChannel g_enc_a;

static uint8_t read_a_a(void)
{
    return (DL_GPIO_readPins(GPIO_ENC_A_PORT, GPIO_ENC_A_ENC_A_A_PIN) != 0U) ? 1U : 0U;
}

static uint8_t read_a_b(void)
{
    return (DL_GPIO_readPins(GPIO_ENC_A_PORT, GPIO_ENC_A_ENC_A_B_PIN) != 0U) ? 1U : 0U;
}
#endif

static uint8_t read_b_a(void)
{
    return (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_A_PIN) != 0U) ? 1U : 0U;
}

static uint8_t read_b_b(void)
{
    return (DL_GPIO_readPins(GPIO_ENC_B_PORT, GPIO_ENC_B_ENC_B_B_PIN) != 0U) ? 1U : 0U;
}

static void encoder_channel_init(EncoderChannel *enc, uint8_t a, uint8_t b)
{
    enc->last_a = a;
    enc->last_b = b;
    enc->count = 0;
    enc->latched = 0;
    enc->position = 0;
}

static void encoder_channel_tick(EncoderChannel *enc, uint8_t a, uint8_t b)
{
    if (a != enc->last_a) {
        enc->count += (a == b) ? 1 : -1;
        enc->last_a = a;
    }
    if (b != enc->last_b) {
        enc->count += (a != b) ? 1 : -1;
        enc->last_b = b;
    }
}

static void encoder_channel_update(EncoderChannel *enc)
{
    enc->latched = enc->count;
    enc->position += (int32_t)enc->count;  /* 位置累积: 本次增量加入总位置 */
    enc->count = 0;
}

void Encoder_Init(void)
{
    encoder_channel_init(&g_enc_b, read_b_a(), read_b_b());
#ifdef GPIO_ENC_A_PORT
    encoder_channel_init(&g_enc_a, read_a_a(), read_a_b());
#endif
}

void Encoder_Tick(void)
{
    encoder_channel_tick(&g_enc_b, read_b_a(), read_b_b());
#ifdef GPIO_ENC_A_PORT
    encoder_channel_tick(&g_enc_a, read_a_a(), read_a_b());
#endif
}

void Encoder_Update(void)
{
    encoder_channel_update(&g_enc_b);
#ifdef GPIO_ENC_A_PORT
    encoder_channel_update(&g_enc_a);
#endif
}

uint8_t Encoder_HasA(void)
{
#ifdef GPIO_ENC_A_PORT
    return 1U;
#else
    return 0U;
#endif
}

int16_t Encoder_GetSpeedCountA(void)
{
#ifdef GPIO_ENC_A_PORT
    return g_enc_a.latched;
#else
    return 0;
#endif
}

int16_t Encoder_GetSpeedCountB(void)
{
    return g_enc_b.latched;
}

int16_t Encoder_GetSpeedCount(void)
{
    return Encoder_GetSpeedCountB();
}

/* === 位置读取 (累积总脉冲, int32_t, 不溢出) === */
int32_t Encoder_GetPositionA(void)
{
#ifdef GPIO_ENC_A_PORT
    return g_enc_a.position;
#else
    return 0;
#endif
}

int32_t Encoder_GetPositionB(void)
{
    return g_enc_b.position;
}

/* 位置清零 (启动/停车时复位里程计) */
void Encoder_ResetPosition(void)
{
#ifdef GPIO_ENC_A_PORT
    g_enc_a.position = 0;
#endif
    g_enc_b.position = 0;
}
