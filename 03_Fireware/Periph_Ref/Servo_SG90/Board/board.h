
#ifndef __BOARD_H__
#define __BOARD_H__

#include "ti_msp_dl_config.h"

#ifndef u8
#define u8 uint8_t
#endif

#ifndef u16
#define u16 uint16_t
#endif

#ifndef u32
#define u32 uint32_t
#endif

#ifndef u64
#define u64 uint64_t
#endif

int LOG_Debug_Out(const char* __file, const char* __func, int __line, const char* format, ...);

#define LOG_D(fmt, ...) \
    do { \
        LOG_Debug_Out(__FILE__, (const char*)__func__, __LINE__, fmt, ##__VA_ARGS__); \
    } while (0)



/* 使用可变参数是实现的类printf函数 */
int lc_printf(char* format,...);

/* 延时函数 */
void delay_us(int __us);
void delay_ms(int __ms);

void delay_1us(int __us);
void delay_1ms(int __ms);

#endif
