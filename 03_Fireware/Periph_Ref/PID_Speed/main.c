/*
 * MSPM0G3507 speed PID demo.
 *
 * UART commands:
 *   P50<enter>  -> Kp = 5.0
 *   I10<enter>  -> Ki = 0.10
 *   D5<enter>   -> Kd = 0.05
 *   T42<enter>  -> target encoder counts per control period
 *   B800<enter> -> base PWM feed-forward
 */
#include "ti_msp_dl_config.h"
#include "motor.h"
#include "encoder.h"
#include "pid.h"

#define PID_PERIOD_MS         (20U)
#define PID_SYSTICK_LOAD      (CPUCLK_FREQ / 1000U * PID_PERIOD_MS)
#define PID_MAX_INTEGRAL      (2500.0f)
#define PID_MAX_OUTPUT        (1000.0f)
#define PWM_LIMIT             (1000)
#define PWM_STEP_LIMIT        (4)

static PID g_speed_pid;
static int g_kp_x10 = 5;
static int g_ki_x100 = 8;
static int g_kd_x100 = 0;
static int g_target = 42;
static int g_base_pwm = 800;
static volatile uint8_t g_pid_tick = 0;

void SysTick_Handler(void)

{
    g_pid_tick = 1;
}

static void uart_putc(char c)
{
    DL_UART_Main_transmitDataBlocking(UART_0_INST, c);
}

static void uart_print_num(int n)
{
    char buf[12];
    int i = 0;

    if (n < 0) {
        uart_putc('-');
        n = -n;
    }

    if (n == 0) {
        uart_putc('0');
        return;
    }

    while (n > 0) {
        buf[i++] = (char)('0' + (n % 10));
        n /= 10;
    }
    while (i > 0) {
        uart_putc(buf[--i]);
    }
}

static void uart_print_pid(void)
{
    uart_putc('P');
    uart_print_num(g_kp_x10);
    uart_putc(' ');
    uart_putc('I');
    uart_print_num(g_ki_x100);
    uart_putc(' ');
    uart_putc('D');
    uart_print_num(g_kd_x100);
    uart_putc(' ');
    uart_putc('T');
    uart_print_num(g_target);
    uart_putc(' ');
    uart_putc('B');
    uart_print_num(g_base_pwm);
    uart_putc('\n');
}

static void pid_apply_params(void)
{
    float kp = (float)g_kp_x10 / 10.0f;
    float ki = (float)g_ki_x100 / 100.0f;
    float kd = (float)g_kd_x100 / 100.0f;

    pid_init(&g_speed_pid, kp, ki, kd,
             PID_MAX_INTEGRAL, PID_MAX_OUTPUT, (float)g_target);
    uart_print_pid();
}

static int limit_pwm(int pwm)
{
    if (pwm > PWM_LIMIT) {
        return PWM_LIMIT;
    }
    if (pwm < -PWM_LIMIT) {
        return -PWM_LIMIT;
    }
    return pwm;
}

static int limit_pwm_step(int pwm, int last_pwm)
{
    if (pwm > last_pwm + PWM_STEP_LIMIT) {
        return last_pwm + PWM_STEP_LIMIT;
    }
    if (pwm < last_pwm - PWM_STEP_LIMIT) {
        return last_pwm - PWM_STEP_LIMIT;
    }
    return pwm;
}

static void uart_poll_params(void)
{
    static int value = 0;
    static int mode = 0;

    while (!DL_UART_isRXFIFOEmpty(UART_0_INST)) {
        char c = (char)DL_UART_Main_receiveData(UART_0_INST);

        if (c >= '0' && c <= '9') {
            value = value * 10 + (c - '0');
        } else if (c == 'P' || c == 'p') {
            mode = 1;
            value = 0;
        } else if (c == 'I' || c == 'i') {
            mode = 2;
            value = 0;
        } else if (c == 'D' || c == 'd') {
            mode = 3;
            value = 0;
        } else if (c == 'T' || c == 't') {
            mode = 4;
            value = 0;
        } else if (c == 'B' || c == 'b') {
            mode = 5;
            value = 0;
        } else {
            if (mode == 1) {
                g_kp_x10 = value;
            } else if (mode == 2) {
                g_ki_x100 = value;
            } else if (mode == 3) {
                g_kd_x100 = value;
            } else if (mode == 4) {
                g_target = value;
            } else if (mode == 5) {
                g_base_pwm = value;
            }

            if (mode != 0) {
                pid_apply_params();
            }
            mode = 0;
            value = 0;
        }
    }
}

int main(void)
{
    int last_pwm = g_base_pwm;

    SYSCFG_DL_init();
    __enable_irq();

    Motor_Init();
    Encoder_Init();
    DL_TimerG_startCounter(PWM_TB6612_INST);
    DL_SYSTICK_config(PID_SYSTICK_LOAD);
    pid_apply_params();

    while (1) {
        Encoder_Tick();
        uart_poll_params();

        if (g_pid_tick != 0) {
            int count;
            int pwm;

            g_pid_tick = 0;
            Encoder_Update();

            count = Encoder_GetCount();
            if (count < 0) {
                count = -count;
            }

            pwm = limit_pwm(g_base_pwm +
                            (int)pid_calc(&g_speed_pid, (float)count));
            pwm = limit_pwm_step(pwm, last_pwm);
            last_pwm = pwm;
            Motor_B((int16_t)pwm);

            static uint8_t csv_skip = 0;
            if (++csv_skip >= 4) {  // 每4个PID周期(=80ms)发一次CSV
                csv_skip = 0;
                uart_print_num(count);   uart_putc(',');
                uart_print_num(pwm);     uart_putc(',');
                uart_print_num(g_target); uart_putc(',');
                uart_print_num(g_kp_x10); uart_putc(',');
                uart_print_num(g_ki_x100); uart_putc(',');
                uart_print_num(g_kd_x100); uart_putc(',');
                uart_print_num(g_base_pwm);
                uart_putc('\n');
            }
        }
    }
}
