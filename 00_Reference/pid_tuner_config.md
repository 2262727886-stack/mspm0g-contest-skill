# PID 调试助手配置指南

## 快速配置

### 1. 串口配置

| 参数 | 值 | 说明 |
|------|-----|------|
| 端口 | COM5 | CH340 USB 转串口 |
| 波特率 | 115200 | MSPM0G UART0 |
| 数据位 | 8 | |
| 校验 | None | |
| 停止位 | 1 | |

### 2. MCU 端代码配置

在 `main.c` 中添加以下配置：

```c
/* ========================= PID 调试助手协议 ========================= */

/* CSV 输出周期 (ms) */
#define PID_TUNER_OUTPUT_PERIOD_MS  20

/* 当前 PID 参数 */
static float g_kp = 3.0f;
static float g_ki = 1.0f;
static float g_kd = 0.0f;

/* 目标速度 */
static int16_t g_target_l = 60;
static int16_t g_target_r = 60;

/* CSV 输出函数 */
static void pid_tuner_output_csv(uint32_t timestamp_ms,
                                  int16_t speed_l, int16_t speed_r,
                                  int16_t target_l, int16_t target_r,
                                  int16_t pwm_l, int16_t pwm_r)
{
    char buf[64];
    int len = sprintf(buf, "%lu,%d,%d,%d,%d,%d,%d,%.1f,%.1f\r\n",
                      timestamp_ms, speed_l, speed_r,
                      target_l, target_r, pwm_l, pwm_r,
                      g_kp, g_ki);
    /* 发送到 UART0 */
    for (int i = 0; i < len; i++) {
        DL_UART_Main_transmitData(UART_0_INST, buf[i]);
    }
}

/* 命令解析函数 */
static void pid_tuner_parse_command(char *cmd)
{
    if (strncmp(cmd, "SET P:", 6) == 0) {
        /* SET P:3.0000 I:1.0000 D:0.0000 */
        sscanf(cmd + 6, "%f", &g_kp);
        char *i_pos = strstr(cmd, "I:");
        if (i_pos) sscanf(i_pos + 2, "%f", &g_ki);
        char *d_pos = strstr(cmd, "D:");
        if (d_pos) sscanf(d_pos + 2, "%f", &g_kd);
        /* 回显确认 */
        uart_printf("OK SET P:%.4f I:%.4f D:%.4f\r\n", g_kp, g_ki, g_kd);
    }
    else if (strncmp(cmd, "TARGET L:", 9) == 0) {
        /* TARGET L:60 R:60 */
        sscanf(cmd + 9, "%d", &g_target_l);
        char *r_pos = strstr(cmd, "R:");
        if (r_pos) sscanf(r_pos + 2, "%d", &g_target_r);
        uart_printf("OK TARGET L=%d R=%d\r\n", g_target_l, g_target_r);
    }
    else if (strcmp(cmd, "STATUS") == 0) {
        /* 返回当前状态 */
        uart_printf("OK STATUS P:%.4f I:%.4f D:%.4f TL:%d TR:%d\r\n",
                    g_kp, g_ki, g_kd, g_target_l, g_target_r);
    }
    else if (strcmp(cmd, "RESET") == 0) {
        /* 重置 PID */
        pid_reset();
        uart_printf("OK RESET\r\n");
    }
    else if (strcmp(cmd, "STOP") == 0) {
        /* 停止电机 */
        motor_stop();
        uart_printf("OK STOP\r\n");
    }
}
```

### 3. 主循环集成

```c
/* 主循环中调用 */
uint32_t last_csv_time = 0;
char cmd_buf[64];
int cmd_idx = 0;

while (1) {
    uint32_t now = sys_tick_ms;

    /* 读取串口命令 */
    while (!DL_UART_isRXFIFOEmpty(UART_0_INST)) {
        char c = (char)DL_UART_Main_receiveData(UART_0_INST);
        if (c == '\n' || c == '\r') {
            if (cmd_idx > 0) {
                cmd_buf[cmd_idx] = '\0';
                pid_tuner_parse_command(cmd_buf);
                cmd_idx = 0;
            }
        } else if (cmd_idx < sizeof(cmd_buf) - 1) {
            cmd_buf[cmd_idx++] = c;
        }
    }

    /* 定时输出 CSV */
    if (now - last_csv_time >= PID_TUNER_OUTPUT_PERIOD_MS) {
        last_csv_time = now;
        pid_tuner_output_csv(now, speed_l, speed_r,
                            g_target_l, g_target_r,
                            duty_l, duty_r);
    }

    /* 其他控制逻辑... */
    delay_ms(1);
}
```

---

## Python 上位机配置

### 安装依赖

```bash
cd PID调试助手
python -m pip install -r requirements.txt
```

### 配置文件

创建 `config.json`：

```json
{
    "SERIAL_PORT": "AUTO",
    "BAUD_RATE": 115200,
    "LLM_API_KEY": "your-api-key-here",
    "LLM_API_BASE_URL": "https://api.openai.com/v1",
    "LLM_MODEL_NAME": "gpt-4o",
    "TUNING_MODE": "speed_pi",
    "BUFFER_SIZE": 100,
    "MAX_TUNING_ROUNDS": 30
}
```

### 启动方式

```bash
# GUI 模式
python PID_DEMO/gui.py

# 仿真模式
python PID_DEMO/launcher.py --sim

# 硬件串口模式
python PID_DEMO/launcher.py --hardware --config config.json
```

---

## VOFA+ 配置

| 参数 | 值 |
|------|-----|
| 端口 | COM5 |
| 波特率 | 115200 |
| 协议 | CSV |
| 分隔符 | `,` |
| 通道 | CH1=速度_L, CH2=速度_R, CH3=目标_L, CH4=目标_R, CH5=PWM_L, CH6=PWM_R |

---

## 调参工作流

1. **测最大速度**: 发送 `B999 T999` 满功率跑 → 记下最大 count
2. **设目标**: `T=上限×0.9` → 设可达目标
3. **设前馈**: `B=上限附近 PWM` → 设前馈
4. **P-only**: `P5 I0 D0` → 看是否稳定
5. **加积分**: `I8` → 消除静差
6. **防振荡**: 降 P 或加 D

---

## 常见问题

| 现象 | 原因 | 解决 |
|------|------|------|
| 上位机无数据 | 串口未连接/波特率错 | 检查 COM5, 115200 |
| CSV 格式错 | 字段顺序不对 | 必须 9 字段: timestamp,speed_L,speed_R,target_L,target_R,pwm_L,pwm_R,Kp,Ki |
| 命令无响应 | 未回显 OK | 检查命令解析代码 |
| 自动调参停止 | TARGET 未回 OK | 确保发送 `OK TARGET L=x R=x` |
