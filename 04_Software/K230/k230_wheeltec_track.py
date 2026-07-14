"""
K230 rectangle tracking -> MSPM0G gimbal UART.

Verified link:
  K230 40-pin header pin 8 / GPIO3 / UART1_TXD -> MSPM0G PB3 / UART3_RX
  Common GND
  9600 baud, 8N1

Frame:
  FF FE pan tilt 00 00 00 BCC
  BCC = XOR of bytes 0..6
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
VIEW_W, VIEW_H = 680, 480
MENU_X = VIEW_W

UART_BAUD = 9600
SEND_EVERY_MS = 33
LINK_TEST_MS = 0

# 鑸垫満瑙掑害
PAN_DEFAULT  = 135    # 搴曠洏榛樿 135掳 (270掳鑼冨洿涓偣)
TILT_DEFAULT = 90     # 鎽囪噦榛樿 90掳 (180掳鑼冨洿涓偣)
PAN_GAIN     = 0.018
TILT_GAIN    = 0.018
PAN_CLAMP    = 25     # pan: 110..160, small range first
TILT_CLAMP   = 45     # tilt: 45..135
PAN_STEP_MAX = 2
TILT_STEP_MAX = 2
TRACK_DEAD_PX = 12
PAN_DIR = 1
TILT_DIR = 1

DETECT_EVERY = 2
X_STRIDE, Y_STRIDE = 5, 5
MIN_PIXELS = 80
MIN_AREA = 120
GC_EVERY = 300

S_SIZE = 48
S_ROI = ((VIEW_W - S_SIZE) // 2, (VIEW_H - S_SIZE) // 2, S_SIZE, S_SIZE)
L_MARGIN, A_MARGIN, B_MARGIN = 18, 16, 16

CAL_BTN = (MENU_X + 8, 340, 104, 56)
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
    try: pts = tp.read()
    except Exception: return None
    if not pts: return None
    p = pts[0]
    try: return int(p.x), int(p.y)
    except: pass
    try: return int(p.x()), int(p.y())
    except: pass
    try: return int(p[0]), int(p[1])
    except: return None

def is_rect_like(b):
    w, h = b.w(), b.h()
    if w <= 0 or h <= 0: return False
    try:
        pixels = b.pixels()
    except:
        pixels = b.area()
    fill = float(pixels) / float(w * h)
    return 0.65 <= fill <= 1.10

def send_wheeltec_frame(angle_base, angle_arm):
    """K230 -> MSPM0G: 8瀛楄妭甯?FF FE pan tilt 00 00 00 BCC"""
    pan = clamp(int(angle_base), PAN_DEFAULT - PAN_CLAMP, PAN_DEFAULT + PAN_CLAMP)
    tilt = clamp(int(angle_arm), TILT_DEFAULT - TILT_CLAMP, TILT_DEFAULT + TILT_CLAMP)

    buf = bytearray(8)
    buf[0] = 0xFF
    buf[1] = 0xFE
    buf[2] = pan & 0xFF
    buf[3] = tilt & 0xFF
    bcc = 0
    for i in range(7):
        bcc ^= buf[i]
    buf[7] = bcc
    uart.write(buf)

def pixel_to_servo(cx, cy, pan_now, tilt_now):
    ex = cx - VIEW_W // 2
    ey = cy - VIEW_H // 2
    if abs(ex) < TRACK_DEAD_PX:
        ex = 0
    if abs(ey) < TRACK_DEAD_PX:
        ey = 0

    pan_step = clamp(int(ex * PAN_GAIN * PAN_DIR), -PAN_STEP_MAX, PAN_STEP_MAX)
    tilt_step = clamp(int(ey * TILT_GAIN * TILT_DIR), -TILT_STEP_MAX, TILT_STEP_MAX)
    pan  = clamp(pan_now + pan_step,
                 PAN_DEFAULT - PAN_CLAMP, PAN_DEFAULT + PAN_CLAMP)
    tilt = clamp(tilt_now + tilt_step,
                 TILT_DEFAULT - TILT_CLAMP, TILT_DEFAULT + TILT_CLAMP)
    return pan, tilt

def draw_menu(img, cal_active, found, pan, tilt, fps):
    try:
        img.draw_rectangle(MENU_X, 0, PW - MENU_X, PH, color=(0,0,0), fill=True)
    except:
        for x in range(MENU_X, PW):
            img.draw_line(x, 0, x, PH-1, color=(0,0,0))
    x, y, w, h = CAL_BTN
    c = (0, 255, 0) if cal_active else (0, 120, 255)
    img.draw_rectangle(x, y, w, h, color=c, thickness=2)
    draw_text(img, x+28, y+17, "CAL", color=c, size=18)
    draw_text(img, MENU_X+8, 24, "WHEELTEC", color=(0,255,0), size=16)
    s = "FOUND" if found else "LOST"
    draw_text(img, MENU_X+8, 54, s,
              color=(0,255,0) if found else (255,80,80), size=14)
    draw_text(img, MENU_X+8, 420, "B:%d A:%d" % (pan, tilt),
              color=(0,255,0), size=12)
    draw_text(img, MENU_X+8, 444, "FPS:%d" % max(1, fps),
              color=(0,255,0), size=10)

# ============================================================
sensor = None; touch = None; uart = None
display_inited = False; media_inited = False; sensor_running = False

try:
    fpioa = FPIOA()
    # K230 40-pin header UART1:
    #   pin 8  / GPIO3 = UART1_TXD
    #   pin 10 / GPIO4 = UART1_RXD
    # Connect pin 8(GPIO3/TX) to MSPM0G PB3/UART3_RX, and share GND.
    fpioa.set_function(3, FPIOA.UART1_TXD)
    fpioa.set_function(4, FPIOA.UART1_RXD)
    uart = UART(UART.UART1, baudrate=UART_BAUD,
                bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
                stop=UART.STOPBITS_ONE)

    sensor = Sensor(id=2)
    sensor.reset()
    sensor.set_framesize(width=PW, height=PH)
    sensor.set_pixformat(Sensor.RGB565)
    sensor.set_hmirror(False)
    sensor.set_vflip(False)

    Display.init(Display.ST7701, width=PW, height=PH)
    display_inited = True
    MediaManager.init()
    media_inited = True
    sensor.run()
    sensor_running = True

    if TOUCH:
        try:
            touch = TOUCH(0)
            print("Touch OK")
        except Exception as e:
            touch = None
            print("Touch: %s" % str(e))

    for _ in range(10):
        tmp = sensor.snapshot(); del tmp
        time.sleep_ms(50)
    gc.collect()

    clock = time.clock(); fc = 0
    start_ms = time.ticks_ms()
    last_send_ms = 0; last_blobs = []
    pan_target = PAN_DEFAULT; tilt_target = TILT_DEFAULT
    cal_active = True; last_pressed = False

    print("=== K230 WHEELTEC Tracker ===")
    print("Touch CAL to calibrate")

    while True:
        os.exitpoint()
        clock.tick(); fc += 1
        img = sensor.snapshot()

        pressed = False
        xy = read_touch(touch)
        if xy:
            tx, ty = xy[0], xy[1]
            if point_in_rect(tx, ty, CAL_BTN):
                pressed = True
                if not last_pressed:
                    t = make_threshold_from_roi(img)
                    threshold = [t]; cal_active = True
                    print("CAL: %s" % str(t))
        last_pressed = pressed

        x, y, w, h = S_ROI
        img.draw_rectangle(x, y, w, h, color=(0, 120, 255), thickness=2)
        img.draw_cross(VIEW_W // 2, VIEW_H // 2,
                       color=(0, 120, 255), size=8)

        now = time.ticks_ms()
        link_test = time.ticks_diff(now, start_ms) < LINK_TEST_MS

        found = False
        if (not link_test) and cal_active and fc % DETECT_EVERY == 0:
            last_blobs = img.find_blobs(threshold,
                                        roi=(0,0,VIEW_W,VIEW_H),
                                        x_stride=X_STRIDE, y_stride=Y_STRIDE,
                                        pixels_threshold=MIN_PIXELS,
                                        area_threshold=MIN_AREA,
                                        merge=False, margin=0)
        if link_test:
            if (time.ticks_diff(now, start_ms) // 500) & 1:
                pan_target, tilt_target = 180, 90
            else:
                pan_target, tilt_target = 90, 90
        elif last_blobs:
            rects = [b for b in last_blobs if is_rect_like(b)]
            if rects:
                found = True
                b = max(rects, key=lambda x: x.pixels())
                pan_target, tilt_target = pixel_to_servo(b.cx(), b.cy(),
                                                         pan_target, tilt_target)
                img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                   color=(0,255,0), thickness=2)
                img.draw_cross(b.cx(), b.cy(), color=(0,255,0), size=12)
            else:
                pan_target  += (PAN_DEFAULT - pan_target) // 8
                tilt_target += (TILT_DEFAULT - tilt_target) // 8
        else:
            pan_target  += (PAN_DEFAULT - pan_target) // 8
            tilt_target += (TILT_DEFAULT - tilt_target) // 8

        if time.ticks_diff(now, last_send_ms) >= SEND_EVERY_MS:
            last_send_ms = now
            send_wheeltec_frame(pan_target, tilt_target)

        draw_menu(img, cal_active, found, pan_target, tilt_target, clock.fps())
        if link_test:
            draw_text(img, 4, PH-18, "UART TEST: pan sweep",
                      color=(255,255,0), size=14)
        else:
            draw_text(img, 4, PH-18,
                      "Put RECT in blue box -> CAL",
                      color=(0,255,0), size=14)
        Display.show_image(img, x=0, y=0)
        del img
        if fc % GC_EVERY == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\nInterrupted")
except BaseException as e:
    print("Error: %s" % str(e))
    import sys; sys.print_exception(e)
finally:
    if sensor_running and sensor: sensor.stop()
    if display_inited: Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    if media_inited: MediaManager.deinit()
    print("Cleaned up")
