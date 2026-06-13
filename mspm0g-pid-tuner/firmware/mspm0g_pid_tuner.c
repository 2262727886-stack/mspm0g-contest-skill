/**
 * mspm0g_pid_tuner.c — MSPM0G3507 固件：速度PI实时调参 + CSV数据输出
 *
 * 功能：
 *   - TIMG12 中断每20ms触发：读取编码器速度 → PI计算 → 更新PWM → 打印CSV到UART0
 *   - UART0 命令解析：SET P:x I:y / STATUS / RESET / TARGET L:x R:y
 *   - PA26 按键：启动/停止调速循环（含去抖动）
 *   - TB6612 两路电机驱动（A=右轮, B=左轮）
 *   - 编码器：左轮 TIMG7 QEI + 右轮 GPIO双边沿中断（软件4倍频）
 *   - 看门狗在主循环中喂狗
 *
 * 引脚分配:
 *   电机PWM: PB15=TIMG8_C0(R_PWM), PB16=TIMG8_C1(L_PWM)
 *   电机方向: PA13=R_IN1, PA12=R_IN2, PB0=L_IN1, PB1=L_IN2
 *   编码器A(右轮): PA15=A相, PA16=B相 — GPIO双边沿中断  ← QEI读取右轮速度
 *   编码器B(左轮): PA17=TIMG7_CH0, PA24=TIMG7_CH1 — TIMG7 QEI
 *   启动按键: PA26 — 内置上拉, 按下=GND
 *   UART0调试口: PA10=TX, PA11=RX (115200 8N1)
 *   OLED I2C0: PA28=SDA, PA31=SCL (SSD1306 0x3C) — 可选显示
 */

#include "ti_msp_dl_config.h"   // SysConfig 自动生成: SYSCFG_DL_init(), 时钟, 引脚
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h>

/* ========================================================================== */
/*  硬件常量 — 按实际接线修改                                                */
/* ========================================================================== */

/* TB6612 电机驱动引脚 (GPIO 位带输出) */
#define R_IN1_PORT  GPIOA              /* 右轮 IN1: PA13 */
#define R_IN1_PIN   DL_GPIO_PIN_13
#define R_IN2_PORT  GPIOA              /* 右轮 IN2: PA12 */
#define R_IN2_PIN   DL_GPIO_PIN_12
#define L_IN1_PORT  GPIOB              /* 左轮 IN1: PB0 */
#define L_IN1_PIN   DL_GPIO_PIN_0
#define L_IN2_PORT  GPIOB              /* 左轮 IN2: PB1 */
#define L_IN2_PIN   DL_GPIO_PIN_1

/* 启动按键 */
#define START_BTN_PORT  GPIOA
#define START_BTN_PIN   DL_GPIO_PIN_26

/* PWM 参数 (SysConfig 中 TIMG8 设为 up-count, prescaler=0, period=4000 → 20kHz) */
#define PWM_PERIOD      4000U

/* PI 控制周期 (TIMG12 设为 period=大概20ms) */
#define CONTROL_PERIOD_MS  20U

/* 编码器线数 */
#define ENCODER_PPR     11      /* MG310 电机磁编码器: 11 线 */
#define GEAR_RATIO      30.0f   /* 减速比 */

/* 缓冲区大小 */
#define CMD_BUF_SIZE    64
#define CSV_LINE_SIZE   128

/* ========================================================================== */
/*  全局变量                                                                */
/* ========================================================================== */

/* — 速度测量 (单位: 脉冲/20ms, 有符号) — */
static volatile int32_t g_pulse_R = 0;    /* 右轮脉冲累计 (GPIO ISR 填充) */
static volatile int32_t g_pulse_L = 0;    /* 左轮脉冲累计 (QEI 读取差值) */

static int32_t g_last_qei_L = 0;          /* 上一次 QEI 计数器值 */

/* — PI 参数 (运行时可变) — */
static volatile float g_Kp = 2.0f;        /* 比例系数 */
static volatile float g_Ki = 0.5f;        /* 积分系数 */

/* — 目标速度 (脉冲/20ms) — */
static volatile int32_t g_target_R = 0;
static volatile int32_t g_target_L = 0;

/* — PI 积分项 — */
static float g_integral_R = 0.0f;
static float g_integral_L = 0.0f;

/* — 系统状态 — */
static volatile bool g_running = false;   /* 调速循环是否启用 */
static volatile uint32_t g_tick_ms = 0;   /* 系统时间戳 (毫秒, 在TIMG12 ISR中递增) */

/* — 命令缓冲 (UART0 RX ISR 填充, main循环解析) — */
static char g_cmd_buf[CMD_BUF_SIZE];
static volatile uint8_t g_cmd_idx = 0;
static volatile bool g_cmd_ready = false;

/* — 看门狗 — */
#define WWDT_INST  WWDT0

/* ========================================================================== */
/*  工具函数: 设置电机转速与方向                                            */
/* ========================================================================== */

/**
 * @brief 设置单路电机转速
 * @param pwm     TIMG8 实例 (共用)
 * @param in1_port, in1_pin   IN1 引脚
 * @param in2_port, in2_pin   IN2 引脚
 * @param duty    占空比值 (0~PWM_PERIOD)
 *                正数=正转, 负数=反转
 *
 * TB6612 方向铁律:
 *   - A通道 (右轮): IN1=H, IN2=L → 正转 (前进)
 *   - B通道 (左轮): IN1=H, IN2=L → 反转 (前进)
 *   PWM 反逻辑: CC = PERIOD - |duty|  (CC=0→100%占空比, CC=PERIOD→0%)
 */
static void motor_set_raw(uint8_t ch, GPIO_Regs *in1_port, uint32_t in1_pin,
                          GPIO_Regs *in2_port, uint32_t in2_pin, int32_t duty)
{
    bool forward;
    if (duty >= 0) {
        forward = true;
    } else {
        forward = false;
        duty = -duty;
    }
    if (duty > (int32_t)PWM_PERIOD) duty = PWM_PERIOD;

    /* 方向控制 */
    if (forward) {
        DL_GPIO_setPins(in1_port, in1_pin);     /* IN1 = H */
        DL_GPIO_clearPins(in2_port, in2_pin);    /* IN2 = L */
    } else {
        DL_GPIO_clearPins(in1_port, in1_pin);    /* IN1 = L */
        DL_GPIO_setPins(in2_port, in2_pin);      /* IN2 = H */
    }

    /* PWM 反逻辑: CC = PERIOD - duty */
    uint32_t cc = PWM_PERIOD - (uint32_t)duty;
    if (ch == 0) {
        DL_TimerG_setCaptureCompareValue(TIMG8_INST, cc, DL_TIMER_CC_0);
    } else {
        DL_TimerG_setCaptureCompareValue(TIMG8_INST, cc, DL_TIMER_CC_1);
    }
}

/** @brief 右轮调速 (A通道) */
static void motor_R_set(int32_t duty) {
    motor_set_raw(0, R_IN1_PORT, R_IN1_PIN, R_IN2_PORT, R_IN2_PIN, duty);
}

/** @brief 左轮调速 (B通道, IN1=H为反转, 所以取反) */
static void motor_L_set(int32_t duty) {
    /* 左轮: IN1=H → 反转 → 前进, 所以直接传入负值即可 */
    motor_set_raw(1, L_IN1_PORT, L_IN1_PIN, L_IN2_PORT, L_IN2_PIN, -duty);
}

/* ========================================================================== */
/*  UART0 输出 (重定向 printf 或直接调用)                                   */
/* ========================================================================== */

/** @brief 通过 UART0 发送一行 CSV 数据 */
static void uart_print_csv(void)
{
    char line[CSV_LINE_SIZE];
    int32_t pwm_R = PWM_PERIOD - DL_TimerG_getCaptureCompareValue(TIMG8_INST, DL_TIMER_CC_0);
    int32_t pwm_L = PWM_PERIOD - DL_TimerG_getCaptureCompareValue(TIMG8_INST, DL_TIMER_CC_1);

    snprintf(line, sizeof(line),
             "%lu,%ld,%ld,%ld,%ld,%ld,%ld,%.3f,%.3f\r\n",
             (unsigned long)g_tick_ms,
             (long)g_pulse_L, (long)g_pulse_R,   /* 实际速度 */
             (long)g_target_L, (long)g_target_R, /* 目标速度 */
             (long)pwm_L, (long)pwm_R,           /* PWM 占空比 */
             (double)g_Kp, (double)g_Ki);
    DL_UART_Main_transmitDataBlocking(UART0_INST, (uint8_t *)line, strlen(line));
}

/** @brief 通过 UART0 发送字符串 */
static void uart_print(const char *str)
{
    DL_UART_Main_transmitDataBlocking(UART0_INST, (uint8_t *)str, strlen(str));
}

/* ========================================================================== */
/*  PI 控制 (在 TIMG12 ISR 中调用)                                          */
/* ========================================================================== */

/**
 * @brief 根据编码器脉冲数计算速度 PI 输出
 * @param pulse    当前周期的脉冲计数 (有符号)
 * @param target   目标脉冲数
 * @param integral 积分累计值 (指针, 需持久化)
 * @return PWM 占空比 (0~4000)
 */
static int32_t pi_compute(int32_t pulse, int32_t target, float *integral)
{
    int32_t error = target - pulse;

    /* 积分累计 + 抗积分饱和 (PWM范围 0~4000) */
    *integral += g_Ki * (float)error;
    if (*integral > 4000.0f)  *integral = 4000.0f;
    if (*integral < -4000.0f) *integral = -4000.0f;

    float output_f = g_Kp * (float)error + *integral;
    int32_t output = (int32_t)output_f;

    /* PWM 限幅 */
    if (output > 4000) output = 4000;
    if (output < 0)    output = 0;

    return output;
}

/* ========================================================================== */
/*  TIMG12 中断服务程序 (20ms 控制周期)                                     */
/* ========================================================================== */

/** @brief TIMG12 零周期中断: 速度PI计算 + CSV输出 */
void TIMG12_IRQHandler(void)
{
    /* 清除中断标志 (SysConfig 生成函数) */
    DL_TimerG_clearInterruptStatus(TIMG12_INST, DL_TIMER_IIDX_ZERO);

    g_tick_ms += CONTROL_PERIOD_MS;   /* 时间戳递增 */

    if (!g_running) {
        /* 未启动: 电机停转, 积分清零, 脉冲清零 */
        motor_R_set(0);
        motor_L_set(0);
        g_integral_R = 0.0f;
        g_integral_L = 0.0f;
        g_pulse_R = 0;
        g_pulse_L = 0;
        return;
    }

    /* —— 读取左轮速度 (QEI 差值) —— */
    uint32_t qei_now = DL_TimerG_getTimerCount(TIMG7_INST);
    int32_t  qei_diff = (int32_t)(qei_now - g_last_qei_L);
    g_last_qei_L = qei_now;
    g_pulse_L = qei_diff;   /* 左轮脉冲/20ms (有符号) */

    /* —— 读取右轮速度 (GPIO ISR 累计, 原子读取) —— */
    int32_t pulse_R_local = g_pulse_R;
    g_pulse_R = 0;   /* 清零准备下一个周期 */

    /* —— PI 计算 —— */
    int32_t duty_L = pi_compute(g_pulse_L, g_target_L, &g_integral_L);
    int32_t duty_R = pi_compute(pulse_R_local, g_target_R, &g_integral_R);

    /* —— 更新 PWM —— */
    motor_L_set(duty_L);
    motor_R_set(duty_R);

    /* —— CSV 输出 —— */
    uart_print_csv();
}

/* ========================================================================== */
/*  编码器右轮 GPIO 双边沿中断 (软件4倍频)                                  */
/* ========================================================================== */

/**
 * @brief GPIOA 中断: PA15=A相, PA16=B相 双边沿触发实现4倍频
 *
 * 状态机: 根据当前 AB 两相电平组合, 判断旋转方向并计数
 * AB = 00→01→11→10→00 为正转, AB = 00→10→11→01→00 为反转
 */
void GROUP1_IRQHandler(void)
{
    /* 读取 AB 两相当前电平 */
    uint32_t a = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_15) >> 15) & 1U;   /* PA15 = A */
    uint32_t b = (DL_GPIO_readPins(GPIOA, DL_GPIO_PIN_16) >> 16) & 1U;   /* PA16 = B */

    /* 记录上一状态并更新方向 (简化: 用 A 异或上次 B 判断方向) */
    static uint32_t last_ab = 0;  /* bit1=上次A, bit0=上次B */
    uint32_t last_a = (last_ab >> 1) & 1U;
    uint32_t last_b = last_ab & 1U;

    /* 4倍频: A相变化或B相变化都计数, 方向由 A xor B_last 决定 */
    if ((a ^ last_a) || (b ^ last_b)) {
        /* 方向判断: A 异或 上次B */
        if (a ^ last_b) {
            g_pulse_R++;   /* 正转 */
        } else {
            g_pulse_R--;   /* 反转 */
        }
        last_ab = (a << 1) | b;
    }

    /* 清除 GPIOA 中断标志 */
    DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_15);
    DL_GPIO_clearInterruptStatus(GPIOA, DL_GPIO_PIN_16);
}

/* ========================================================================== */
/*  UART0 RX 中断: 接收串口命令                                            */
/* ========================================================================== */

/**
 * @brief UART0 接收中断: 逐字符接收, 遇 '\n' 触发命令解析
 */
void UART0_IRQHandler(void)
{
    uint8_t byte;
    /* 从 RX FIFO 读一个字节 */
    DL_UART_Main_receiveData(UART0_INST, &byte, 1);

    if (byte == '\n' || byte == '\r') {
        if (g_cmd_idx > 0) {
            g_cmd_buf[g_cmd_idx] = '\0';
            g_cmd_ready = true;
            g_cmd_idx = 0;
        }
    } else if (g_cmd_idx < CMD_BUF_SIZE - 1) {
        g_cmd_buf[g_cmd_idx++] = (char)byte;
    }
}

/* ========================================================================== */
/*  命令解析                                                                  */
/* ========================================================================== */

/** @brief 解析并执行串口命令 */
static void parse_command(const char *cmd)
{
    if (strncmp(cmd, "SET ", 4) == 0) {
        /* 格式: SET P:2.5 I:0.3 */
        float p = 0, i = 0;
        if (sscanf(cmd, "SET P:%f I:%f", &p, &i) == 2) {
            g_Kp = p;
            g_Ki = i;
            /* 积分清零, 防止参数突变导致积分冲击 */
            g_integral_R = 0.0f;
            g_integral_L = 0.0f;
            char resp[64];
            snprintf(resp, sizeof(resp), "OK P=%.3f I=%.3f\r\n", (double)g_Kp, (double)g_Ki);
            uart_print(resp);
        } else {
            uart_print("ERR FORMAT: SET P:x I:y\r\n");
        }
    }
    else if (strncmp(cmd, "TARGET ", 7) == 0) {
        /* 格式: TARGET L:100 R:100 (脉冲/20ms) */
        int32_t tL = 0, tR = 0;
        if (sscanf(cmd, "TARGET L:%ld R:%ld", (long *)&tL, (long *)&tR) == 2) {
            g_target_L = tL;
            g_target_R = tR;
            /* 切换目标时清积分 */
            g_integral_R = 0.0f;
            g_integral_L = 0.0f;
            char resp[64];
            snprintf(resp, sizeof(resp), "OK TARGET L=%ld R=%ld\r\n", (long)g_target_L, (long)g_target_R);
            uart_print(resp);
        } else {
            uart_print("ERR FORMAT: TARGET L:x R:y\r\n");
        }
    }
    else if (strcmp(cmd, "STATUS") == 0) {
        char resp[128];
        snprintf(resp, sizeof(resp),
                 "STATUS: run=%d Kp=%.3f Ki=%.3f TGT_L=%ld TGT_R=%ld SPD_L=%ld SPD_R=%ld\r\n",
                 g_running ? 1 : 0,
                 (double)g_Kp, (double)g_Ki,
                 (long)g_target_L, (long)g_target_R,
                 (long)g_pulse_L, (long)g_pulse_R);
        uart_print(resp);
    }
    else if (strcmp(cmd, "RESET") == 0) {
        g_Kp = 2.0f;
        g_Ki = 0.5f;
        g_target_L = 0;
        g_target_R = 0;
        g_integral_R = 0.0f;
        g_integral_L = 0.0f;
        g_running = false;
        g_cmd_idx = 0;
        uart_print("OK RESET\r\n");
    }
    else if (strcmp(cmd, "STOP") == 0) {
        g_running = false;
        motor_R_set(0);
        motor_L_set(0);
        uart_print("OK STOPPED\r\n");
    }
    else if (strcmp(cmd, "START") == 0) {
        g_running = true;
        uart_print("OK STARTED\r\n");
    }
    else if (cmd[0] != '\0') {
        uart_print("ERR UNKNOWN CMD\r\n");
    }
    /* cmd[0]=='\0' 是空行, 忽略 */
}

/* ========================================================================== */
/*  按键扫描 (去抖动)                                                        */
/* ========================================================================== */

/**
 * @brief 读取 PA26 按键状态 (内置上拉, 按下=0)
 * @return true 按键刚按下 (下降沿)
 */
static bool start_btn_pressed(void)
{
    static uint32_t last_stable = 1;      /* 上次稳定值 (未按下=1) */
    static uint32_t debounce_cnt = 0;
    static bool     last_state = false;  /* 上次输出状态 */

    uint32_t raw = (DL_GPIO_readPins(START_BTN_PORT, START_BTN_PIN) != 0) ? 1U : 0U;

    if (raw == last_stable) {
        debounce_cnt = 0;
    } else {
        debounce_cnt++;
        if (debounce_cnt >= 5) {   /* 约5ms去抖 (每ms扫描一次) */
            last_stable = raw;
            debounce_cnt = 0;
        }
    }

    bool current_state = (last_stable == 0U);  /* true = 按下 */
    bool edge = current_state && !last_state;
    last_state = current_state;
    return edge;
}

/* ========================================================================== */
/*  主函数                                                                    */
/* ========================================================================== */

int main(void)
{
    /* —— SysConfig 生成的外设初始化 (时钟, GPIO, TIMG, UART0) —— */
    SYSCFG_DL_init();

    /* —— 电机停止 —— */
    motor_R_set(0);
    motor_L_set(0);

    /* —— 使能中断 —— */
    NVIC_EnableIRQ(TIMG12_INT_IRQn);   /* 20ms 控制周期 */
    NVIC_EnableIRQ(GPIOA_INT_IRQn);    /* 编码器右轮 */
    NVIC_EnableIRQ(UART0_INT_IRQn);    /* 串口命令 */

    /* —— 发送就绪信号 —— */
    uart_print("MSPM0G PID TUNER READY\r\n");

    /* —— 主循环 —— */
    while (1) {
        /* 喂狗 */
        DL_WWDT_restart(WWDT0_INST);

        /* 按键扫描: 切换启动/停止 */
        if (start_btn_pressed()) {
            if (g_running) {
                g_running = false;
                motor_R_set(0);
                motor_L_set(0);
                uart_print("BTN: STOPPED\r\n");
            } else {
                g_running = true;
                g_integral_R = 0.0f;
                g_integral_L = 0.0f;
                uart_print("BTN: STARTED\r\n");
            }
        }

        /* 串口命令处理 */
        if (g_cmd_ready) {
            g_cmd_ready = false;
            parse_command(g_cmd_buf);
        }

        /* 1ms 延时 (用于按键去抖) */
        DL_Delay_us(1000);
    }

    return 0;
}
