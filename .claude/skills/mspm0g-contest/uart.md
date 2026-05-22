# UART (printf + K230通信 + 协议解析)

## UART 初始化

**调试串口 (printf 重定向)：**
```c
#include <stdio.h>

int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

// SysConfig: UART0(PA10=TX,PA11=RX, 板载CH340, ✅已验证) → 115200-8-N-1
void uart_init(void) {
    // SysConfig 自动生成完整初始化
}

// 接收中断
void UART0_INST_IRQHandler(void) {
    uint8_t data = DL_UART_receiveData(UART0);
    // 环形缓冲存入 data
}
```


### --- UART 协议解析 ---

```c
// 帧格式: 帧头(2B) + 长度(1B) + 命令(1B) + 数据(NB) + 校验(1B, 和校验)
#define FRAME_HEAD1 0xA5
#define FRAME_HEAD2 0x5A
#define RX_BUF_SIZE  128

typedef struct {
    uint8_t buf[RX_BUF_SIZE];
    uint8_t head;
    uint8_t tail;
    uint8_t parse_state;  // 0:等HEAD1, 1:等HEAD2, 2:等LEN, 3:收数据
    uint8_t data_len;
    uint8_t data_idx;
    uint8_t checksum;
} UART_RingBuf;

static UART_RingBuf uart_rx = {0};

void UART0_INST_IRQHandler(void) {
    uint8_t byte = DL_UART_receiveData(UART0);
    // 存入环形缓冲
    uart_rx.buf[uart_rx.head] = byte;
    uart_rx.head = (uart_rx.head + 1) % RX_BUF_SIZE;
}

// 主循环中调用解析
bool uart_parse_frame(uint8_t *cmd, uint8_t *data, uint8_t *data_len) {
    while (uart_rx.tail != uart_rx.head) {
        uint8_t b = uart_rx.buf[uart_rx.tail];
        uart_rx.tail = (uart_rx.tail + 1) % RX_BUF_SIZE;

        switch (uart_rx.parse_state) {
        case 0:
            if (b == FRAME_HEAD1) { uart_rx.parse_state = 1; uart_rx.checksum = b; }
            break;
        case 1:
            if (b == FRAME_HEAD2) { uart_rx.parse_state = 2; uart_rx.checksum += b; }
            else uart_rx.parse_state = 0;
            break;
        case 2:
            if (b <= RX_BUF_SIZE - 4) {
                uart_rx.data_len = b;
                uart_rx.data_idx = 0;
                uart_rx.parse_state = 3;
                uart_rx.checksum += b;
            } else uart_rx.parse_state = 0;
            break;
        case 3:
            uart_rx.checksum += b;
            if (uart_rx.data_idx == 0) *cmd = b;
            else data[uart_rx.data_idx - 1] = b;
            uart_rx.data_idx++;
            if (uart_rx.data_idx >= uart_rx.data_len) {
                // 校验
                uint8_t check_sum = uart_rx.checksum;
                uart_rx.parse_state = 0;
                *data_len = uart_rx.data_len - 1;  // 不含命令字节
                if (check_sum == 0) return true;    // 和校验正确
            }
            break;
        }
    }
    return false;
}

// 打包发送
void uart_send_frame(uint8_t cmd, uint8_t *data, uint8_t len) {
    uint8_t checksum = FRAME_HEAD1 + FRAME_HEAD2 + (len + 1) + cmd;
    DL_UART_transmitDataBlocking(UART0, FRAME_HEAD1);
    DL_UART_transmitDataBlocking(UART0, FRAME_HEAD2);
    DL_UART_transmitDataBlocking(UART0, len + 1);
    DL_UART_transmitDataBlocking(UART0, cmd);
    for (int i = 0; i < len; i++) {
        checksum += data[i];
        DL_UART_transmitDataBlocking(UART0, data[i]);
    }
    DL_UART_transmitDataBlocking(UART0, (uint8_t)(-checksum));  // 补码和校验
}
```


### CCS 生成 .txt 文件 (串口烧录用)

CCS 默认只生成 `.out`，需在 **Project → Properties → Build → Steps → Post-build steps** 添加：

```
${CCS_INSTALL_ROOT}/tools/compiler/ti-cgt-armllvm_4.0.2.LTS/bin/tiarmhex --ti_txt ${ProjName}.out
```

---

### printf 重定向到串口 (CCS)

```c
#include "ti_msp_dl_config.h"
#include <stdio.h>
#include <string.h>

/* fputc 重定向到 UART0 (PA0=TX) */
int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

/* 完整重定向: 如需 fputs/puts 也重定向 */
int fputs(const char *s, FILE *f) {
    uint16_t len = strlen(s);
    for (uint16_t i = 0; i < len; i++)
        DL_UART_transmitDataBlocking(UART0, (uint8_t)s[i]);
    return len;
}

int puts(const char *s) {
    int n = fputs(s, stdout);
    fputs("\n", stdout);
    return n + 1;
}
```

**SysConfig UART 配置要点：**
- UART0: PA10=TX, PA11=RX, 115200-8-N-1
- **建议关闭 TX FIFO** (TX FIFO Size = 0)，否则短字符串可能不发送
- 或发送后调用 `DL_UART_flushTXFIFO(UART0)`

---

