"""
K230 舵机追踪 — 视觉检测 + UART 坐标发送
===========================================
用途: K230 摄像头检测彩色目标 → 计算舵机角度 → UART2 发送给 MSPM0G3507
联调: MSPM0G 通过 UART3(PB2/PB3) 接收, 驱动 PB8/PB9 舵机

硬件连接 (K230排针 → MSPM0G):
  K230 GPIO5  (排针11, UART2_TXD) → MSPM0G PB3 (UART3_RX)
  K230 GPIO6  (排针13, UART2_RXD) → MSPM0G PB2 (UART3_TX)
  GND 共地

K230 排针 UART 速查:
  串口号 | TXD引脚 | RXD引脚 | 排针位       | 备注
  UART1  | GPIO3   | GPIO4   | 排针08,10    | 可用
  UART2  | GPIO5   | GPIO6   | 排针11,13    | ✅ 推荐(独立)
  UART3  | GPIO32  | GPIO33  | 排针37,40    | 可用
  UART4  | GPIO36  | GPIO37  | 排针29,31    | 可用(避开GPIO48/49与CSI2共用)

帧协议 (10字节):
  [0xA5][0x5A][CMD][PAN_L][PAN_H][TILT_L][TILT_H][EXTRA_L][EXTRA_H][CHK]
  PAN/TILT 单位 0.1°, 小端序
  CHK = 前9字节异或
  CMD: 0x01=目标坐标, 0x04=目标丢失

操作:
  IDE 运行 → 对准彩色目标 → 按 K2(GPIO53) 自动校准 LAB 阈值 → 追踪开始
  触摸屏/IDE窗口显示十字准星 + 目标框
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART, FPIOA, Pin
import image, time, os, gc, struct

# ============================================================
# 配置参数
# ============================================================
IMG_W, IMG_H = 320, 240              # QVGA 高帧率优先
SATURATION_THRESH = 192               # 自动校准: 彩色像素判据(RGB max-min差)
CAL_ROI_W, CAL_ROI_H = 80, 60        # 自动校准采样区域(中心)
DETECT_EVERY = 1                      # 每帧检测(VGA以下无压力)
UART_BAUD = 115200
SEND_EVERY_MS = 33                    # 发送间隔(~30fps)
GC_EVERY_FRAMES = 200                 # GC 间隔
STATUS_PRINT_MS = 2000                # 状态打印间隔

# 舵机角度映射
PAN_DEFAULT  = 900     # 默认 90.0° (中心)
TILT_DEFAULT = 900
PAN_GAIN     = 3.0     # 水平追踪灵敏度: 像素误差→角度修正(0.1°/px)
TILT_GAIN    = 3.0     # 俯仰追踪灵敏度
PAN_CLAMP    = 750     # 水平限幅: ±75.0° (范围 15.0°~165.0°)
TILT_CLAMP   = 600     # 俯仰限幅: ±60.0° (范围 30.0°~150.0°)

# LAB 颜色预设 (自动校准时被覆盖)
THRESHOLD = [(42, 92, -24, 26, -33, 17)]  # 默认值, 启动后 CAL 校准

# ============================================================
# 颜色预设表 (自动校准用)
# ============================================================
COLOR_PRESETS = {
    "red":    {"a_lo": 15, "a_hi": 127, "b_lo":  10, "b_hi": 127},
    "green":  {"a_lo":-128,"a_hi":  -8, "b_lo":-128, "b_hi": 127},
    "blue":   {"a_lo":-128,"a_hi": 127, "b_lo":-128, "b_hi": -20},
    "yellow": {"a_lo":-128,"a_hi": 127, "b_lo": 15,  "b_hi": 127},
    "orange": {"a_lo": 15, "a_hi": 127, "b_lo": 15,  "b_hi": 127},
    "purple": {"a_lo": 15, "a_hi": 127, "b_lo":-128, "b_hi": -20},
    "white":  {"a_lo":-128,"a_hi": 127, "b_lo":-128, "b_hi": 127},
    "black":  {"a_lo":-128,"a_hi": 127, "b_lo":-128, "b_hi": 127},
}

# ============================================================
# 初始化
# ============================================================

# 清理上次运行残留 (防 snapshot failed(3))
try:
    MediaManager.deinit()
    time.sleep_ms(200)
except Exception:
    pass

# --- FPIOA: UART2 (排针11=GPIO5=TXD, 排针13=GPIO6=RXD) ---
fpioa = FPIOA()
fpioa.set_function(5, FPIOA.UART2_TXD)
fpioa.set_function(6, FPIOA.UART2_RXD)
uart = UART(UART.UART2, baudrate=UART_BAUD,
            bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
            stop=UART.STOPBITS_ONE)

# --- 按键: GPIO53(板载用户键) 用于 CAL 校准 ---
fpioa.set_function(53, FPIOA.GPIO53)
btn = Pin(53, Pin.IN, Pin.PULL_DOWN)  # 按下=高电平

# --- 摄像头: GC2093 ---
sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=IMG_W, height=IMG_H)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

# --- 显示 (VIRT=IDE调试, ST7701=物理屏脱机) ---
DISPLAY_VIRT = True  # IDE 调试用 True, 脱机改为 False
if DISPLAY_VIRT:
    Display.init(Display.VIRT, width=640, height=480, to_ide=True)
else:
    Display.init(Display.ST7701, width=800, height=480)

MediaManager.init()
sensor.run()
# 等 VI 管道产出第一帧 (防 snapshot failed(3))
time.sleep_ms(200)

# ============================================================
# 工具函数
# ============================================================

def auto_calibrate(img):
    """一键 LAB 校准: 采画面中心区域 → RGB565统计 → 颜色预设 → LAB阈值"""
    cx, cy = IMG_W // 2, IMG_H // 2
    rw, rh = CAL_ROI_W, CAL_ROI_H
    rx = max(0, cx - rw // 2)
    ry = max(0, cy - rh // 2)
    rw = min(rw, IMG_W - rx)
    rh = min(rh, IMG_H - ry)

    roi = img.copy(roi=(rx, ry, rw, rh))
    if roi is None:
        return None

    s = roi.get_statistics()
    del roi

    rm, gm, bm = s[0], s[6], s[12]        # RGB mean
    rmx, gmx, bmx = s[5], s[11], s[17]    # RGB max
    rmn, gmn, bmn = s[4], s[10], s[16]    # RGB min

    # 计算 LAB L 通道: 亮度范围, 加减余量
    L_lo = max(0,   int((rmn + gmn + bmn) / 3 * 0.65))
    L_hi = min(100, int((rmx + gmx + bmx) / 3 * 1.35))
    if L_hi - L_lo < 15:
        L_lo, L_hi = max(0, L_lo - 8), min(100, L_hi + 8)

    # 颜色判定 (按顺序匹配, 首命中即停)
    A_lo, A_hi = -128, 127
    B_lo, B_hi = -128, 127

    tests = [
        ("red",    rm > gm + 25 and rm > bm + 25),
        ("green",  gm > rm + 25 and gm > bm + 25),
        ("blue",   bm > rm + 25 and bm > gm + 25),
        ("yellow", rm > 140 and gm > 110 and bm < 90),
        ("orange", rm > 160 and 60 < gm < 140 and bm < 80),
        ("purple", rm > 100 and bm > 100 and gm < 80),
        ("white",  rm > 180 and gm > 180 and bm > 180),
        ("black",  rm < 60 and gm < 60 and bm < 60),
    ]
    for name, matched in tests:
        if matched:
            A_lo, A_hi = COLOR_PRESETS[name]["a_lo"], COLOR_PRESETS[name]["a_hi"]
            B_lo, B_hi = COLOR_PRESETS[name]["b_lo"], COLOR_PRESETS[name]["b_hi"]
            break

    return [(L_lo, L_hi, A_lo, A_hi, B_lo, B_hi)]


def send_frame(pan_x10, tilt_x10, cmd=0x01, extra=0):
    """发送10字节帧到MSPM0G"""
    buf = bytearray(10)
    buf[0] = 0xA5
    buf[1] = 0x5A
    buf[2] = cmd
    # 小端序 int16
    struct.pack_into('<h', buf, 3, pan_x10)
    struct.pack_into('<h', buf, 5, tilt_x10)
    struct.pack_into('<h', buf, 7, extra)
    # 校验: 前9字节异或
    chk = 0
    for i in range(9):
        chk ^= buf[i]
    buf[9] = chk
    uart.write(buf)


def send_lost():
    """发送目标丢失帧"""
    buf = bytearray(10)
    buf[0] = 0xA5
    buf[1] = 0x5A
    buf[2] = 0x04
    chk = 0
    for i in range(9):
        chk ^= buf[i]
    buf[9] = chk
    uart.write(buf)


def pixel_to_servo(blob_cx, blob_cy):
    """像素坐标 → 舵机角度(0.1°单位)
    画面中心=舵机90°, 偏移量×增益=角度修正
    """
    cx_err = blob_cx - IMG_W // 2   # px, 正值=偏右
    cy_err = blob_cy - IMG_H // 2   # px, 正值=偏下

    pan  = int(PAN_DEFAULT  + cx_err * PAN_GAIN)
    tilt = int(TILT_DEFAULT + cy_err * TILT_GAIN)

    # 限幅
    pan  = max(PAN_DEFAULT - PAN_CLAMP, min(PAN_DEFAULT + PAN_CLAMP, pan))
    tilt = max(TILT_DEFAULT - TILT_CLAMP, min(TILT_DEFAULT + TILT_CLAMP, tilt))

    return pan, tilt


# ============================================================
# 主循环
# ============================================================
clock = time.clock()
fc = 0
last_send_ms = 0
last_status_ms = 0
last_gc_ms = time.ticks_ms()
btn_was_pressed = False
last_blobs = []
pan_target = PAN_DEFAULT
tilt_target = TILT_DEFAULT
cal_done = False

print("=== K230 Servo Tracker ===")
print("Pan 舵机: PB9=TIMA0_CH1, Tilt 舵机: PB8=TIMA0_CH0")
print("K2(GPIO53): CAL 一键校准 | UART2→M0G UART3 115200")
print("对准目标 → 按 K2 校准 → 追踪开始")

while True:
    os.exitpoint()
    clock.tick()
    fc += 1

    img = sensor.snapshot()

    # --- 按键: CAL 校准 ---
    btn_now = (btn.value() == 1)
    if btn_now and not btn_was_pressed:
        new_thr = auto_calibrate(img)
        if new_thr:
            THRESHOLD = new_thr
            cal_done = True
            print("CAL OK: THRESHOLD =", THRESHOLD)
        else:
            print("CAL FAIL: 请将彩色目标放在画面中心")
    btn_was_pressed = btn_now

    # --- 目标检测 ---
    if cal_done and fc % DETECT_EVERY == 0:
        last_blobs = img.find_blobs(THRESHOLD,
                                    roi=(0, 0, IMG_W, IMG_H),
                                    x_stride=2, y_stride=2,
                                    pixels_threshold=30,
                                    area_threshold=50,
                                    merge=False, margin=0)
    if last_blobs:
        # 取最大色块
        b = max(last_blobs, key=lambda x: x.pixels())
        pan_target, tilt_target = pixel_to_servo(b.cx(), b.cy())

        # 绘制目标
        img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                           color=(0, 255, 0), thickness=2)
        img.draw_cross(b.cx(), b.cy(), color=(0, 255, 0), size=12)
    else:
        # 没有目标: 缓慢回中
        pan_target  += (PAN_DEFAULT - pan_target) // 8
        tilt_target += (TILT_DEFAULT - tilt_target) // 8

    # --- UART 发送 ---
    now_ms = time.ticks_ms()
    if time.ticks_diff(now_ms, last_send_ms) >= SEND_EVERY_MS:
        last_send_ms = now_ms
        if last_blobs:
            send_frame(pan_target, tilt_target, cmd=0x01, extra=len(last_blobs))
        else:
            send_lost()

    # --- 画面UI ---
    # 十字准星(画面中心=舵机90°位置)
    img.draw_cross(IMG_W // 2, IMG_H // 2, color=(255, 255, 0), size=16)
    img.draw_circle(IMG_W // 2, IMG_H // 2, 5, color=(255, 255, 0))

    # 状态文字
    s = "CAL" if not cal_done else "TRACK"
    c = (0, 120, 255) if not cal_done else (0, 255, 0)
    img.draw_string_advanced(4, 4, 16, s, color=c)

    if cal_done:
        ang = "P:%d T:%d" % (pan_target // 10, tilt_target // 10)
        img.draw_string_advanced(4, IMG_H - 20, 14, ang, color=(255, 255, 255))

    # --- 显示 ---
    Display.show_image(img)

    # --- GC ---
    if fc % GC_EVERY_FRAMES == 0:
        t = time.ticks_ms()
        if time.ticks_diff(t, last_gc_ms) > 1000:
            last_gc_ms = t
            gc.collect()

    # --- 周期状态打印 ---
    if STATUS_PRINT_MS > 0:
        t2 = time.ticks_ms()
        if time.ticks_diff(t2, last_status_ms) >= STATUS_PRINT_MS:
            last_status_ms = t2
            fps = clock.fps()
            n = len(last_blobs)
            print("FPS:%d Targets:%d Pan:%.1f Tilt:%.1f" %
                  (fps, n, pan_target / 10.0, tilt_target / 10.0))
