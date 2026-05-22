#include "ti_msp_dl_config.h"
#include "gimbal.h"
#include "oled.h"
#include <stdint.h>

#define FRAME_HEAD1          0xFFU
#define FRAME_HEAD2          0xFEU
#define K230_FRAME8_LEN      8U
#define RX_BYTE_LED_MS       5U
#define VALID_FRAME_LED_MS   200U
#define OLED_REFRESH_MS      1000U

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0U; i < ms; i++) {
        delay_cycles(CPUCLK_FREQ / 1000U);
    }
}

static void led_on(void)
{
    DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN);
}

static void led_off(void)
{
    DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN);
}

static char hex_digit(uint8_t v)
{
    v &= 0x0FU;
    return (v < 10U) ? (char)('0' + v) : (char)('A' + v - 10U);
}

static void hex8(uint8_t v, char *out)
{
    out[0] = hex_digit((uint8_t)(v >> 4));
    out[1] = hex_digit(v);
    out[2] = '\0';
}

static void u32_to_dec(uint32_t v, char *out)
{
    char tmp[10];
    uint8_t n = 0U;

    if (v == 0U) {
        out[0] = '0';
        out[1] = '\0';
        return;
    }

    while ((v > 0U) && (n < sizeof(tmp))) {
        tmp[n++] = (char)('0' + (v % 10U));
        v /= 10U;
    }

    for (uint8_t i = 0U; i < n; i++) {
        out[i] = tmp[n - 1U - i];
    }
    out[n] = '\0';
}

static void oled_put_u32(uint8_t page, const char *label, uint32_t value)
{
    char line[22];
    char num[11];
    uint8_t i = 0U;
    uint8_t j = 0U;

    while ((label[j] != '\0') && (i < sizeof(line) - 1U)) {
        line[i++] = label[j++];
    }

    u32_to_dec(value, num);
    j = 0U;
    while ((num[j] != '\0') && (i < sizeof(line) - 1U)) {
        line[i++] = num[j++];
    }
    line[i] = '\0';

    OLED_ClearPage(page);
    OLED_Puts(page, 0U, line);
}

static void oled_update(uint32_t rx_count, uint32_t head_count,
                        uint32_t frame_count, uint32_t bcc_ok,
                        uint32_t bcc_err, uint8_t pan, uint8_t tilt,
                        const uint8_t *raw, uint8_t raw_pos, uint8_t state)
{
    char line[22];
    char hx[3];

    oled_put_u32(0U, "RX:", rx_count);
    oled_put_u32(1U, "HEAD:", head_count);
    oled_put_u32(2U, "FRAME:", frame_count);
    oled_put_u32(3U, "OK:", bcc_ok);
    oled_put_u32(4U, "ERR:", bcc_err);

    {
        char num[11];
        uint8_t i = 0U;
        uint8_t j = 0U;
        line[i++] = 'P';
        line[i++] = ':';
        u32_to_dec(pan, num);
        while ((num[j] != '\0') && (i < sizeof(line) - 1U)) line[i++] = num[j++];
        line[i++] = ' ';
        line[i++] = 'T';
        line[i++] = ':';
        u32_to_dec(tilt, num);
        j = 0U;
        while ((num[j] != '\0') && (i < sizeof(line) - 1U)) line[i++] = num[j++];
        line[i] = '\0';
    }
    OLED_ClearPage(5U);
    OLED_Puts(5U, 0U, line);

    line[0] = 'R'; line[1] = ':';
    {
        uint8_t i = 2U;
        for (uint8_t n = 0U; n < 4U; n++) {
            uint8_t idx = (uint8_t)((raw_pos + n) & 0x07U);
            hex8(raw[idx], hx);
            line[i++] = hx[0];
            line[i++] = hx[1];
            if (n != 3U) line[i++] = ' ';
        }
        line[i] = '\0';
    }
    OLED_ClearPage(6U);
    OLED_Puts(6U, 0U, line);

    line[0] = 'R'; line[1] = ':';
    {
        uint8_t i = 2U;
        for (uint8_t n = 4U; n < 8U; n++) {
            uint8_t idx = (uint8_t)((raw_pos + n) & 0x07U);
            hex8(raw[idx], hx);
            line[i++] = hx[0];
            line[i++] = hx[1];
            if (n != 7U) line[i++] = ' ';
        }
        line[i++] = ' ';
        line[i++] = 'S';
        line[i++] = ':';
        line[i++] = (char)('0' + state);
        line[i] = '\0';
    }
    OLED_ClearPage(7U);
    OLED_Puts(7U, 0U, line);
}

static void gimbal_self_test(void)
{
    led_on();
    Gimbal_SetPan(90U);
    Gimbal_SetTilt(60U);
    delay_ms(700U);

    Gimbal_SetPan(180U);
    Gimbal_SetTilt(120U);
    delay_ms(700U);

    Gimbal_SetPan(135U);
    Gimbal_SetTilt(90U);
    delay_ms(700U);
    led_off();
}

int main(void)
{
    uint8_t rx_state = 0U;
    uint8_t rx_idx = 0U;
    uint8_t rx_buf[K230_FRAME8_LEN];
    uint16_t led_timer = 0U;
    uint16_t oled_timer = 0U;
    uint32_t rx_count = 0U;
    uint32_t head_count = 0U;
    uint32_t frame_count = 0U;
    uint32_t bcc_ok = 0U;
    uint32_t bcc_err = 0U;
    uint8_t last_pan = 135U;
    uint8_t last_tilt = 90U;
    uint8_t raw[8] = {0};
    uint8_t raw_pos = 0U;

    SYSCFG_DL_init();
    DL_GPIO_setDigitalInternalResistor(GPIO_UART_K230_IOMUX_RX, DL_GPIO_RESISTOR_PULL_UP);

    Gimbal_Init();
    (void)OLED_Init();
    OLED_Puts(0U, 0U, "K230 OLED DBG");
    OLED_Puts(1U, 0U, "RX PB3 115200");
    gimbal_self_test();

    while (1) {
        while (!DL_UART_Main_isRXFIFOEmpty(UART_K230_INST)) {
            uint8_t b = DL_UART_Main_receiveData(UART_K230_INST);
            rx_count++;
            raw[raw_pos] = b;
            raw_pos = (uint8_t)((raw_pos + 1U) & 0x07U);

            if (led_timer < RX_BYTE_LED_MS) {
                led_timer = RX_BYTE_LED_MS;
            }

            switch (rx_state) {
            case 0U:
                if (b == FRAME_HEAD1) {
                    rx_buf[0] = b;
                    rx_state = 1U;
                }
                break;

            case 1U:
                if (b == FRAME_HEAD2) {
                    rx_buf[1] = b;
                    rx_idx = 2U;
                    rx_state = 2U;
                    head_count++;
                } else if (b == FRAME_HEAD1) {
                    rx_buf[0] = b;
                } else {
                    rx_state = 0U;
                }
                break;

            case 2U:
                rx_buf[rx_idx++] = b;
                if (rx_idx == 4U) {
                    last_pan = rx_buf[2];
                    last_tilt = rx_buf[3];
                    Gimbal_SetPan(last_pan);
                    Gimbal_SetTilt(last_tilt);
                    frame_count++;
                    led_timer = VALID_FRAME_LED_MS;
                }

                if (rx_idx >= K230_FRAME8_LEN) {
                    uint8_t bcc = 0U;
                    for (uint8_t i = 0U; i < (K230_FRAME8_LEN - 1U); i++) {
                        bcc ^= rx_buf[i];
                    }
                    if (bcc == rx_buf[7]) {
                        bcc_ok++;
                    } else {
                        bcc_err++;
                    }
                    rx_state = 0U;
                }

                if (b == FRAME_HEAD1) {
                    rx_buf[0] = b;
                    rx_state = 1U;
                    rx_idx = 1U;
                }
                break;

            default:
                rx_state = 0U;
                break;
            }
        }

        if (led_timer > 0U) {
            led_on();
            led_timer--;
        } else {
            led_off();
        }

        if (oled_timer >= OLED_REFRESH_MS) {
            oled_timer = 0U;
            oled_update(rx_count, head_count, frame_count, bcc_ok, bcc_err,
                        last_pan, last_tilt, raw, raw_pos, rx_state);
        } else {
            oled_timer++;
        }

        delay_ms(1U);
    }
}
