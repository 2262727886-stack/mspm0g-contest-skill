/**
 * @file empty.c
 * @brief MSPM0G car control: OLED on I2C0, MPU6050 on I2C1.
 *
 * Pin table for this stage:
 *   SSD1306 OLED SDA  -> PA28, PINCM3,  I2C0_SDA, address 0x3C
 *   SSD1306 OLED SCL  -> PA31, PINCM6,  I2C0_SCL
 *   MPU6050 SDA       -> PA10,          I2C1_SDA
 *   MPU6050 SCL       -> PA11,          I2C1_SCL
 *   Board LED         -> PB22, GPIO
 *   Gyro zero key     -> PA25, GPIO input pull-up, active low
 *   Start key         -> PA26, GPIO input pull-up, active low
 *
 * PA19/PA20 are SWD, PA2-PA6 are clock pins.
 */
#include "ti_msp_dl_config.h"
#include "oled.h"
#include "i2c_utils.h"
#include "motor.h"
#include "encoder.h"
#include "pid.h"
#include "mpu6050.h"
#include <stdint.h>

#define MOTOR_PID_PERIOD_MS       20U
#define OLED_UPDATE_PERIOD_MS     100U
#define UART_DEBUG_PERIOD_MS      100U
/* 速度环基础目标: 每20ms的编码器边沿数 (MG310霍尔265PPR, 4x解码=1060计数/圈, 轮周长15.08cm, ≈70.3计数/cm) */
/* 4 计数/20ms → 200计数/s → ~2.8 cm/s (慢速稳定行走) */
#define MOTOR_A_TARGET_COUNT      9.0f
#define MOTOR_B_TARGET_COUNT      9.0f
/* PWM 限幅与前馈 (匹配低速目标=6, FF=6×12=72) */
#define MOTOR_PWM_MIN_START       50
#define MOTOR_PWM_MAX_OUTPUT      500
#define MOTOR_PWM_FF_PER_COUNT    12.0f
#define MOTOR_PWM_STEP_PER_PID    20
/* 速度低通滤波: alpha越大响应越快, 0.65→时间常数≈2周期(40ms) */
#define MOTOR_SPEED_FILTER_ALPHA  0.65f
/* 位置环P增益: 1个count的位置误差→速度目标修正0.3个count/周期 (保守, 防速度过冲) */
#define POS_KP                    0.3f
#define POS_KI                    0.01f
#define POS_MAX_INTEGRAL          10.0f
#define POS_ERR_MAX               30      /* 位置误差上限: 超过此值暂停目标前进,防暴冲 */
#define POS_CORR_MAX              6.0f    /* 位置修正上限: 最多改变±6计数/周期 */
#define MOTOR_MAX_SPEED_TARGET    18.0f   /* 速度目标上限: 3×基础速度 */
/* 航向PD: 增益大幅提高, 修正量从±0.6提升到±5.0 */
#define HEADING_KP                1.5f
#define HEADING_KD                0.08f
#define HEADING_CORR_MAX          5.0f
#define HEADING_GYRO_AXIS_X       0
#define HEADING_GYRO_AXIS_Y       1
#define HEADING_GYRO_AXIS_Z       2
#define HEADING_GYRO_AXIS         HEADING_GYRO_AXIS_Z
#define HEADING_GYRO_SIGN         (1.0f)
#define HEADING_CORR_SIGN         (1.0f)
#define MOTOR_A_OUTPUT_SIGN       (-1)
#define MOTOR_B_OUTPUT_SIGN       (-1)
#define MOTOR_A_ENCODER_SIGN      (1)
#define MOTOR_B_ENCODER_SIGN      (-1)

static void delay_ms(uint32_t ms)
{
    for (uint32_t i = 0; i < ms; i++) {
        delay_cycles(CPUCLK_FREQ / 1000U);
    }
}

static uint8_t g_key_was_down = 0U;
static PID g_motor_a_pid;           /* 右轮速度PID (A=右轮, PWMA=PB15) */
static PID g_motor_b_pid;           /* 左轮速度PID (B=左轮, PWMB=PB16) */
static int16_t g_motor_a_speed_raw = 0;
static int16_t g_motor_b_speed_raw = 0;
static int16_t g_motor_a_speed = 0;
static int16_t g_motor_b_speed = 0;
static float g_motor_a_speed_filtered = 0.0f;
static float g_motor_b_speed_filtered = 0.0f;
static int16_t g_motor_a_pwm = 0;
static int16_t g_motor_b_pwm = 0;
static uint8_t g_motor_enable = 0U;
/* 位置环变量: 累积编码器总脉冲, int32_t 防止溢出 */
static int32_t g_pos_a = 0;         /* 右轮累积位置 */
static int32_t g_pos_b = 0;         /* 左轮累积位置 */
static int32_t g_pos_target = 0;    /* 共同位置目标, 每周期递增 */
static float g_pos_a_integral = 0.0f; /* 右轮位置积分 */
static float g_pos_b_integral = 0.0f; /* 左轮位置积分 */
static uint8_t g_start_key_was_down = 0U;
static int g_mpu_status = -99;
static float g_gyro_z_offset = 0.0f;
static float g_yaw_deg = 0.0f;
static float g_yaw_target_deg = 0.0f;
static float g_heading_correction = 0.0f;
static uint16_t g_heading_confidence = 0U;  /* 航向可信度计数, 启动后渐进启用 */
#define HEADING_CONFIDENCE_MAX  50U          /* 50周期=1秒后航向修正全效 */
#ifdef UART_0_INST
static uint8_t g_pending_param = 0U;
static char g_uart_cmd_buf[32];
static uint8_t g_uart_cmd_len = 0U;
static uint8_t g_uart_idle_ms = 0U;

#define PENDING_NONE   0U
#define PENDING_KP     1U
#define PENDING_KI     2U
#define PENDING_KD     3U
#define PENDING_TARGET 4U
#endif

static void int32_to_str(int32_t value, char *buf)
{
    char tmp[12];
    uint8_t i = 0U;
    uint8_t out = 0U;
    int32_t v = value;

    if (v < 0) {
        buf[out++] = '-';
        v = -v;
    }

    do {
        tmp[i++] = (char) ('0' + (uint8_t) (v % 10));
        v /= 10;
    } while (v != 0);

    while (i > 0U) {
        buf[out++] = tmp[--i];
    }
    buf[out] = '\0';
}

static void make_line(char *line, const char *prefix, int32_t value)
{
    uint8_t i = 0U;

    while (*prefix != '\0') {
        line[i++] = *prefix++;
    }
    int32_to_str(value, &line[i]);
}

static int16_t clamp_i32_to_i16(int32_t value, int32_t min_value, int32_t max_value)
{
    if (value > max_value) {
        value = max_value;
    }
    if (value < min_value) {
        value = min_value;
    }
    return (int16_t)value;
}

static float clamp_float_local(float value, float min_value, float max_value)
{
    if (value > max_value) {
        return max_value;
    }
    if (value < min_value) {
        return min_value;
    }
    return value;
}

static int16_t shape_motor_pwm(float pid_output, float target)
{
    int32_t pwm = (int32_t)(pid_output + (target * MOTOR_PWM_FF_PER_COUNT));

    if ((target > 0.1f) && (pwm > 0) && (pwm < MOTOR_PWM_MIN_START)) {
        pwm = MOTOR_PWM_MIN_START;
    } else if ((target < -0.1f) && (pwm < 0) && (pwm > -MOTOR_PWM_MIN_START)) {
        pwm = -MOTOR_PWM_MIN_START;
    }

    return clamp_i32_to_i16(pwm, -MOTOR_PWM_MAX_OUTPUT, MOTOR_PWM_MAX_OUTPUT);
}

static int16_t ramp_motor_pwm(int16_t current, int16_t target)
{
    int32_t delta = (int32_t)target - (int32_t)current;

    if (delta > MOTOR_PWM_STEP_PER_PID) {
        delta = MOTOR_PWM_STEP_PER_PID;
    } else if (delta < -MOTOR_PWM_STEP_PER_PID) {
        delta = -MOTOR_PWM_STEP_PER_PID;
    }

    return (int16_t)((int32_t)current + delta);
}

static void pid_reset_all(void)
{
    pid_reset(&g_motor_a_pid);
    pid_reset(&g_motor_b_pid);
    g_motor_a_speed_filtered = (float)g_motor_a_speed_raw;
    g_motor_b_speed_filtered = (float)g_motor_b_speed_raw;
    g_pos_a_integral = 0.0f;
    g_pos_b_integral = 0.0f;
}

static void motor_stop_all(void)
{
    g_motor_a_pwm = 0;
    g_motor_b_pwm = 0;
    g_motor_a_speed = 0;
    g_motor_b_speed = 0;
    g_motor_a_speed_filtered = 0.0f;
    g_motor_b_speed_filtered = 0.0f;
    Motor_Stop();
}

static void pid_set_target_pair(float target_a, float target_b)
{
    pid_set_target(&g_motor_a_pid, target_a);
    pid_set_target(&g_motor_b_pid, target_b);
}

#ifdef UART_0_INST
static void pid_set_target_all(float target)
{
    pid_set_target_pair(target, target);
}
#endif

static float get_heading_rate_dps(const MPU6050_ScaledData *data)
{
#if HEADING_GYRO_AXIS == HEADING_GYRO_AXIS_X
    return data->gx_dps * HEADING_GYRO_SIGN;
#elif HEADING_GYRO_AXIS == HEADING_GYRO_AXIS_Y
    return data->gy_dps * HEADING_GYRO_SIGN;
#else
    return data->gz_dps * HEADING_GYRO_SIGN;
#endif
}

static void mpu_reset_yaw(void)
{
    /* 快速偏航清零: 不复校陀螺零偏, 不阻塞。用于启动时 */
    g_yaw_deg = 0.0f;
    g_yaw_target_deg = 0.0f;
    g_heading_correction = 0.0f;
    g_heading_confidence = 0U;
}

static void mpu_zero_yaw(void)
{
    MPU6050_ScaledData data;
    float sum = 0.0f;
    uint16_t count = 0U;

    g_yaw_deg = 0.0f;
    g_yaw_target_deg = 0.0f;
    g_heading_correction = 0.0f;
    g_heading_confidence = 0U;  /* 航向软启用复位 */

    if (g_mpu_status != 0) {
        return;
    }

    for (uint16_t i = 0U; i < 200U; i++) {
        if (MPU6050_ReadScaled(&data) == 0) {
            sum += get_heading_rate_dps(&data);
            count++;
        }
        delay_ms(5U);
    }

    /* 采样数不足(通信失败>75%) → 拒绝更新, 保持旧偏移量 */
    if (count < 50U) {
        return;
    }
    float new_offset = sum / (float)count;
    /* 合理性检查: 静止时陀螺零偏不应超过 2°/s, 否则是MPU异常或车在移动 */
    float abs_offset = (new_offset > 0.0f) ? new_offset : -new_offset;
    if (abs_offset > 2.0f) {
        return;  /* 拒绝异常偏移, 保持旧值 */
    }
    g_gyro_z_offset = new_offset;
}

static void mpu_update_heading(void)
{
    MPU6050_ScaledData data;

    if (g_mpu_status != 0) {
        g_heading_correction = 0.0f;
        g_heading_confidence = 0U;
        return;
    }

    if (MPU6050_ReadScaled(&data) == 0) {
        float gz = get_heading_rate_dps(&data) - g_gyro_z_offset;
        float error;

        g_yaw_deg += gz * ((float)MOTOR_PID_PERIOD_MS / 1000.0f);
        error = g_yaw_target_deg - g_yaw_deg;
        g_heading_correction = ((HEADING_KP * error) - (HEADING_KD * gz)) * HEADING_CORR_SIGN;
        g_heading_correction = clamp_float_local(g_heading_correction,
                                                 -HEADING_CORR_MAX,
                                                 HEADING_CORR_MAX);
        /* 航向软启用: 启动后渐进增加修正力度, 防止校准未稳定时乱转 */
        if (g_heading_confidence < HEADING_CONFIDENCE_MAX) {
            g_heading_confidence++;
            float ramp = (float)g_heading_confidence / (float)HEADING_CONFIDENCE_MAX;
            g_heading_correction *= ramp;
        }
    } else {
        /* MPU读取失败不立即归零, 保持上一拍修正值; 但连续失败则衰减 */
        g_heading_correction *= 0.5f;
        g_heading_confidence = 0U;  /* 通信恢复后重新渐进 */
    }
}

static void car_start(void)
{
    motor_stop_all();
    Encoder_ResetPosition();  /* 位置清零 */
    g_pos_a = 0;
    g_pos_b = 0;
    g_pos_target = 0;
    g_pos_a_integral = 0.0f;
    g_pos_b_integral = 0.0f;
    mpu_zero_yaw();           /* 每次启动重新校准陀螺零偏(阻塞1秒), 确保偏移正确 */
    g_yaw_target_deg = g_yaw_deg;
    pid_reset_all();
    pid_set_target_pair(MOTOR_A_TARGET_COUNT, MOTOR_B_TARGET_COUNT);
    g_motor_enable = 1U;
}

static void car_stop(void)
{
    g_motor_enable = 0U;
    pid_set_target_pair(0.0f, 0.0f);
    pid_reset_all();
    motor_stop_all();
}

#ifdef UART_0_INST
static void uart_putc(char c)
{
    DL_UART_Main_transmitDataBlocking(UART_0_INST, (uint8_t)c);
}

static void uart_puts(const char *s)
{
    while (*s != '\0') {
        uart_putc(*s++);
    }
}

static void uart_put_i32(int32_t value)
{
    char buf[12];
    int32_to_str(value, buf);
    uart_puts(buf);
}

static uint8_t starts_with(const char *s, const char *prefix)
{
    while (*prefix != '\0') {
        if (*s++ != *prefix++) {
            return 0U;
        }
    }
    return 1U;
}

static char to_lower_char(char c)
{
    if ((c >= 'A') && (c <= 'Z')) {
        return (char)(c - 'A' + 'a');
    }
    return c;
}

static void normalize_command(const char *src, char *dst, uint8_t dst_size)
{
    uint8_t out = 0U;

    while ((*src != '\0') && (out < (dst_size - 1U))) {
        char c = to_lower_char(*src++);

        if ((c == ' ') || (c == '\t')) {
            continue;
        }
        if (c == ':') {
            c = '=';
        }

        dst[out++] = c;
    }
    dst[out] = '\0';
}

static const char *value_after_key(const char *cmd)
{
    while ((*cmd != '\0') && (*cmd != '=')) {
        cmd++;
    }
    if (*cmd == '=') {
        cmd++;
    }
    return cmd;
}

static uint8_t has_number(const char *s)
{
    while ((*s == '=') || (*s == ' ') || (*s == '\t')) {
        s++;
    }

    if ((*s == '-') || (*s == '+')) {
        s++;
    }

    return (((*s >= '0') && (*s <= '9')) || (*s == '.')) ? 1U : 0U;
}

static float parse_float_value(const char *s)
{
    float value = 0.0f;
    float frac_scale = 0.1f;
    uint8_t neg = 0U;
    uint8_t in_frac = 0U;

    while ((*s == '=') || (*s == ' ') || (*s == '\t')) {
        s++;
    }

    if (*s == '-') {
        neg = 1U;
        s++;
    }

    while (*s != '\0') {
        if (*s == '.') {
            in_frac = 1U;
        } else if ((*s >= '0') && (*s <= '9')) {
            if (in_frac == 0U) {
                value = (value * 10.0f) + (float)(*s - '0');
            } else {
                value += (float)(*s - '0') * frac_scale;
                frac_scale *= 0.1f;
            }
        } else {
            break;
        }
        s++;
    }

    return (neg != 0U) ? -value : value;
}

static void apply_pending_value(float value)
{
    if (g_pending_param == PENDING_KP) {
        g_motor_a_pid.kp = value;
        g_motor_b_pid.kp = value;
        uart_puts("# set kp\r\n");
    } else if (g_pending_param == PENDING_KI) {
        g_motor_a_pid.ki = value;
        g_motor_b_pid.ki = value;
        pid_reset_all();
        uart_puts("# set ki reset_i\r\n");
    } else if (g_pending_param == PENDING_KD) {
        g_motor_a_pid.kd = value;
        g_motor_b_pid.kd = value;
        uart_puts("# set kd\r\n");
    } else if (g_pending_param == PENDING_TARGET) {
        pid_set_target_all(value);
        pid_reset_all();
        g_motor_enable = 1U;
        uart_puts("# set target\r\n");
    }

    g_pending_param = PENDING_NONE;
}

static void pid_apply_command(const char *cmd)
{
    char norm[24];
    normalize_command(cmd, norm, sizeof(norm));

    if ((g_pending_param != PENDING_NONE) && (norm[0] == '=')) {
        const char *v = &norm[1];
        if (has_number(v) != 0U) {
            apply_pending_value(parse_float_value(v));
        } else {
            uart_puts("# wait value\r\n");
        }
    } else if ((g_pending_param != PENDING_NONE) && (has_number(norm) != 0U)) {
        apply_pending_value(parse_float_value(norm));
    } else if ((starts_with(norm, "kp=") != 0U) || (starts_with(norm, "p=") != 0U)) {
        const char *v = value_after_key(norm);
        if (has_number(v) != 0U) {
            g_motor_a_pid.kp = parse_float_value(v);
            g_motor_b_pid.kp = parse_float_value(v);
            uart_puts("# set kp\r\n");
        } else {
            g_pending_param = PENDING_KP;
            uart_puts("# wait kp value\r\n");
        }
    } else if ((norm[0] == 'k') && (norm[1] == 'p') && (norm[2] == '\0')) {
        g_pending_param = PENDING_KP;
        uart_puts("# wait kp value\r\n");
    } else if (starts_with(norm, "p") != 0U) {
        if (has_number(&norm[1]) != 0U) {
            g_motor_a_pid.kp = parse_float_value(&norm[1]);
            g_motor_b_pid.kp = parse_float_value(&norm[1]);
            uart_puts("# set kp\r\n");
        } else {
            g_pending_param = PENDING_KP;
            uart_puts("# wait kp value\r\n");
        }
    } else if ((starts_with(norm, "ki=") != 0U) || (starts_with(norm, "i=") != 0U)) {
        const char *v = value_after_key(norm);
        if (has_number(v) != 0U) {
            g_motor_a_pid.ki = parse_float_value(v);
            g_motor_b_pid.ki = parse_float_value(v);
            pid_reset_all();
            uart_puts("# set ki reset_i\r\n");
        } else {
            g_pending_param = PENDING_KI;
            uart_puts("# wait ki value\r\n");
        }
    } else if ((norm[0] == 'k') && (norm[1] == 'i') && (norm[2] == '\0')) {
        g_pending_param = PENDING_KI;
        uart_puts("# wait ki value\r\n");
    } else if (starts_with(norm, "i") != 0U) {
        if (has_number(&norm[1]) != 0U) {
            g_motor_a_pid.ki = parse_float_value(&norm[1]);
            g_motor_b_pid.ki = parse_float_value(&norm[1]);
            pid_reset_all();
            uart_puts("# set ki reset_i\r\n");
        } else {
            g_pending_param = PENDING_KI;
            uart_puts("# wait ki value\r\n");
        }
    } else if ((starts_with(norm, "kd=") != 0U) || (starts_with(norm, "d=") != 0U)) {
        const char *v = value_after_key(norm);
        if (has_number(v) != 0U) {
            g_motor_a_pid.kd = parse_float_value(v);
            g_motor_b_pid.kd = parse_float_value(v);
            uart_puts("# set kd\r\n");
        } else {
            g_pending_param = PENDING_KD;
            uart_puts("# wait kd value\r\n");
        }
    } else if ((norm[0] == 'k') && (norm[1] == 'd') && (norm[2] == '\0')) {
        g_pending_param = PENDING_KD;
        uart_puts("# wait kd value\r\n");
    } else if (starts_with(norm, "d") != 0U) {
        if (has_number(&norm[1]) != 0U) {
            g_motor_a_pid.kd = parse_float_value(&norm[1]);
            g_motor_b_pid.kd = parse_float_value(&norm[1]);
            uart_puts("# set kd\r\n");
        } else {
            g_pending_param = PENDING_KD;
            uart_puts("# wait kd value\r\n");
        }
    } else if ((starts_with(norm, "t=") != 0U) || (starts_with(norm, "target=") != 0U)) {
        const char *v = value_after_key(norm);
        if (has_number(v) != 0U) {
            pid_set_target_all(parse_float_value(v));
            pid_reset_all();
            g_motor_enable = 1U;
            uart_puts("# set target\r\n");
        } else {
            g_pending_param = PENDING_TARGET;
            uart_puts("# wait target value\r\n");
        }
    } else if ((norm[0] == 't') && (norm[1] == '\0')) {
        g_pending_param = PENDING_TARGET;
        uart_puts("# wait target value\r\n");
    } else if (starts_with(norm, "t") != 0U) {
        if (has_number(&norm[1]) != 0U) {
            pid_set_target_all(parse_float_value(&norm[1]));
            pid_reset_all();
            g_motor_enable = 1U;
            uart_puts("# set target\r\n");
        } else {
            g_pending_param = PENDING_TARGET;
            uart_puts("# wait target value\r\n");
        }
    } else if ((starts_with(norm, "stop") != 0U) || (starts_with(norm, "s0") != 0U)) {
        g_motor_enable = 0U;
        pid_set_target_all(0.0f);
        pid_reset_all();
        motor_stop_all();
        uart_puts("# stop\r\n");
    } else if ((starts_with(norm, "reset") != 0U) || (starts_with(norm, "r") != 0U)) {
        pid_reset_all();
        uart_puts("# reset pid\r\n");
    } else if ((starts_with(norm, "start") != 0U) || (starts_with(norm, "s1") != 0U)) {
        g_motor_enable = 1U;
        uart_puts("# start\r\n");
    } else {
        uart_puts("# unknown cmd: ");
        uart_puts(norm);
        uart_puts("\r\n");
    }
}

static void uart_poll_command(void)
{
    uint8_t got_byte = 0U;

    while (!DL_UART_Main_isRXFIFOEmpty(UART_0_INST)) {
        char c = (char)DL_UART_Main_receiveData(UART_0_INST);
        got_byte = 1U;
        g_uart_idle_ms = 0U;

        if ((c == '\r') || (c == '\n')) {
            continue;
        }

        if ((c == ';') || (c == '!')) {
            if (g_uart_cmd_len > 0U) {
                g_uart_cmd_buf[g_uart_cmd_len] = '\0';
                pid_apply_command(g_uart_cmd_buf);
                g_uart_cmd_len = 0U;
            }
        } else if (g_uart_cmd_len < (sizeof(g_uart_cmd_buf) - 1U)) {
            g_uart_cmd_buf[g_uart_cmd_len++] = c;
        } else {
            g_uart_cmd_len = 0U;
            uart_puts("# cmd too long\r\n");
        }
    }

    if ((got_byte == 0U) && (g_uart_cmd_len > 0U)) {
        if (++g_uart_idle_ms >= 30U) {
            g_uart_cmd_buf[g_uart_cmd_len] = '\0';
            pid_apply_command(g_uart_cmd_buf);
            g_uart_cmd_len = 0U;
            g_uart_idle_ms = 0U;
        }
    }
}
#else
static void uart_putc(char c)
{
    (void)c;
}

static void uart_puts(const char *s)
{
    (void)s;
}

static void uart_put_i32(int32_t value)
{
    (void)value;
}

static void uart_poll_command(void)
{
}
#endif

static char hex_digit(uint8_t v)
{
    v &= 0x0FU;
    if (v < 10U) {
        return (char) ('0' + v);
    }
    return (char) ('A' + (v - 10U));
}

static void append_hex_addr(char *line, uint8_t *idx, uint8_t addr)
{
    if (*idx > 14U) {
        return;
    }

    line[(*idx)++] = ' ';
    line[(*idx)++] = hex_digit((uint8_t) (addr >> 4));
    line[(*idx)++] = hex_digit(addr);
    line[*idx] = '\0';
}

static void scan_bus_to_oled(I2C_Regs *i2c, const char *title, uint16_t hold_ms)
{
    char line[18];
    uint8_t line_idx = 0U;
    uint8_t page = 1U;
    uint8_t found = 0U;

    OLED_Clear();
    OLED_Puts(0, 0, title);

    line[0] = '\0';
    for (uint8_t addr = 0x08U; addr <= 0x77U; addr++) {
        if (i2c_probe_reg(i2c, addr, 0x00U) == 0) {
            append_hex_addr(line, &line_idx, addr);
            found++;

            if (line_idx >= 15U) {
                OLED_Puts(page++, 0, line);
                line[0] = '\0';
                line_idx = 0U;
                if (page >= 7U) {
                    break;
                }
            }
        }
        delay_ms(2U);
    }

    if (line_idx > 0U) {
        OLED_Puts(page++, 0, line);
    }

    if (found == 0U) {
        OLED_Puts(2, 0, "NONE");
    } else {
        make_line(line, "COUNT:", (int16_t) found);
        OLED_Puts(7, 0, line);
    }

    delay_ms(hold_ms);
}

static void show_i2c_scan(void)
{
    scan_bus_to_oled(I2C_OLED_INST, "SCAN I2C0 OLED", 1800U);
}

static void show_status(int oled_ret)
{
    char line[18];

    if (oled_ret != 0) {
        return;
    }

    OLED_Clear();
    OLED_Puts(0, 0, "MSPM0G CAR");
    OLED_Puts(1, 0, "OLED: I2C0 OK");
    if (g_mpu_status == 0) {
        OLED_Puts(2, 0, "MPU: I2C1 OK");
    } else {
        make_line(line, "MPU ERR:", g_mpu_status);
        OLED_Puts(2, 0, line);
    }
    OLED_Puts(4, 0, "A26 START");
    OLED_Puts(5, 0, "A25 ZERO/STOP");
    delay_ms(800U);
}

static uint8_t cal_key_is_down(void)
{
    return (DL_GPIO_readPins(GPIO_KEY_PORT, GPIO_KEY_CAL_KEY_PIN) == 0U) ? 1U : 0U;
}

static uint8_t cal_key_pressed_event(void)
{
    uint8_t down = cal_key_is_down();
    uint8_t pressed = 0U;

    if ((down != 0U) && (g_key_was_down == 0U)) {
        delay_ms(20U);
        if (cal_key_is_down() != 0U) {
            pressed = 1U;
        }
    }

    g_key_was_down = down;
    return pressed;
}

static uint8_t start_key_is_down(void)
{
    return (DL_GPIO_readPins(GPIO_START_PORT, GPIO_START_START_KEY_PIN) == 0U) ? 1U : 0U;
}

static uint8_t start_key_pressed_event(void)
{
    uint8_t down = start_key_is_down();
    uint8_t pressed = 0U;

    if ((down != 0U) && (g_start_key_was_down == 0U)) {
        delay_ms(20U);
        if (start_key_is_down() != 0U) {
            pressed = 1U;
        }
    }

    g_start_key_was_down = down;
    return pressed;
}

static void pid_debug_uart_print(void)
{
    uart_put_i32((int32_t)g_motor_a_pid.target);
    uart_putc(',');
    uart_put_i32((int32_t)g_motor_b_pid.target);
    uart_putc(',');
    uart_put_i32(g_motor_a_speed);
    uart_putc(',');
    uart_put_i32(g_motor_b_speed);
    uart_putc(',');
    uart_put_i32(g_motor_a_pwm);
    uart_putc(',');
    uart_put_i32(g_motor_b_pwm);
    uart_putc(',');
    uart_put_i32((int32_t)g_motor_a_pid.error);
    uart_putc(',');
    uart_put_i32((int32_t)g_motor_b_pid.error);
    uart_putc(',');
    uart_put_i32((int32_t)(g_pos_target - g_pos_a));  /* 右轮位置误差 */
    uart_putc(',');
    uart_put_i32((int32_t)(g_pos_target - g_pos_b));  /* 左轮位置误差 */
    uart_putc(',');
    uart_put_i32((int32_t)(g_heading_correction * 10.0f)); /* 航向修正×10 */
    uart_putc(',');
    uart_put_i32(g_motor_enable);
    uart_puts("\r\n");
}

int main(void)
{
    char line[18];
    int oled_ret;
    uint16_t pid_elapsed_ms = 0U;
    uint16_t oled_elapsed_ms = 0U;
    uint16_t uart_elapsed_ms = 0U;

    SYSCFG_DL_init();
    __enable_irq();

    oled_ret = OLED_Init();
    if (oled_ret == 0) {
        show_i2c_scan();
    }

    g_mpu_status = MPU6050_Init();
    delay_ms(300U);            /* MPU6050 启动后额外稳定时间, 防校准采到瞬态 */
    mpu_zero_yaw();            /* 上电陀螺零偏校准 (阻塞1秒) */
    show_status(oled_ret);
    Motor_Init();
    Encoder_Init();
    pid_init(&g_motor_a_pid, 20.0f, 0.10f, 0.0f, 300.0f, 500.0f, MOTOR_A_TARGET_COUNT);
    pid_init(&g_motor_b_pid, 20.0f, 0.10f, 0.0f, 300.0f, 500.0f, MOTOR_B_TARGET_COUNT);
    uart_puts("# CSV: a_tgt,b_tgt,a_spd,b_spd,a_pwm,b_pwm,a_err,b_err,pos_err_a,pos_err_b,head_corr_x10,en\r\n");
    uart_puts("# cmds: kp=18.0 ki=0.45 kd=0 t=16 pp=0.8 pi=0.02 stop start reset\r\n");
    uart_puts("# B=左轮 A=右轮 | 位置环 PP=POS_KP PI=POS_KI | 航向 HP=HEADING_KP HD=HEADING_KD\r\n");

    if (oled_ret == 0) {
        OLED_Clear();
        OLED_Puts(0, 0, "READY");
        OLED_Puts(1, 0, "PRESS A26");
    }

    while (1) {
        Encoder_Tick();
        pid_elapsed_ms++;
        oled_elapsed_ms++;
        uart_elapsed_ms++;
        uart_poll_command();

        if (cal_key_pressed_event() != 0U) {
            car_stop();
            Encoder_ResetPosition();  /* 编码器位置里程清零 */
            g_pos_a = 0;              /* 位置环全部复位 */
            g_pos_b = 0;
            g_pos_target = 0;
            g_pos_a_integral = 0.0f;
            g_pos_b_integral = 0.0f;
            mpu_zero_yaw();
            if (oled_ret == 0) {
                OLED_ClearPage(7);
                OLED_Puts(7, 0, "CAL OK");
            }
            uart_puts("# CAL: encoder zero + gyro zero done\r\n");
        }

        if (start_key_pressed_event() != 0U) {
            car_start();
            uart_puts("# start by PA26\r\n");
        }

        if (pid_elapsed_ms >= MOTOR_PID_PERIOD_MS) {
            pid_elapsed_ms = 0U;
            Encoder_Update();
            g_motor_a_speed_raw = (int16_t)(MOTOR_A_ENCODER_SIGN * Encoder_GetSpeedCountA());
            g_motor_b_speed_raw = (int16_t)(MOTOR_B_ENCODER_SIGN * Encoder_GetSpeedCountB());
            /* 位置累积: 读取编码器总脉冲 (int32_t, 不溢出) */
            g_pos_a = MOTOR_A_ENCODER_SIGN * Encoder_GetPositionA();
            g_pos_b = MOTOR_B_ENCODER_SIGN * Encoder_GetPositionB();
            if (g_motor_enable != 0U) {
                mpu_update_heading();
                /* 位置目标前进: 但若两轮都严重落后则暂停, 防止目标跑飞 */
                int32_t max_pos_err = (g_pos_target - g_pos_a) > (g_pos_target - g_pos_b)
                                      ? (g_pos_target - g_pos_a) : (g_pos_target - g_pos_b);
                if (max_pos_err < POS_ERR_MAX) {
                    g_pos_target += (int32_t)MOTOR_A_TARGET_COUNT;
                }
                /* --- 位置环: P + I 消除两轮累积距离差异 --- */
                float pos_err_a = (float)(g_pos_target - g_pos_a);
                float pos_err_b = (float)(g_pos_target - g_pos_b);
                g_pos_a_integral += pos_err_a;
                g_pos_b_integral += pos_err_b;
                if (g_pos_a_integral >  POS_MAX_INTEGRAL) g_pos_a_integral =  POS_MAX_INTEGRAL;
                if (g_pos_a_integral < -POS_MAX_INTEGRAL) g_pos_a_integral = -POS_MAX_INTEGRAL;
                if (g_pos_b_integral >  POS_MAX_INTEGRAL) g_pos_b_integral =  POS_MAX_INTEGRAL;
                if (g_pos_b_integral < -POS_MAX_INTEGRAL) g_pos_b_integral = -POS_MAX_INTEGRAL;
                /* 位置修正: P×误差 + I×积分, 然后限幅防止暴冲 */
                float pos_corr_a = POS_KP * pos_err_a + POS_KI * g_pos_a_integral;
                float pos_corr_b = POS_KP * pos_err_b + POS_KI * g_pos_b_integral;
                pos_corr_a = clamp_float_local(pos_corr_a, -POS_CORR_MAX, POS_CORR_MAX);
                pos_corr_b = clamp_float_local(pos_corr_b, -POS_CORR_MAX, POS_CORR_MAX);
                /* 速度目标 = 基础速度 + 位置修正 + 航向修正, 总上限 MOTOR_MAX_SPEED_TARGET */
                /* A=右轮: 航向修正减右轮→右转; B=左轮: 航向修正加左轮→右转 */
                float speed_target_a = MOTOR_A_TARGET_COUNT + pos_corr_a - g_heading_correction;
                float speed_target_b = MOTOR_B_TARGET_COUNT + pos_corr_b + g_heading_correction;
                if (speed_target_a < 0.0f) speed_target_a = 0.0f;
                if (speed_target_a > MOTOR_MAX_SPEED_TARGET) speed_target_a = MOTOR_MAX_SPEED_TARGET;
                if (speed_target_b < 0.0f) speed_target_b = 0.0f;
                if (speed_target_b > MOTOR_MAX_SPEED_TARGET) speed_target_b = MOTOR_MAX_SPEED_TARGET;
                pid_set_target_pair(speed_target_a, speed_target_b);
                /* 速度低通滤波 */
                g_motor_a_speed_filtered += ((float)g_motor_a_speed_raw - g_motor_a_speed_filtered) *
                                            MOTOR_SPEED_FILTER_ALPHA;
                g_motor_b_speed_filtered += ((float)g_motor_b_speed_raw - g_motor_b_speed_filtered) *
                                            MOTOR_SPEED_FILTER_ALPHA;
                g_motor_a_speed = (int16_t)g_motor_a_speed_filtered;
                g_motor_b_speed = (int16_t)g_motor_b_speed_filtered;
                /* 速度环 PID 计算 */
                float pid_out_a = pid_calc(&g_motor_a_pid, g_motor_a_speed_filtered);
                float pid_out_b = pid_calc(&g_motor_b_pid, g_motor_b_speed_filtered);
                int16_t target_pwm_a = shape_motor_pwm(pid_out_a, g_motor_a_pid.target);
                int16_t target_pwm_b = shape_motor_pwm(pid_out_b, g_motor_b_pid.target);
                g_motor_a_pwm = ramp_motor_pwm(g_motor_a_pwm, target_pwm_a);
                g_motor_b_pwm = ramp_motor_pwm(g_motor_b_pwm, target_pwm_b);
                /* A=右轮, B=左轮 */
                Motor_SetA((int16_t)(MOTOR_A_OUTPUT_SIGN * g_motor_a_pwm));
                Motor_SetB((int16_t)(MOTOR_B_OUTPUT_SIGN * g_motor_b_pwm));
            } else {
                g_heading_correction = 0.0f;
                motor_stop_all();
            }
        }

        if ((uart_elapsed_ms >= UART_DEBUG_PERIOD_MS)) {
            uart_elapsed_ms = 0U;
            pid_debug_uart_print();
        }

        if ((oled_elapsed_ms >= OLED_UPDATE_PERIOD_MS) && (oled_ret == 0)) {
            oled_elapsed_ms = 0U;
            DL_GPIO_togglePins(GPIOB, DL_GPIO_PIN_22);

            OLED_ClearPage(1);
            make_line(line, "A:", g_motor_a_speed_raw);
            OLED_Puts(1, 0, line);
            make_line(line, "B:", g_motor_b_speed_raw);
            OLED_Puts(1, 54, line);

            OLED_ClearPage(2);
            make_line(line, "AP:", g_motor_a_pwm);
            OLED_Puts(2, 0, line);
            make_line(line, "BP:", g_motor_b_pwm);
            OLED_Puts(2, 54, line);

            OLED_ClearPage(3);
            make_line(line, "AE:", (int32_t)g_motor_a_pid.error);
            OLED_Puts(3, 0, line);
            make_line(line, "BE:", (int32_t)g_motor_b_pid.error);
            OLED_Puts(3, 54, line);

            OLED_ClearPage(4);
            make_line(line, "PE:", (int32_t)(g_pos_target - g_pos_a));
            OLED_Puts(4, 0, line);
            make_line(line, "Y:", (int32_t)g_yaw_deg);
            OLED_Puts(4, 54, line);

            OLED_ClearPage(5);
            make_line(line, "C:", (int32_t)(g_heading_correction * 10.0f));
            OLED_Puts(5, 0, line);
            make_line(line, "EN:", g_motor_enable);
            OLED_Puts(5, 54, line);
        }
        delay_ms(1U);
    }
}
