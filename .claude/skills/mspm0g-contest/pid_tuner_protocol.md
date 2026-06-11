# MSPM0G3507 PID Tuner 通信协议模板

PC 端 PID 自动调参工具与 MSPM0G3507 固件的通信协议。用户若要使用自动 PID 调参功能，MCU 固件必须按此模板实现。

> **硬性规范**：PID 调试助手只支持本页定义的 UART 协议。固件若没有实现本协议，尤其是 `TARGET`/`STATUS` 回包和 9 字段 CSV，GUI 会判定通信未就绪，不能进入自动调参。

---

## 1. 通信概述

| 参数 | 值 |
|------|-----|
| 接口 | UART (推荐 PA10=TX, PA11=RX) |
| 波特率 | 115200, 8N1 |
| 通信方式 | 全双工: MCU 持续发 CSV 数据, PC 随时发文本命令 |
| MCU→PC 格式 | CSV 行, `\r\n` 结尾 |
| PC→MCU 格式 | 文本命令, `\r\n` 结尾 |

**接线必须交叉**：

| 方向 | 接线 |
|------|------|
| MCU 发数据 | MSPM0G `PA10/UART0_TX` → CH340/USB 串口 `RX` |
| PC 发命令 | CH340/USB 串口 `TX` → MSPM0G `PA11/UART0_RX` |
| 共地 | CH340/USB 串口 `GND` ↔ MSPM0G `GND` |

---

## 2. MCU → PC: CSV 数据格式

```
timestamp,speed_L,speed_R,target_L,target_R,pwm_L,pwm_R,Kp,Ki\r\n
```

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| timestamp | int | 时间戳 (可填 0) | `0` |
| speed_L | int | 左轮当前速度 (编码器脉冲) | `45` |
| speed_R | int | 右轮当前速度 | `46` |
| target_L | int | 左轮目标速度 | `60` |
| target_R | int | 右轮目标速度 | `60` |
| pwm_L | int | 左轮 PWM 占空比 | `1000` |
| pwm_R | int | 右轮 PWM 占空比 | `1000` |
| Kp | float | 当前速度环 Kp | `3.000` |
| Ki | float | 当前速度环 Ki | `1.000` |

**发送频率**: 建议 20~50ms 一次 (20~50Hz)

**示例数据流**:
```
0,58,59,60,60,1000,1000,3.000,1.000
0,56,57,60,60,1000,1000,3.000,1.000
0,54,55,60,60,1000,1000,3.000,1.000
```

---

## 3. PC → MCU: 命令格式

| 命令 | 格式 | 说明 | 应答 |
|------|------|------|------|
| SET | `SET P:3.5 I:1.2\r\n` | 修改 Kp/Ki | `OK P=3.500 I=1.200 D=0.000` |
| SET+D | `SET P:3.5 I:1.2 D:0.0\r\n` | 修改 Kp/Ki/Kd | `OK P=3.500 I=1.200 D=0.000` |
| STATUS | `STATUS\r\n` | 查询当前状态 | `P=3.500 I=1.200 D=0.000 TL=60 TR=60` |
| RESET | `RESET\r\n` | 恢复默认 PID | `OK RESET` |
| STOP | `STOP\r\n` | 目标速度清零并停车 | `OK STOP` |
| TARGET | `TARGET L:60 R:60\r\n` | 修改左右轮目标速度 | `OK TARGET L=60 R=60` |

**注意**:
- 命令以 `\r\n` 结尾
- SET 命令同时修改左右轮 PID (当前版本共用参数)
- Kp 范围: 0.1 ~ 50.0, Ki 范围: 0.0 ~ 20.0
- 自动调参启动时会先发送 `TARGET L:<目标> R:<目标>`，并等待 `OK TARGET L=<目标> R=<目标>`、`STATUS` 中 `TL/TR` 匹配，或 CSV 中 `target_L/target_R` 匹配。若仍回显 `20,20`，说明 PC→MCU 的 RX 线未通或固件不是最新协议。

---

## 4. SysConfig 配置

```
UART 实例:
  Name:        DEBUG_UART (或任意名)
  TX Pin:      PA10
  RX Pin:      PA11
  Baud Rate:   115200
  Frame:       8N1
  RX FIFO:     1 byte threshold
  TX FIFO:     3/4 empty threshold
```

SysConfig 脚本参考:
```js
const UART1 = UART.addInstance();
UART1.$name                    = "DEBUG_UART";
UART1.targetBaudRate           = 115200;
UART1.enableFIFO               = true;
UART1.peripheral.$assign       = "UART0";
UART1.peripheral.txPin.$assign = "PA10";
UART1.peripheral.rxPin.$assign = "PA11";
```

---

## 5. 固件代码模板

### 5.1 PID 变量 (全局, volatile)

```c
volatile float g_tuner_Kp = 3.0f;      // 速度环 Kp
volatile float g_tuner_Ki = 1.0f;      // 速度环 Ki
volatile int16_t g_tuner_target = 60;  // 目标速度
```

**关键**: 这些变量必须是 `volatile`，因为 UART 中断会修改它们。用户代码中直接使用 `g_tuner_Kp` / `g_tuner_Ki` 替代硬编码的 PID 常量。

### 5.2 CSV 输出函数

在速度 PI 计算完成后调用 (20~50ms 一次):

```c
static void send_csv(int16_t spd_l, int16_t spd_r,
                     int16_t duty_l, int16_t duty_r)
{
    char line[96];
    int len = snprintf(line, sizeof(line),
        "%d,%d,%d,%d,%d,%d,%d,%.3f,%.3f\r\n",
        0, (int)spd_l, (int)spd_r,
        (int)g_tuner_target, (int)g_tuner_target,
        (int)duty_l, (int)duty_r,
        (double)g_tuner_Kp, (double)g_tuner_Ki);
    for (int i = 0; i < len; i++)
        DL_UART_transmitDataBlocking(DEBUG_UART_INST, (uint8_t)line[i]);
}
```

### 5.3 UART 接收中断

```c
#define CMD_BUF_SIZE  32
static char   g_cmd_buf[CMD_BUF_SIZE];
static uint8_t g_cmd_idx;

void DEBUG_UART_INST_IRQHandler(void)
{
    switch (DL_UART_getPendingInterrupt(DEBUG_UART_INST)) {
    case DL_UART_IIDX_RX: {
        uint8_t ch = DL_UART_receiveData(DEBUG_UART_INST);
        if (ch == '\r' || ch == '\n') {
            if (g_cmd_idx > 0) {
                g_cmd_buf[g_cmd_idx] = '\0';
                parse_tuner_cmd(g_cmd_buf);
                g_cmd_idx = 0;
            }
        } else if (g_cmd_idx < CMD_BUF_SIZE - 1) {
            g_cmd_buf[g_cmd_idx++] = (char)ch;
        }
        break;
    }
    default: break;
    }
}
```

### 5.4 命令解析

```c
static void parse_tuner_cmd(const char *cmd)
{
    float p, i; int t, len; char resp[64];
    (void)t;

    if (sscanf(cmd, "SET P:%f I:%f", &p, &i) == 2) {
        if (p > 0.1f && p <= 50.0f)  g_tuner_Kp = p;
        if (i >= 0.0f && i <= 20.0f) g_tuner_Ki = i;
        len = snprintf(resp, sizeof(resp), "OK P=%.3f I=%.3f\r\n",
                       (double)g_tuner_Kp, (double)g_tuner_Ki);
    }
    else if (strncmp(cmd, "STATUS", 6) == 0) {
        len = snprintf(resp, sizeof(resp), "P=%.3f I=%.3f TGT=%d\r\n",
                       (double)g_tuner_Kp, (double)g_tuner_Ki, (int)g_tuner_target);
    }
    else if (strncmp(cmd, "RESET", 5) == 0) {
        g_tuner_Kp = 3.0f; g_tuner_Ki = 1.0f; g_tuner_target = 60;
        len = snprintf(resp, sizeof(resp), "OK RESET\r\n");
    }
    else { return; }

    for (int i = 0; i < len; i++)
        DL_UART_transmitDataBlocking(DEBUG_UART_INST, (uint8_t)resp[i]);
}
```

---

## 6. 完整参考工程

`workspace_ccstheia/pid_tuner_test/` — 最小验证工程
- `main.c` — 完整通信模板 (含三角波测试数据生成)
- `empty.syscfg` — SysConfig UART 配置
- 编译烧录后可用 PC 端 PID Tuner 连接验证

---

## 7. 集成到现有工程的步骤

1. **SysConfig**: 添加 UART, PA10=TX, PA11=RX, 115200
2. **变量**: 将原有 `#define SPEED_KP` / `#define SPEED_KI` 替换为 `extern volatile float g_tuner_Kp/g_tuner_Ki`
3. **CSV 输出**: 在速度 PI 计算后调用 `send_csv()`
4. **中断**: 添加 UART RX 中断处理函数
5. **命令解析**: 复制 `parse_tuner_cmd()` 函数
6. **编译** → PC 端 PID Tuner 连接同一 COM 口 → 开始调参
