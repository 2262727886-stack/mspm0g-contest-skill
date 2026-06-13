/**
 * main.c — MSPM0G3507 小车速度 PID 闭环 + 串口调试助手
 *
 * 硬件:
 *   MCU:       MSPM0G3507 (天猛星开发板)
 *   电机驱动:  TB6612FNG
 *   电机:      MG310 直流减速电机 + 霍尔编码器
 *   启动按键:  PA25 (低电平有效)
 *   调试串口:  UART0, PA10=TX, PA11=RX, 115200 8N1
 *
 * 控制逻辑:
 *   1. PA25 按键切换 运行/停止
 *   2. 运行时: 每 20ms 读编码器 → PID 计算 → PWM 输出
 *   3. 调试模式: PC 通过串口实时修改 PID 参数和目标速度
 *   4. 比赛模式: 关闭串口输出 (PID_TUNER_ENABLE=0), 纯 MCU 独立运行
 *
 * PID 算法:
 *   位置式 PID + 前馈
 *   output = target * pwm_per_pulse + Kp*e + Ki*Σe + Kd*Δe
 *   前馈项 (target * pwm_per_pulse) 提供基础 PWM, PID 只修正残余误差
 */

#include "ti_msp_dl_config.h"
#include "button.h"
#include "encoder.h"
#include "motor.h"
#include "pid_tuner.h"
#include "speed_pid.h"
#include <stdbool.h>
#include <stdint.h>

/* ═══════════════════════════════════════════════════════════════
 * 可调参数
 * ═══════════════════════════════════════════════════════════════ */

/* 速度闭环周期 (ms)。编码器每 20ms 采样一次，对应 50Hz 控制频率。 */
#define SPEED_PERIOD_MS       20U

/* CSV 输出周期 (ms)。调试时 40ms 发一次数据给 PC。比赛时无效 (宏关闭)。 */
#define CSV_PERIOD_MS         40U

/**
 * 前馈系数: 每个编码器脉冲对应多少 PWM
 *
 * 含义: 目标速度 60 脉冲/20ms → 基础 PWM = 60 * 8 = 480
 * PID 在此基础上 ±修正。
 *
 * 调参建议:
 *   - 先设 kp=0, ki=0, 只用前馈: 把 target 设到期望速度
 *   - 逐渐增大此值, 看编码器读数能否接近 target
 *   - 读数偏小 → 增大; 读数偏大 → 减小
 *   - 典型范围: 5~15 (取决于电池电压和地面摩擦力)
 */
#define DEFAULT_PWM_PER_PULSE 8

/**
 * PWM 输出上限
 *
 * TIMG8 周期 = 2133, 死区 = 30, 所以最大有效 duty = 2103。
 * 设 1500 留余量, 防止电机满功率失控。
 */
#define DEFAULT_PWM_LIMIT     1500

/* ═══════════════════════════════════════════════════════════════
 * 全局变量
 * ═══════════════════════════════════════════════════════════════ */

/* SysTick 毫秒计数器 (1ms 中断递增) */
static volatile uint32_t g_ms_ticks;

void SysTick_Handler(void)
{
    g_ms_ticks++;
}

static uint32_t millis(void)
{
    return g_ms_ticks;
}

/**
 * PA25 按键原始状态 (上拉输入, 按下接地)
 */
static bool start_key_raw_pressed(void)
{
    return (DL_GPIO_readPins(START_PORT, START_BTN_PIN) == 0U);
}

/**
 * LED 状态指示
 */
static void set_run_led(bool running)
{
    if (running) {
        DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN);
    } else {
        DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN);
    }
}

/* ═══════════════════════════════════════════════════════════════
 * 主函数
 * ═══════════════════════════════════════════════════════════════ */
int main(void)
{
    Button start_btn;           /* 启动按键去抖状态 */
    SpeedPid pid_left;          /* 左轮 PID 控制器 */
    SpeedPid pid_right;         /* 右轮 PID 控制器 */
    uint32_t last_speed_ms = 0U;  /* 上次速度闭环时间 */
    uint32_t last_csv_ms = 0U;    /* 上次 CSV 输出时间 */
    int16_t speed_left = 0;       /* 左轮当前速度 (脉冲/20ms) */
    int16_t speed_right = 0;      /* 右轮当前速度 (脉冲/20ms) */
    int16_t pwm_left = 0;         /* 左轮 PWM 输出 */
    int16_t pwm_right = 0;        /* 右轮 PWM 输出 */
    bool running = false;         /* 运行状态 */

    /* ── 系统初始化 ── */
    SYSCFG_DL_init();
    SysTick_Config(CPUCLK_FREQ / 1000U);  /* 1ms SysTick */

    /* PA25 按键: 上拉输入 + 滞回 */
    DL_GPIO_initDigitalInputFeatures(START_BTN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    button_init(&start_btn, millis());
    encoder_init();       /* 编码器 GPIO 中断初始化 */
    motor_init();         /* 电机 PWM + 方向 GPIO 初始化 */
    pid_tuner_init();     /* UART 调试助手初始化 */

    /* ── PID 控制器初始化 (使用调试助手默认值) ── */
    speed_pid_init(&pid_left, g_pid_tuner.kp, g_pid_tuner.ki,
        g_pid_tuner.kd, DEFAULT_PWM_PER_PULSE, DEFAULT_PWM_LIMIT);
    speed_pid_init(&pid_right, g_pid_tuner.kp, g_pid_tuner.ki,
        g_pid_tuner.kd, DEFAULT_PWM_PER_PULSE, DEFAULT_PWM_LIMIT);

    motor_stop();
    set_run_led(false);

    /* ═══════════════════════════════════════════════════════════
     * 主循环
     * ═══════════════════════════════════════════════════════════ */
    while (1) {
        uint32_t now = millis();

#if PID_TUNER_ENABLE
        /* 调试模式: 轮询 UART 接收 PC 命令 (高频, 避免被 CSV 饿死) */
        pid_tuner_poll();
#endif

        /* ── PA25 按键: 切换运行/停止 ── */
        if (button_update_pressed_event(&start_btn, start_key_raw_pressed(), now)) {
            running = !running;
            speed_pid_reset(&pid_left);
            speed_pid_reset(&pid_right);
            pwm_left = 0;
            pwm_right = 0;
            if (!running) {
                motor_stop();
            }
            set_run_led(running);
        }

        /* ── PC 下发 RESET 命令 ── */
        if (g_pid_tuner.reset_request) {
            g_pid_tuner.reset_request = false;
            speed_pid_reset(&pid_left);
            speed_pid_reset(&pid_right);
            pwm_left = 0;
            pwm_right = 0;
            if (!running) {
                motor_stop();
            }
        }

        /* ── 速度闭环 (每 SPEED_PERIOD_MS 执行一次) ── */
        if ((now - last_speed_ms) >= SPEED_PERIOD_MS) {
            last_speed_ms = now;

            /* 读取编码器并清零 (原子操作) */
            encoder_sample_and_clear(&speed_left, &speed_right);

            /* 同步 PC 下发的最新 PID 参数 */
            pid_left.kp = g_pid_tuner.kp;
            pid_left.ki = g_pid_tuner.ki;
            pid_left.kd = g_pid_tuner.kd;
            pid_right.kp = g_pid_tuner.kp;
            pid_right.ki = g_pid_tuner.ki;
            pid_right.kd = g_pid_tuner.kd;

            if (running) {
                /* PID 计算: 前馈 + 位置式 PID */
                pwm_left = speed_pid_update(&pid_left,
                    g_pid_tuner.target_left, speed_left);
                pwm_right = speed_pid_update(&pid_right,
                    g_pid_tuner.target_right, speed_right);
                motor_left_set(pwm_left);
                motor_right_set(pwm_right);
            } else {
                /* 停车: 清零 PID 状态和 PWM */
                pwm_left = 0;
                pwm_right = 0;
                speed_pid_reset(&pid_left);
                speed_pid_reset(&pid_right);
                motor_stop();
            }
        }

#if PID_TUNER_ENABLE
        /* 调试模式: 每 CSV_PERIOD_MS 发送 CSV 数据给 PC */
        if ((now - last_csv_ms) >= CSV_PERIOD_MS) {
            last_csv_ms = now;
            pid_tuner_send_csv(now, speed_left, speed_right, pwm_left, pwm_right);
        }
#endif
    }
}
