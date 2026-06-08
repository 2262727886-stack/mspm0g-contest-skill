/**
 * motor.c — TB6612FNG 双路直流电机驱动实现
 *
 * TB6612 真值表:
 *   AIN1=H, AIN2=L → 右轮前进
 *   AIN1=L, AIN2=H → 右轮后退
 *   BIN1=H, BIN2=L → 左轮前进
 *   BIN1=L, BIN2=H → 左轮后退
 *   xIN1=xIN2      → 制动/滑行
 *
 * PWM 输出使用反逻辑: DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST, MAX - duty, CC_INDEX)
 *   duty=0 → CC=MAX → 0% 输出 (停止)
 *   duty=MAX → CC=0 → 100% 输出 (全速)
 */

#include "motor.h"
#include "ti_msp_dl_config.h"

/* ========================= GPIO 引脚定义 ========================= */
/* 右轮方向 (A通道, GPIOA) */
#define AIN1_IOMUX  (IOMUX_PINCM35)        /* PA13 */
#define AIN1_PIN    (DL_GPIO_PIN_13)
#define AIN2_IOMUX  (IOMUX_PINCM34)        /* PA12 */
#define AIN2_PIN    (DL_GPIO_PIN_12)

/* 左轮方向 (B通道, GPIOB) */
#define BIN1_IOMUX  (IOMUX_PINCM12)        /* PB0 */
#define BIN1_PIN    (DL_GPIO_PIN_0)
#define BIN2_IOMUX  (IOMUX_PINCM13)        /* PB1 */
#define BIN2_PIN    (DL_GPIO_PIN_1)

/* ========================= 内部辅助函数 ========================= */

/* 限制 duty 到安全范围 */
static uint16_t limit_duty(int16_t duty)
{
    int16_t max = (int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD);
    if (duty < 0) duty = (int16_t)(-duty);
    if (duty > max) duty = max;
    return (uint16_t)duty;
}

/* 左轮方向 */
static void left_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(GPIOB, BIN1_PIN);
    else     DL_GPIO_clearPins(GPIOB, BIN1_PIN);
    if (in2) DL_GPIO_setPins(GPIOB, BIN2_PIN);
    else     DL_GPIO_clearPins(GPIOB, BIN2_PIN);
}

/* 右轮方向 */
static void right_dir(bool in1, bool in2)
{
    if (in1) DL_GPIO_setPins(GPIOA, AIN1_PIN);
    else     DL_GPIO_clearPins(GPIOA, AIN1_PIN);
    if (in2) DL_GPIO_setPins(GPIOA, AIN2_PIN);
    else     DL_GPIO_clearPins(GPIOA, AIN2_PIN);
}

/* 左轮 PWM (PB16 = TIMG8_C1) */
static void left_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST,
        (uint16_t)(MOTOR_PWM_MAX - duty), DL_TIMER_CC_1_INDEX);
}

/* 右轮 PWM (PB15 = TIMG8_C0) */
static void right_pwm(uint16_t duty)
{
    DL_TimerG_setCaptureCompareValue(MOTOR_PWM_INST,
        (uint16_t)(MOTOR_PWM_MAX - duty), DL_TIMER_CC_0_INDEX);
}

/* ========================= 公开接口实现 ========================= */

void Motor_Init(void)
{
    /* 配置方向引脚为输出 */
    DL_GPIO_initDigitalOutput(AIN1_IOMUX);
    DL_GPIO_initDigitalOutput(AIN2_IOMUX);
    DL_GPIO_initDigitalOutput(BIN1_IOMUX);
    DL_GPIO_initDigitalOutput(BIN2_IOMUX);

    /* 初始状态: 全部低电平 (停车) */
    DL_GPIO_clearPins(GPIOA, AIN1_PIN | AIN2_PIN);
    DL_GPIO_clearPins(GPIOB, BIN1_PIN | BIN2_PIN);
    DL_GPIO_enableOutput(GPIOA, AIN1_PIN | AIN2_PIN);
    DL_GPIO_enableOutput(GPIOB, BIN1_PIN | BIN2_PIN);

    /* 启动 PWM 计数器 (SysConfig 生成后默认不启动) */
    DL_TimerG_startCounter(MOTOR_PWM_INST);
}

void Motor_LeftSet(int16_t duty)
{
    if (duty > 0)      left_dir(false, true);   /* 前进: BIN1=L, BIN2=H */
    else if (duty < 0) left_dir(true, false);   /* 后退: BIN1=H, BIN2=L */
    else               left_dir(false, false);  /* 制动 */
    left_pwm(limit_duty(duty));
}

void Motor_RightSet(int16_t duty)
{
    if (duty > 0)      right_dir(false, true);  /* 前进: AIN1=L, AIN2=H */
    else if (duty < 0) right_dir(true, false);  /* 后退: AIN1=H, AIN2=L */
    else               right_dir(false, false); /* 制动 */
    right_pwm(limit_duty(duty));
}

void Motor_Stop(void)
{
    left_dir(false, false);
    right_dir(false, false);
    left_pwm(0);
    right_pwm(0);
}
