from machine import UART, FPIOA
import time

BAUD = 9600

def make_frame(pan, tilt):
    buf = bytearray([0xFF, 0xFE, pan & 0xFF, tilt & 0xFF, 0, 0, 0, 0])
    bcc = 0
    for i in range(7):
        bcc ^= buf[i]
    buf[7] = bcc
    return buf

fpioa = FPIOA()

# 40-pin header candidates. Connect each TX candidate to MSPM0G PB3/RX.
ports = []

try:
    fpioa.set_function(3, FPIOA.UART1_TXD)     # 40-pin pin 8
    ports.append(("U1-P8-GPIO3", UART(UART.UART1, baudrate=BAUD,
                                      bits=UART.EIGHTBITS,
                                      parity=UART.PARITY_NONE,
                                      stop=UART.STOPBITS_ONE),
                  make_frame(111, 90)))
except Exception as e:
    print("UART1 init failed:", e)

try:
    fpioa.set_function(5, FPIOA.UART2_TXD)     # 40-pin pin 11
    ports.append(("U2-P11-GPIO5", UART(UART.UART2, baudrate=BAUD,
                                       bits=UART.EIGHTBITS,
                                       parity=UART.PARITY_NONE,
                                       stop=UART.STOPBITS_ONE),
                  make_frame(122, 90)))
except Exception as e:
    print("UART2 init failed:", e)

try:
    fpioa.set_function(32, FPIOA.UART3_TXD)    # 40-pin pin 37
    ports.append(("U3-P37-GPIO32", UART(UART.UART3, baudrate=BAUD,
                                        bits=UART.EIGHTBITS,
                                        parity=UART.PARITY_NONE,
                                        stop=UART.STOPBITS_ONE),
                  make_frame(133, 90)))
except Exception as e:
    print("UART3 init failed:", e)

try:
    fpioa.set_function(36, FPIOA.UART4_TXD)    # 40-pin pin 29
    ports.append(("U4-P29-GPIO36", UART(UART.UART4, baudrate=BAUD,
                                        bits=UART.EIGHTBITS,
                                        parity=UART.PARITY_NONE,
                                        stop=UART.STOPBITS_ONE),
                  make_frame(144, 90)))
except Exception as e:
    print("UART4 init failed:", e)

print("K230 UART all-port test")
for name, _, frame in ports:
    print(name, list(frame))

while True:
    for name, uart, frame in ports:
        uart.write(frame)
        print("TX", name, list(frame))
        time.sleep_ms(250)
