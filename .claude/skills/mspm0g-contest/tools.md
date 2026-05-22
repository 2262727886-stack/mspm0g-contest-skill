# 工具链参考

## 四、CCS 工程配置

### 新建工程步骤
1. CCS → File → New → CCS Project
2. Target: MSPM0G3507
3. Project template: Empty Project (with main.c)
4. 勾选 SysConfig support
5. 打开 `.syscfg` 文件，使用图形界面配置外设

### 关键文件说明
- `.vscode/c_cpp_properties.json` — VS Code C/C++ 依赖库配置，必须在创建工程后自行生成/更新。缺失或路径错误会导致 `ti_msp_dl_config.h`、DriverLib、CMSIS 头文件误报不存在。
- `ti_msp_dl_config.h` — SysConfig 自动生成，包含所有外设初始化
- `ti_msp_dl_config.c` — SysConfig 自动生成的初始化函数 `SYSCFG_DL_init()`
- `main.c` — 用户代码，在 `SYSCFG_DL_init()` 之后编写
- SDK 默认安装路径: `C:\ti\mspm0_sdk_2_10_00_04\`

### VS Code c_cpp_properties 必备模板

每次创建 MSPM0G3507 CCS/Theia 工程后，必须按当前机器路径生成 `.vscode/c_cpp_properties.json`。若安装路径不同，只替换路径；不要删除工程 `Debug` 目录，因为 SysConfig 生成的 `ti_msp_dl_config.h` 通常在这里。

```json
{
    "configurations": [
        {
            "name": "MSPM0G3507_Config",
            "includePath": [
                "${workspaceFolder}",
                "${workspaceFolder}/Debug",
                "C:/ti/mspm0_sdk_2_10_00_04/source",
                "C:/ti/mspm0_sdk_2_10_00_04/source/third_party/CMSIS/Core/Include",
                "C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/include"
            ],
            "defines": [
                "__MSPM0G3507__",
                "__USE_SYSCONFIG__"
            ],
            "compilerPath": "C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/bin/tiarmclang.exe",
            "compilerArgs": [
                "-mcpu=cortex-m0plus",
                "-march=thumbv6m",
                "-mthumb",
                "-mfloat-abi=soft"
            ],
            "cStandard": "c11",
            "cppStandard": "c++11",
            "intelliSenseMode": "windows-clang-arm",
            "browse": {
                "path": [
                    "${workspaceFolder}",
                    "${workspaceFolder}/Debug",
                    "C:/ti/mspm0_sdk_2_10_00_04/source"
                ],
                "limitSymbolsToIncludedHeaders": true
            }
        }
    ],
    "version": 4
}
```

### 自动适配不同安装路径

生成 `c_cpp_properties.json` 时替换以下路径：

| 占位 | 说明 | 示例 |
|------|------|------|
| `SDK_PATH` | MSPM0 SDK 安装目录 | `C:/ti/mspm0_sdk_2_10_00_04` |
| `CCS_COMPILER_PATH` | CCS 编译器目录 | `C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_*` |

**生成规则**：
1. `${workspaceFolder}` 和 `${workspaceFolder}/Debug` 始终有效，不用改
2. SDK 路径按实际安装位置替换（常见: `C:/ti/mspm0_sdk_x_xx_xx_xx`）
3. 编译器版本号 `4.0.3.LTS` 按实际 CCS 版本调整
4. Debug 目录必须存在（SysConfig 生成的 `ti_msp_dl_config.h` 在此）
5. 新建工程首次编译后，检查 `.vscode/` 是否自动生成；如未生成则手动按此模板创建

### main.c 最小框架
```c
#include "ti_msp_dl_config.h"

int main(void) {
    SYSCFG_DL_init();           // 初始化所有 SysConfig 外设
    __enable_irq();             // 全局中断使能
    while (1) {}
}
```
> 详细框架见下章「外设初始化代码模板」

---

## 五、SysConfig GUI 配置指南

### 界面布局

打开 `.syscfg` 文件后，CCS 会显示 SysConfig 图形界面：

```
┌──────────────────────────┬─────────────────────────────┐
│  左侧: Available Peripherals │  右侧: 配置面板              │
│  (可添加的外设列表)          │  (选定外设的参数配置)         │
│                            │                             │
│  📌 ADD 按钮 → 搜索外设     │  已添加的外设会显示在这里      │
│  ├── GPIO                  │  点击可修改引脚、参数         │
│  ├── UART                  │                             │
│  ├── I2C                   │                             │
│  ├── SPI                   │                             │
│  ├── Timer                 │                             │
│  ├── ADC                   │                             │
│  ├── OPA                   │                             │
│  └── SYSCTL (时钟)         │                             │
└──────────────────────────┴─────────────────────────────┘
```

### 配置步骤：UART0 调试串口

```
1. 点左侧 "ADD" → 搜索 "UART" → 选 "UART (Main)"
2. 配置面板中:
   Name:          UART_0
   TX Pin:        PA0  ← 下拉选择
   RX Pin:        PA1
   Baud Rate:     115200
   Data Bits:     8
   Parity:        None
   Stop Bits:     1
3. Advanced → TX FIFO Size: 选 "Disabled" (避免短字符串卡 FIFO)
4. 保存 (Ctrl+S)
```

### 配置步骤：GPIO 输出 (LED)

```
1. 点 "ADD" → 搜索 "GPIO" → 选 "GPIO Pin"
2. 配置:
   Pin:           PA7
   Direction:     Output
   Initial Value: Low
   (PA7 无特殊功能冲突, 直接可用)
3. 需要多个 GPIO 时重复 ADD, 每个引脚一个实例
```

### 配置步骤：GPIO 输入 (按键)

```
1. 点 "ADD" → "GPIO Pin"
2. 配置:
   Pin:           PA14
   Direction:     Input
   Pull:          Pull-up  (或 Pull-down 取决于硬件)
   Interrupt:     Falling edge (如果上拉, 按下=低电平)
3. 启用中断后 SysConfig 自动生成 IRQHandler 框架
```

### 配置步骤：I2C 双总线 (OLED + MPU6050)

```
1. 点 "ADD" → 搜索 "I2C" → 选 "I2C (Main)"，添加两个实例
2. I2C0 (OLED):
   Name:          I2C_OLED, Peripheral: I2C0
   SDA Pin:       PA28, SCL Pin: PA31
   Speed:         400 kHz, TXFIFO Trigger: BYTES_1
3. I2C1 (MPU6050):
   Name:          I2C_MPU, Peripheral: I2C1
   SDA/SCL Pin:   待用户确认，禁止 PA10/PA11
   Speed:         400 kHz, TXFIFO Trigger: BYTES_1
4. ⚠️ PA10/PA11 为板载 CH340 固定占用，不要通过“拔掉 USB”来复用
5. 板载已有上拉电阻, 不需要配内部上拉
```

### 配置步骤：PWM (电机)

```
1. 点 "ADD" → 搜索 "Timer" → 选 "Timer G" (通用定时器)
   或选 "Timer A" (高级定时器, 带死区)
2. 电机推荐 TIMA0:
   Name:          TIMA_0
   Mode:          PWM
   Period:        4000 (80MHz/4000 = 20kHz)
   CC0 Pin:       PB0  ← TIMA0_C2
   CC1 Pin:       PB1  ← TIMA0_C3
3. 保存后, ti_msp_dl_config.h 自动生成:
   - DL_TimerA_setPeriod(TIMA0, 4000)
   - DL_TimerA_setCaptureCompareValue(TIMA0, 0, duty)
```

### 配置步骤：编码器 (TIMG 正交编码)

```
1. 点 "ADD" → "Timer G"
2. 配置:
   Name:          TIMG_6
   Mode:          Encoder / QEI (正交编码接口)
   A Phase Pin:   PB2
   B Phase Pin:   PB3
3. 自动生成初始化代码, DL_TimerG_getTimerCount() 读脉冲数
```

### 配置步骤：ADC (TCRT5000)

```
1. 点 "ADD" → 搜索 "ADC" → 选 "ADC12"
2. 配置:
   Name:          ADC_0
   Resolution:    12-bit
   Sample Time:   默认
   Memory 0:      Channel 0 → 选 PA24
   Memory 1:      Channel 1 → 选 PA25
   ...依次添加 5 路
3. 如需软件触发:
   Trigger:       Software
   Conversion Mode: Single
```

### 配置步骤：时钟 (SYSCTL)

```
1. 左侧 → 已有一项 "SYSCTL" (默认添加)
2. 点开 SYSCTL:
   SYSOSC:        32MHz (默认)
   SYSPLL:        Disabled (默认) — 省电, 32MHz 够用
   MCLK Source:   SYSOSC
   MCLK Divider:  /1 (不分频)
3. 如需 80MHz:
   SYSPLL:        Enabled
   SYSPLL Source: SYSOSC
   SYSPLL Ref:    32MHz
   MCLK Source:   SYSPLL (80MHz)
   ⚠️ 96MHz 超频不支持, 最大 80MHz
4. 配完查 CPUCLK_FREQ 宏确认 (ti_msp_dl_config.h)
```

### 常见 SysConfig 错误

| 错误提示 | 原因 | 解决 |
|----------|------|------|
| "Pin conflict" | 两个外设用了同一引脚 | 改其中一个 |
| "Function not available" | 引脚不支持该功能 | 换引脚 |
| "Timer instance not available" | 定时器已被占用 | 用另一个 TIMG |
| "Pull-up not valid on open drain" | 开漏引脚不支持内部上拉 | 加外部上拉或换引脚 |

---


## 九、调试与调参工具

### --- 串口 PID 调参 (配合 VOFA+ / SerialPlot) ---

**VOFA+ FireWater 协议 — 实时发送多变量波形：**

```c
// Vofa+ 的 FireWater 协议: 每帧以尾部 0x00 0x00 0x80 0x7F 结束
// 支持同时显示多条 float 曲线
void vofa_send_floats(float *data, uint8_t count) {
    uint8_t *p = (uint8_t*)data;
    for (int i = 0; i < count * 4; i++) {
        DL_UART_transmitDataBlocking(UART0, p[i]);
    }
    // 帧尾
    uint8_t tail[4] = {0x00, 0x00, 0x80, 0x7F};
    for (int i = 0; i < 4; i++) DL_UART_transmitDataBlocking(UART0, tail[i]);
}

// 使用示例: 在控制循环中发送 PID 相关变量用于调参
// float debug_data[4] = {setpoint, measurement, pwm_output, pid->integral};
// vofa_send_floats(debug_data, 4);
```

**SerialPlot 兼容格式 (float 二进制 + 同步帧头)：**

```c
// SerialPlot: 帧头 + N 个 float (大端), 波特率 921600 或更高
void serialplot_send(float *data, uint8_t count) {
    uint8_t header[2] = {0xAA, 0xAA};  // 自定义帧头
    for (int i = 0; i < 2; i++) DL_UART_transmitDataBlocking(UART0, header[i]);

    for (int i = 0; i < count; i++) {
        // 大端 float
        uint32_t raw;
        memcpy(&raw, &data[i], 4);
        DL_UART_transmitDataBlocking(UART0, (raw >> 24) & 0xFF);
        DL_UART_transmitDataBlocking(UART0, (raw >> 16) & 0xFF);
        DL_UART_transmitDataBlocking(UART0, (raw >> 8) & 0xFF);
        DL_UART_transmitDataBlocking(UART0, raw & 0xFF);
    }
}
```

**串口调试助手 PID 在线调参 (文本协议)：**

```c
// 协议: "P 1.5\n" "I 0.02\n" "D 0.1\n" "T 1000\n" (target)
// PC 端发送 → MSPM0 解析 → 更新 PID 参数
void uart_pid_tune(PID_Controller *pid, float *target) {
    static char line[32];
    static uint8_t idx = 0;
    while (DL_UART_isDataAvailable(UART0)) {
        char c = DL_UART_receiveData(UART0);
        if (c == '\r') continue;
        if (c == '\n') {
            line[idx] = 0;
            char cmd; float val;
            if (sscanf(line, "%c %f", &cmd, &val) == 2) {
                switch (cmd) {
                case 'P': pid->Kp = val; break;
                case 'I': pid->Ki = val; break;
                case 'D': pid->Kd = val; break;
                case 'T': *target   = val; break;
                }
            }
            idx = 0;
        } else if (idx < sizeof(line) - 1) {
            line[idx++] = c;
        }
    }
}

// 打印当前参数 (方便确认)
void uart_print_pid_params(PID_Controller *pid, float target) {
    printf("Kp=%.3f Ki=%.4f Kd=%.3f Target=%.2f\r\n",
           pid->Kp, pid->Ki, pid->Kd, target);
}
```

### --- 按键长按/短按/双击识别 ---

```c
typedef struct {
    uint32_t press_time;
    uint32_t release_time;
    uint8_t  state;      // 0:idle, 1:pressed, 2:waiting_double
    uint8_t  event;      // 0:none, 1:short, 2:long, 3:double
} Button;

#define BTN_SHORT_MS   30
#define BTN_LONG_MS    800
#define BTN_DOUBLE_MS  400
extern volatile uint32_t g_ms_ticks;  // 1ms 系统滴答

void button_update(Button *btn, bool pressed) {
    btn->event = 0;
    switch (btn->state) {
    case 0: // idle
        if (pressed) {
            btn->state = 1;
            btn->press_time = g_ms_ticks;
        }
        break;
    case 1: // pressed
        if (!pressed) {
            uint32_t hold = g_ms_ticks - btn->press_time;
            if (hold >= BTN_LONG_MS) {
                btn->event = 2;  // 长按
                btn->state = 0;
            } else if (hold >= BTN_SHORT_MS) {
                btn->state = 2;
                btn->release_time = g_ms_ticks;
            }
        }
        break;
    case 2: // waiting_double
        if (pressed) {
            btn->state = 1;
            btn->press_time = g_ms_ticks;
        } else if ((g_ms_ticks - btn->release_time) > BTN_DOUBLE_MS) {
            btn->event = 1;  // 短按
            btn->state = 0;
        }
        break;
    }
}
// 主循环调用: button_update(&btn, DL_GPIO_readPins(...) == 0);
// if (btn.event == 1) { /* 短按 */ }
// if (btn.event == 2) { /* 长按 */ }
// if (btn.event == 3) { /* 双击 — 在 case 1 第一个短按释放后进入 case 2 时若再次按下即双击 */ }
```

## 十、看门狗 WDT 配置

### 概述

看门狗定时器 (WDT) 是一个独立运行的递减计数器，主程序必须周期"喂狗"。如果在设定时间内没有喂狗，WDT 会触发系统复位。这是电赛控制题**最低成本的安全保障**——程序卡死时自动重启，避免小车失控。

### SysConfig 配置

```
1. 点 "ADD" → 搜索 "WDT" → 选 "Watchdog Timer"
2. 配置:
   Clock Source:  LFOSC (32.768kHz, 低功耗独立时钟)
   Period:        1 second (1 秒窗口)
   Window:        No window (简单模式)
3. 保存
```

### 基础代码

> SDk 外设名为 **WWDT** (Window Watchdog Timer)，API 前缀 `DL_WWDT_`，不是 `DL_WDT_`。

```c
#include "ti_msp_dl_config.h"

int main(void)
{
    SYSCFG_DL_init();  // SysConfig 已完成 WWDT 全部配置和使能

    printf("System boot, WWDT enabled\r\n");

    while (1)
    {
        read_sensors();
        pid_control();
        motor_output();

        /* 喂狗: DL_WWDT_restart, 不是 DL_WDT_feed! */
        DL_WWDT_restart(WWDT0_INST);
    }
}
```

### 中断里喂狗

```c
/* 中断喂狗在特定条件下可接受 (如 SDK 例程 wwdt_window_mode_periodic_reset) */
/* 但25E推荐主循环喂狗: 最简单的安全保证 */
void TIMER_0_INST_IRQHandler(void) {
    // 如果定时器和WWDT窗口对齐, 可以在此喂狗
    DL_WWDT_restart(WWDT0_INST);
}
```

### 关键 API (dl_wwdt.h)

| 函数 | 作用 |
|------|------|
| `DL_WWDT_restart(WWDT0_INST)` | 喂狗 (清零计数器) |
| `DL_WWDT_isRunning(WWDT0_INST)` | 检查是否运行中 |

> 周期/窗口/使能全在 SysConfig GUI 配置, 没有 `DL_WDT_setPeriod/enable/getCount` 等函数。

### 复位原因检测

```c
/* 启动时检查是否 WDT 触发过复位 */
if (DL_SYSCTL_getResetCause() & DL_SYSCTL_RESET_CAUSE_WDT) {
    printf("上次复位原因: 看门狗超时!\r\n");
    // 可能是程序卡死, 记录错误方便排查
    DL_SYSCTL_clearResetCause(DL_SYSCTL_RESET_CAUSE_WDT);
}
```

---

## 十一、Flash 参数存储 (校准值持久化)

### 概述

TCRT5000 黑白阈值、PID 参数、编码器偏移这些值在断电后会丢失。MSPM0G3507 的 Flash 可以在**运行时**写入指定扇区实现持久化存储。

### Flash 布局

```
MSPM0G3507 Flash: 128KB
┌─────────────────────────────┐ 0x0000_0000
│  用户程序 (~100KB)           │
│  .text, .rodata, .data ...  │
├─────────────────────────────┤ 0x0001_9000  ← 程序结束地址
│  空闲空间                     │
├─────────────────────────────┤ 0x0001_F000  ← 用来存参数
│  参数存储扇区 (4KB)           │  最后一个扇区
└─────────────────────────────┘ 0x0002_0000
```

### 参数结构体 + 读写代码 (基于 flashctl_multiple_size_write 例程)

```c
#include "ti_msp_dl_config.h"

/* Flash基地址 (避开程序区) */
#define PARAM_FLASH_ADDR   0x0001F000

typedef struct __attribute__((aligned(8))) {  /* Flash要求8字节对齐 */
    uint32_t magic;
    uint32_t version;
    uint16_t tcrt_min[8];    /* 8路循迹校准 */
    uint16_t tcrt_max[8];
    float    pid_kp, pid_ki, pid_kd;
    float    base_speed;
    int32_t  encoder_offset;
    uint32_t crc32;
} PersistentParams;

static PersistentParams g_params;

/* 擦除扇区 */
DL_FLASHCTL_COMMAND_STATUS flash_erase(uint32_t addr) {
    DL_FlashCTL_unprotectSector(FLASHCTL, addr, DL_FLASHCTL_REGION_SELECT_MAIN);
    return DL_FlashCTL_eraseMemoryFromRAM(
        FLASHCTL, addr, DL_FLASHCTL_COMMAND_SIZE_SECTOR);
}

/* 写入32位字 (每次写入前需解锁) */
DL_FLASHCTL_COMMAND_STATUS flash_write32(uint32_t addr, uint32_t *data) {
    DL_FlashCTL_unprotectSector(FLASHCTL, addr, DL_FLASHCTL_REGION_SELECT_MAIN);
    return DL_FlashCTL_programMemoryFromRAM32WithECCGenerated(
        FLASHCTL, addr, data);
}

/* 保存参数 (擦除→逐字写入) */
bool flash_save_params(void) {
    uint32_t checksum = 0;
    uint32_t *p = (uint32_t *)&g_params;
    for (int i = 0; i < sizeof(g_params)/4 - 1; i++) checksum ^= p[i];
    g_params.crc32 = checksum;

    if (flash_erase(PARAM_FLASH_ADDR) != DL_FLASHCTL_COMMAND_STATUS_FAILED) {
        for (int i = 0; i < sizeof(g_params)/4; i++) {
            if (flash_write32(PARAM_FLASH_ADDR + i*4, &p[i])
                == DL_FLASHCTL_COMMAND_STATUS_FAILED)
                return false;
        }
        return true;
    }
    return false;
}

/* 从 Flash 读取 */
bool flash_load_params(void) {
    PersistentParams *stored = (PersistentParams *)PARAM_FLASH_ADDR;
    if (stored->magic != 0xAA55EE11) return false;
    uint32_t cs = 0;
    uint32_t *p = (uint32_t *)stored;
    for (int i = 0; i < sizeof(g_params)/4 - 1; i++) cs ^= p[i];
    if (cs != stored->crc32) return false;
    memcpy(&g_params, stored, sizeof(PersistentParams));
    return true;
    }

    /* 加载 */
    memcpy(&g_params, stored, sizeof(PersistentParams));
    printf("Flash 参数加载成功\r\n");
    return true;
}

/* ---- 初始化默认参数 ---- */
void params_init_default(void) {
    g_params.magic   = 0xAA55EE11;
    g_params.version = 1;
    memset(g_params.tcrt_min, 0, sizeof(g_params.tcrt_min));
    memset(g_params.tcrt_max, 0, sizeof(g_params.tcrt_max));
    g_params.pid_kp  = 2.0f;
    g_params.pid_ki  = 0.1f;
    g_params.pid_kd  = 0.05f;
    g_params.base_speed = 0.5f;
    g_params.encoder_offset = 0;
}

/* ---- 主程序使用 ---- */
int main(void)
{
    SYSCFG_DL_init();
    __enable_irq();

    params_init_default();
    /* 尝试从 Flash 加载, 成功则覆盖默认值 */
    flash_load_params();

    printf("PID: Kp=%.2f Ki=%.3f Kd=%.3f\r\n",
           g_params.pid_kp, g_params.pid_ki, g_params.pid_kd);

    /* 运行时修改参数后保存 */
    g_params.pid_kp = 3.5f;   /* 调好参数 */
    flash_save_params();       /* 永久保存 */
    printf("参数已保存到 Flash\r\n");
    /* 下次上电自动加载 */
}
```

### 关键 API (基于 flashctl_multiple_size_write 例程)

| 函数 | 作用 |
|------|------|
| `DL_FlashCTL_unprotectSector(FLASHCTL, addr, region)` | 解锁扇区 (每次写/擦前调用) |
| `DL_FlashCTL_eraseMemoryFromRAM(FLASHCTL, addr, size)` | 擦除扇区 |
| `DL_FlashCTL_programMemoryFromRAM32WithECCGenerated(FLASHCTL, addr, &data)` | 写入32位 |
| `DL_FlashCTL_programMemoryFromRAM64WithECCGenerated(FLASHCTL, addr, &data)` | 写入64位 |

### 注意事项

| 问题 | 解决 |
|------|------|
| **地址对齐** | 8字节对齐 (word address), 非4字节 |
| **每次写前解锁** | 每项操作前都要调 `unprotectSector` |
| **返回值检查** | 所有操作返回 `DL_FLASHCTL_COMMAND_STATUS`, 检查 FAILED |
| **ECC 自动生成** | `WithECCGenerated` 版函数硬件自动算 ECC |
| **扇区选择** | 用地址指定扇区 (如 `0x0001F000`), 非扇区编号 |
## 十二、中文取模教程

### 工具

推荐 **PCtoLCD2002** (免费, 百度搜索下载)

### 取模设置

```
模式: 字符模式
选项 → 字模选项:
  点阵格式:  阴码 (1=点亮, 0=熄灭)
  取模走向:  纵向取模, 字节倒序
  字体大小:  16×16 (每个汉字 32 字节)
  输出格式:  C51 格式
```

### 操作步骤

```
1. 输入汉字, 如 "电赛"
2. 设置字体大小 16×16
3. 点击 "生成字模"
4. 复制生成的数组
```

### 天猛星 OLED 汉字显示代码

```c
/* PCtoLCD2002 生成: 16×16 纵向列行式, 阴码 */
typedef struct {
    uint8_t code[32];  /* 16×16 / 8 = 32 字节 */
} Hanzi16;

static const Hanzi16 hanzi_e = {  /* 电 */
    {0x00,0x01,0x00,0x01,0x00,0x01,0xF8,0x3F,
     0x08,0x21,0x08,0x21,0x08,0x21,0xF8,0x3F,
     0x08,0x21,0x08,0x21,0x08,0x21,0xF8,0x3F,
     0x00,0x01,0x00,0x01,0x00,0x01,0x00,0x01}
};

void oled_draw_hanzi16(uint8_t x, uint8_t y, const Hanzi16 *hz) {
    for (uint8_t col = 0; col < 16; col++) {
        uint16_t data = hz->code[col*2] | (hz->code[col*2+1] << 8);
        for (uint8_t row = 0; row < 16; row++) {
            oled_draw_pixel(x + col, y + row, (data >> row) & 1);
        }
    }
}

void oled_puts_cn(uint8_t x, uint8_t y, const char *str) {
    /* 查表法: 根据字符串查找对应的 Hanzi16 结构体 */
    /* 需要预建汉字-字模映射表 */
    while (*str) {
        if (*str & 0x80) {  /* 中文 (UTF-8 高位) */
            /* GB2312 区位码查表, 此处简化为直接跳过 */
            str += 3;  /* UTF-8 中文 3 字节 */
            x += 16;
        } else {  /* ASCII */
            oled_putchar(x, y, *str++);
            x += 6;
        }
        if (x > OLED_WIDTH - 16) { x = 0; y += 16; }
    }
}
```

---

## 十三、烧录与调试工具链

### 三种烧录方式

| 方式 | 工具 | 接口 | 速度 | 推荐度 | 文件格式 |
|------|------|------|------|--------|----------|
| **XDS110** | TI XDS110 + UniFlash/CCS | SWD (PA19/PA20) | 快 | ⭐⭐⭐ 强烈推荐 | .out |
| **J-Link** | SEGGER J-Link + UniFlash | SWD (PA19/PA20) | 快 | ⭐⭐⭐ | .out |
| **串口(BSL)** | UniFlash + BSL ROM | PA0(TX)/PA1(RX) (开漏) | 慢(920B/s) | ✅ **已验证可用** | .txt (tiarmhex生成) |

**✅ BSL 串口烧录实测验证 (2025-05-18)：**
- UniFlash 9.5.0 + COM5 + MSPM0G3507 烧录成功，程序正常执行
- ⚠️ 两个误报错误可忽略：`Image Loading Failed` 和 `Verification Failed for Datablock` — 固件实际已烧入
- 小固件(<1KB) 触发 `Data Block Size less than 1KB` 假警告，不影响运行
- **推荐 BSL 作为 XDS110 到货前的可靠替代方案**

### J-Link 烧录步骤

```
1. 用杜邦线连接:  J-Link        天猛星
                  SWDIO (TMS) → PA19
                  SWCLK       → PA20
                  3.3V        → 3.3V
                  GND         → GND
2. 打开 UniFlash → Device: MSPM0G3507
3. 选择 Connection: SEGGER J-Link
4. Load Image → 选择 .out 文件
5. 勾选 "Run Target After Program Load"
6. 点击 "Load Image" 烧录
```

### XDS110 烧录步骤

```
1. 杜邦线连接:    XDS110       天猛星
                  TMS/SWDIO  → PA19
                  TCK/SWCLK  → PA20
                  3V3        → 3.3V
                  GND        → GND
2. UniFlash → Connection: Texas Instruments XDS110 USB Debug Probe
3. Load Image → 烧录
4. 无需按 BSL/RST 键
```

### XDS110 快速编译+烧录脚本 (✅ 实测验证)

XDS110 烧录固定 ~4 秒开销（TI 调试服务器初始化），实际烧录 <100ms。使用脚本可减少手动操作。

**DSLite 命令行烧录 (核心命令)：**
```bash
DSLite flash -c mspm0g3507.ccxml \
    -s "AutoResetOnConnect=true" \
    -s "VerifyAfterProgramLoad=2" \
    test_1.out
```

**关键设置说明：**
| 设置 | 作用 |
|------|------|
| `AutoResetOnConnect=true` | 连接前自动复位芯片，避免超时 |
| `VerifyAfterProgramLoad=2` | 跳过烧录后验证，节省时间 |

**快速编译+烧录脚本 (fast_flash.sh)：**
```bash
#!/bin/bash
# 用法: ./fast_flash.sh
set -e
PROJ="工程目录路径"
CC="C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/bin/tiarmclang.exe"
DSLSITE="C:/ti/uniflash_9.5.0/deskdb/content/TICloudAgent/win/ccs_base/DebugServer/bin/DSLite.exe"
CCXML="C:/ti/uniflash_9.5.0/deskdb/content/TICloudAgent/win/scripting/examples/debugger/mspm0g3507/mspm0g3507.ccxml"
SDK="C:/ti/mspm0_sdk_2_10_00_04/source"

cd "$PROJ/Debug"

# 只编译改动的 .c 文件
for src in ../empty.c ../encoder.c ../motor.c ../pid.c; do
    obj="./$(basename "${src%.c}.o")"
    if [ "$src" -nt "$obj" ]; then
        echo "CC $(basename $src)"
        "$CC" -c -D__MSPM0G3507__ -D__USE_SYSCONFIG__ \
            -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 \
            -I"$PROJ" -I"$PROJ/Debug" -I"$SDK/third_party/CMSIS/Core/Include" -I"$SDK" \
            -gdwarf-3 -Wall -o"$obj" "$src" 2>&1 | grep -E "error|Error" || true
    fi
done

# 链接
echo "LINK"
"$CC" -D__MSPM0G3507__ -D__USE_SYSCONFIG__ \
    -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 \
    -Wl,-i"$SDK" -Wl,-i"$PROJ" -Wl,-i"$PROJ/Debug/syscfg" \
    -Wl,-i"C:/ti/ccs2020/ccs/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/lib" \
    -Wl,--rom_model -o "test_1.out" \
    ./empty.o ./ti_msp_dl_config.o ./startup_mspm0g350x_ticlang.o ./encoder.o ./motor.o ./pid.o \
    -Wl,-l"./device_linker.cmd" -Wl,-ldevice.cmd.genlibs -Wl,-llibc.a 2>&1 | grep -E "error|Error" || true

# 烧录
echo "FLASH"
"$DSLSITE" flash -c "$CCXML" -s "AutoResetOnConnect=true" -s "VerifyAfterProgramLoad=2" "./test_1.out" 2>&1 | grep -E "Success|Failed|error"
```

**Windows 批处理版 (fast_flash.bat)：**
```bat
@echo off
rem ===== 用户配置区 (按实际安装路径修改) =====
set PROJ=<你的CCS工程目录路径>
set CC=<CCS安装目录>\tools\compiler\ti-cgt-armllvm_4.0.3.LTS\bin\tiarmclang.exe
set DSLITE=<UniFlash安装目录>\deskdb\content\TICloudAgent\win\ccs_base\DebugServer\bin\DSLite.exe
set CCXML=<UniFlash安装目录>\deskdb\content\TICloudAgent\win\scripting\examples\debugger\mspm0g3507\mspm0g3507.ccxml
set SDK=<MSPM0 SDK安装目录>\source

cd /d "%PROJ%\Debug"

rem 编译改动文件
for %%s in (empty encoder motor pid) do (
    if "..\%%s.c" is newer than "%%s.o" (
        echo CC %%s.c
        "%CC%" -c -D__MSPM0G3507__ -D__USE_SYSCONFIG__ -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -I"%PROJ%" -I"%PROJ%\Debug" -I"%SDK%\third_party\CMSIS\Core\Include" -I"%SDK%" -gdwarf-3 -Wall -o"%%s.o" "..\%%s.c" 2>nul
    )
)

rem 链接
echo LINK
"%CC%" -D__MSPM0G3507__ -D__USE_SYSCONFIG__ -march=thumbv6m -mcpu=cortex-m0plus -mfloat-abi=soft -mlittle-endian -mthumb -O2 -Wl,-i"%SDK%" -Wl,-i"%PROJ%" -Wl,-i"%PROJ%\Debug\syscfg" -Wl,-i"C:\ti\ccs2020\ccs\tools\compiler\ti-cgt-armllvm_4.0.3.LTS\lib" -Wl,--rom_model -o "test_1.out" empty.o ti_msp_dl_config.o startup_mspm0g350x_ticlang.o encoder.o motor.o pid.o -Wl,-l"device_linker.cmd" -Wl,-ldevice.cmd.genlibs -Wl,-llibc.a 2>nul

rem 烧录
echo FLASH
"%DSLITE%" flash -c "%CCXML%" -s "AutoResetOnConnect=true" -s "VerifyAfterProgramLoad=2" "test_1.out" 2>&1 | findstr /C:"Success" /C:"Failed" /C:"error"
echo DONE
```

**耗时分析：**
| 阶段 | 耗时 | 说明 |
|------|------|------|
| 调试服务器初始化 | ~4 秒 | TI 工具链固有开销，不可避免 |
| 增量编译 | <1 秒 | 只编译改动文件 |
| 链接 | <0.5 秒 | |
| 实际烧录 1.9KB | <100ms | |

### 串口(BSL)烧录 (✅ 实测验证)

```
1. CCS 编译 → Ctrl+B
2. 生成 .txt: tiarmhex --ti_txt firmware.out -o firmware.txt
3. UniFlash → Device: MSPM0G3507 → Connection: UART
4. COM Port: COM5 → Load Image → 选 .txt
5. 按住 BSL 键 → 按 RST → 1秒后松 BSL
6. UniFlash 点 Start
7. 报错忽略: "Image Loading Failed" 和 "Verification Failed" 均为误报警
8. 拔插 Type-C 冷启动 → OK
```

> **实测**: BSL 烧录 920B @ 0.9kB/s, 程序正常执行。XDS110 到货前可靠替代。

### CCS Post-build 自动生成 .txt

CCS → Project → Properties → Build → Steps → Post-build steps：

```
${CCS_INSTALL_ROOT}/tools/compiler/ti-cgt-armllvm_4.0.3.LTS/bin/tiarmhex --ti_txt ${ProjName}.out
```

### 软件触发 BSL (基于 bsl_software_invoke_app_demo_uart 例程验证)

无需按硬件 BSL 键，代码中触发进入 BSL 模式：

```c
/* 方法1: 按键触发 — GPIO中断中置标志, 主循环检测后调用 */
volatile bool BSL_trigger_flag = false;

void GROUP1_IRQHandler(void) {
    switch (DL_Interrupt_getPendingGroup(DL_INTERRUPT_GROUP_1)) {
        case GPIO_SWITCHES_INT_IIDX:
            BSL_trigger_flag = true;  // 按键触发
            break;
    }
}

/* 方法2: UART收到0x22触发 */
void UART_0_INST_IRQHandler(void) {
    switch (DL_UART_Main_getPendingInterrupt(UART_0_INST)) {
        case DL_UART_MAIN_IIDX_RX:
            if (DL_UART_Main_receiveData(UART_0_INST) == 0x22)
                BSL_trigger_flag = true;
            break;
    }
}

/* 软件调用BSL (含BSL_ERR_01工作区: 清SRAM后跳转) */
__STATIC_INLINE void invokeBSL(void) {
    __asm(
        "ldr r4, = 0x41C40018\n"   // SRAMFLASH register
        "ldr r4, [r4]\n"
        "ldr r1, = 0x03FF0000\n"   // SRAM_SZ mask
        "ands r4, r1\n"
        "lsrs r4, r4, #6\n"        // to kB
        "ldr r1, = 0x20200000\n"   // NON-ECC start
        "adds r2, r4, r1\n"
        "movs r3, #0\n"
        "clear_loop:\n"            // 清SRAM (BSL_ERR_01)
        "str r3, [r1]\n"
        "adds r1, r1, #4\n"
        "cmp r1, r2\n"
        "blo clear_loop\n"
        // 强制进入BSL复位
        "str %[lvl], [%[lvl_addr]]\n"
        "str %[cmd], [%[cmd_addr]]"
        : : [lvl_addr]"r"(&SYSCTL->SOCLOCK.RESETLEVEL),
            [lvl]"r"(DL_SYSCTL_RESET_BOOTLOADER_ENTRY),
            [cmd_addr]"r"(&SYSCTL->SOCLOCK.RESETCMD),
            [cmd]"r"(SYSCTL_RESETCMD_KEY_VALUE | SYSCTL_RESETCMD_GO_TRUE)
        : "r1","r2","r3","r4"
    );
}

/* 主循环 */
if (BSL_trigger_flag) {
    invokeBSL();  // 跳转BSL, 不复返回
}
```

### CCS 生成 .txt 文件 (串口烧录用)

CCS 默认只生成 `.out`，需在 **Project → Properties → Build → Steps → Post-build steps** 添加：

```
${CCS_INSTALL_ROOT}/tools/compiler/ti-cgt-armllvm_4.0.2.LTS/bin/tiarmhex --ti_txt ${ProjName}.out
```

---

### printf 重定向到串口 (CCS)

```c
#include "ti_msp_dl_config.h"
#include <stdio.h>
#include <string.h>

/* fputc 重定向到 UART0 (PA0=TX) */
int fputc(int ch, FILE *f) {
    DL_UART_transmitDataBlocking(UART0, (uint8_t)ch);
    return ch;
}

/* 完整重定向: 如需 fputs/puts 也重定向 */
int fputs(const char *s, FILE *f) {
    uint16_t len = strlen(s);
    for (uint16_t i = 0; i < len; i++)
        DL_UART_transmitDataBlocking(UART0, (uint8_t)s[i]);
    return len;
}

int puts(const char *s) {
    int n = fputs(s, stdout);
    fputs("\n", stdout);
    return n + 1;
}
```

**SysConfig UART 配置要点：**
- UART0: PA10=TX, PA11=RX, 115200-8-N-1
- **建议关闭 TX FIFO** (TX FIFO Size = 0)，否则短字符串可能不发送
- 或发送后调用 `DL_UART_flushTXFIFO(UART0)`

---

### VOFA+ PID 实时调参

> VOFA+ FireWater/JustFloat 协议代码和操作步骤见 [第六章：调试与调参工具](#六调试与调参工具)。此处不重复。

---

### Python 串口抓取脚本

```python
"""serial_capture.py — 抓取 PID 调试数据的 Python 脚本"""
import serial
import csv
import sys
from datetime import datetime

# === 配置 ===
PORT = 'COM3'       # ⚠️ 需根据实际串口号修改, 不确定时运行后看提示
BAUD = 115200
CSV_PATH = 'pid_data.csv'

def list_ports():
    """列出可用串口"""
    import serial.tools.list_ports
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("未找到串口! 请检查 USB 连接")
        return
    print("可用串口:")
    for p in ports:
        print(f"  {p.device} — {p.description}")

def capture():
    if PORT == 'COM3':
        list_ports()
        print(f"\n请在脚本中修改 PORT 变量为实际串口号")
    
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print(f"已连接 {PORT}, 开始抓取... (Ctrl+C 停止)")
    
    with open(CSV_PATH, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['timestamp', 'ch0', 'ch1', 'ch2', 'ch3'])
        
        try:
            while True:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    try:
                        vals = [float(v.strip()) for v in line.split(',') if v.strip()]
                        ts = datetime.now().isoformat()
                        writer.writerow([ts] + vals)
                        f.flush()  # 实时写入磁盘
                        print(f"[{ts}] {vals}")
                    except ValueError:
                        pass  # 非数据行跳过
        except KeyboardInterrupt:
            print(f"\n已保存到 {CSV_PATH}")
        finally:
            ser.close()

if __name__ == '__main__':
    capture()
```

---

### 串口日志调试

**串口助手确认串口号：**
```
1. 设备管理器 → 端口(COM和LPT) → 找 "USB-SERIAL CH340"
2. 记下 COM 号 (如 COM5)
3. 串口助手选对应 COM, 115200-8-N-1, 打开
4. 按天猛星 RST, 应能看到 printf 输出
```

**CCS 调试时查看串口输出：**
- CCS 内建的 Terminal 视图可直接看 UART 输出
- 或另开 VOFA+/串口助手查看

**常见串口问题：**

| 问题 | 解决 |
|------|------|
| 串口打不开 | 检查是否被 CCS/其他程序占用, 关掉CCS Terminal |
| 数据乱码 | 检查波特率是否匹配 (115200) |
| printf 无输出 | 检查 fputc 重定向, 确认 UART0 在 SysConfig 中已配置 |
| 短字符串丢失 | 关闭 UART TX FIFO 或发送后 flush |





---

