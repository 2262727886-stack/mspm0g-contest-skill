/**
 * @file oled.c
 * @brief SSD1306 128x64 OLED driver for Tianmengxing I2C OLED header.
 *
 * Wiring:
 *   OLED SDA -> PA28 / I2C0_SDA
 *   OLED SCL -> PA31 / I2C0_SCL
 *   OLED address -> 0x3C
 */
#include "oled.h"
#include "i2c_utils.h"

#define OLED_I2C     I2C_OLED_INST
#define OLED_ADDR    0x3CU
#define OLED_PAGES   8U
#define OLED_WIDTH   128U
#define OLED_ASYNC_CHARS 16U
#define OLED_ASYNC_BYTES (OLED_ASYNC_CHARS * 6U)

typedef enum {
    OLED_ASYNC_IDLE,
    OLED_ASYNC_CMD_PAGE,
    OLED_ASYNC_CMD_COL_LOW,
    OLED_ASYNC_CMD_COL_HIGH,
    OLED_ASYNC_DATA
} OLED_AsyncState;

static char gOledLines[OLED_PAGES][OLED_ASYNC_CHARS + 1U];
static uint8_t gOledDirtyMask;
static uint8_t gOledAsyncPage;
static uint8_t gOledAsyncOffset;
static uint8_t gOledAsyncData[OLED_ASYNC_BYTES];
static OLED_AsyncState gOledAsyncState = OLED_ASYNC_IDLE;

static int oled_cmd(uint8_t cmd)
{
    uint8_t buf[2] = {0x00U, cmd};
    return i2c_write_bytes(OLED_I2C, OLED_ADDR, buf, sizeof(buf));
}

static int oled_cmd_async(uint8_t cmd)
{
    uint8_t buf[2] = {0x00U, cmd};
    return i2c_try_write_bytes(OLED_I2C, OLED_ADDR, buf, sizeof(buf));
}

static int oled_data_async(const uint8_t *data, uint8_t len)
{
    uint8_t buf[8];

    if (len > 7U) {
        len = 7U;
    }

    buf[0] = 0x40U;
    for (uint8_t i = 0; i < len; i++) {
        buf[i + 1U] = data[i];
    }

    return i2c_try_write_bytes(OLED_I2C, OLED_ADDR, buf, (uint8_t) (len + 1U));
}

static int oled_data(const uint8_t *data, uint8_t len)
{
    uint8_t buf[8];
    uint8_t offset = 0U;

    while (offset < len) {
        uint8_t chunk = (uint8_t) (len - offset);
        if (chunk > 7U) {
            chunk = 7U;
        }

        buf[0] = 0x40U;
        for (uint8_t i = 0; i < chunk; i++) {
            buf[i + 1U] = data[offset + i];
        }

        int ret = i2c_write_bytes(OLED_I2C, OLED_ADDR, buf, (uint8_t) (chunk + 1U));
        if (ret != 0) {
            return ret;
        }
        offset = (uint8_t) (offset + chunk);
    }

    return 0;
}

static void oled_set_pos(uint8_t page, uint8_t col)
{
    oled_cmd((uint8_t) (0xB0U | (page & 0x07U)));
    oled_cmd((uint8_t) (0x00U | (col & 0x0FU)));
    oled_cmd((uint8_t) (0x10U | (col >> 4)));
}

void OLED_ClearPage(uint8_t page)
{
    static const uint8_t zero[16] = {0};

    if (page >= OLED_PAGES) {
        return;
    }

    oled_set_pos(page, 0U);
    for (uint8_t i = 0; i < (OLED_WIDTH / 16U); i++) {
        oled_data(zero, sizeof(zero));
    }
}

void OLED_Clear(void)
{
    for (uint8_t page = 0; page < OLED_PAGES; page++) {
        OLED_ClearPage(page);
    }
}

static const uint8_t *font5x7(char c)
{
    static const uint8_t blank[5] = {0x00, 0x00, 0x00, 0x00, 0x00};
    static const uint8_t colon[5] = {0x00, 0x36, 0x36, 0x00, 0x00};
    static const uint8_t minus[5] = {0x08, 0x08, 0x08, 0x08, 0x08};
    static const uint8_t dot[5]   = {0x00, 0x30, 0x30, 0x00, 0x00};
    static const uint8_t slash[5] = {0x40, 0x20, 0x10, 0x08, 0x04};
    static const uint8_t digits[10][5] = {
        {0x3E,0x51,0x49,0x45,0x3E}, {0x00,0x42,0x7F,0x40,0x00},
        {0x42,0x61,0x51,0x49,0x46}, {0x21,0x41,0x45,0x4B,0x31},
        {0x18,0x14,0x12,0x7F,0x10}, {0x27,0x45,0x45,0x45,0x39},
        {0x3C,0x4A,0x49,0x49,0x30}, {0x01,0x71,0x09,0x05,0x03},
        {0x36,0x49,0x49,0x49,0x36}, {0x06,0x49,0x49,0x29,0x1E},
    };
    static const uint8_t letters[26][5] = {
        {0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},
        {0x3E,0x41,0x41,0x41,0x22},{0x7F,0x41,0x41,0x22,0x1C},
        {0x7F,0x49,0x49,0x49,0x41},{0x7F,0x09,0x09,0x09,0x01},
        {0x3E,0x41,0x49,0x49,0x7A},{0x7F,0x08,0x08,0x08,0x7F},
        {0x00,0x41,0x7F,0x41,0x00},{0x20,0x40,0x41,0x3F,0x01},
        {0x7F,0x08,0x14,0x22,0x41},{0x7F,0x40,0x40,0x40,0x40},
        {0x7F,0x02,0x0C,0x02,0x7F},{0x7F,0x04,0x08,0x10,0x7F},
        {0x3E,0x41,0x41,0x41,0x3E},{0x7F,0x09,0x09,0x09,0x06},
        {0x3E,0x41,0x51,0x21,0x5E},{0x7F,0x09,0x19,0x29,0x46},
        {0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7F,0x01,0x01},
        {0x3F,0x40,0x40,0x40,0x3F},{0x1F,0x20,0x40,0x20,0x1F},
        {0x7F,0x20,0x18,0x20,0x7F},{0x63,0x14,0x08,0x14,0x63},
        {0x07,0x08,0x70,0x08,0x07},{0x61,0x51,0x49,0x45,0x43},
    };

    if ((c >= '0') && (c <= '9')) return digits[c - '0'];
    if ((c >= 'A') && (c <= 'Z')) return letters[c - 'A'];
    if ((c >= 'a') && (c <= 'z')) return letters[c - 'a'];
    if (c == ':') return colon;
    if (c == '-') return minus;
    if (c == '.') return dot;
    if (c == '/') return slash;
    return blank;
}

void OLED_Puts(uint8_t page, uint8_t col, const char *s)
{
    if ((page >= OLED_PAGES) || (col >= OLED_WIDTH) || (s == 0)) {
        return;
    }

    oled_set_pos(page, col);
    while ((*s != '\0') && (col <= (OLED_WIDTH - 6U))) {
        uint8_t out[6];
        const uint8_t *glyph = font5x7(*s++);

        for (uint8_t i = 0; i < 5U; i++) {
            out[i] = glyph[i];
        }
        out[5] = 0x00U;
        oled_data(out, sizeof(out));
        col = (uint8_t) (col + 6U);
    }
}

void OLED_PutsLine(uint8_t page, const char *s)
{
    uint8_t line[OLED_WIDTH] = {0};
    uint8_t col = 0U;

    if ((page >= OLED_PAGES) || (s == 0)) {
        return;
    }

    while ((*s != '\0') && (col <= (OLED_WIDTH - 6U))) {
        const uint8_t *glyph = font5x7(*s++);

        for (uint8_t i = 0; i < 5U; i++) {
            line[col + i] = glyph[i];
        }
        col = (uint8_t) (col + 6U);
    }

    oled_set_pos(page, 0U);
    (void) oled_data(line, sizeof(line));
}

static void oled_render_async_line(uint8_t page)
{
    uint8_t col = 0U;

    for (uint8_t i = 0; i < OLED_ASYNC_BYTES; i++) {
        gOledAsyncData[i] = 0U;
    }

    for (uint8_t ch = 0; ch < OLED_ASYNC_CHARS; ch++) {
        const uint8_t *glyph = font5x7(gOledLines[page][ch]);

        for (uint8_t i = 0; i < 5U; i++) {
            gOledAsyncData[col + i] = glyph[i];
        }
        col = (uint8_t) (col + 6U);
    }
}

void OLED_RequestLine(uint8_t page, const char *s)
{
    uint8_t i;

    if ((page >= OLED_PAGES) || (s == 0)) {
        return;
    }

    for (i = 0U; i < OLED_ASYNC_CHARS; i++) {
        if (*s != '\0') {
            gOledLines[page][i] = *s++;
        } else {
            gOledLines[page][i] = ' ';
        }
    }
    gOledLines[page][OLED_ASYNC_CHARS] = '\0';
    gOledDirtyMask |= (uint8_t) (1U << page);
}

void OLED_Service(void)
{
    int ret;

    switch (gOledAsyncState) {
        case OLED_ASYNC_IDLE:
            if (gOledDirtyMask == 0U) {
                return;
            }
            for (uint8_t page = 0U; page < OLED_PAGES; page++) {
                if (gOledDirtyMask & (uint8_t) (1U << page)) {
                    gOledDirtyMask &= (uint8_t) ~(1U << page);
                    gOledAsyncPage = page;
                    gOledAsyncOffset = 0U;
                    oled_render_async_line(page);
                    gOledAsyncState = OLED_ASYNC_CMD_PAGE;
                    break;
                }
            }
            break;

        case OLED_ASYNC_CMD_PAGE:
            ret = oled_cmd_async((uint8_t) (0xB0U | (gOledAsyncPage & 0x07U)));
            if (ret == 0) {
                gOledAsyncState = OLED_ASYNC_CMD_COL_LOW;
            } else if (ret < 0) {
                gOledAsyncState = OLED_ASYNC_IDLE;
            }
            break;

        case OLED_ASYNC_CMD_COL_LOW:
            ret = oled_cmd_async(0x00U);
            if (ret == 0) {
                gOledAsyncState = OLED_ASYNC_CMD_COL_HIGH;
            } else if (ret < 0) {
                gOledAsyncState = OLED_ASYNC_IDLE;
            }
            break;

        case OLED_ASYNC_CMD_COL_HIGH:
            ret = oled_cmd_async(0x10U);
            if (ret == 0) {
                gOledAsyncState = OLED_ASYNC_DATA;
            } else if (ret < 0) {
                gOledAsyncState = OLED_ASYNC_IDLE;
            }
            break;

        case OLED_ASYNC_DATA: {
            uint8_t len = (uint8_t) (OLED_ASYNC_BYTES - gOledAsyncOffset);
            if (len > 7U) {
                len = 7U;
            }

            ret = oled_data_async(&gOledAsyncData[gOledAsyncOffset], len);
            if (ret == 0) {
                gOledAsyncOffset = (uint8_t) (gOledAsyncOffset + len);
                if (gOledAsyncOffset >= OLED_ASYNC_BYTES) {
                    gOledAsyncState = OLED_ASYNC_IDLE;
                }
            } else if (ret < 0) {
                gOledAsyncState = OLED_ASYNC_IDLE;
            }
            break;
        }

        default:
            gOledAsyncState = OLED_ASYNC_IDLE;
            break;
    }
}

int OLED_Init(void)
{
    const uint8_t init_cmds[] = {
        0xAE, 0x20, 0x00, 0xB0, 0xC8, 0x00, 0x10, 0x40,
        0x81, 0x7F, 0xA1, 0xA6, 0xA8, 0x3F, 0xA4, 0xD3,
        0x00, 0xD5, 0x80, 0xD9, 0xF1, 0xDA, 0x12, 0xDB,
        0x40, 0x8D, 0x14, 0xAF,
    };

    delay_cycles(3200000U);
    for (uint8_t i = 0; i < sizeof(init_cmds); i++) {
        int ret = oled_cmd(init_cmds[i]);
        if (ret != 0) {
            return ret;
        }
    }

    OLED_Clear();
    return 0;
}
