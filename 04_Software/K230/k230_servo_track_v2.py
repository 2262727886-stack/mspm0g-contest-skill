"""
K230 舵机追踪 — 基于已验证的 shape_detect 模板
================================================
GC2093 + ST7701 800x480 直出 + 触摸 CAL + UART2 发送坐标给 MSPM0G

硬件连接:
  K230 GPIO5  (排针11, UART2_TXD) → MSPM0G PB3 (UART3_RX)
  K230 GPIO6  (排针13, UART2_RXD) → MSPM0G PB2 (UART3_TX)
  MSPM0G PB9=TIMA0_CH1=Pan舵机, PB8=TIMA0_CH0=Tilt舵机

帧协议(10字节):
  [0xA5][0x5A][CMD][PAN_L][PAN_H][TILT_L][TILT_H][0][0][CHK]
  PAN/TILT int16 小端序, 单位 0.1° (900=90.0°)
  CHK = 前9字节异或, CMD: 0x01=目标, 0x04=丢失

操作:
  触摸 CAL 按钮 → 自动校准当前颜色阈值 → 追踪开始
  ALL/RECT/TRI/CIR 切换检测模式
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART, FPIOA, Pin
import image, time, os, gc, struct

try:
    from machine import TOUCH
except Exception:
    TOUCH = None

# ============================================================
# 配置
# ============================================================
PW, PH = 800, 480              # 屏幕尺寸 = 摄像头尺寸 (零缩放)
VIEW_W, VIEW_H = 680, 480      # 左侧视觉区域
MENU_X = VIEW_W                # 右侧触摸菜单起点
MENU_W = PW - VIEW_W

# UART
UART_BAUD = 115200
SEND_EVERY_MS = 33             # ~30fps 发送

# 追踪
PAN_DEFAULT  = 900             # 默认 90.0°
TILT_DEFAULT = 900
PAN_GAIN     = 3.0             # 像素→角度(0.1°/px)
TILT_GAIN    = 3.0
PAN_CLAMP    = 750             # ±75°
TILT_CLAMP   = 600             # ±60°

# 检测
DETECT_EVERY = 2               # 隔帧检测
DETECT_X_STRIDE = 5
DETECT_Y_STRIDE = 5
MIN_PIXELS = 80
MIN_AREA = 120
MAX_TARGETS = 3
GC_EVERY_FRAMES = 300
STATUS_PRINT_MS = 0            # 脱机关闭周期打印

# CAL 采样框 (画面中心)
SAMPLE_SIZE = 48
SAMPLE_ROI = ((VIEW_W - SAMPLE_SIZE) // 2, (VIEW_H - SAMPLE_SIZE) // 2,
              SAMPLE_SIZE, SAMPLE_SIZE)
L_MARGIN, A_MARGIN, B_MARGIN = 18, 16, 16

# UI 按钮
CAL_BTN = (MENU_X + 8, 340, 104, 56)
MENU_BUTTONS = [
    ("ALL",  MENU_X + 8, 24,  104, 48),
    ("RECT", MENU_X + 8, 92,  104, 48),
    ("TRI",  MENU_X + 8, 160, 104, 48),
    ("CIR",  MENU_X + 8, 228, 104, 48),
]

active_threshold = (42, 92, -24, 26, -33, 17)

# ============================================================
# 工具函数
# ============================================================

def clamp(v, lo, hi):
    if v < lo: return lo
    if v > hi: return hi
    return v

def draw_text(img, x, y, text, color=(0, 255, 0), size=14):
    try:
        img.draw_string_advanced(x, y, size, text, color=color)
    except Exception:
        img.draw_string(x, y, text, color=color)

def make_threshold_from_roi(img):
    st = img.get_statistics(roi=SAMPLE_ROI)
    l, a, b = st.l_mean(), st.a_mean(), st.b_mean()
    return (clamp(l - L_MARGIN, 0, 100),
            clamp(l + L_MARGIN, 0, 100),
            clamp(a - A_MARGIN, -128, 127),
            clamp(a + A_MARGIN, -128, 127),
            clamp(b - B_MARGIN, -128, 127),
            clamp(b + B_MARGIN, -128, 127))

def point_in_rect(px, py, rect):
    x, y, w, h = rect
    return x <= px < x + w and y <= py < y + h

def read_touch_xy(tp):
    if tp is None: return None
    try:
        pts = tp.read()
    except Exception:
        return None
    if not pts: return None
    p = pts[0]
    try: return int(p.x), int(p.y)
    except Exception: pass
    try: return int(p.x()), int(p.y())
    except Exception: pass
    try: return int(p[0]), int(p[1])
    except Exception: return None

def send_frame(pan_x10, tilt_x10, cmd=0x01):
    buf = bytearray(10)
    buf[0] = 0xA5; buf[1] = 0x5A; buf[2] = cmd
    struct.pack_into('<h', buf, 3, pan_x10)
    struct.pack_into('<h', buf, 5, tilt_x10)
    chk = 0
    for i in range(9): chk ^= buf[i]
    buf[9] = chk
    uart.write(buf)

def pixel_to_servo(cx, cy):
    cx_err = cx - VIEW_W // 2
    cy_err = cy - VIEW_H // 2
    pan  = clamp(int(PAN_DEFAULT + cx_err * PAN_GAIN),
                 PAN_DEFAULT - PAN_CLAMP, PAN_DEFAULT + PAN_CLAMP)
    tilt = clamp(int(TILT_DEFAULT + cy_err * TILT_GAIN),
                 TILT_DEFAULT - TILT_CLAMP, TILT_DEFAULT + TILT_CLAMP)
    return pan, tilt

def draw_menu(img, mode, status, pan, tilt):
    try:
        img.draw_rectangle(MENU_X, 0, MENU_W, PH, color=(0,0,0), fill=True)
    except Exception:
        for x in range(MENU_X, PW):
            img.draw_line(x, 0, x, PH-1, color=(0,0,0))
    draw_text(img, MENU_X + 3, 2, "MODE", color=(0,255,0), size=7)
    for label, sx, sy, w, h in MENU_BUTTONS:
        active = (label == mode)
        color = (0,255,0) if active else (120,120,120)
        img.draw_rectangle(sx, sy, w, h, color=color, thickness=2)
        draw_text(img, sx+18, sy+14, label, color=color, size=18)
    x, y, w, h = CAL_BTN
    img.draw_rectangle(x, y, w, h, color=(0,120,255), thickness=2)
    draw_text(img, x+28, y+17, "CAL", color=(0,120,255), size=18)
    # 舵机角度
    draw_text(img, MENU_X+8, 420,
              "P:%d T:%d" % (pan//10, tilt//10), color=(0,255,0), size=12)
    draw_text(img, MENU_X+8, 444, status, color=(0,255,0), size=10)

# ============================================================
# 初始化
# ============================================================
sensor = None
touch = None
display_inited = False
media_inited = False
sensor_running = False
uart = None

try:
    # --- FPIOA: UART2 (GPIO5=排针11=TXD, GPIO6=排针13=RXD) ---
    fpioa = FPIOA()
    fpioa.set_function(5, FPIOA.UART2_TXD)
    fpioa.set_function(6, FPIOA.UART2_RXD)
    uart = UART(UART.UART2, baudrate=UART_BAUD,
                bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
                stop=UART.STOPBITS_ONE)

    # --- 传感器 ---
    sensor = Sensor(id=2)
    sensor.reset()
    sensor.set_framesize(width=PW, height=PH)
    sensor.set_pixformat(Sensor.RGB565)
    sensor.set_hmirror(False)
    sensor.set_vflip(False)

    # --- 显示屏 ---
    Display.init(Display.ST7701, width=PW, height=PH)
    display_inited = True
    MediaManager.init()
    media_inited = True
    sensor.run()
    sensor_running = True

    # --- 触摸屏 ---
    if TOUCH:
        try:
            touch = TOUCH(0)
            print("Touch OK")
        except Exception as e:
            touch = None
            print("Touch init failed: %s" % str(e))

    # ★ 关键: 预热10帧, 等 VI 管道稳定 (防 snapshot failed(3))
    for _ in range(10):
        tmp = sensor.snapshot()
        del tmp
        time.sleep_ms(50)
    gc.collect()

    # ============================================================
    # 主循环
    # ============================================================
    clock = time.clock()
    fc = 0
    last_pressed = False
    last_send_ms = 0
    mode = "ALL"
    last_blobs = []
    pan_target = PAN_DEFAULT
    tilt_target = TILT_DEFAULT

    print("=== K230 Servo Tracker ===")
    print("Pan: PB9=TIMA0_CH1  Tilt: PB8=TIMA0_CH0")
    print("Tap CAL to calibrate, then tracking starts")
    print("LAB threshold: %s" % str(active_threshold))

    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot()

        # --- 触摸处理 ---
        pressed = False
        xy = read_touch_xy(touch)
        if xy:
            tx, ty = xy[0], xy[1]
            # 模式按钮
            for label, sx, sy, w, h in MENU_BUTTONS:
                if point_in_rect(tx, ty, (sx, sy, w, h)):
                    pressed = True
                    if not last_pressed:
                        mode = label
                        print("Mode: %s" % mode)
                    break
            # CAL 按钮
            if point_in_rect(tx, ty, CAL_BTN):
                pressed = True
                if not last_pressed:
                    active_threshold = make_threshold_from_roi(img)
                    print("CAL: %s" % str(active_threshold))
        last_pressed = pressed

        # --- 绘制采样框 ---
        x, y, w, h = SAMPLE_ROI
        img.draw_rectangle(x, y, w, h, color=(0, 120, 255), thickness=2)
        img.draw_cross(VIEW_W // 2, VIEW_H // 2,
                       color=(0, 120, 255), size=8)

        # --- 检测 ---
        if fc % DETECT_EVERY == 0:
            last_blobs = img.find_blobs([active_threshold],
                                        roi=(0, 0, VIEW_W, VIEW_H),
                                        x_stride=DETECT_X_STRIDE,
                                        y_stride=DETECT_Y_STRIDE,
                                        pixels_threshold=MIN_PIXELS,
                                        area_threshold=MIN_AREA,
                                        merge=False, margin=0)
        if last_blobs:
            b = max(last_blobs, key=lambda x: x.pixels())
            pan_target, tilt_target = pixel_to_servo(b.cx(), b.cy())
            img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                               color=(0, 255, 0), thickness=2)
            img.draw_cross(b.cx(), b.cy(), color=(0, 255, 0), size=12)
        else:
            # 无目标: 缓慢回中
            pan_target  += (PAN_DEFAULT - pan_target) // 8
            tilt_target += (TILT_DEFAULT - tilt_target) // 8

        # --- UART 发送 ---
        now = time.ticks_ms()
        if time.ticks_diff(now, last_send_ms) >= SEND_EVERY_MS:
            last_send_ms = now
            if last_blobs:
                send_frame(pan_target, tilt_target, cmd=0x01)
            else:
                send_frame(pan_target, tilt_target, cmd=0x04)

        # --- UI ---
        n = len(last_blobs)
        status = "%s N:%d FPS:%d P:%d T:%d" % (
            mode, n, max(1, clock.fps()),
            pan_target // 10, tilt_target // 10)
        draw_text(img, 4, PH - 18, status, color=(0, 255, 0), size=14)
        draw_menu(img, mode, status, pan_target, tilt_target)

        Display.show_image(img, x=0, y=0)

        del img
        if fc % GC_EVERY_FRAMES == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\nInterrupted")
except BaseException as e:
    print("Runtime error: %s" % str(e))
    import sys
    sys.print_exception(e)
finally:
    if sensor_running and sensor:
        sensor.stop()
    if display_inited:
        Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    if media_inited:
        MediaManager.deinit()
    print("Cleaned up")
