# CLAUDE.md 模块索引

每个 .md 文件对应 CLAUDE.md 的一个章节，便于维护和贡献。

## 模块列表

| 文件 | 对应章节 | 内容 |
|------|---------|------|
| `01_rules.md` | ⚠️ 强制开发规范 | 资料边界、引脚铁律、代码质量、API安全 |
| `02_mcu_specs.md` | 一、MCU速查 | MSPM0G3507 参数、引脚映射、决策表 |
| `03_peripherals.md` | 二、外设初始化 | GPIO, Timer, ADC, UART, I2C, SPI, OPA, HC-SR04, MPU6050, OLED, 矩阵按键, EC11, UART协议 |
| `04_algorithms.md` | 三、控制算法 | PID, 滤波器, 卡尔曼, 电机控制 |
| `05_hardware.md` | 四、硬件连接 | TB6612, MPU6050, OLED, HC-05, 电源 |
| `06_ccs_setup.md` | 五、CCS工程配置 | 新建工程、SysConfig、main.c框架 |
| `07_debug_tools.md` | 六、调试工具 | VOFA+, SerialPlot, PID调参, 按键识别 |
| `08_workflow.md` | 七~八、工作流程+注意事项 | 处理优先级、常见坑 |
| `09_contests.md` | 九~十一、电赛真题 | 25E, 24H, 23E |
| `10_k230_api.md` | 十二~十三、K230 API | 速查+已知问题 |
| `11_k230_m0g.md` | 十四、双芯方案 | 通信协议、管道代码、真题分工 |
| `12_hardware_list.md` | 十五、硬件清单 | 引脚总表、电源方案、冲突检查 |
| `13_flash_debug.md` | 十六、烧录调试 | JLink/XDS110/BSL, printf, VOFA+, Python |

## 编译单体 CLAUDE.md

```bash
cd modules
cat 01_rules.md 02_mcu_specs.md 03_peripherals.md 04_algorithms.md \
    05_hardware.md 06_ccs_setup.md 07_debug_tools.md 08_workflow.md \
    09_contests.md 10_k230_api.md 11_k230_m0g.md 12_hardware_list.md \
    13_flash_debug.md > ../CLAUDE_MODULES.md
```

当前 CLAUDE.md 为单体版本 (直接维护)，模块文件为可选拆分的辅助版本。
