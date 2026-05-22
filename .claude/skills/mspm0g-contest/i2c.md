# I2C (OLED + MPU6050)

## I2C 初始化

**0.96" OLED (SSD1306 I2C0) 驱动 (✅ 实机验证)：**

> 基于通用 `i2c_write_bytes()`，5x7 字体。I2C0 (PA28=SDA, PA31=SCL, 400kHz)

```c
#define OLED_ADDR 0x3C

/* 写命令 */
static int oled_cmd(uint8_t cmd) {
    uint8_t buf[2] = {0x00, cmd};
    return i2c_write_bytes(OLED_I2C_INST, OLED_ADDR, buf, sizeof(buf));
}

/* 写数据 (分块, 每块≤7字节) */
static int oled_data(const uint8_t *data, uint8_t len) {
    uint8_t buf[8];
    uint8_t offset = 0;
    while (offset < len) {
        uint8_t chunk = (uint8_t)(len - offset);
        if (chunk > 7) chunk = 7;
        buf[0] = 0x40;
        for (uint8_t i = 0; i < chunk; i++)
            buf[i + 1] = data[offset + i];
        int ret = i2c_write_bytes(OLED_I2C_INST, OLED_ADDR, buf, (uint8_t)(chunk + 1));
        if (ret != 0) return ret;
        offset = (uint8_t)(offset + chunk);
    }
    return 0;
}

/* 设置光标位置 */
static void oled_set_pos(uint8_t page, uint8_t col) {
    oled_cmd((uint8_t)(0xB0 | (page & 0x07)));
    oled_cmd((uint8_t)(0x00 | (col & 0x0F)));
    oled_cmd((uint8_t)(0x10 | (col >> 4)));
}

/* SSD1306 初始化序列 */
static void oled_init(void) {
    uint8_t cmds[] = {
        0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0x00,0x40,
        0x8D,0x14,0x20,0x00,0xA1,0xC8,0xDA,0x12,
        0x81,0xCF,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF
    };
    for (int i = 0; i < sizeof(cmds); i++) oled_cmd(cmds[i]);
}

/* 5x7 ASCII 字模 (0x30-0x39 数字, 0x41-0x5A 大写) */
static const uint8_t *font5x7(char c) {
    static const uint8_t digits[10][5] = {
        {0x3E,0x51,0x49,0x45,0x3E},{0x00,0x42,0x7F,0x40,0x00},
        {0x42,0x61,0x51,0x49,0x46},{0x21,0x41,0x45,0x4B,0x31},
        {0x18,0x14,0x12,0x7F,0x10},{0x27,0x45,0x45,0x45,0x39},
        {0x3C,0x4A,0x49,0x49,0x30},{0x01,0x71,0x09,0x05,0x03},
        {0x36,0x49,0x49,0x49,0x36},{0x06,0x49,0x49,0x29,0x1E},
    };
    static const uint8_t letters[26][5] = {
        {0x7E,0x11,0x11,0x11,0x7E},{0x7F,0x49,0x49,0x49,0x36},
        {0x3E,0x41,0x41,0x41,0x22},{0x7F,0x41,0x41,0x22,0x1C},
        {0x7F,0x49,0x49,0x49,0x41},{0x7F,0x09,0x09,0x09,0x01},
        {0x3E,0x41,0x49,0x49,0x7A},{0x7F,0x08,0x08,0x08,0x7F},
        {0x00,0x41,0x7F,0x41,0x00},{0x20,0x40,0x41,0x3F,0x01},
        {0x7F,0x08,0x14,0x22,0x41},{0x7F,0x40,0x40,0x40,0x40},
        {0x7F,0x02,0x0C,0x02,0x7F},{0x7F,0x04,0x08,0x10,0x7F},
        {0x3E,0x41,0x41,0x41,0x3E},{0x7F,0x09,0x09,0x09,0x06},
        {0x3E,0x41,0x51,0x21,0x5E},{0x7F,0x09,0x19,0x29,0x46},
        {0x46,0x49,0x49,0x49,0x31},{0x01,0x01,0x7F,0x01,0x01},
        {0x3F,0x40,0x40,0x40,0x3F},{0x1F,0x20,0x40,0x20,0x1F},
        {0x7F,0x20,0x18,0x20,0x7F},{0x63,0x14,0x08,0x14,0x63},
        {0x07,0x08,0x70,0x08,0x07},{0x61,0x51,0x49,0x45,0x43},
    };
    static const uint8_t blank[5] = {0x00,0x00,0x00,0x00,0x00};
    static const uint8_t colon[5] = {0x00,0x36,0x36,0x00,0x00};
    static const uint8_t minus[5] = {0x08,0x08,0x08,0x08,0x08};
    if (c >= '0' && c <= '9') return digits[c - '0'];
    if (c >= 'A' && c <= 'Z') return letters[c - 'A'];
    if (c >= 'a' && c <= 'z') return letters[c - 'a'];
    if (c == ':') return colon;
    if (c == '-') return minus;
    return blank;
}

/* 在指定页/列显示字符串 */
static void oled_puts(uint8_t page, uint8_t col, const char *s) {
    oled_set_pos(page, col);
    while (*s) {
        uint8_t out[6];
        const uint8_t *glyph = font5x7(*s++);
        for (uint8_t i = 0; i < 5; i++) out[i] = glyph[i];
        out[5] = 0x00;
        oled_data(out, sizeof(out));
    }
}

// SysConfig: I2C_OLED → I2C0 → SDA: PA28, SCL: PA31, 400kHz, TXFIFO=BYTES_1
```


### --- I2C 通用驱动 (✅ 实机验证) ---

> 通用 I2C 读写函数，通过 `I2C_Regs *i2c` 参数复用，适用于 I2C0/I2C1。

```c
#define I2C_TIMEOUT 100000U

/* 等待总线 IDLE */
static int i2c_wait_idle(I2C_Regs *i2c) {
    uint32_t t = I2C_TIMEOUT;
    while (!(DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_IDLE)) {
        if (--t == 0) return -1;
    }
    return 0;
}

/* 等待传输完成 (检查 BUSY + ERROR) */
static int i2c_wait_done(I2C_Regs *i2c) {
    uint32_t t = I2C_TIMEOUT;
    while (DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_BUSY) {
        if (DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_ERROR) return -2;
        if (--t == 0) return -1;
    }
    if (DL_I2C_getControllerStatus(i2c) & DL_I2C_CONTROLLER_STATUS_ERROR) return -2;
    return 0;
}

/* 通用 I2C 写 (带超时+错误检查) */
static int i2c_write_bytes(I2C_Regs *i2c, uint8_t addr, const uint8_t *buf, uint8_t len) {
    if (!buf || !len) return -4;
    if (i2c_wait_idle(i2c) != 0) return -1;
    DL_I2C_flushControllerTXFIFO(i2c);
    DL_I2C_flushControllerRXFIFO(i2c);
    DL_I2C_fillControllerTXFIFO(i2c, buf, len);
    DL_I2C_startControllerTransfer(i2c, addr, DL_I2C_CONTROLLER_DIRECTION_TX, len);
    delay_cycles(16);
    return i2c_wait_done(i2c);
}
```


### --- MPU6050 完整驱动 (I2C1, 引脚待确认) ---

> ⚠️ PA10/PA11 已被板载 CH340 固定占用，不能再接 MPU6050。以下驱动逻辑可复用，但 SysConfig 中的 I2C1 SDA/SCL 必须按用户实际接线选择未占用引脚，并先实机验证。

```c
#define MPU6050_ADDR      0x68
#define REG_SMPLRT_DIV    0x19
#define REG_CONFIG        0x1A
#define REG_GYRO_CONFIG   0x1B
#define REG_ACCEL_CONFIG  0x1C
#define REG_ACCEL_XOUT_H  0x3B
#define REG_PWR_MGMT_1    0x6B
#define REG_WHO_AM_I      0x75

/* 写寄存器 */
static int mpu_write_reg(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = {reg, val};
    return i2c_write_bytes(MPU_I2C_INST, MPU6050_ADDR, buf, sizeof(buf));
}

/* 读多字节 (逐字节从RX FIFO读) */
static int mpu_read_multi(uint8_t reg, uint8_t *buf, uint8_t len) {
    if (!buf || !len) return -4;
    /* 发送寄存器地址 */
    if (i2c_write_bytes(MPU_I2C_INST, MPU6050_ADDR, &reg, 1) != 0) return -2;
    if (i2c_wait_idle(MPU_I2C_INST) != 0) return -3;
    /* 接收数据 */
    DL_I2C_flushControllerRXFIFO(MPU_I2C_INST);
    DL_I2C_startControllerTransfer(MPU_I2C_INST, MPU6050_ADDR,
        DL_I2C_CONTROLLER_DIRECTION_RX, len);
    delay_cycles(16);
    for (uint8_t i = 0; i < len; i++) {
        uint32_t t = I2C_TIMEOUT;
        while (DL_I2C_isControllerRXFIFOEmpty(MPU_I2C_INST)) {
            if (DL_I2C_getControllerStatus(MPU_I2C_INST) & DL_I2C_CONTROLLER_STATUS_ERROR)
                return -5;
            if (--t == 0) return -6;
        }
        buf[i] = DL_I2C_receiveControllerData(MPU_I2C_INST);
    }
    return i2c_wait_done(MPU_I2C_INST);
}

/* 初始化: 唤醒, ±2000°/s, ±8g, 1kHz */
static int mpu_init(void) {
    uint8_t who = 0;
    if (mpu_write_reg(REG_PWR_MGMT_1, 0x00) != 0) return -1;
    delay_ms(100);
    if (mpu_read_multi(REG_WHO_AM_I, &who, 1) != 0) return -2;
    if (who != 0x68) return -3;
    if (mpu_write_reg(REG_SMPLRT_DIV, 0x07) != 0) return -4;
    if (mpu_write_reg(REG_CONFIG, 0x03) != 0) return -5;
    if (mpu_write_reg(REG_GYRO_CONFIG, 0x18) != 0) return -6;
    if (mpu_write_reg(REG_ACCEL_CONFIG, 0x10) != 0) return -7;
    return 0;
}

/* 读取全部数据 (14字节: ax,ay,az,temp,gx,gy,gz) */
typedef struct { int16_t ax, ay, az, gx, gy, gz, temp; } MPU6050_Data;

static int mpu_read_all(MPU6050_Data *d) {
    uint8_t buf[14] = {0};
    int ret = mpu_read_multi(REG_ACCEL_XOUT_H, buf, sizeof(buf));
    if (ret != 0) return ret;
    d->ax   = (int16_t)((buf[0] << 8) | buf[1]);
    d->ay   = (int16_t)((buf[2] << 8) | buf[3]);
    d->az   = (int16_t)((buf[4] << 8) | buf[5]);
    d->temp = (int16_t)((buf[6] << 8) | buf[7]);
    d->gx   = (int16_t)((buf[8] << 8) | buf[9]);
    d->gy   = (int16_t)((buf[10] << 8) | buf[11]);
    d->gz   = (int16_t)((buf[12] << 8) | buf[13]);
    return 0;
}

// SysConfig 配置:
// I2C_MPU → I2C1/软件I2C → SDA/SCL: 按实际接线配置，禁止 PA10/PA11, 400kHz, TXFIFO=BYTES_1
```

// 加速度计 → 角度 (pitch: atan2(-ax, sqrt(ay^2+az^2)), roll: atan2(ay, az))
// 注意: 6轴 Mahony 无磁力计修正, yaw 会漂移, 仅 pitch/roll 可靠
float mpu6050_accel_pitch(float ax, float ay, float az) {
    return atan2f(-ax, sqrtf(ay*ay + az*az)) * 57.29578f;
}
float mpu6050_accel_roll(float ay, float az) {
    return atan2f(ay, az) * 57.29578f;
}

// Mahony AHRS 姿态解算 (六轴, 2K 参数)
typedef struct {
    float q0, q1, q2, q3;  // 四元数
    float kp, ki;           // PI 增益
    float integral_fb_x, integral_fb_y, integral_fb_z;
} MahonyAHRS;

void mahony_init(MahonyAHRS *m, float kp, float ki) {
    m->q0 = 1.0f; m->q1 = 0.0f; m->q2 = 0.0f; m->q3 = 0.0f;
    m->kp = kp; m->ki = ki;
    m->integral_fb_x = m->integral_fb_y = m->integral_fb_z = 0.0f;
}

void mahony_update(MahonyAHRS *m, float gx, float gy, float gz,
                   float ax, float ay, float az, float dt) {
    float recip_norm;
    float hx, hy, bx, bz;
    float vx, vy, vz, wx, wy, wz;
    float ex, ey, ez;
    float qa, qb, qc;

    // 加速度计归一化
    recip_norm = 1.0f / sqrtf(ax*ax + ay*ay + az*az);
    ax *= recip_norm; ay *= recip_norm; az *= recip_norm;

    // 重力方向估计
    vx = 2.0f * (m->q1*m->q3 - m->q0*m->q2);
    vy = 2.0f * (m->q0*m->q1 + m->q2*m->q3);
    vz = m->q0*m->q0 - m->q1*m->q1 - m->q2*m->q2 + m->q3*m->q3;

    // 误差
    ex = ay*vz - az*vy;
    ey = az*vx - ax*vz;
    ez = ax*vy - ay*vx;

    // 积分反馈
    m->integral_fb_x += m->ki * ex * dt;
    m->integral_fb_y += m->ki * ey * dt;
    m->integral_fb_z += m->ki * ez * dt;

    // 修正陀螺仪
    gx += m->kp*ex + m->integral_fb_x;
    gy += m->kp*ey + m->integral_fb_y;
    gz += m->kp*ez + m->integral_fb_z;

    // 四元数更新
    qa = m->q0; qb = m->q1; qc = m->q2;
    m->q0 += (-qb*gx - qc*gy - m->q3*gz) * 0.5f * dt;
    m->q1 += ( qa*gx + qc*gz - m->q3*gy) * 0.5f * dt;
    m->q2 += ( qa*gy - qb*gz + m->q3*gx) * 0.5f * dt;
    m->q3 += ( qa*gz + qb*gy - qc*gx) * 0.5f * dt;

    // 归一化
    recip_norm = 1.0f / sqrtf(m->q0*m->q0 + m->q1*m->q1 + m->q2*m->q2 + m->q3*m->q3);
    m->q0 *= recip_norm; m->q1 *= recip_norm; m->q2 *= recip_norm; m->q3 *= recip_norm;
}

// 从四元数提取 pitch/roll (度)
float mahony_get_pitch(MahonyAHRS *m) {
    return asinf(2.0f*(m->q2*m->q3 + m->q0*m->q1)) * 57.29578f;
}
float mahony_get_roll(MahonyAHRS *m) {
    return atan2f(2.0f*(m->q0*m->q2 - m->q1*m->q3),
                  1.0f - 2.0f*(m->q2*m->q2 + m->q1*m->q1)) * 57.29578f;
}
```

> ⚠️ OLED 驱动以 [I2C 章节](#i2c0oled-driver) 的实机验证版本为准，此处不再重复。


## 七、I2C 总线共享指南 (拓展板已物理分离)

> **拓展板已将 OLED(I2C0) 和 MPU6050(I2C1) 分离到独立总线，不再需要软件调度。**
> 以下内容适用于旧版同总线方案，仅作参考。

### 旧版问题

OLED (0x3C) 和 MPU6050 (0x68) 共用 I2C0，同时刷 OLED 和读 MPU6050 会阻塞总线。

### 解决方案

```c
/* === I2C 设备管理 === */
typedef struct {
    uint8_t addr;          /* 从机地址 */
    uint32_t last_access;  /* 上次访问时间戳 */
    uint32_t min_interval; /* 最小访问间隔 (ms) */
} I2C_Device;

static I2C_Device i2c_dev_oled = {0x3C, 0, 100};  /* OLED: 100ms 间隔 */
static I2C_Device i2c_dev_mpu  = {0x68, 0, 5};     /* MPU: 5ms 间隔 */

/* 设备内核对 I2C 总线访问 */
bool i2c_device_access(I2C_Device *dev) {
    if (g_ms_ticks - dev->last_access < dev->min_interval) return false;
    dev->last_access = g_ms_ticks;
    return true;
}

/* 主循环调度 */
void main_loop(void) {
    while (1) {
        /* 每 100ms 刷新一次 OLED (耗时约 20ms, 发 1024 字节) */
        if (i2c_device_access(&i2c_dev_oled)) {
            oled_update_display();  /* 只刷新变化的部分, 不全刷 */
        }
        /* 每 5ms 读一次 MPU6050 (耗时约 1ms, 发 14 字节) */
        if (i2c_device_access(&i2c_dev_mpu)) {
            mpu6050_read_all(&mpu_data);
        }
        /* PID 计算不依赖 I2C, 随时可以执行 */
        pid_control_loop();
    }
}
```

### I2C 冲突检测

```c
/* 发送前检查总线是否忙 */
if (DL_I2C_getControllerStatus(I2C0) & DL_I2C_CONTROLLER_STATUS_BUSY) {
    return;  // 上次传输未完成, 跳过
}

/* 超时保护: startControllerTransfer 自动生成 STOP, 无需手动 */
#define I2C_TIMEOUT_MS  10
uint32_t t0 = g_ms_ticks;
while (DL_I2C_getControllerStatus(I2C0) & DL_I2C_CONTROLLER_STATUS_BUSY) {
    if (g_ms_ticks - t0 > I2C_TIMEOUT_MS) {
        DL_I2C_disableStopCondition(I2C0);  // 异常时强制释放总线
        break;
    }
}
```

### OLED 部分刷新 (省带宽)

```c
/* 只刷新变化区域而不是整屏 */
void oled_update_partial(uint8_t page_start, uint8_t page_end) {
    oled_write_cmd(0x21); oled_write_cmd(0x00); oled_write_cmd(127);  /* 列 */
    oled_write_cmd(0x22); oled_write_cmd(page_start); oled_write_cmd(page_end);
    oled_write_data_buf(&oled_framebuffer[page_start * 128],
                         (page_end - page_start + 1) * 128);
}
```

---

