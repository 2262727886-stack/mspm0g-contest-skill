# K230 -> MSPM0G UART Gimbal Bring-up

This note records the verified 2026-05 K230 vision-to-MSPM0G3507 gimbal UART
path and the debugging sequence that worked on real hardware.

## Verified Wiring

| Signal | Connection |
| --- | --- |
| K230 TX | 40-pin header pin 8, GPIO3, UART1_TXD |
| MSPM0G RX | PB3, UART3_RX |
| Optional MSPM0G TX | PB2, UART3_TX |
| Ground | K230 GND to MSPM0G GND |
| Baud | 9600 8N1 |

Only TX and GND are required for one-way K230 control of the MSPM0G gimbal.

## Frame

```text
FF FE pan tilt 00 00 00 BCC
```

`BCC` is XOR of bytes 0..6.

Example:

```text
pan=122, tilt=90 -> FF FE 7A 5A 00 00 00 21
```

## K230 API Pattern

```python
from machine import UART, FPIOA

fpioa = FPIOA()
fpioa.set_function(3, FPIOA.UART1_TXD)   # 40-pin pin 8
fpioa.set_function(4, FPIOA.UART1_RXD)   # optional, 40-pin pin 10

uart = UART(UART.UART1, baudrate=9600,
            bits=UART.EIGHTBITS,
            parity=UART.PARITY_NONE,
            stop=UART.STOPBITS_ONE)
```

## MSPM0G SysConfig Pattern

```js
UART_K230.$name = "UART_K230";
UART_K230.targetBaudRate = 9600;
UART_K230.peripheral.rxPin.$assign = "PB3";
UART_K230.peripheral.txPin.$assign = "PB2";
UART_K230.peripheral.$suggestSolution = "UART3";
```

## OLED Debug Interpretation

| OLED field | Meaning |
| --- | --- |
| `RX` | Total bytes seen on MSPM0G PB3 |
| `HEAD` | `FF FE` header count |
| `FRAME` | `pan/tilt` parsed and servo command issued |
| `OK` | BCC valid |
| `ERR` | BCC invalid |
| `P/T` | Last pan/tilt bytes |
| `RAW` | Last 8 raw RX bytes |

If `RX` rises but `HEAD` only rises occasionally, treat it as wrong pin, bad
ground, bad contact, or unsuitable baud. Do not tune the vision algorithm yet.

## All-port K230 Test

Use `workspace_ccstheia/test_2/k230_uart_all_test.py` to identify the actual
physical TX pin:

| K230 UART | Header pin | GPIO | Sent pan |
| --- | --- | --- | --- |
| UART1 | pin 8 | GPIO3 | 111 |
| UART2 | pin 11 | GPIO5 | 122 |
| UART3 | pin 37 | GPIO32 | 133 |
| UART4 | pin 29 | GPIO36 | 144 |

Connect one K230 TX candidate to MSPM0G PB3. The OLED `P:` value identifies the
working line. In the verified setup, header pin 8/GPIO3/UART1_TXD was correct.

## Avoid These Mistakes

- Do not assume PB3 is TX. In the verified firmware PB3 is UART3_RX.
- Do not confuse K230 GPIO numbers with 40-pin header numbers.
- Do not start with 115200 on long jumper wiring. Verify 9600 first.
- Do not debug LAB thresholds before fixed UART frames are stable.
- Do not send pan angles above 255 in a one-byte protocol.
- Do not map pixel error directly to absolute servo angle during bring-up; use
  incremental steps, deadband, and tight clamps first.
