/**
 * empty.c — IMU601 小车主控: 走直线 + 90度旋转
 *
 * 功能:
 *   PA25 短按: 切换直行/停止 (编码器速度均衡 PI)
 *   PA25 长按: 陀螺仪零偏校准 (静止状态)
 *   PA26 短按: 原地顺时针旋转 90度 (yaw PID)
 *
 * 控制架构:
 *   IDLE → PA25 → STRAIGHT (编码器 PI 内环, 20ms)
 *   IDLE → PA26 → TURN (yaw PID, 20ms, 自动回 IDLE)
 *   STRAIGHT → PA25 → IDLE (停车)
 *
 * 硬件:
 *   MCU=MSPM0G3507, IMU=IMU601(UART0), OLED=SSD1306(I2C0)
 *   电机=TB6612FNG+MG310, 编码器=霍尔(A相双边沿)
 */

#include "ti_msp_dl_config.h"
#include "oled.h"
#include "imu601.h"
#include "motor.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <math.h>

/* ========================= SysTick 1ms ========================= */

volatile uint32_t g_millis;

void SysTick_Handler(void)
{
    g_millis++;
}

/* ========================= 编码器 (PA15 右轮 / PA17 左轮) ========================= */

#define ENC_R_IOMUX  (IOMUX_PINCM37)   /* PA15 — 右轮 A 相 */
#define ENC_R_PIN    (DL_GPIO_PIN_15)
#define ENC_L_IOMUX  (IOMUX_PINCM39)   /* PA17 — 左轮 A 相 */
#define ENC_L_PIN    (DL_GPIO_PIN_17)

static volatile int16_t g_enc_r;       /* 右轮边沿计数 (中断写, 主循环读清零) */
static volatile int16_t g_enc_l;       /* 左轮边沿计数 */

static void encoder_init(void)
{
    /* 配置为上拉输入 + 滞回 */
    DL_GPIO_initDigitalInputFeatures(ENC_R_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(ENC_L_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    /* 双边沿检测: PA15 用低16位寄存器, PA17 用高16位寄存器 */
    DL_GPIO_setLowerPinsPolarity(GPIOA, DL_GPIO_PIN_15_EDGE_RISE_FALL);
    DL_GPIO_setUpperPinsPolarity(GPIOA, DL_GPIO_PIN_17_EDGE_RISE_FALL);

    /* 使能中断 */
    DL_GPIO_clearInterruptStatus(GPIOA, ENC_R_PIN | ENC_L_PIN);
    DL_GPIO_enableInterrupt(GPIOA, ENC_R_PIN | ENC_L_PIN);
    NVIC_EnableIRQ(GPIOA_INT_IRQn);
}

static void encoder_clear_counts(void)
{
    __disable_irq();
    g_enc_l = 0;
    g_enc_r = 0;
    __enable_irq();
}

/* GROUP1 中断: 编码器边沿计数 (只做++, 不调任何函数) */
void GROUP1_IRQHandler(void)
{
    uint32_t st = DL_GPIO_getEnabledInterruptStatus(GPIOA, ENC_R_PIN | ENC_L_PIN);
    if (st & ENC_R_PIN) g_enc_r++;
    if (st & ENC_L_PIN) g_enc_l++;
    DL_GPIO_clearInterruptStatus(GPIOA, st);
}

/* ========================= 按键 (PA25 / PA26) ========================= */

#define KEY_START_IOMUX  (IOMUX_PINCM55)   /* PA25 */
#define KEY_START_PIN    (DL_GPIO_PIN_25)
#define KEY_TURN_IOMUX   (IOMUX_PINCM59)   /* PA26 */
#define KEY_TURN_PIN     (DL_GPIO_PIN_26)

static bool key_read(uint32_t pin)
{
    return (DL_GPIO_readPins(GPIOA, pin) == 0U); /* 上拉, 按下=低 */
}

/**
 * 按键扫描: 返回事件类型
 *   0=无事件, 1=短按, 2=长按 (>1s)
 */
typedef struct {
    bool     last;          /* 上次稳定状态 */
    uint16_t hold_ms;       /* 按住持续时间 */
    bool     reported;      /* 长按已报告 */
} KeyState;

static uint8_t key_scan(KeyState *ks, bool current)
{
    uint8_t event = 0U;

    if (current) {
        /* 按下 */
        if (ks->hold_ms < 2000U) ks->hold_ms++;
        if (ks->hold_ms == 20U && !ks->reported) {
            event = 1U; /* 短按 (按下 20ms 触发) */
        }
        if (ks->hold_ms >= 1000U && !ks->reported) {
            event = 2U; /* 长按 */
            ks->reported = true;
        }
    } else {
        /* 松开 */
        ks->hold_ms = 0U;
        ks->reported = false;
    }
    ks->last = current;
    return event;
}

static KeyState s_ks_start, s_ks_turn;

/* ========================= 8-way line sensor ========================= */

#define LINE0_IOMUX  (IOMUX_PINCM56)  /* PB25: left 1 */
#define LINE1_IOMUX  (IOMUX_PINCM52)  /* PB24: left 2 */
#define LINE2_IOMUX  (IOMUX_PINCM48)  /* PB20: left 3 */
#define LINE3_IOMUX  (IOMUX_PINCM36)  /* PA14: left 4 */
#define LINE4_IOMUX  (IOMUX_PINCM44)  /* PB18: right 4 */
#define LINE5_IOMUX  (IOMUX_PINCM45)  /* PB19: right 3 */
#define LINE6_IOMUX  (IOMUX_PINCM27)  /* PB10: right 2 */
#define LINE7_IOMUX  (IOMUX_PINCM14)  /* PA7 : right 1 */

#define LINE0_PIN    (DL_GPIO_PIN_25)
#define LINE1_PIN    (DL_GPIO_PIN_24)
#define LINE2_PIN    (DL_GPIO_PIN_20)
#define LINE3_PIN    (DL_GPIO_PIN_14)
#define LINE4_PIN    (DL_GPIO_PIN_18)
#define LINE5_PIN    (DL_GPIO_PIN_19)
#define LINE6_PIN    (DL_GPIO_PIN_10)
#define LINE7_PIN    (DL_GPIO_PIN_7)

static uint8_t s_line_bits;            /* bit0~bit7 = left to right, active-low */

static void line_sensor_input(uint32_t iomux)
{
    DL_GPIO_initDigitalInputFeatures(iomux,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
}

static void line_sensor_init(void)
{
    line_sensor_input(LINE0_IOMUX);
    line_sensor_input(LINE1_IOMUX);
    line_sensor_input(LINE2_IOMUX);
    line_sensor_input(LINE3_IOMUX);
    line_sensor_input(LINE4_IOMUX);
    line_sensor_input(LINE5_IOMUX);
    line_sensor_input(LINE6_IOMUX);
    line_sensor_input(LINE7_IOMUX);
}

static uint8_t line_sensor_read_active_low(void)
{
    uint8_t bits = 0U;

    if (DL_GPIO_readPins(GPIOB, LINE0_PIN) == 0U) bits |= (1U << 0);
    if (DL_GPIO_readPins(GPIOB, LINE1_PIN) == 0U) bits |= (1U << 1);
    if (DL_GPIO_readPins(GPIOB, LINE2_PIN) == 0U) bits |= (1U << 2);
    if (DL_GPIO_readPins(GPIOA, LINE3_PIN) == 0U) bits |= (1U << 3);
    if (DL_GPIO_readPins(GPIOB, LINE4_PIN) == 0U) bits |= (1U << 4);
    if (DL_GPIO_readPins(GPIOB, LINE5_PIN) == 0U) bits |= (1U << 5);
    if (DL_GPIO_readPins(GPIOB, LINE6_PIN) == 0U) bits |= (1U << 6);
    if (DL_GPIO_readPins(GPIOA, LINE7_PIN) == 0U) bits |= (1U << 7);

    return bits;
}

/* ========================= 软件串口调试 (PA10 TX, 9600 baud) ========================= */

#define DBG_TX_IOMUX  (IOMUX_PINCM21)  /* PA10 */
#define DBG_TX_PIN    (DL_GPIO_PIN_10)
#define SOFT_BIT_CYC  (3333U)           /* 9600 baud @ 32MHz */

static void dbg_init(void)
{
    DL_GPIO_initDigitalOutput(DBG_TX_IOMUX);
    DL_GPIO_setPins(GPIOA, DBG_TX_PIN);
    DL_GPIO_enableOutput(GPIOA, DBG_TX_PIN);
}

static void dbg_tx_bit(bool high)
{
    if (high) DL_GPIO_setPins(GPIOA, DBG_TX_PIN);
    else      DL_GPIO_clearPins(GPIOA, DBG_TX_PIN);
    delay_cycles(SOFT_BIT_CYC);
}

static void dbg_tx_byte(uint8_t b)
{
    dbg_tx_bit(false); /* start */
    for (uint8_t i = 0U; i < 8U; i++)
        dbg_tx_bit((b & (1U << i)) != 0U);
    dbg_tx_bit(true);  /* stop */
}

static void dbg_puts(const char *s)
{
    while (*s) dbg_tx_byte((uint8_t)*s++);
}

/* ========================= 工具函数 ========================= */

static float wrap_180(float a)
{
    while (a >  180.0f) a -= 360.0f;
    while (a < -180.0f) a += 360.0f;
    return a;
}

static float absf(float v) { return (v < 0.0f) ? -v : v; }

static int16_t ramp_to(int16_t cur, int16_t target, int16_t step)
{
    if (cur < target) {
        cur += step;
        if (cur > target) cur = target;
    } else if (cur > target) {
        cur -= step;
        if (cur < target) cur = target;
    }
    return cur;
}

/* ========================= 运行状态 ========================= */

typedef enum { MODE_IDLE, MODE_STRAIGHT, MODE_LINE, MODE_TURN } RunMode;

/* 8-way line tracking: bit0~bit7 are left to right, active-low. */
#define LINE_BASE_DUTY      (260)
#define LINE_RAMP           (10)
#define LINE_CTRL_MS        (20U)
#define LINE_KP             (12)
#define LINE_CORR_LIMIT     (500)
#define LINE_SEARCH_DUTY    (180)

/* 走直线参数 */
#define STRAIGHT_DUTY       (260)       /* 基础前进 PWM */
#define STRAIGHT_RAMP       (5)         /* 每10ms斜坡步进 */
#define STRAIGHT_CTRL_MS    (20U)       /* 速度闭环周期 */
#define STRAIGHT_KP         (3)         /* 左右均衡 P */
#define STRAIGHT_KI         (1)         /* 左右均衡 I */
#define STRAIGHT_LIMIT      (120)       /* 均衡修正上限 */

/* 转弯参数 */
#define TURN_DEG            (90.0f)     /* 目标角度 */
#define TURN_CTRL_MS        (20U)       /* 控制周期 */
#define TURN_KP             (5.0f)      /* 比例 */
#define TURN_KI             (0.0f)      /* 积分 (已禁用) */
#define TURN_KD             (0.4f)      /* 微分 (gyroZ) */
#define TURN_PWM_MIN        (120)       /* 远离目标最小 PWM */
#define TURN_PWM_MAX        (620)       /* 最大 PWM */
#define TURN_NEAR_ERR       (12.0f)     /* 近目标区阈值 */
#define TURN_NEAR_PWM_MIN   (120)       /* 近目标区最小: 与远区相同, 保证不停转 */
#define TURN_NEAR_PWM_MAX   (260)       /* 近目标区最大 PWM */
#define TURN_TIMEOUT_MS     (3000U)     /* 超时: 3秒未完成强制停车 */
#define TURN_STOP_ERR       (3.0f)      /* 停车角度死区 */
#define TURN_STOP_GYRO      (25.0f)     /* 停车角速度阈值 */
#define TURN_SETTLE         (3U)        /* 连续稳定次数 */
#define TURN_INT_LIMIT      (600.0f)    /* 积分限幅 */

static RunMode  s_mode = MODE_IDLE;
static int16_t  s_line_error;          /* negative=line left, positive=line right */
static int16_t  s_line_last_error;     /* used to search after line is lost */
static bool     s_line_has_last;       /* false until one valid black-line sample appears */
static char     s_line_dir = 'S';      /* L/R/F/S direction shown on OLED */

/* 走直线状态 */
static int16_t  s_duty_l, s_duty_r;    /* 当前实际输出 (斜坡后) */
static int16_t  s_balance;             /* 均衡修正量 */
static int16_t  s_balance_i;           /* 均衡积分 */

/* 转弯状态 */
static float    s_turn_target;         /* 目标 yaw */
static float    s_turn_integral;       /* 积分项 */
static int16_t  s_turn_pwm;            /* 当前转弯 PWM */
static float    s_turn_error;          /* 当前角度误差 */
static uint8_t  s_turn_settle;         /* 稳定计数 */
static uint32_t s_turn_start_ms;       /* 转弯启动时间 (超时保护) */

/* ========================= 转弯 PWM 限幅 ========================= */

static int16_t clamp_turn_pwm(float output, float err)
{
    int16_t pwm_min = TURN_PWM_MIN;
    int16_t pwm_max = TURN_PWM_MAX;

    /* 近目标区: 降低 PWM 范围, 防止过冲抖动 */
    if (absf(err) < TURN_NEAR_ERR) {
        pwm_min = TURN_NEAR_PWM_MIN;
        pwm_max = TURN_NEAR_PWM_MAX;
    }

    /* 限幅 */
    if (output >  (float)pwm_max) output =  (float)pwm_max;
    if (output < -(float)pwm_max) output = -(float)pwm_max;

    /* 最小 PWM (保证电机能转) */
    if (output > 0.0f && output < (float)pwm_min) output = (float)pwm_min;
    if (output < 0.0f && output > -(float)pwm_min) output = -(float)pwm_min;

    return (output >= 0.0f) ? (int16_t)(output + 0.5f) : (int16_t)(output - 0.5f);
}

static int16_t clamp_i16(int16_t v, int16_t lo, int16_t hi)
{
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

static void line_bits_to_string(uint8_t bits, char out[9])
{
    for (uint8_t i = 0U; i < 8U; i++) {
        out[i] = (bits & (uint8_t)(1U << i)) ? '0' : '1';
    }
    out[8] = '\0';
}

static bool line_calc_error(uint8_t bits, int16_t *error)
{
    static const int8_t weight[8] = { -35, -25, -15, -5, 5, 15, 25, 35 };
    int16_t sum = 0;
    int16_t count = 0;

    for (uint8_t i = 0U; i < 8U; i++) {
        if (bits & (uint8_t)(1U << i)) {
            sum += weight[i];
            count++;
        }
    }
    if (count == 0) return false;

    *error = (int16_t)(sum / count);
    return true;
}

/* ========================= OLED 显示 ========================= */

static void oled_show_status(float yaw, int16_t spd_l, int16_t spd_r)
{
    char line[22];
    char line_bits[9];

    line_bits_to_string(s_line_bits, line_bits);

    /* 第0行: 模式 */
    switch (s_mode) {
    case MODE_IDLE:
        OLED_ClearPage(0);
        OLED_Puts(0, 0, "IDLE");
        break;
    case MODE_STRAIGHT:
        OLED_ClearPage(0);
        OLED_Puts(0, 0, "STRAIGHT");
        break;
    case MODE_LINE:
        OLED_ClearPage(0);
        OLED_Puts(0, 0, "LINE");
        break;
    case MODE_TURN:
        OLED_ClearPage(0);
        OLED_Puts(0, 0, "TURN 90");
        break;
    }

    /* 第1行: yaw */
    OLED_ClearPage(1);
    snprintf(line, sizeof(line), "L:%s %02X", line_bits, s_line_bits);
    OLED_Puts(1, 0, line);

    /* 第2行: 左轮编码器 */
    OLED_ClearPage(2);
    snprintf(line, sizeof(line), "E:%d DIR:%c", s_line_error, s_line_dir);
    OLED_Puts(2, 0, line);

    /* 第3行: 右轮编码器 */
    OLED_ClearPage(3);
    snprintf(line, sizeof(line), "S:%d/%d Y:%.0f", spd_l, spd_r, yaw);
    OLED_Puts(3, 0, line);

    /* 第4行: 左轮 PWM */
    OLED_ClearPage(4);
    snprintf(line, sizeof(line), "DL:%d", s_duty_l);
    OLED_Puts(4, 0, line);

    /* 第5行: 右轮 PWM */
    OLED_ClearPage(5);
    snprintf(line, sizeof(line), "DR:%d", s_duty_r);
    OLED_Puts(5, 0, line);

    /* 第6行: 转弯误差或陀螺仪校准状态 */
    OLED_ClearPage(6);
    if (IMU601_IsGyroCalibrating()) {
        OLED_Puts(6, 0, "CALIBRATING...");
    } else if (s_mode == MODE_TURN) {
        uint32_t elapsed = (uint32_t)(g_millis - s_turn_start_ms);
        snprintf(line, sizeof(line), "E:%.0f P:%d T:%lu",
                 s_turn_error, s_turn_pwm, (unsigned long)(elapsed/1000U));
        OLED_Puts(6, 0, line);
    } else if (s_mode == MODE_LINE) {
        snprintf(line, sizeof(line), "LINE %c %d", s_line_dir, s_line_error);
        OLED_Puts(6, 0, line);
    } else {
        snprintf(line, sizeof(line), "B:%d", s_balance);
        OLED_Puts(6, 0, line);
    }

    /* 第7行: 提示 */
    OLED_ClearPage(7);
    if (s_mode == MODE_IDLE) {
        OLED_Puts(7, 0, "25:LINE 26:TURN");
    } else if (s_mode == MODE_LINE) {
        OLED_Puts(7, 0, "25:STOP");
    } else if (s_mode == MODE_STRAIGHT) {
        OLED_Puts(7, 0, "25:STOP");
    }
}

/* ========================= 走直线控制 (20ms 周期) ========================= */

static void straight_control(void)
{
    static uint32_t last_ms;
    int16_t spd_l, spd_r, err;

    if (s_mode != MODE_STRAIGHT) return;
    if ((uint32_t)(g_millis - last_ms) < STRAIGHT_CTRL_MS) return;
    last_ms = g_millis;

    /* 读取编码器并清零 */
    __disable_irq();
    spd_l = g_enc_l;
    spd_r = g_enc_r;
    g_enc_l = 0;
    g_enc_r = 0;
    __enable_irq();

    /* 取绝对值 (只关心速度大小) */
    spd_l = (spd_l < 0) ? -spd_l : spd_l;
    spd_r = (spd_r < 0) ? -spd_r : spd_r;

    /* 速度均衡 PI: err>0 → 左轮快 → 减左加右 */
    err = spd_l - spd_r;
    s_balance_i += err;
    if (s_balance_i >  STRAIGHT_LIMIT) s_balance_i =  STRAIGHT_LIMIT;
    if (s_balance_i < -STRAIGHT_LIMIT) s_balance_i = -STRAIGHT_LIMIT;

    s_balance = STRAIGHT_KP * err + STRAIGHT_KI * s_balance_i;
    if (s_balance >  STRAIGHT_LIMIT) s_balance =  STRAIGHT_LIMIT;
    if (s_balance < -STRAIGHT_LIMIT) s_balance = -STRAIGHT_LIMIT;
}

/* ========================= 转弯控制 (20ms 周期) ========================= */

static void line_control(void)
{
    static uint32_t last_ms;
    int16_t err = 0;
    int16_t corr;
    int16_t target_l;
    int16_t target_r;

    if (s_mode != MODE_LINE) return;
    if ((uint32_t)(g_millis - last_ms) < LINE_CTRL_MS) return;
    last_ms = g_millis;

    if (line_calc_error(s_line_bits, &err)) {
        s_line_error = err;
        s_line_last_error = err;
        s_line_has_last = true;
        corr = clamp_i16((int16_t)(err * LINE_KP), -LINE_CORR_LIMIT, LINE_CORR_LIMIT);

        target_l = (int16_t)(LINE_BASE_DUTY + corr);
        target_r = (int16_t)(LINE_BASE_DUTY - corr);
        target_l = clamp_i16(target_l, (int16_t)(-(int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD)),
                             (int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD));
        target_r = clamp_i16(target_r, (int16_t)(-(int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD)),
                             (int16_t)(MOTOR_PWM_MAX - MOTOR_PWM_DEAD));

        if (err < -8)      s_line_dir = 'L';
        else if (err > 8)  s_line_dir = 'R';
        else               s_line_dir = 'F';
    } else if (s_line_has_last) {
        s_line_error = 0;
        if (s_line_last_error < 0) {
            target_l = (int16_t)(-LINE_SEARCH_DUTY);
            target_r = LINE_SEARCH_DUTY;
            s_line_dir = 'L';
        } else {
            target_l = LINE_SEARCH_DUTY;
            target_r = (int16_t)(-LINE_SEARCH_DUTY);
            s_line_dir = 'R';
        }
    } else {
        s_line_error = 0;
        target_l = LINE_BASE_DUTY / 2;
        target_r = LINE_BASE_DUTY / 2;
        s_line_dir = 'F';
    }

    s_duty_l = ramp_to(s_duty_l, target_l, LINE_RAMP);
    s_duty_r = ramp_to(s_duty_r, target_r, LINE_RAMP);
    Motor_LeftSet(s_duty_l);
    Motor_RightSet(s_duty_r);
}

static void turn_control(void)
{
    static uint32_t last_ms;
    float yaw, gyro_z, err, output;
    int16_t pwm;

    if (s_mode != MODE_TURN) return;
    if ((uint32_t)(g_millis - last_ms) < TURN_CTRL_MS) return;
    last_ms = g_millis;

    /* 超时保护: 超过 TURN_TIMEOUT_MS 强制停车, 避免卡死 */
    if ((uint32_t)(g_millis - s_turn_start_ms) >= TURN_TIMEOUT_MS) {
        s_mode = MODE_IDLE;
        s_turn_integral = 0.0f;
        s_turn_pwm = 0;
        Motor_Stop();
        return;
    }

    yaw = IMU601_GetYaw();
    gyro_z = IMU601_GetGyroZ();

    /* 角度误差 */
    err = wrap_180(yaw - s_turn_target);
    s_turn_error = err;

    /* 停车判断: 角度误差小 + 角速度小 → 连续 N 次后停车 */
    if (absf(err) <= TURN_STOP_ERR && absf(gyro_z) <= TURN_STOP_GYRO) {
        if (++s_turn_settle >= TURN_SETTLE) {
            s_mode = MODE_IDLE;
            s_turn_integral = 0.0f;
            s_turn_pwm = 0;
            Motor_Stop();
            return;
        }
    } else {
        s_turn_settle = 0U;
    }

    /* PID 计算: 顺时针 yaw/gyroZ 为负, +Kd*gyroZ 用作阻尼 */
    s_turn_integral += err * ((float)TURN_CTRL_MS / 1000.0f);
    if (s_turn_integral >  TURN_INT_LIMIT) s_turn_integral =  TURN_INT_LIMIT;
    if (s_turn_integral < -TURN_INT_LIMIT) s_turn_integral = -TURN_INT_LIMIT;

    output = TURN_KP * err + TURN_KI * s_turn_integral + TURN_KD * gyro_z;
    pwm = clamp_turn_pwm(output, err);
    s_turn_pwm = pwm;

    /* 左轮正转, 右轮反转 → 原地顺时针 */
    Motor_LeftSet(pwm);
    Motor_RightSet((int16_t)(-pwm));
}

/* ========================= 主函数 ========================= */

int main(void)
{
    uint32_t oled_div = 0;
    int16_t spd_l_show = 0, spd_r_show = 0;
    float yaw_show = 0.0f;

    /* 1. SysConfig 外设初始化 */
    SYSCFG_DL_init();
    SysTick_Config(CPUCLK_FREQ / 1000U);   /* 1ms SysTick */

    /* 2. 模块初始化 */
    Motor_Init();
    encoder_init();
    line_sensor_init();
    dbg_init();

    /* 按键上拉 (SysConfig 未配置, 手动初始化) */
    DL_GPIO_initDigitalInputFeatures(KEY_START_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);
    DL_GPIO_initDigitalInputFeatures(KEY_TURN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    /* OLED */
    OLED_Init();
    OLED_Clear();
    OLED_Puts(0, 0, "IMU601 CAR");
    OLED_Puts(1, 0, "INIT...");

    /* IMU601 (会阻塞 ~600ms 等模块就绪) */
    IMU601_Init();
    OLED_Puts(2, 0, "IMU OK");

    /* 启动后自动陀螺仪校准 (静止状态, ~640ms) */
    OLED_Puts(3, 0, "GYRO CAL...");
    IMU601_StartGyroCal();
    while (IMU601_IsGyroCalibrating()) {
        IMU601_ParseService(); /* 解析数据, 喂校准采样 */
    }
    OLED_Puts(4, 0, "CAL DONE");
    delay_cycles(1600000U); /* 显示 500ms */

    OLED_Clear();
    OLED_Puts(0, 0, "IDLE");
    OLED_Puts(7, 0, "25:LINE 26:TURN");

    /* ========================= 主循环 ========================= */
    while (1) {
        /* --- IMU 数据解析 (最高优先级, 防溢出) --- */
        IMU601_ParseService();

        /* bit0~bit7 matches PB25,PB24,PB20,PA14,PB18,PB19,PB10,PA7. */
        s_line_bits = line_sensor_read_active_low();

        /* --- 按键扫描 (每循环一次) --- */
        {
            bool p25 = key_read(KEY_START_PIN);
            uint8_t e25 = key_scan(&s_ks_start, p25);

            /* PA25 短按: 切换直行/停止 */
            if (e25 == 1U && !IMU601_IsGyroCalibrating()) {
                if (s_mode == MODE_LINE) {
                    /* 停止直行 */
                    s_mode = MODE_IDLE;
                    s_balance = 0;
                    s_balance_i = 0;
                    s_duty_l = 0;
                    s_duty_r = 0;
                    s_line_error = 0;
                    s_line_last_error = 0;
                    s_line_has_last = false;
                    s_line_dir = 'S';
                    Motor_Stop();
                } else if (s_mode == MODE_IDLE) {
                    /* 开始直行 */
                    Motor_Stop();
                    encoder_clear_counts();
                    s_mode = MODE_LINE;
                    s_balance = 0;
                    s_balance_i = 0;
                    s_duty_l = 0;
                    s_duty_r = 0;
                    if (line_calc_error(s_line_bits, &s_line_error)) {
                        s_line_last_error = s_line_error;
                        s_line_has_last = true;
                        if (s_line_error < -8)      s_line_dir = 'L';
                        else if (s_line_error > 8)  s_line_dir = 'R';
                        else                        s_line_dir = 'F';
                    } else {
                        s_line_error = 0;
                        s_line_last_error = 0;
                        s_line_has_last = false;
                        s_line_dir = 'S';
                    }
                }
                /* MODE_TURN 时按 PA25 无反应 */
            }

            /* PA25 长按: 陀螺仪校准 (仅 IDLE 状态) */
            if (e25 == 2U && s_mode == MODE_IDLE) {
                Motor_Stop();
                OLED_ClearPage(0);
                OLED_Puts(0, 0, "CALIBRATING...");
                IMU601_StartGyroCal();
            }
        }

        {
            bool p26 = key_read(KEY_TURN_PIN);
            uint8_t e26 = key_scan(&s_ks_turn, p26);

            /* PA26 短按: 启动 90 度转弯 (仅 IDLE 状态) */
            if (e26 == 1U && s_mode == MODE_IDLE &&
                !IMU601_IsGyroCalibrating() && IMU601_IsGyroCalDone()) {
                s_mode = MODE_TURN;
                s_turn_target = wrap_180(IMU601_GetYaw() - TURN_DEG);
                s_turn_integral = 0.0f;
                s_turn_pwm = 0;
                s_turn_error = TURN_DEG;
                s_turn_settle = 0U;
                s_turn_start_ms = g_millis; /* 记录启动时间, 超时保护 */
            }
        }

        /* --- 控制服务 --- */
        straight_control();
        line_control();
        turn_control();

        /* --- 走直线斜坡输出 (10ms 周期) --- */
        if (s_mode == MODE_STRAIGHT) {
            int16_t target_l = (int16_t)(STRAIGHT_DUTY - s_balance);
            int16_t target_r = (int16_t)(STRAIGHT_DUTY + s_balance);
            s_duty_l = ramp_to(s_duty_l, target_l, STRAIGHT_RAMP);
            s_duty_r = ramp_to(s_duty_r, target_r, STRAIGHT_RAMP);
            Motor_LeftSet(s_duty_l);
            Motor_RightSet(s_duty_r);
        }

        /* --- OLED 约 10Hz 刷新 --- */
        if (++oled_div >= 10U) {
            oled_div = 0;
            yaw_show = IMU601_GetYaw();

            /* 读取编码器速度用于显示 (不清零, straight_control 已清) */
            __disable_irq();
            spd_l_show = g_enc_l;
            spd_r_show = g_enc_r;
            __enable_irq();
            if (spd_l_show < 0) spd_l_show = -spd_l_show;
            if (spd_r_show < 0) spd_r_show = -spd_r_show;

            oled_show_status(yaw_show, spd_l_show, spd_r_show);
        }

        /* --- 软串口调试 (500ms) --- */
        {
            static uint32_t last_dbg;
            if ((uint32_t)(g_millis - last_dbg) >= 500U) {
                last_dbg = g_millis;
                char buf[48];
                float gz = IMU601_GetGyroZ();
                snprintf(buf, sizeof(buf), "Y:%.1f GZ:%.1f M:%d L:%02X\r\n",
                         yaw_show, gz, (int)s_mode, s_line_bits);
                dbg_puts(buf);
            }
        }
    }
}
