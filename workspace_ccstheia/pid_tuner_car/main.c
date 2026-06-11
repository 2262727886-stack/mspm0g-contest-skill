/**
 * main.c - PA25 start/stop + UART PID tuner car project
 *
 * Hardware assumptions:
 *   MCU: MSPM0G3507 Tianmengxing board
 *   Motor driver: TB6612FNG
 *   Motors: MG310 encoder motors
 *   Start key: PA25, active low
 *   PID tuner UART: PA10=TX, PA11=RX, 115200 8N1
 *
 * Control loop:
 *   1. PA25 toggles run/stop.
 *   2. PC sends SET/TARGET/STATUS/RESET text commands.
 *   3. MCU sends CSV speed/PWM/PID data for the PC PID tuner.
 */

#include "ti_msp_dl_config.h"
#include "button.h"
#include "encoder.h"
#include "motor.h"
#include "pid_tuner.h"
#include "speed_pid.h"
#include <stdbool.h>
#include <stdint.h>

#define SPEED_PERIOD_MS       20U
#define CSV_PERIOD_MS         40U
#define DEFAULT_PWM_LIMIT     1500

static volatile uint32_t g_ms_ticks;

void SysTick_Handler(void)
{
    g_ms_ticks++;
}

static uint32_t millis(void)
{
    return g_ms_ticks;
}

static bool start_key_raw_pressed(void)
{
    /* PA25 使用上拉输入，按键按下时接地，所以读到 0 表示按下。 */
    return (DL_GPIO_readPins(START_PORT, START_BTN_PIN) == 0U);
}

static void set_run_led(bool running)
{
    if (running) {
        DL_GPIO_setPins(GPIO_PORT, GPIO_LED_PIN);
    } else {
        DL_GPIO_clearPins(GPIO_PORT, GPIO_LED_PIN);
    }
}

int main(void)
{
    Button start_btn;
    SpeedPid pid_left;
    SpeedPid pid_right;
    uint32_t last_speed_ms = 0U;
    uint32_t last_csv_ms = 0U;
    int16_t speed_left = 0;
    int16_t speed_right = 0;
    int16_t pwm_left = 0;
    int16_t pwm_right = 0;
    bool running = false;

    SYSCFG_DL_init();
    SysTick_Config(CPUCLK_FREQ / 1000U);

    /* PA25 必须显式上拉，否则按键悬空时会随机启停。 */
    DL_GPIO_initDigitalInputFeatures(START_BTN_IOMUX,
        DL_GPIO_INVERSION_DISABLE, DL_GPIO_RESISTOR_PULL_UP,
        DL_GPIO_HYSTERESIS_ENABLE, DL_GPIO_WAKEUP_DISABLE);

    button_init(&start_btn, millis());
    encoder_init();
    motor_init();
    pid_tuner_init();

    speed_pid_init(&pid_left, g_pid_tuner.kp, g_pid_tuner.ki,
        g_pid_tuner.kd, DEFAULT_PWM_LIMIT);
    speed_pid_init(&pid_right, g_pid_tuner.kp, g_pid_tuner.ki,
        g_pid_tuner.kd, DEFAULT_PWM_LIMIT);

    motor_stop();
    set_run_led(false);

    while (1) {
        uint32_t now = millis();

        /* 串口轮询放在主循环最高频位置，避免 PC 下发参数时被 CSV 输出饿死。 */
        pid_tuner_poll();

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

        if ((now - last_speed_ms) >= SPEED_PERIOD_MS) {
            last_speed_ms = now;
            encoder_sample_and_clear(&speed_left, &speed_right);

            pid_left.kp = g_pid_tuner.kp;
            pid_left.ki = g_pid_tuner.ki;
            pid_left.kd = g_pid_tuner.kd;
            pid_right.kp = g_pid_tuner.kp;
            pid_right.ki = g_pid_tuner.ki;
            pid_right.kd = g_pid_tuner.kd;

            if (running) {
                pwm_left = speed_pid_update(&pid_left,
                    g_pid_tuner.target_left, speed_left);
                pwm_right = speed_pid_update(&pid_right,
                    g_pid_tuner.target_right, speed_right);
                motor_left_set(pwm_left);
                motor_right_set(pwm_right);
            } else {
                pwm_left = 0;
                pwm_right = 0;
                speed_pid_reset(&pid_left);
                speed_pid_reset(&pid_right);
                motor_stop();
            }
        }

        if ((now - last_csv_ms) >= CSV_PERIOD_MS) {
            last_csv_ms = now;
            pid_tuner_send_csv(now, speed_left, speed_right, pwm_left, pwm_right);
        }
    }
}
