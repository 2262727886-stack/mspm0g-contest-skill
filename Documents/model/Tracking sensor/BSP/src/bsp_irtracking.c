/*
 * 立创开发板软硬件资料与相关扩展板软硬件资料官网全部开源
 * 开发板官网：www.lckfb.com
 * 文档网站：wiki.lckfb.com
 * 技术支持常驻论坛，任何技术问题欢迎随时交流学习
 * 嘉立创社区问答：https://www.jlc-bbs.com/lckfb
 * 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
 * 不靠卖板赚钱，以培养中国工程师为己任
 */

#include "bsp_irtracking.h"
#include "stdio.h"


/**********************************************************
 * 函 数 名 称：ADC_GET
 * 函 数 功 能：读取一次ADC数据
 * 传 入 参 数：无
 * 函 数 返 回：无
 * 作       者：LCKFB
 * 备       注：LP
**********************************************************/
static uint32_t ADC_GET(void)
{
    DL_ADC12_startConversion(ADC12_0_INST);
    while (DL_ADC12_getStatus(ADC12_0_INST) & DL_ADC12_STATUS_CONVERSION_ACTIVE);
    return DL_ADC12_getMemResult(ADC12_0_INST, ADC12_0_ADCMEM_CH0);
}
/******************************************************************
 * 函 数 名 称：Get_ADC_Value
 * 函 数 说 明：对ADC值进行平均值计算后输出
 * 函 数 形 参：
 * 函 数 返 回：对应扫描的ADC值
 * 作       者：LCKFB
 * 备       注：无
******************************************************************/
unsigned int Get_ADC_Value(void)
{
    unsigned char i = 0;
    unsigned int AdcValue = 0;

    /* 因为采集 SAMPLES 次，故循环 SAMPLES 次 */
    for(i = 0; i < SAMPLES; i++)
    {
            /*    累加    */
            AdcValue += ADC_GET();
    }
    /* 求平均值 */
    AdcValue = AdcValue / SAMPLES;

    return AdcValue;
}
/******************************************************************
 * 函 数 名 称：Get_DO
 * 函 数 说 明：读取传感器识别状态
 * 函 数 形 参：无
 * 函 数 返 回：1=识别为黑色   0=识别的不是黑色
 * 作       者：LCKFB
 * 备       注：可以通过模块上的可调电阻调整识别黑色的阈值
******************************************************************/
unsigned char Get_DO(void)
{
    if( IR_DO == 1 )
    {
        return 1;
    }
    else
    {
        return 0;
    }
}
