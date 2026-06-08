"""
K230 矩形追踪 + 舵机控制
=========================
基于已验证 shape_detect 模板, 专注检测矩形色块 → UART2 发送坐标

操作:
  1. 把彩色矩形放在画面中心的蓝色校准框内
  2. 触摸右侧 CAL 按钮 → 自动 LAB 校准
  3. 检测到矩形后: 绿色框+十字, 坐标通过 UART2 发给 MSPM0G
  4. MSPM0G PB3=RX 接收, 驱动 PB9(Pan)/PB8(Tilt) 舵机追踪

硬件:
  K230 GPIO5(排针11) → MSPM0G PB3(UART3_RX)
  K230 GPIO6(排针13) → MSPM0G PB2(UART3_TX)
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import UART, FPIOA
import image, time, os, gc, struct

try:
    from machine import TOUCH
except Exception:
    TOUCH = None

# ============================================================
PW, PH = 800, 480
VIEW_W, VIEW_H = 680, 480  # 左侧视觉区域
MENU_X = VIEW_W             # 右侧菜单栏

# UART
UART_BAUD = 115200
SEND_EVERY_MS = 33

# 舵机角度映射
PAN_DEFAULT  = 900     # 90.0°
TILT_DEFAULT = 900
PAN_GAIN     = 3.0     # 像素→角度(0.1°/px), 越大越灵敏
TILT_GAIN    = 3.0
PAN_CLAMP    = 750     # ±75°限幅
TILT_CLAMP   = 600     # ±60°限幅

# 检测参数
DETECT_EVERY = 2       # 隔帧检测, 提帧率
X_STRIDE, Y_STRIDE = 5, 5
MIN_PIXELS = 80
MIN_AREA = 120
GC_EVERY = 300

# CAL 采样框 (画面中心)
S_SIZE = 48
S_ROI = ((VIEW_W - S_SIZE) // 2, (VIEW_H - S_SIZE) // 2, S_SIZE, S_SIZE)
L_MARGIN, A_MARGIN, B_MARGIN = 18, 16, 16

# UI
CAL_BTN = (MENU_X + 8, 340, 104, 56)

# 默认阈值 (CAL 前使用, 不会匹配任何东西; CAL 后自动更新)
threshold = [(42, 92, -24, 26, -33, 17)]

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
    st = img.get_statistics(roi=S_ROI)
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

def read_touch(tp):
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

def is_rect_like(b):
    """判断 blob 是否像矩形: 外接框填充率接近 1.0"""
    w, h = b.w(), b.h()
    if w <= 0 or h <= 0: return False
    pixels = b.pixels() if hasattr(b, 'pixels') and callable(b.pixels) else b.area()
    fill = float(pixels) / float(w * h)
    return 0.65 <= fill <= 1.10   # 矩形填充率接近1.0

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
    ex = cx - VIEW_W // 2
    ey = cy - VIEW_H // 2
    pan  = clamp(int(PAN_DEFAULT + ex * PAN_GAIN),
                 PAN_DEFAULT - PAN_CLAMP, PAN_DEFAULT + PAN_CLAMP)
    tilt = clamp(int(TILT_DEFAULT + ey * TILT_GAIN),
                 TILT_DEFAULT - TILT_CLAMP, TILT_DEFAULT + TILT_CLAMP)
    return pan, tilt

def draw_menu(img, cal_active, found, pan, tilt, fps):
    try:
        img.draw_rectangle(MENU_X, 0, PW - MENU_X, PH, color=(0,0,0), fill=True)
    except Exception:
        for x in range(MENU_X, PW):
            img.draw_line(x, 0, x, PH - 1, color=(0,0,0))

    # CAL 按钮
    x, y, w, h = CAL_BTN
    c = (0, 255, 0) if cal_active else (0, 120, 255)
    img.draw_rectangle(x, y, w, h, color=c, thickness=2)
    draw_text(img, x + 28, y + 17, "CAL", color=c, size=18)

    # 状态
    draw_text(img, MENU_X + 8, 24, "RECT TRACK", color=(0,255,0), size=16)
    status = "FOUND" if found else "LOST"
    draw_text(img, MENU_X + 8, 54, status,
              color=(0, 255, 0) if found else (255, 80, 80), size=14)
    draw_text(img, MENU_X + 8, 420, "P:%d T:%d" % (pan // 10, tilt // 10),
              color=(0, 255, 0), size=12)
    draw_text(img, MENU_X + 8, 444, "FPS:%d" % max(1, fps),
              color=(0, 255, 0), size=10)

# ============================================================
sensor = None
touch = None
display_inited = False
media_inited = False
sensor_running = False
uart = None

try:
    # --- FPIOA: UART2 ---
    fpioa = FPIOA()
    fpioa.set_function(5, FPIOA.UART2_TXD)
    fpioa.set_function(6, FPIOA.UART2_RXD)
    uart = UART(UART.UART2, baudrate=UART_BAUD,
                bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
                stop=UART.STOPBITS_ONE)

    # --- Sensor ---
    sensor = Sensor(id=2)
    sensor.reset()
    sensor.set_framesize(width=PW, height=PH)
    sensor.set_pixformat(Sensor.RGB565)
    sensor.set_hmirror(False)
    sensor.set_vflip(False)

    # --- Display ---
    Display.init(Display.ST7701, width=PW, height=PH)
    display_inited = True
    MediaManager.init()
    media_inited = True
    sensor.run()
    sensor_running = True

    # --- Touch ---
    if TOUCH:
        try:
            touch = TOUCH(0)
            print("Touch OK")
        except Exception as e:
            touch = None
            print("Touch: %s" % str(e))
    else:
        print("No TOUCH module")

    # ★ 10帧预热
    for _ in range(10):
        tmp = sensor.snapshot()
        del tmp
        time.sleep_ms(50)
    gc.collect()

    # ============================================================
    clock = time.clock()
    fc = 0
    last_send_ms = 0
    last_blobs = []
    pan_target = PAN_DEFAULT
    tilt_target = TILT_DEFAULT
    cal_active = False
    last_pressed = False

    print("=== K230 Rect Tracker ===")
    print("Touch CAL to calibrate, then tracking starts")
    print("Servo: Pan=PB9/TIMA0_CH1  Tilt=PB8/TIMA0_CH0")

    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot()

        # --- 触摸 CAL ---
        pressed = False
        xy = read_touch(touch)
        if xy:
            tx, ty = xy[0], xy[1]
            if point_in_rect(tx, ty, CAL_BTN):
                pressed = True
                if not last_pressed:
                    t = make_threshold_from_roi(img)
                    threshold = [t]
                    cal_active = True
                    print("CAL: %s" % str(t))
        last_pressed = pressed

        # --- 绘制校准框+十字 ---
        x, y, w, h = S_ROI
        img.draw_rectangle(x, y, w, h, color=(0, 120, 255), thickness=2)
        img.draw_cross(VIEW_W // 2, VIEW_H // 2,
                       color=(0, 120, 255), size=8)

        # --- 矩形检测 ---
        found = False
        if cal_active and fc % DETECT_EVERY == 0:
            last_blobs = img.find_blobs(threshold,
                                        roi=(0, 0, VIEW_W, VIEW_H),
                                        x_stride=X_STRIDE, y_stride=Y_STRIDE,
                                        pixels_threshold=MIN_PIXELS,
                                        area_threshold=MIN_AREA,
                                        merge=False, margin=0)
        if last_blobs:
            # 筛选矩形: 填充率 0.65~1.10
            rects = [b for b in last_blobs if is_rect_like(b)]
            if rects:
                found = True
                b = max(rects, key=lambda x: x.pixels())
                pan_target, tilt_target = pixel_to_servo(b.cx(), b.cy())
                # 绿色框+十字
                img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                   color=(0, 255, 0), thickness=2)
                img.draw_cross(b.cx(), b.cy(), color=(0, 255, 0), size=12)
            else:
                # 有 blob 但不是矩形: 缓慢回中
                pan_target  += (PAN_DEFAULT - pan_target) // 8
                tilt_target += (TILT_DEFAULT - tilt_target) // 8
        else:
            pan_target  += (PAN_DEFAULT - pan_target) // 8
            tilt_target += (TILT_DEFAULT - tilt_target) // 8

        # --- UART 发送 ---
        now = time.ticks_ms()
        if time.ticks_diff(now, last_send_ms) >= SEND_EVERY_MS:
            last_send_ms = now
            send_frame(pan_target, tilt_target, cmd=0x01 if found else 0x04)

        # --- 右侧菜单 ---
        draw_menu(img, cal_active, found, pan_target, tilt_target, clock.fps())

        # --- 状态文字 ---
        draw_text(img, 4, PH - 18,
                  "Put RECT in blue box -> CAL",
                  color=(0, 255, 0), size=14)

        Display.show_image(img, x=0, y=0)

        del img
        if fc % GC_EVERY == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\nInterrupted")
except BaseException as e:
    print("Error: %s" % str(e))
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
