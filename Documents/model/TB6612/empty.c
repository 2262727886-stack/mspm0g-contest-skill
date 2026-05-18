/*
 * Copyright (c) 2021, Texas Instruments Incorporated
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 *
 * *  Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 *
 * *  Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * *  Neither the name of Texas Instruments Incorporated nor the names of
 *    its contributors may be used to endorse or promote products derived
 *    from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
 * THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
 * PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
 * CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
 * EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
 * PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
 * OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
 * WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
 * OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
 * EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include "ti_msp_dl_config.h"
#include "board.h"
#include "bsp_tb6612.h"

int main(void)
{
    SYSCFG_DL_init();

    TB6612_Motor_Stop();

    lc_printf("\nTB6612 Motor Demo Start...\r\n");

    while (1) 
    {
        // 正反转自己定义

        for(int i = 0; i < 1000; i += 50)
        {
            AO_Control(1, i);// A端电机转动 速度最大1000
            BO_Control(1, i);// B端电机转动 速度最大1000

            lc_printf("Dir[ 1 ]   i[ %d ]\r\n",i);

            delay_ms(500);
        }
        TB6612_Motor_Stop(); // 停止转动
        delay_ms(1000);

        for(int i = 0; i < 1000; i += 50)
        {
            AO_Control(0, i);// A端电机转动 速度最大1000
            BO_Control(0, i);// B端电机转动 速度最大1000

            lc_printf("Dir[ 0 ]   i[ %d ]\r\n",i);

            delay_ms(500);
        }
        TB6612_Motor_Stop(); // 停止转动
        delay_ms(1000);
    }
}
