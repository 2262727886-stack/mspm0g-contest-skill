/*
 * 立创开发板软硬件资料与相关扩展板软硬件资料官网全部开源
 * 开发板官网：www.lckfb.com
 * 文档网站：wiki.lckfb.com
 * 技术支持常驻论坛，任何技术问题欢迎随时交流学习
 * 嘉立创社区问答：https://www.jlc-bbs.com/lckfb
 * 关注bilibili账号：【立创开发板】，掌握我们的最新动态！
 * 不靠卖板赚钱，以培养中国工程师为己任
 */
#include "bsp_sg90.h"

unsigned int Servo_Angle = 0;//舵机角度

/******************************************************************
   配置占空比 范围 0 ~ (per-1)
   t = 0.5ms-------------------舵机会转动 0 °
   t = 1.0ms-------------------舵机会转动 45°
   t = 1.5ms-------------------舵机会转动 90°
   t = 2.0ms-------------------舵机会转动 135°
   t = 2.5ms-------------------舵机会转动180°
******************************************************************/

/******************************************************************
 * 函 数 名 称：Set_Servo_Angle
 * 函 数 说 明：设置角度
 * 函 数 形 参：angle=要设置的角度，范围0-180
 * 函 数 返 回：无
 * 作       者：LCKFB
 * 备       注：无
******************************************************************/
void Set_Servo_Angle(unsigned int angle)
{
    uint32_t period = 400;

    if(angle > 180)
    {
        angle = 180; // 限制角度在0到180度之间
    }

    Servo_Angle = angle;

    // 计算PWM占空比
    // 0.5ms对应的计数 = 10
    // 2.5ms对应的计数 = 50
    float min_count = 10.0f;
    float max_count = 50.0f;
    float range = max_count - min_count;
    float ServoAngle = min_count + (((float)angle / 180.0f) * range);

    DL_TimerG_setCaptureCompareValue(PWM_SG90_INST, GPIO_PWM_SG90_C0_IDX, (unsigned int)(ServoAngle + 0.5f));
}

/******************************************************************
 * 函 数 名 称：读取当前角度
 * 函 数 说 明：Get_Servo_Angle
 * 函 数 形 参：无
 * 函 数 返 回：当前角度
 * 作       者：LCKFB
 * 备       注：使用前必须确保之前使用过
                void Set_Servo_Angle(unsigned int angle)
                函数设置过角度
******************************************************************/
unsigned int Get_Servo_Angle(void)
{
    return Servo_Angle;
}