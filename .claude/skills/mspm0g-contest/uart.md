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

## JDY-31 蓝牙串口透传 (PID无线调参)

> **工程**: `workspace_ccstheia/jdy31_pid_test/` — 完整的最小测试单元

### JDY-31 V1.3 规格速查

| 参数 | 值 |
|------|-----|
| 芯片 | JDY-31 (蓝牙3.0 SPP) |
| 模式 | **仅从机** |
| 电压 | 1.8~3.6V (**3.3V，不可5V**) |
| 电流 | ~7.5mA |
| 距离 | 约30米 |
| **默认波特率** | **9600** ⚠️ |
| 默认配对密码 | 1234 |
| 默认广播名 | JDY-31-SPP |
| 最大吞吐量 | 16K bytes/s |
| 引脚 | TXD, RXD, VCC, GND, STATE (可选) |

### 硬件接线 (MSPM0G3507)

| JDY-31 | MSPM0G | 说明 |
|--------|--------|------|
| TXD | PB7 (UART1_RX) | JDY→M0G, 3.3V电平 |
| RXD | PB6 (UART1_TX) | M0G→JDY |
| VCC | 3.3V | **禁止5V** |
| GND | GND | 共地 |
| STATE | PA14 (GPIO) | 高=蓝牙已连接, 可选 |

### 完整 AT 指令集 (9600 8N1, 必须跟 `\r\n`)

| 指令 | 响应 | 功能 |
|------|------|------|
| `AT+VERSION` | `+VERSION=JDY-31-V1.2,Bluetooth V3.0` | 版本查询 |
| `AT+RESET` | `+OK` | 软复位 |
| `AT+DISC` | `+OK` | 断开连接 |
| `AT+LADDR` | `+LADDR=xx:xx:xx:xx:xx:xx` | 查MAC |
| `AT+PIN1234` | `+OK` | 设密码 |
| `AT+PIN` | `+PIN=1234` | 查密码 |
| `AT+BAUD8` | `+OK` | 设115200 (参数见下表) |
| `AT+BAUD` | `+BAUD=8` | 查波特率 |
| `AT+NAME小车主控` | `OK` | 设广播名 (最长18字节) |
| `AT+NAME` | `+NAME=JDY-31-SPP` | 查广播名 |
| `AT+DEFAULT` | `OK` | 恢复出厂 |
| `AT+ENLOG0` | `OK` | **关闭状态输出 (推荐)** |
| `AT+ENLOG` | `+ENLOG=1` | 查状态输出使能 |

**波特率编码：**

| 参数 | 波特率 | 备注 |
|------|--------|------|
| 4 | **9600** | 默认 |
| 5 | 19200 | |
| 6 | 38400 | |
| 7 | 57600 | |
| 8 | 115200 | **推荐** |
| 9 | 128000 | 最高 |

### 上电配置流程 (USB-TTL, 不要接M0G)

```
1. USB-TTL 3.3V 接 JDY-31 (TX→RX, RX→TX, VCC→3.3V, GND→GND)
2. 串口助手 9600 8N1, \r\n 结尾
3. 发送 AT+BAUD8        → 返回 +OK
4. 发送 AT+NAMEmyCarBT   → 返回 OK
5. 发送 AT+PIN1234       → 返回 +OK (密码默认就是1234, 可跳过)
6. 发送 AT+ENLOG0        → 返回 OK (关闭连接/断开状态消息)
7. 发送 AT+RESET         → 返回 +OK
8. 串口助手切 115200 → 重新打开端口
9. 发送 AT+VERSION       → 验证通信, 应返回 +VERSION=...
10. 断开 USB-TTL, 接到 MSPM0G 的 UART1 上
```

### ENLOG 说明 (V1.3 新增)

| 值 | 行为 |
|----|------|
| `AT+ENLOG1` (默认) | 连接/断开时串口输出 `+CONNECTED=MAC` 等日志 |
| `AT+ENLOG0` | **关闭**状态输出，透传数据更纯净 |

> **强烈建议设为0**：ENLOG=1时，蓝牙连接成功会发送 `\r\n+CONNECTED=12:34:56:78:9A:BC\r\n`，PID命令解析器会把 `+` 开头的行误处理。设为0后只输出纯PID数据。

### PC 端蓝牙上位机

| 方案 | 连接方式 | 适用 |
|------|---------|------|
| **Win蓝牙+串口助手** (推荐) | 配对→蓝牙COM口→115200 | 最简单 |
| **VOFA+** | CSV协议→蓝牙COM口 | 已有，可无线看PID曲线 |
| **手机蓝牙调试器** | SPP配对→发文本命令 | 小车跑动时手机直接调 |

### PID 无线调参工作流

```
┌──────────────┐  SPP 115200   ┌──────────────┐
│ PC蓝牙/手机  │ ◄────────────► │ JDY-31 从机  │
│ 串口助手     │                │ UART→M0G     │
└──────────────┘                └──────┬───────┘
                                       │ PB6/PB7
                                  ┌────▼───────┐
                                  │ MSPM0G3507 │
                                  │ PID + 电机  │
                                  └────────────┘

1. 编译烧录 jdy31_pid_test 工程
2. OLED显示 "JDY31 BT INIT..." → 等待蓝牙连接
3. PC蓝牙配对 → 打开蓝牙COM口 115200
4. 看到 "JDY31 PID Ready" 问候帧 → 通信OK
5. 发 P5 回车 → 返回 "P5 I8 D0 T42 B800" → OLED更新 → 参数生效
6. 发 I10 回车 → 加大积分 → 发 T60 回车 → 提高目标速度
7. 小车跑动中随时手机发送命令无级调参
```

### UART1 SysConfig 配置

```
ADD → UART → Name: UART_JDY31 → Baud Rate: 115200
  → TX: PB6 → RX: PB7 → 8N1 → 保存
```

