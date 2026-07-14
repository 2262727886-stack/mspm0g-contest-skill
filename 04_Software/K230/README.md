# K230 视觉脚本

K230 庐山派 (CanMV MicroPython) 视觉识别与双芯通信脚本。

## 脚本清单

| 脚本 | 功能 | 来源 |
|------|------|------|
| `k230_cam_test.py` | 摄像头基础测试（验证 GC2093 出图） | 根目录 |
| `k230_cam_test_25e.py` | 25E 竞赛视觉：A4 黑框检测 + OLED + UART | test_2 |
| `k230_shape_detect.py` | 形状检测（矩形/三角形/圆形） | 根目录 |
| `k230_triangle_detect.py` | 三角形检测 | 根目录 |
| `k230_rect_detect.py` | 矩形检测 | 根目录 |
| `k230_touch_tuner.py` | 触摸屏 PID 调参界面 | 根目录 |
| `k230_sensor_diag.py` | 传感器诊断脚本 | 根目录 |
| `servo_test_minimal.py` | 舵机最小化测试 | 根目录 |
| `k230_servo_track.py` | 色块追踪（主脚本） | test_2 |
| `k230_servo_track_v2.py` | 色块追踪 v2 | test_2 |
| `k230_wheeltec_track.py` | Wheeltec 协议目标追踪 | test_2 |
| `k230_rect_track.py` | 矩形识别 + 追踪 | test_2 |
| `k230_cam_lcd_test.py` | 摄像头 + MIPI LCD 联调 | test_2 |
| `k230_touch_test.py` | 触摸屏功能测试 | test_2 |
| `k230_uart_all_test.py` | UART 全通道通信测试 | test_2 |

## 开发铁律

1. 导入必须用 `from media.sensor import *` 星号导入
2. 构造用 `Sensor(id=2)`，不是 `Sensor(width=..., height=...)`
3. 主循环首行必须是 `os.exitpoint()`
4. GPIO 必须先 `fpioa.set_function()` 再 `Pin()`
5. Pin 只有 `pin.value(1/0)`，无 high()/low()/on()/off()
6. PWM 仅 2 个位置参数: `PWM(2, 50)`
7. ADC 最高 1.8V，超压烧毁芯片
8. LAB 阈值必须在场地灯光下现场校准
