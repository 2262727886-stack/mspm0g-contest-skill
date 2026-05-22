# 竞赛准备与真题方案

## 一、竞赛准备清单

### 赛前 1 周

- [ ] **SDK 全家桶安装**: CCS + SysConfig + MSPM0 SDK (最新版)
- [ ] 跑通 XDS110/J-Link 烧录流程, 验证 dslite 命令可用
- [ ] 所有外设模块单独测试通过 (LED, 按键, UART, I2C, PWM, ADC)
- [ ] OLED 显示 "电赛 Ready" + MPU6050 正确输出姿态角
- [ ] 电机空载跑通: PWM + 编码器读数 + PID 速度闭环
- [ ] TCRT5000 在白纸/黑线上校准, VOFA+ 看到位置曲线
- [ ] K230 连接验证: find_blobs 检测红色物体 → UART 发坐标
- [ ] 制作并打印标定棋盘格/靶纸/A4 靶

### 赛前 1 天

- [ ] **完整系统联调**: 所有模块同时工作, 测功耗/发热
- [ ] 电池满电, 备 2 组以上
- [ ] 所有杜邦线/排线检查接触良好
- [ ] CCS 工程打 ZIP 备份 + GitHub 推送
- [ ] **UniFlash/CCS 离线可用** (场馆可能无网)
- [ ] 打印引脚对照表 + 快速排错流程图

### 比赛日

- [ ] 到场先查场地光线 → 重新校准 TCRT5000 / K230 LAB 阈值
- [ ] 测场地尺寸是否与题目一致 (100cm 正方形/间距)
- [ ] 先跑最简单用例验证基本功能
- [ ] **每改一次代码, 先 git commit 备份**
- [ ] 电池电压 < 7.0V 即换电 (MG310 额定 7.4V)

### 常见故障排查

| 症状 | 先查 |
|------|------|
| 程序不跑 | SWD 是否接触, BCR 是否正常 |
| 串口无输出 | PA0/PA1 上拉, 波特率匹配, FIFO 关闭 |
| 电机不转 | TB6612 STBY=高, VM≥7V, 方向引脚电平 |
| 编码器读 0 | AB 相接线, TIMG 编码器模式使能 |
| OLED 花屏 | I2C 地址 0x3C, 上电后 delay 100ms |
| K230 无数据 | FPIOA 是否先配, 波特率是否 115200 |

### 注意事项

- **PA0/PA1 开漏**: BSL 烧录用 9600, 用户程序 115200 需确保上拉
- **SysConfig 默认 32MHz**: 不用 PLL 时 SysTick 配 32000 非 80000
- **I2C 死等**: 从设备不响应时加超时 + STOP 恢复
- **K230 UART 先 FPIOA**: `set_function(11, UART2_TXD)` 再 `UART(...)`


---


## 十七、电赛真题方案



> 以下三题为 2023-2025 年 TI 杯电赛控制类真题，均基于 MSPM0G3507 + K230 双芯架构。


### 18.1 25年电赛 E 题 — 简易自行瞄准装置

### 系统架构

```
                    ┌─────────────┐
        TCRT5000×5  │   MSPM0G    │
        循迹阵列 ───→│   (巡迹+PID) │──→ TB6612 → 电机A(左)
                    │             │──→ TB6612 → 电机B(右)
    EC11编码器×2 ──→│             │
                    │             │──→ 舵机1 (Pan/水平)
        按键/OLED ──┤             │──→ 舵机2 (Tilt/俯仰)
                    └─────────────┘
                           │
                    蓝紫激光笔 (接继电器/MOS)
```

**场地坐标系 (cm)：**
```
A(0,0) ────────── B(100,0)
  │                  │
  │   行驶轨迹(黑线)   │
  │   逆时针方向       │
  │                  │
D(0,100) ──────── C(100,100)

靶面中心: (50, -50)，靶面与AB平行，竖立
靶面高度: ≤50cm
```

### --- TCRT5000 五路循迹 ---

```c
// 5路红外传感器接 ADC0 通道 0~4
#define TCRT_CHANNELS 5
static uint16_t tcrt_min[TCRT_CHANNELS];  // 白底校准值
static uint16_t tcrt_max[TCRT_CHANNELS];  // 黑线校准值

// 上电自动校准: 小车在白底上放3秒，再在黑线上放3秒
void tcrt_calibrate_white(void) {
    for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
        tcrt_min[ch] = 4095;  // 初始最大化
    }
    for (int i = 0; i < 200; i++) {
        for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
            uint16_t val = adc_read_channel(ch);
            if (val < tcrt_min[ch]) tcrt_min[ch] = val;
        }
        delay_ms(10);
    }
}

void tcrt_calibrate_black(void) {
    for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
        tcrt_max[ch] = 0;
    }
    for (int i = 0; i < 200; i++) {
        for (int ch = 0; ch < TCRT_CHANNELS; ch++) {
            uint16_t val = adc_read_channel(ch);
            if (val > tcrt_max[ch]) tcrt_max[ch] = val;
        }
        delay_ms(10);
    }
}

// 归一化: 0.0(全白) ~ 1.0(全黑)
float tcrt_read_normalized(uint8_t ch) {
    uint16_t val = adc_read_channel(ch);
    float norm = (float)(val - tcrt_min[ch]) / (tcrt_max[ch] - tcrt_min[ch] + 1);
    if (norm < 0) norm = 0;
    if (norm > 1.0f) norm = 1.0f;
    return norm;
}

// 加权位置计算: 返回-1.0(最左) ~ +1.0(最右), 0为居中
float tcrt_get_position(void) {
    float sum_val = 0, sum_weight = 0;
    float sensor_positions[5] = {-1.0f, -0.5f, 0.0f, 0.5f, 1.0f};
    for (int i = 0; i < TCRT_CHANNELS; i++) {
        float v = tcrt_read_normalized(i);
        // 阈值过滤噪声
        if (v > 0.1f) {
            sum_val += v * sensor_positions[i];
            sum_weight += v;
        }
    }
    if (sum_weight < 0.05f) return 0.0f;  // 全部白，保持直行
    return sum_val / sum_weight;
}

// 判断是否完全离线 (5路全白 = 冲出赛道)
bool tcrt_is_lost(void) {
    float sum = 0;
    for (int i = 0; i < TCRT_CHANNELS; i++) sum += tcrt_read_normalized(i);
    return sum < 0.1f;
}
```

### --- 巡线转向 PID ---

```c
// 转向 PID: 输入为线位置误差(-1~+1), 输出为差速修正(-1~+1)
PID_Controller steer_pid;

// 差分驱动: base_speed 基础速度, steer_output 转向修正(-1~+1)
void differential_drive(float base_speed, float steer_output) {
    float left_speed  = base_speed * (1.0f - steer_output);
    float right_speed = base_speed * (1.0f + steer_output);

    // 限幅
    if (left_speed  < 0) left_speed  = 0;
    if (right_speed < 0) right_speed = 0;
    if (left_speed  > 1.0f) left_speed  = 1.0f;
    if (right_speed > 1.0f) right_speed = 1.0f;

    // 写入 PWM 占空比 (TIMG8: CH0=PB15左, CH1=PB16右)
    uint32_t period = 4000; // 20kHz
    pwm_set_duty(0, left_speed * period);   // TIMG8_CH0 → 左电机
    pwm_set_duty(1, right_speed * period);  // TIMG8_CH1 → 右电机
}

// 主控循环 (放在 1kHz 定时中断或主循环中)
float line_err = tcrt_get_position();
float steer = pid_update(&steer_pid, line_err, 0.001f); // dt=1ms
differential_drive(0.5f, steer);  // 50% 基础速度
```

### --- 圈数检测 ---

```c
// 基于十字路口的圈数检测: 行驶轨迹是正方形，连续检测到4段直线+4个直角转弯
// 简化方案: 用编码器距离 + 方向判断
volatile uint8_t lap_count = 0;
volatile uint8_t segment = 0;     // 0=AB, 1=BC, 2=CD, 3=DA
volatile float   segment_dist = 0; // 当前段已行驶距离

// 编码器累计: 在定时中断中每1ms累加
// MG310 电机: 减速比 1:20.409, 霍尔编码器 13PPR
// 输出轴 PPR = 13 × 20.409 ≈ 265 (霍尔版) 或 500 × 20.409 ≈ 10204 (GMR版)
// 车轮: 48mm 橡胶轮胎, 周长 = π×4.8cm
#define WHEEL_CIRCUMFERENCE 15.08f  // π×4.8cm (MG310常用48mm轮胎)
#define ENCODER_PPR         265     // 霍尔编码器输出轴脉冲数/圈(13×20.409)
// #define ENCODER_PPR      10204  // GMR编码器版(高精度), 按需切换

void lap_detector_update(int32_t enc_left, int32_t enc_right, float dt) {
    // 左右轮平均距离
    float avg_pulses = (enc_left + enc_right) / 2.0f;
    float distance_cm = avg_pulses / ENCODER_PPR * WHEEL_CIRCUMFERENCE;
    segment_dist += fabsf(distance_cm);

    // 每100cm切换段
    if (segment_dist >= 100.0f) {
        segment_dist -= 100.0f;
        segment = (segment + 1) % 4;
        if (segment == 0) lap_count++;
    }
}
```

### --- 二维云台舵机控制 ---

```c
// 25E 拓展板: 舵机1=PB9(TIMA0_CH1, Pan), 舵机2=PB8(TIMA0_CH0, Tilt)
void gimbal_set_pan(float angle_deg) {
    servo1_set_angle(angle_deg + 90);  // 映射 0~180
}
void gimbal_set_tilt(float angle_deg) {
    servo2_set_angle(angle_deg);       // 0~60 → 0~180
}

// 激光笔开关 (拓展板: 激光未专门分配, 可用 PB27 LED 位或 GPIO 扩展)
// #define LASER_ON()   DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_27)
// #define LASER_OFF()  DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_27)
```

### --- 瞄准几何解算 ---

```c
// 场地坐标系 (cm): A(0,0), B(100,0), C(100,100), D(0,100)
// 靶心坐标 (cm): (50, -50)
#define TARGET_X  50.0f
#define TARGET_Y -50.0f
#define TARGET_Z  25.0f  // 靶心高度(cm), 实测校准
#define GIMBAL_Z   8.0f  // 云台离地高度(cm)

// 根据小车位置计算 Pan 角度 (绕Z轴旋转)
float compute_pan_angle(float car_x, float car_y, float car_heading) {
    // car_heading: 小车朝向角度(°), 逆时针, 0=AB方向(右), 90=BC方向(上)
    float dx = TARGET_X - car_x;
    float dy = TARGET_Y - car_y;
    // 目标相对于小车的世界坐标系方位角
    float world_azimuth = atan2f(dy, dx) * 57.29578f;  // 转度
    // Pan 云台在小车坐标中的角度 (相对于车头)
    float pan = world_azimuth - car_heading;
    // 归一化到 ±180°
    while (pan > 180) pan -= 360;
    while (pan < -180) pan += 360;
    return pan;
}

// 计算 Tilt 俯仰角度
float compute_tilt_angle(float car_x, float car_y) {
    float dx = TARGET_X - car_x;
    float dy = TARGET_Y - car_y;
    float horizontal_dist = sqrtf(dx*dx + dy*dy);
    float dz = TARGET_Z - GIMBAL_Z;
    return atan2f(dz, horizontal_dist) * 57.29578f;
}

// 计算小车在正方形轨迹上的实时位置 (简化: 基于累计距离推算)
void compute_car_position(float total_distance_cm,
                          float *x, float *y, float *heading) {
    float d = fmodf(total_distance_cm, 400.0f);  // 单圈400cm
    if (d < 100) {           // AB段: (d, 0), 方向 0°
        *x = d; *y = 0; *heading = 0;
    } else if (d < 200) {   // BC段: (100, d-100), 方向 90°
        *x = 100; *y = d - 100; *heading = 90;
    } else if (d < 300) {   // CD段: (300-d, 100), 方向 180°
        *x = 300 - d; *y = 100; *heading = 180;
    } else {                // DA段: (0, 400-d), 方向 270°
        *x = 0; *y = 400 - d; *heading = 270;
    }
}
```

### --- 同步画圆算法 (发挥部分3) ---

```c
// 需求: 小车行驶1圈期间, 激光沿靶面上半径6cm的红色圆弧同步画1圈
// 同步误差 < 1/4圈

// 靶面坐标系: X→(水平,平行AB), Z→(垂直,靶面高度)
// 靶心在靶面上的坐标: (0, 0)  (即靶面中心)
// 画圆半径: 6cm

float sync_draw_circle_phase(float car_total_distance_cm) {
    // 小车行驶距离 → 0~2π 相位
    return fmodf(car_total_distance_cm, 400.0f) / 400.0f * 6.2831853f;
}

// 计算激光在靶面上的目标点 (靶面坐标系, cm)
void get_laser_target_on_target(float phase, float radius,
                                float *tx, float *tz) {
    *tx = radius * cosf(phase);   // 水平偏移
    *tz = radius * sinf(phase);   // 垂直偏移
}

// 将靶面坐标转换为云台角度
void target_to_gimbal(float target_x, float target_z,
                      float car_x, float car_y,
                      float *pan, float *tilt) {
    // 靶面点在空间中的实际坐标
    float world_x = TARGET_X + target_x;  // 靶面水平
    float world_z = TARGET_Z + target_z;  // 靶面垂直
    float world_y = TARGET_Y;

    float dx = world_x - car_x;
    float dy = world_y - car_y;
    *pan  = atan2f(dy, dx) * 57.29578f;
    float h_dist = sqrtf(dx*dx + dy*dy);
    *tilt = atan2f(world_z - GIMBAL_Z, h_dist) * 57.29578f;
}
```

### --- 参数设置界面 (OLED + EC11) ---

```c
// 可调参数
typedef struct {
    uint8_t  laps;        // 圈数 1~5
    float    base_speed;  // 基础速度 0.2~1.0
    float    pid_kp;      // 转向 Kp
    float    pid_ki;      // 转向 Ki
    float    pid_kd;      // 转向 Kd
    bool     laser_mode;  // 连续发光/瞄准
} ContestParams;

static ContestParams params = {1, 0.5f, 2.0f, 0.1f, 0.05f, true};

// EC11 旋转选择菜单
void menu_edit_params(void) {
    oled_clear();
    oled_puts(0, 0, ">> Laps Speed Kp Ki Kd");
    // EC11 旋钮选参数, 按键切换, 长按确认
    // 每次修改后 oled_show_float() 刷新显示
    oled_refresh();
}
```

### --- 完整控制流程 (发挥部分) ---

```c
// 状态机
typedef enum {
    STATE_IDLE,              // 等待启动
    STATE_AUTO_TRACK,        // 自动巡线 (基本要求1)
    STATE_AIM_STATIC,        // 静止瞄准 (基本要求2)
    STATE_AIM_MOVING,        // 移动瞄准 (基本要求3)
    STATE_COMBINED,          // 巡线+连续瞄准 (发挥部分)
    STATE_COMPLETE,          // 完成
} SystemState;

// 主循环控制 (简化)
void contest_loop(void) {
    static float total_dist = 0;
    static float lap_start_dist = 0;
    static uint32_t start_time = 0;

    // 读取编码器
    int32_t enc_l = encoder_read_left();
    int32_t enc_r = encoder_read_right();

    // 巡线
    float line_err = tcrt_get_position();
    float steer = pid_update(&steer_pid, line_err, 0.001f);

    // 圈数检测
    lap_detector_update(enc_l, enc_r, 0.001f);
    total_dist += (enc_l + enc_r) / 2.0f / ENCODER_PPR * WHEEL_CIRCUMFERENCE;

    // 瞄准解算
    float cx, cy, heading;
    compute_car_position(total_dist, &cx, &cy, &heading);
    float pan  = compute_pan_angle(cx, cy, heading);
    float tilt = compute_tilt_angle(cx, cy);

    // 画圆模式 (发挥3): 叠加圆偏移
    if (params.laser_mode && params.laps > 0) {
        float phase = sync_draw_circle_phase(total_dist);
        float tx, tz;
        get_laser_target_on_target(phase, 6.0f, &tx, &tz);
        target_to_gimbal(tx, tz, cx, cy, &pan, &tilt);
    }

    // 执行
    gimbal_set_pan(pan);
    gimbal_set_tilt(tilt);
    differential_drive(params.base_speed, steer);

    // UART 调试输出
    // float debug[4] = {line_err, steer, pan, tilt};
    // vofa_send_floats(debug, 4);
}
```

---

### 18.2 24年电赛 H 题 — 自动行驶小车

### 赛道几何模型

```
        100cm (直线段)
    A ────────────────── B
   /←─── r=40cm ───→\     ↑
  │    左半圆弧         │    │ 直线段间距
  │                    │    │ 2×40=80cm
   \                  /     ↓
    D ────────────────── C

场地: 220cm×120cm (含边距)
轨迹总长一圈: 2×100 + 2×π×40 ≈ 451.3cm
半圆弧长: ≈125.7cm
```

**四节点 (弧线顶点/切点)：**
```
A: 左上切点  B: 右上切点
C: 右下切点  D: 左下切点
```

**要求路径：**
| 要求 | 路径 | 通过点 | 限时 |
|------|------|--------|------|
| (1) | A→B | B停车 | ≤15s |
| (2) | 顺时针一圈 | A→B→C→D→A | ≤30s |
| (3) | A→C→B→D→A | 通过所有4点 | ≤40s |
| (4) | 要求(3)路径×4圈 | 每圈4点 | 越少越好 |

### --- 赛道段定义 ---

```c
// 赛道段类型
typedef enum {
    SEG_STRAIGHT,   // 直线段 (100cm)
    SEG_LEFT_ARC,   // 左半圆弧 (r=40cm, πr≈125.7cm)
    SEG_RIGHT_ARC,  // 右半圆弧
} SegmentType;

typedef struct {
    SegmentType type;
    float       length_cm;    // 段长度
    uint32_t    encoder_ticks;// 编码器脉冲数
} TrackSegment;

// 4段组成一圈 (从A开始顺时针):
// S0: A→B 上直线, S1: B→C 右弧, S2: C→D 下直线, S3: D→A 左弧
static const TrackSegment track_lap[4] = {
    {SEG_STRAIGHT,  100.0f, 0},  // S0: 上直线, 换算后填充
    {SEG_RIGHT_ARC, 125.7f, 0},  // S1: 右弧
    {SEG_STRAIGHT,  100.0f, 0},  // S2: 下直线
    {SEG_LEFT_ARC,  125.7f, 0},  // S3: 左弧
};

// 编码器距离换算
#define ENC_TICKS_PER_CM (ENCODER_PPR / WHEEL_CIRCUMFERENCE)

// 段编码器脉冲数初始化
void track_segments_init(void) {
    for (int i = 0; i < 4; i++) {
        ((TrackSegment*)track_lap)[i].encoder_ticks =
            (uint32_t)(track_lap[i].length_cm * ENC_TICKS_PER_CM);
    }
}
```

### --- 路线规划 (路径表) ---

```c
// 路径定义: 按序经过的段号, 段号0~3 对应 S0~S3
// 要求(1): A→B, 只走 S0
static const int8_t route_1[] = {0, -1};  // -1 表示终点

// 要求(2): A→B→C→D→A, 顺时针一圈 S0→S1→S2→S3
static const int8_t route_2[] = {0, 1, 2, 3, -1};

// 要求(3): A→C→B→D→A
// A→C: 左弧向下 S3 → 下直线向左 S2
// C→B: 右弧向上 S1 (反向)  → 实际就是 S1 段，但方向相反
// 注意: 小车只能前进，所以沿赛道反向行驶时是"正常循迹方向"的逆
// 简化处理: A→C = S3+S2, C→B = S1, B→D = S0+S3, D→A = S3
// 即: S3→S2→S1→S0→S3→S3 → 合并为两圈中的 6 段
static const int8_t route_3[] = {3, 2, 1, 0, 3, -1};
// 说明: A →(S3左弧)→ D →(S2下直线)→ C →(S1右弧)→ B →(S0上直线+B→A→左弧)→ D →(S3左弧)→ A

// 要求(4): 要求(3) 路径 × 4
static int8_t route_4[24];  // 动态生成: route_3 重复4次
```

### --- 弯道/直道自适应 PID ---

```c
// 弯道和直道用不同 PID 参数
// 弯道线更弯，需要更大的 Kp 来跟踪
PID_Controller pid_straight;   // 直道转向PID
PID_Controller pid_curve;      // 弯道转向PID

// 判断当前是在直道还是弯道
SegmentType current_segment_type(void) {
    return track_lap[current_seg_idx].type;
}

float adaptive_steer(float line_err, float dt) {
    float steer;
    if (current_segment_type() == SEG_STRAIGHT) {
        steer = pid_update(&pid_straight, line_err, dt);
    } else {
        steer = pid_update(&pid_curve, line_err, dt);
    }
    return steer;
}

// 典型参数:
// pid_straight: Kp=1.8, Ki=0.08, Kd=0.05
// pid_curve:    Kp=3.0, Ki=0.15, Kd=0.10
```

### --- 节点检测 (A/B/C/D 点) ---

```c
// 检测到达节点: 编码器距离 + 线传感器突变 (弧线→直线过渡处)
// 弧线-直线交汇处, 5路传感器会有短暂的特殊模式

volatile uint8_t  reached_point = 0;   // 0=无, 1/2/3/4=A/B/C/D的检测标志
volatile uint32_t point_timestamp = 0; // 到达时刻

void check_point_reached(void) {
    // 方法1: 编码器距离——当前段剩余距离 < 阈值
    if (seg_remaining_dist < 3.0f) {  // 距离目标点 < 3cm
        reached_point = 1;
        point_timestamp = g_ms_ticks;
        return;
    }

    // 方法2: 传感器模式检测——5路全部"看到线"且位置居中
    // (弧线切点处线比较直，可用于辅助判断)
    float sum = 0;
    for (int i = 0; i < TCRT_CHANNELS; i++) sum += tcrt_read_normalized(i);
    float pos = fabsf(tcrt_get_position());
    if (sum > 1.5f && pos < 0.15f && seg_remaining_dist < 8.0f) {
        reached_point = 1;
        point_timestamp = g_ms_ticks;
    }
}
```

### --- 定点刹车控制 ---

```c
// S曲线减速: 距离目标点越近, 速度越低
// 参考公式: v = sqrt(2 * a * d), a 为减速度
#define MAX_SPEED      0.6f   // 直道巡航速度 (占空比)
#define MIN_SPEED      0.15f  // 弯道最低速度
#define DECEL_RATE     0.3f   // 减速度 (m/s^2, 按实际调)

float compute_target_speed(float dist_to_stop, bool is_final_stop) {
    if (!is_final_stop) {
        // 途经点: 不减速太多, 流畅通过
        return (dist_to_stop < 15.0f) ? MAX_SPEED * 0.6f : MAX_SPEED;
    }
    // 终点停车: 渐进减速
    if (dist_to_stop > 40.0f) return MAX_SPEED;
    if (dist_to_stop < 5.0f)  return 0.0f;   // 刹车
    // 中间: 线性减速
    return MAX_SPEED * dist_to_stop / 40.0f;
}

// 刹车执行 (拓展板: AIN1=PA13, AIN2=PA12, BIN1=PB0, BIN2=PB1)
void brake_now(void) {
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_13);   // AIN1=0
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_12);   // AIN2=0
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_0);    // BIN1=0
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);    // BIN2=0
    pwm_set_duty(0, 0);   // PWMA=0
    pwm_set_duty(1, 0);   // PWMB=0
}
```

### --- 声光指示 ---

```c
#define BUZZER_PIN  DL_GPIO_PIN_17  // PB17 蜂鸣器 (拓展板)
#define LED_PIN     DL_GPIO_PIN_27  // PB27 LED (拓展板)

void indicator_beep(uint8_t times, uint32_t duration_ms) {
    for (int i = 0; i < times; i++) {
        DL_GPIO_setPins(GPIOB, BUZZER_PIN);  // 蜂鸣器
        DL_GPIO_setPins(GPIOB, LED_PIN);     // LED
        delay_ms(duration_ms);
        DL_GPIO_clearPins(GPIOB, BUZZER_PIN);
        DL_GPIO_clearPins(GPIOB, LED_PIN);
        if (times > 1) delay_ms(150);
    }
}

// 到达每个点: 短鸣 1声 + LED 闪 1次
void point_indicator(void) {
    indicator_beep(1, 200);
}

// 最终停车: 长鸣 3声 + LED 长亮 2秒
void stop_indicator(void) {
    DL_GPIO_setPins(GPIOA, LED_PIN);
    indicator_beep(3, 500);
    DL_GPIO_clearPins(GPIOA, LED_PIN);
}
```

### --- 前进锁定 (不得后退) ---

```c
// TB6612 AIN1/AIN2 控制左电机方向
// BIN1/BIN2 控制右电机方向
// 前进: AIN1=1, AIN2=0 / BIN1=1, BIN2=0
// 后退: AIN1=0, AIN2=1 (本题禁用)

typedef enum {
    MOTOR_FORWARD = 0,
    // MOTOR_BACKWARD = 1,  // 本题禁用
    MOTOR_BRAKE    = 2,
} MotorDirection;

void motor_set_forward(void) {
    // 拓展板: AIN1=PA13, AIN2=PA12, BIN1=PB0, BIN2=PB1
    DL_GPIO_setPins(GPIOA, DL_GPIO_PIN_13);   // AIN1=1
    DL_GPIO_clearPins(GPIOA, DL_GPIO_PIN_12); // AIN2=0
    DL_GPIO_setPins(GPIOB, DL_GPIO_PIN_0);    // BIN1=1
    DL_GPIO_clearPins(GPIOB, DL_GPIO_PIN_1);  // BIN2=0
}

// 安全封装: 差分驱动只调整占空比, 不动方向
void safe_differential_drive(float left, float right) {
    motor_set_forward();  // 始终前进
    pwm_set_duty(0, (uint32_t)(left  * 4000));  // TIMG8_CH0=PB15
    pwm_set_duty(1, (uint32_t)(right * 4000));  // TIMG8_CH1=PB16
}
```

### --- H 题主控逻辑 ---

```c
typedef struct {
    uint8_t  route_type;    // 1/2/3/4 对应要求(1)~(4)
    uint8_t  total_points;  // 本路线总途经点
    uint8_t  point_idx;     // 当前途经点序号
    uint8_t  lap_count;     // 已完成圈数
    int8_t   seg_sequence[32]; // 段序列
    uint8_t  seg_count;     // 段序列长度
    uint8_t  seg_idx;       // 当前段索引
    float    seg_progress;  // 当前段已走距离
    bool     is_finished;
} H_ContestState;

void h_contest_init(H_ContestState *s, uint8_t route_type) {
    s->route_type = route_type;
    s->point_idx  = 0;
    s->lap_count  = 0;
    s->seg_idx    = 0;
    s->seg_progress = 0;
    s->is_finished  = false;

    // 根据路线类型填充段序列
    const int8_t (*route)[];
    switch (route_type) {
    case 1: route = &route_1; break;
    case 2: route = &route_2; break;
    case 3: route = &route_3; break;
    case 4: // 重复 route_3 × 4
        for (int i = 0; i < 4; i++) {
            for (int j = 0; route_3[j] >= 0; j++)
                s->seg_sequence[i*5 + j] = route_3[j];
        }
        s->seg_sequence[20] = -1;
        route = NULL; break;
    default: return;
    }
    if (route) {
        for (int i = 0; (*route)[i] >= 0; i++)
            s->seg_sequence[i] = (*route)[i];
        s->seg_sequence[i] = -1;
    }
}

void h_contest_loop(H_ContestState *s) {
    if (s->is_finished) return;

    // 读编码器
    int32_t enc_l = encoder_read_left();
    int32_t enc_r = encoder_read_right();
    float avg_dist = (enc_l + enc_r) / 2.0f / ENC_TICKS_PER_CM;

    // 更新段进度
    s->seg_progress += avg_dist;
    int8_t seg = s->seg_sequence[s->seg_idx];
    if (seg < 0) { s->is_finished = true; brake_now(); stop_indicator(); return; }
    float seg_len = track_lap[seg].length_cm;

    // 检测是否到达节点
    float remaining = seg_len - s->seg_progress;
    if (remaining < 2.0f) {
        s->point_idx++;
        point_indicator();
        s->seg_progress = 0;
        s->seg_idx++;
        // 判断是否是终点
        if (s->seg_sequence[s->seg_idx] < 0) {
            s->lap_count++;
            if (s->route_type == 4 && s->lap_count >= 4) {
                s->is_finished = true;
                brake_now();
                stop_indicator();
                return;
            }
        }
    }

    // 巡线 + 速度控制
    float line_err = tcrt_get_position();
    float steer = adaptive_steer(line_err, 0.001f);

    bool is_final = (s->seg_sequence[s->seg_idx] < 0);
    float speed = compute_target_speed(remaining, is_final);
    safe_differential_drive(speed + steer, speed - steer);
}
```

---

### 18.3 23年电赛 E 题 — 运动目标控制与自动追踪系统

### 系统架构

```
┌──── RED 系统 (独立MCU) ────┐     ┌──── GREEN 系统 (独立MCU) ────┐
│                             │     │                               │
│  MSPM0G #1                  │     │  MSPM0G #2                    │
│  ├─ 键盘(模式选择+启动)      │     │  ├─ OV7725+FIFO(摄像头)        │
│  ├─ OLED(显示当前路径)       │     │  ├─ OLED(显示追踪状态)          │
│  ├─ 舵机1(Pan)              │     │  ├─ 舵机1(Pan)                │
│  ├─ 舵机2(Tilt)             │     │  ├─ 舵机2(Tilt)              │
│  └─ 红色激光笔(MOS驱动)      │     │  └─ 绿色激光笔(MOS驱动)        │
└─────────────────────────────┘     └───────────────────────────────┘
         ↕ 不能通信 ↕                         ↕ 摄像头 ↕
    ┌─────────────────────────────────────────────────────┐
    │           白色屏幕 (1m 前方, >0.6×0.6m)              │
    │    ┌─────────────────────┐                          │
    │    │   0.5m×0.5m 正方形   │                          │
    │    │   中心 = 原点(0,0)    │                          │
    │    └─────────────────────┘                          │
    └─────────────────────────────────────────────────────┘
```

**坐标系 (屏幕平面，单位 cm)：**
- 原点: (0, 0) = 屏幕中心
- 正方形: (±25, ±25)
- 屏幕距云台: 100cm (Z方向)
- Pan/Tilt 角度: 绕 Z 轴 / 绕水平轴

### --- 红色系统: 路径生成 ---

**正方形边线路径 (基本要求2)：**
```c
// 屏幕 0.5m×0.5m, 边线路径: 上→右→下→左, 顺时针
// 光斑距边线 ≤2cm, 即路径在 ±23cm 处 (中心往边 25cm 减 2cm)
#define SQ_HALF  23.0f  // 正方形半边距

typedef struct {
    float x, y;    // 屏幕坐标 (cm)
} Point2D;

// 正方形路径 (50个采样点, 30秒走一圈 → 每点 0.6s → 每步 4cm)
static Point2D square_path[200];
static uint16_t  square_path_len = 0;

void generate_square_path(void) {
    // 上边: (SQ_HALF, -SQ_HALF) → (SQ_HALF, SQ_HALF)  右移
    // 左边: (SQ_HALF, SQ_HALF) → (-SQ_HALF, SQ_HALF)   下移
    // 下边: (-SQ_HALF, SQ_HALF) → (-SQ_HALF, -SQ_HALF) 左移
    // 右边: (-SQ_HALF, -SQ_HALF) → (SQ_HALF, -SQ_HALF) 上移
    // 用 Bresenham 或直接等距采样填充
    float step = 1.0f;  // 每步 1cm
    float xs[] = { SQ_HALF,  SQ_HALF, -SQ_HALF, -SQ_HALF,  SQ_HALF};
    float ys[] = {-SQ_HALF,  SQ_HALF,  SQ_HALF, -SQ_HALF, -SQ_HALF};
    int idx = 0;
    for (int seg = 0; seg < 4; seg++) {
        float dx = xs[seg+1] - xs[seg];
        float dy = ys[seg+1] - ys[seg];
        float dist = sqrtf(dx*dx + dy*dy);
        int steps = (int)(dist / step);
        for (int i = 0; i < steps; i++) {
            float t = (float)i / steps;
            square_path[idx].x = xs[seg] + dx * t;
            square_path[idx].y = ys[seg] + dy * t;
            idx++;
        }
    }
    square_path_len = idx;
}
```

**A4 靶纸路径 (基本要求3/4)：**
```c
// A4: 29.7cm×21cm, 胶带宽 1.8cm
// 光斑沿胶带中心线移动 → 路径比 A4 边缘内移 0.9cm
#define A4_HALF_W  14.85f  // 29.7/2
#define A4_HALF_H  10.5f   // 21/2
#define TAPE_OFFSET 0.9f   // 胶带半宽

static Point2D a4_path[200];
static uint16_t  a4_path_len = 0;

// 旋转任意角度 θ (弧度)
void generate_a4_path(float center_x, float center_y, float theta) {
    float hw = A4_HALF_W - TAPE_OFFSET;
    float hh = A4_HALF_H - TAPE_OFFSET;
    float corners[4][2] = {
        { hw, -hh}, { hw,  hh}, {-hw,  hh}, {-hw, -hh}
    };
    // 旋转 + 平移
    float c = cosf(theta), s = sinf(theta);
    float xs[5], ys[5];
    for (int i = 0; i < 4; i++) {
        float rx = corners[i][0]*c - corners[i][1]*s + center_x;
        float ry = corners[i][0]*s + corners[i][1]*c + center_y;
        xs[i] = rx; ys[i] = ry;
    }
    xs[4] = xs[0]; ys[4] = ys[0];  // 闭合

    float step = 0.8f;
    int idx = 0;
    for (int seg = 0; seg < 4; seg++) {
        float dx = xs[seg+1] - xs[seg];
        float dy = ys[seg+1] - ys[seg];
        float dist = sqrtf(dx*dx + dy*dy);
        int steps = (int)(dist / step);
        for (int i = 0; i < steps; i++) {
            float t = (float)i / steps;
            a4_path[idx].x = xs[seg] + dx * t;
            a4_path[idx].y = ys[seg] + dy * t;
            idx++;
        }
    }
    a4_path_len = idx;
}
```

**屏幕坐标 → 云台角度：**
```c
#define SCREEN_DIST 100.0f  // 屏幕距云台 1m = 100cm

void screen_to_gimbal(float sx, float sy, float *pan, float *tilt) {
    // sx, sy: 屏幕上的目标坐标 (cm), 原点(0,0)=屏幕中心
    // 转换: 水平偏移 → Pan角, 垂直偏移+距离 → Tilt角
    *pan  = atan2f(sx, SCREEN_DIST) * 57.29578f;
    float h_dist = sqrtf(SCREEN_DIST*SCREEN_DIST + sx*sx);
    *tilt = atan2f(sy, h_dist) * 57.29578f;
}
```

**红色系统主控：**
```c
typedef enum {
    RED_IDLE,
    RED_RESET,      // 基本要求1: 回到原点
    RED_SQUARE,     // 基本要求2: 正方形边线
    RED_A4_NORMAL,  // 基本要求3: A4靶纸
    RED_A4_ROTATED, // 基本要求4: 旋转A4靶纸
    RED_PAUSED,     // 制动
} RedState;

void red_system_loop(RedState *state, uint32_t *path_idx, uint32_t elapsed_ms) {
    Point2D target;
    switch (*state) {
    case RED_RESET:
        target.x = 0; target.y = 0;  // 原点
        if (elapsed_ms > 1000) *state = RED_IDLE;  // 1秒到原点
        break;
    case RED_SQUARE:
        // 30秒 200步 → 每步 150ms
        *path_idx = (elapsed_ms / 150) % square_path_len;
        if (elapsed_ms > 30000) *state = RED_IDLE;
        target = square_path[*path_idx];
        break;
    case RED_A4_NORMAL:
    case RED_A4_ROTATED:
        *path_idx = (elapsed_ms / 150) % a4_path_len;
        if (elapsed_ms > 30000) *state = RED_IDLE;
        target = a4_path[*path_idx];
        break;
    case RED_PAUSED:
        return;  // 不动
    default: return;
    }
    float pan, tilt;
    screen_to_gimbal(target.x, target.y, &pan, &tilt);
    gimbal_set_pan(pan);
    gimbal_set_tilt(tilt);
}
```

### --- 绿色系统: 摄像头红光斑检测 ---

```c
// OV7725 + AL422B FIFO 摄像头模块
// 典型连接: 8-bit parallel D0~D7 + PCLK + VSYNC + HREF
// FIFO 读: 先拉低 OE, 再给 RE 脉冲读出 1 字节

// 简化方案: 只读 80×60 下采样图像, 仅检查红色通道
#define CAM_WIDTH   80
#define CAM_HEIGHT  60
#define RED_THRESHOLD  200  // R 通道阈值 (0~255), 按实测调整
#define MIN_RED_PIXELS  5   // 最少红色像素数

typedef struct {
    uint16_t sum_x, sum_y;
    uint16_t count;
    float    cx, cy;  // 光斑中心 (屏幕坐标 cm)
    bool     detected;
} RedSpot;

// 从 FIFO 读一帧并检测红光斑
// 原理: 仅读 R 分量(每像素 2 字节 RGB565), 超过阈值则累计质心
RedSpot detect_red_spot(void) {
    RedSpot spot = {0};

    // FIFO 复位读指针
    fifo_reset_read();

    for (int y = 0; y < CAM_HEIGHT; y++) {
        for (int x = 0; x < CAM_WIDTH; x++) {
            uint16_t pixel = fifo_read_16();  // RGB565
            uint8_t r = (pixel >> 11) & 0x1F; // R 分量 5-bit
            r = (r << 3) | (r >> 2);           // 扩展到 8-bit
            if (r > RED_THRESHOLD) {
                spot.sum_x += x;
                spot.sum_y += y;
                spot.count++;
            }
        }
    }

    if (spot.count >= MIN_RED_PIXELS) {
        spot.detected = true;
        // 像素坐标 → 屏幕坐标
        // 假设摄像头视角与屏幕对应, 屏幕 50cm 范围映射到 80px
        float scale_x = 50.0f / CAM_WIDTH;   // cm/pixel
        float scale_y = 50.0f / CAM_HEIGHT;
        spot.cx = ((float)spot.sum_x / spot.count - CAM_WIDTH/2)  * scale_x;
        spot.cy = ((float)spot.sum_y / spot.count - CAM_HEIGHT/2) * scale_y;
    }

    return spot;
}

// FIFO 基础操作 (GPIO 模拟)
#define FIFO_OE_PIN  DL_GPIO_PIN_14  // PA14
#define FIFO_RE_PIN  DL_GPIO_PIN_15  // PA15
// D0~D7 接 GPIOB 全口

uint16_t fifo_read_16(void) {
    uint8_t hi, lo;
    DL_GPIO_clearPins(GPIOA, FIFO_OE_PIN);    // OE=0
    DL_GPIO_clearPins(GPIOA, FIFO_RE_PIN);    delay_us(1);
    hi = DL_GPIO_readPins(GPIOB, 0xFF);       // 读 D0~D7
    DL_GPIO_setPins(GPIOA, FIFO_RE_PIN);      // RE=1
    DL_GPIO_clearPins(GPIOA, FIFO_RE_PIN);    delay_us(1);
    lo = DL_GPIO_readPins(GPIOB, 0xFF);
    DL_GPIO_setPins(GPIOA, FIFO_RE_PIN);
    DL_GPIO_setPins(GPIOA, FIFO_OE_PIN);      // OE=1
    return ((uint16_t)hi << 8) | lo;
}
```

**无摄像头的简化方案 — 四象限光电传感器：**
```c
// 如果摄像方案太复杂, 可用 4 个光敏电阻/光电管构成四象限检测
// 4 个传感器对准屏幕, 比较各象限亮度 → 估算红点位置
// 精度低于摄像方案, 但 MCU 开销极小

typedef struct {
    uint16_t top_left, top_right, bot_left, bot_right;
} QuadrantSensor;

Point2D quadrant_to_position(QuadrantSensor *q) {
    float total = q->top_left + q->top_right + q->bot_left + q->bot_right + 1;
    float x = ((q->top_right + q->bot_right) - (q->top_left + q->bot_left)) / total * 25.0f;
    float y = ((q->bot_left + q->bot_right) - (q->top_left + q->top_right)) / total * 25.0f;
    return (Point2D){x, y};
}
```

### --- 绿色系统: 视觉追踪闭环 ---

```c
typedef enum {
    GREEN_IDLE,
    GREEN_TRACKING,   // 追踪中
    GREEN_LOST,       // 丢失目标
    GREEN_PAUSED,     // 制动
} GreenState;

// 视觉追踪 PID (两个独立的 PID: X方向 + Y方向)
PID_Controller pid_track_x;  // X→Pan
PID_Controller pid_track_y;  // Y→Tilt

void green_system_loop(GreenState *state) {
    RedSpot spot = detect_red_spot();

    if (!spot.detected) {
        *state = GREEN_LOST;
        // 丢失目标: 扫描搜索 (缓慢扫 Pan)
        static float scan_angle = -45;
        scan_angle += 0.5f;
        if (scan_angle > 45) scan_angle = -45;
        gimbal_set_pan(scan_angle);
        return;
    }

    *state = GREEN_TRACKING;

    // X/Y 误差 → PID → 修正云台角度
    float current_pan  = pid_get_last_output(&pid_track_x);
    float current_tilt = pid_get_last_output(&pid_track_y);

    float pan_correction  = pid_update(&pid_track_x, spot.cx, 0.02f);
    float tilt_correction = pid_update(&pid_track_y, spot.cy, 0.02f);

    gimbal_set_pan(pan_correction);
    gimbal_set_tilt(tilt_correction);

    // 判断追踪成功: 误差 < 3cm (对应角度 ≈ arctan(3/100) ≈ 1.7°)
    float err_pan  = fabsf(spot.cx) * 57.29578f / SCREEN_DIST;
    float err_tilt = fabsf(spot.cy) * 57.29578f / SCREEN_DIST;
    if (err_pan < 1.7f && err_tilt < 1.7f) {
        // 追踪成功: 连续声光
        DL_GPIO_setPins(GPIOA, LED_PIN);
    } else {
        DL_GPIO_clearPins(GPIOA, LED_PIN);
    }
}
```

### --- 双系统暂停与制动 ---

```c
// 两个系统独立按键: KEY1(红)暂停, KEY2(绿)暂停
// 题目要求: 同时按下暂停键, 两个光斑应"立即制动"
// 因为红/绿系统不通信, "同时按下"靠人工实现
// 制动: 立即停止 PWM 更新 → 舵机停在原位

volatile bool g_red_paused  = false;
volatile bool g_green_paused = false;

// 在按键中断中:
void pause_button_isr(void) {
    // 关激光 (通过 MOS)
    LASER_OFF();
    // 设置暂停标志 → 主循环停止舵机角度更新
    g_red_paused = true;  // 或 g_green_paused = true
}

// 一键启动追踪 (发挥部分1):
// 按下启动键 → green_system_loop 立即执行 detect_red_spot + PID 追踪
```

### --- 双系统完整初始化 ---

```c
// 红色系统 main()
void red_main(void) {
    SYSCFG_DL_init();
    __enable_irq();
    oled_init();
    generate_square_path();
    generate_a4_path(5.0f, 8.0f, 0.0f);  // A4贴屏幕右上角

    RedState state = RED_IDLE;
    uint32_t start_ms = 0;
    uint32_t path_idx = 0;

    while (1) {
        // 按键选择模式
        if (btn_mode_pressed()) {
            state = (state + 1) % 5;  // 循环切换模式
            start_ms = g_ms_ticks;
        }
        if (btn_pause_pressed()) g_red_paused = !g_red_paused;
        if (g_red_paused) { LASER_OFF(); continue; }
        LASER_ON();

        uint32_t elapsed = g_ms_ticks - start_ms;
        red_system_loop(&state, &path_idx, elapsed);
        delay_ms(20);
    }
}

// 绿色系统 main()
void green_main(void) {
    SYSCFG_DL_init();
    __enable_irq();
    oled_init();
    camera_init();  // 初始化 OV7725+FIFO

    GreenState state = GREEN_IDLE;
    pid_init(&pid_track_x, 0.8f, 0.02f, 0.1f);  // 视觉 X PID
    pid_init(&pid_track_y, 0.8f, 0.02f, 0.1f);  // 视觉 Y PID

    while (1) {
        if (btn_track_start_pressed()) {
            state = GREEN_TRACKING;
        }
        if (btn_pause_pressed()) g_green_paused = !g_green_paused;
        if (g_green_paused) { LASER_OFF(); continue; }
        LASER_ON();

        green_system_loop(&state);
        delay_ms(20);
    }
}
```

