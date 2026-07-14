#include "uart_debug.h"

/**
 * 重定义 fputc，使 printf 通过 UART0 输出
 * 需要在编译选项中添加 -DPART_MSPM0G3507 和链接 -lprintf
 */
int fputc(int ch, FILE *f)
{
    DL_UART_Main_transmitDataBlocking8(UART_0_INST, (uint8_t)ch);
    return ch;
}
