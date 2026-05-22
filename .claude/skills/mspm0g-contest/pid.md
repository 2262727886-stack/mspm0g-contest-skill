# PID + 滤波器 + 电机控制

## PID 控制器

### PID 控制器 (⚠️ 重点章节 — 实测调参验证)

#### 架构铁律

```
前馈 PWM (Base) + PID 增量 — 不要从 0 起调!
┌──────────┐     ┌──────────┐     ┌───────────┐
│ SysTick  │ ──→ │ Encoder  │ ──→ │ PID calc  │ ──→ PWM = Base ± Δ
│ 10/20ms  │     │ Update() │     │ (position)│
└──────────┘     └──────────┘     └───────────┘
      ↑ 固定周期! 不能用主循环count!
```

#### 已验证的实现

```c
// pid.h — 位置式 PID (编码器脉冲计数域)
typedef struct {
    float kp, ki, kd;
    float target, error, last_error, integral;
    float max_integral, max_output, output;
} PID;

void pid_init(PID *pid, float kp, float ki, float kd,
              float max_integral, float max_output, float target);
float pid_calc(PID *pid, float current);  // PID_OUT = Kp*E + Ki*ΣE + Kd*dE

// 主循环框架 (SysTick 10ms)
#define PID_PERIOD_MS         (10U)
#define PID_SYSTICK_LOAD      (CPUCLK_FREQ / 1000U * PID_PERIOD_MS)
#define PID_MAX_INTEGRAL      (2500.0f)
#define PWM_STEP_LIMIT        (4)          // 每次调节不超过±4

volatile uint8_t g_pid_tick = 0;
void SysTick_Handler(void) { g_pid_tick = 1; }

int main(void) {
    SYSCFG_DL_init(); __enable_irq();
    Motor_Init(); Encoder_Init();
    DL_TimerG_startCounter(PWM_TB6612_INST);
    DL_SYSTICK_config(PID_SYSTICK_LOAD);  // 硬件定时器, 不是delay!

    pid_init(&pid, 0.5f, 0.08f, 0.0f, 2500, 1000, 42);
    int base_pwm = 800;  // 前馈! 不是从0开始

    while (1) {
        Encoder_Tick();  // 全速轮询

        if (g_pid_tick) {
            g_pid_tick = 0;
            Encoder_Update();
            int count = abs(Encoder_GetCount());

            int pwm = base_pwm + (int)pid_calc(&pid, (float)count);
            pwm = clamp(pwm, 0, 1000);
            pwm = step_limit(pwm, last_pwm, PWM_STEP_LIMIT);
            last_pwm = pwm;
            Motor_B(pwm);
        }
    }
}
```

#### ⚠️ 调参必读 (6 大陷阱)

| # | 陷阱 | 后果 | 正确做法 |
|---|------|------|---------|
| **1** | **PID 从 0 开始** | 电机不起转,积分饱和 | **前馈 Base PWM=800**,PID 只做 ±200 微调 |
| **2** | **主循环 delay 当采样** | UART 阻塞导致周期不准 | **SysTick 硬件定时器**, 10ms 固定周期 |
| **3** | **PWM 跳变太大** | 电机抽搐抖动 | **步进限幅 ±4/次**, 防突变 |
| **4** | **目标超过物理上限** | PID 永远在饱和 | 先满 PWM 测最大计数, 目标×0.95 |
| **5** | **编码器负值直入 PID** | error 方向反了 | **abs(count)** 取绝对值 |
| **6** | **`setCaptureCompareValue` 参数反** | PWM 写入错通道 | 正确: `(inst, VALUE, INDEX)` |

#### 实测参数 (MG310 + TB6612 + 电池 7.4V)

| 采样周期 | Base PWM | Kp | Ki | Kd | 目标 | 实测计数 |
|----------|---------|-----|-----|-----|------|---------|
| 10ms | 800 | 0.5 | 0.08 | 0 | 42 | 41~43 |
| 20ms | 800 | 0.5 | 0.08 | 0 | 80 | 82~86 |

> **调参顺序**: 先设 B800 T=实测最大值×0.9 → P=0.5 I=0 D=0 → 看是否稳定 → 微量加 I

#### 串口实时调参 (✅ 实测可用)

串口发送命令修改 PID 参数，无需重编译烧录：

```c
// UART 命令解析 (主循环中调用)
static void uart_poll_params(void) {
    static int value = 0, mode = 0;  // 0=none 1=P 2=I 3=D 4=T 5=B

    while (!DL_UART_isRXFIFOEmpty(UART_0_INST)) {
        char c = (char)DL_UART_Main_receiveData(UART_0_INST);

        if (c >= '0' && c <= '9') {
            value = value * 10 + (c - '0');
        } else if (c == 'P') { mode = 1; value = 0; }
        else if (c == 'I')  { mode = 2; value = 0; }
        else if (c == 'D')  { mode = 3; value = 0; }
        else if (c == 'T')  { mode = 4; value = 0; }
        else if (c == 'B')  { mode = 5; value = 0; }
        else {
            if (mode == 1) g_kp_x10 = value;      // P50 = Kp 5.0
            if (mode == 2) g_ki_x100 = value;     // I8  = Ki 0.08
            if (mode == 3) g_kd_x100 = value;     // D5  = Kd 0.05
            if (mode == 4) g_target = value;      // T42 = 目标42
            if (mode == 5) g_base_pwm = value;    // B800= 前馈800
            if (mode) pid_apply_params();         // 复位PID
            mode = 0; value = 0;
        }
    }
}
```

**命令格式 (数值=实际值×10/100)：**

| 命令 | 含义 | 示例 |
|------|------|------|
| `P5` | Kp = 0.5 | Kp×10 = 5 |
| `I8` | Ki = 0.08 | Ki×100 = 8 |
| `D0` | Kd = 0 | |
| `T42` | target = 42 脉冲/周期 | |
| `B800` | base PWM = 800 (前馈) | |
| 回车 | **自动重置 PID，回显确认** | |

**CSV 输出格式 (兼容 VOFA+ / Excel / 串口绘图)：**
```
count,pwm,target,Kp_x10,Ki_x100,Kd_x100,base_pwm
62,590,42,5,8,0,800
```

> ⚠️ **VOFA+ 串口命令防丢**: CSV 输出频率降到每 4 个 PID 周期 (80ms)。`csv_skip` 计数器跳过不发 CSV 的周期，UART RX 空闲接收命令不丢包。

**VOFA+ 连接设置：**
| 参数 | 值 |
|------|-----|
| 端口 | COM5 |
| 波特率 | 115200 |
| 协议 | CSV |
| 分隔符 | `,` |
| 通道 | CH1=速度 CH2=PWM CH3=目标 |

**调参工作流：**
1. 先发 `B999 T999` 满功率跑 → 记下最大 count = 上限
2. `T=上限×0.9` → 设可达目标
3. `B=上限附近 PWM` → 设前馈
4. `P5 I0 D0` → P-only 看是否稳定
5. `I8` → 加微量积分消除静差
6. 振荡 → 降 P 或加 D

#### 完整例程

> `Documents/model/PID_Speed/` 包含可直接编译运行的完整工程：
> `main.c` + `pid.c/h` + `encoder.c/h` + `motor.c/h` + `empty.syscfg`

#### ⚠️ 串口调参自动配置

当用户说"调PID"时，自动执行以下配置：

**串口设置 (必须)：**

| 参数 | 值 |
|------|-----|
| 端口 | COM5 (CH340, PA10/PA11) |
| 波特率 | 115200 |
| 数据位 | 8 |
| 校验 | None |
| 停止位 | 1 |
| 工具 | 串口调试助手 / PuTTY / VS Code Serial Monitor |

**操作步骤：**
1. 打开串口助手 → **COM5, 115200**
2. 启动后自动输出 CSV: `count,pwm,target,Kp,Ki,Kd,base`
3. 在发送框输入命令 → 点发送
4. 每次改参数后自动回显确认 (如 `P5 I8 D0 T42 B800`)
5. 数据可**拷贝粘贴到 Excel**，插入折线图观察趋势

**PID 调参快捷命令：**
```
B800 T42 P5 I8 D0     ← 推荐起始值
B999 T999             ← 测最大计数(不要长时间满功率)
B800 T82 P5 I8 D0     ← 20ms采样用
```

### 滤波器

**一阶低通滤波器：**
```c
typedef struct {
    float alpha;   // 滤波系数 = dt/(RC+dt), 取值范围 (0,1]
    float output;
} LowPassFilter;

float lpf_update(LowPassFilter *f, float input) {
    f->output = f->alpha * input + (1.0f - f->alpha) * f->output;
    return f->output;
}
```

**滑动平均滤波：**
```c
#define MA_WINDOW 8
typedef struct {
    uint16_t buf[MA_WINDOW];
    uint8_t  idx;
    uint32_t sum;
    uint8_t  count;
} MovingAvg;

uint16_t ma_update(MovingAvg *ma, uint16_t val) {
    ma->sum -= ma->buf[ma->idx];
    ma->sum += val;
    ma->buf[ma->idx] = val;
    ma->idx = (ma->idx + 1) % MA_WINDOW;
    if (ma->count < MA_WINDOW) ma->count++;
    return (uint16_t)(ma->sum / ma->count);
}
```

**互补滤波 (IMU 姿态融合)：**
```c
// 陀螺仪积分 + 加速度计修正
typedef struct {
    float angle;     // 输出角度
    float alpha;     // 互补系数, 典型 0.98
    float dt;        // 采样周期
} ComplementaryFilter;

float cf_update(ComplementaryFilter *cf, float gyro_rate, float accel_angle) {
    // gyro_rate: 陀螺仪角速度 (°/s)
    // accel_angle: 加速度计推算的角度
    cf->angle = cf->alpha * (cf->angle + gyro_rate * cf->dt)
              + (1.0f - cf->alpha) * accel_angle;
    return cf->angle;
}
```

**卡尔曼滤波 (1D，适合单轴角度融合)：**
```c
typedef struct {
    float x;   // 状态估计
    float p;   // 估计协方差
    float q;   // 过程噪声
    float r;   // 测量噪声
    float k;   // 卡尔曼增益
} Kalman1D;

void kalman1d_init(Kalman1D *kf, float q, float r) {
    kf->x = 0; kf->p = 1; kf->q = q; kf->r = r; kf->k = 0;
}

float kalman1d_update(Kalman1D *kf, float measurement) {
    kf->p += kf->q;
    kf->k  = kf->p / (kf->p + kf->r);
    kf->x += kf->k * (measurement - kf->x);
    kf->p *= (1 - kf->k);
    return kf->x;
}

// 陀螺仪+加速度计角度融合示例：
// 每 dt 秒调用: angle = kalman1d_update(&kf,
//     accel_angle + (angle + gyro_rate*dt)  // 融合输入
// );
// 或直接用: 先用 gyro*dt 做预测，再用 accel 做更新
```

### 电机控制

**直流电机速度闭环 (PWM + 编码器)：**
```c
typedef struct {
    PID_Controller speed_pid;
    uint32_t pwm_channel;
    uint32_t pwm_period;
    int32_t  target_speed;   // 目标速度 (编码器脉冲/控制周期)
    int32_t  current_speed;
    // 编码器读数
    int32_t  last_encoder;
} DC_Motor;

void motor_speed_control(DC_Motor *motor, int32_t encoder_val, float dt) {
    motor->current_speed = encoder_val - motor->last_encoder;
    motor->last_encoder = encoder_val;

    float output = pid_update(&motor->speed_pid,
                              (float)motor->current_speed, dt);

    // 将 PID 输出映射到 PWM 占空比
    if (output > motor->pwm_period) output = motor->pwm_period;
    if (output < 0) output = 0;

    DL_TimerG_setCaptureCompareValue(TIMG0, motor->pwm_channel, (uint32_t)output);
}
```

**舵机控制 (TIMA0 50Hz PWM, 500~2500us)：**
```c
// 25E 拓展板: 舵机1=PB9(TIMA0_CH1), 舵机2=PB8(TIMA0_CH0)
// 20ms 周期 = 50Hz, 脉宽 0.5~2.5ms 对应 0°~180°
// SysConfig: TIMA0 → PWM → PB8=CH0, PB9=CH1, period=25000
#define SERVO_PERIOD  25000
#define SERVO_MIN     625    // 0.5ms 对应
#define SERVO_MAX     3125   // 2.5ms 对应
#define SERVO_MID     1875   // 1.5ms 对应 90°

void servo1_set_angle(uint32_t angle_deg) { // 舵机1 PB9=CH1, 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    DL_TimerA_setCaptureCompareValue(TIMA0, 1, pulse);
}
void servo2_set_angle(uint32_t angle_deg) { // 舵机2 PB8=CH0, 0~180
    uint32_t pulse = SERVO_MIN + (SERVO_MAX - SERVO_MIN) * angle_deg / 180;
    DL_TimerA_setCaptureCompareValue(TIMA0, 0, pulse);
}
```

**步进电机控制 (A4988/DRV8825 脉冲+方向)：**
```c
// STEP 引脚连接 GPIO, DIR 连接 GPIO
void stepper_step(int steps, uint8_t dir_pin_state, uint32_t step_delay_us) {
    // 设置方向
    if (dir_pin_state) DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_8);
    else DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_8);

    for (int i = 0; i < steps; i++) {
        DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_9);   // STEP high
        delay_us(step_delay_us / 2);
        DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_9); // STEP low
        delay_us(step_delay_us / 2);
    }
}
```

---

