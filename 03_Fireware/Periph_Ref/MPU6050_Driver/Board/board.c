

#include <string.h>
#include <stdio.h>
#include <stdarg.h>
#include "board.h"
#include "ti/driverlib/m0p/dl_core.h"


static void uart0_sendChar(uint8_t dat)
{
    //当串口0忙的时候等待，不忙的时候再发送传进来的字符
    while( DL_UART_isBusy(UART_0_INST) == true );

    //发送单个字符
    DL_UART_Main_transmitData(UART_0_INST, dat);
}


static void uart0_sendString(char* str)
{
    //当前字符串地址不在结尾 并且 字符串首地址不为空
    while( *str!=0 && str!=0 )
    {
        //发送字符串首地址中的字符，并且在发送完成之后首地址自增
        uart0_sendChar(*str++);
    }
}

/* 将c库的printf函数重新定位到USART */
int fputc(int ch, FILE *f)
{
    // 发送单个字符
    uart0_sendChar( (uint8_t)ch );

    return ch;
}

int LOG_Debug_Out(const char* __file, const char* __func, int __line, const char* format, ...)
{
    va_list args;
    va_start(args, format);

    // 前缀信息
    char log_buff[64] = {0};
    sprintf(log_buff, "[%s Func:%s Line:%d] ",__file,__func,__line);

    // 创建一个足够大的缓冲区来存储格式化后的字符串
    char buffer[512] = {0};
    strcpy(buffer, log_buff); // 使用strcpy来复制前缀信息
    int len = vsnprintf(buffer + strlen(buffer), sizeof(buffer) - strlen(buffer), format, args); // 追加到buffer中

    va_end(args);

    // 发送格式化后的字符串
    char temp_buff[] = "\r\n";
    strcat(buffer, temp_buff);
    uart0_sendString(buffer);

    return len;
}



int lc_printf(char* format,...)
{
    va_list args;
    va_start(args, format);

    // 创建一个足够大的缓冲区来存储格式化后的字符串
    char buffer[512] = {0};
    int len = vsnprintf(buffer, sizeof(buffer), format, args);

    va_end(args);

    // 发送格式化后的字符串
    uart0_sendString(buffer);

    return len;
}


/* ================ 延时函数封装 =================== */

void delay_us(int __us) { delay_cycles( (CPUCLK_FREQ / 1000 / 1000)*__us); }
void delay_ms(int __ms) { delay_cycles( (CPUCLK_FREQ / 1000)*__ms); }

void delay_1us(int __us) { delay_cycles( (CPUCLK_FREQ / 1000 / 1000)*__us); }
void delay_1ms(int __ms) { delay_cycles( (CPUCLK_FREQ / 1000)*__ms); }
