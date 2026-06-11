# pid_tuner_car

MSPM0G3507 小车 PID 调试工程：PA25 控制启停，PC 端 PID 调试助手通过 UART0 发送参数并接收 CSV 曲线数据。

## 硬件连接

默认接线见 `PINMAP.md`。本工程按天猛星小车默认映射编写：

- TB6612FNG A 通道接右轮，B 通道接左轮。
- PA25 按键一端接 PA25，另一端接 GND，软件启用内部上拉。
- CH340/USB 串口使用 PA10=TX、PA11=RX，115200 8N1。
- PA10/PA11 已用于 UART0，不能同时接 MPU6050 I2C1。

## 使用步骤

1. CCS Theia 打开 `workspace_ccstheia/pid_tuner_car/`。
2. 打开 `empty.syscfg`，确认引脚和你的实车一致。
3. 编译并用 XDS110 烧录。
4. 架空车轮，打开 `PID调试助手`，选择对应 COM 口和 115200 波特率。
5. 按 PA25 启动/停止小车。

## PC -> MCU 命令

```text
SET P:3.0000 I:1.0000 D:0.0000
TARGET L:60 R:60
STATUS
RESET
STOP
```

## MCU -> PC CSV

每 40ms 输出一行：

```text
timestamp_ms,speed_L,speed_R,target_L,target_R,pwm_L,pwm_R,Kp,Ki
```

示例：

```text
1200,58,59,60,60,780,790,3.000,1.000
```

## 调试建议

- 首次测试必须架空车轮。
- 先发送 `TARGET L:30 R:30` 小目标速度，再按 PA25 启动。
- 如果车轮方向反了，优先检查 TB6612 A/B 通道和 `motor_left_set()` / `motor_right_set()` 的方向极性。
- 如果串口助手收不到 CSV，确认 PA10/PA11 没有被 I2C1/MPU6050 占用。

