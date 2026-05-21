"""
K230 shape detector
===================
Detect rectangle, triangle and circle with one-tap LAB calibration.

Usage:
1. Put the target color inside the blue center box.
2. Tap the CAL button on the touch screen.
3. The program updates the LAB threshold and detects shapes of that color.

This version keeps the camera frame small to avoid fast frame buffer errors.
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

try:
    from machine import TOUCH
except Exception:
    TOUCH = None


# Camera frame equals ST7701 LCD, so Display.show_image() can be full-screen
# without software scaling or a second large image allocation.
PW, PH = 800, 480
DW, DH = 800, 480

# Left side is camera/detection view, right side is the black menu bar.
VIEW_W, VIEW_H = 680, 480
MENU_X = VIEW_W
MENU_W = DW - MENU_X
MENU_IMG_X = VIEW_W
MENU_IMG_W = PW - VIEW_W

# Initial LAB threshold. Tap CAL to replace it with current center sample.
active_threshold = (42, 92, -24, 26, -33, 17)

# Center sampling box for calibration, inside the left camera view.
SAMPLE_SIZE = 48
SAMPLE_ROI = ((VIEW_W - SAMPLE_SIZE) // 2, (VIEW_H - SAMPLE_SIZE) // 2,
              SAMPLE_SIZE, SAMPLE_SIZE)

# LAB margins around sampled mean.
L_MARGIN = 18
A_MARGIN = 16
B_MARGIN = 16

# UI buttons in screen coordinates. They live in the right black menu bar.
MENU_BUTTONS = [
    ("ALL", MENU_X + 8, 24, 104, 48),
    ("RECT", MENU_X + 8, 92, 104, 48),
    ("TRI", MENU_X + 8, 160, 104, 48),
    ("CIR", MENU_X + 8, 228, 104, 48),
]
CAL_BTN = (MENU_X + 8, 340, 104, 56)

# Blob filters.
MIN_PIXELS = 220
MIN_AREA = 500
MAX_TARGETS = 5
DETECT_EVERY = 3
DETECT_X_STRIDE = 5
DETECT_Y_STRIDE = 5
STATUS_PRINT_MS = 0
GC_EVERY_FRAMES = 300
MIN_BLOB_W = 18
MIN_BLOB_H = 18
MAX_BLOB_W = VIEW_W - 8
MAX_BLOB_H = VIEW_H - 8
MIN_FILL = 0.35
MAX_FILL = 1.10
EDGE_MARGIN = 4


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


def draw_text(img, x, y, text, color=(0, 255, 0), size=14):
    try:
        img.draw_string_advanced(x, y, size, text, color=color)
    except Exception:
        img.draw_string(x, y, text, color=color)


def make_threshold_from_roi(img):
    st = img.get_statistics(roi=SAMPLE_ROI)
    l = st.l_mean()
    a = st.a_mean()
    b = st.b_mean()
    return (clamp(l - L_MARGIN, 0, 100),
            clamp(l + L_MARGIN, 0, 100),
            clamp(a - A_MARGIN, -128, 127),
            clamp(a + A_MARGIN, -128, 127),
            clamp(b - B_MARGIN, -128, 127),
            clamp(b + B_MARGIN, -128, 127))


def blob_pixels(b):
    try:
        return b.pixels()
    except Exception:
        try:
            return b.area()
        except Exception:
            return b.w() * b.h()


def blob_roundness(b):
    try:
        return b.roundness()
    except Exception:
        return 0.0


def classify_blob(b):
    w = b.w()
    h = b.h()
    if w <= 0 or h <= 0:
        return "UNK", 0.0

    pixels = blob_pixels(b)
    bbox_area = w * h
    fill = float(pixels) / float(bbox_area)
    aspect_close = abs(w - h) <= max(w, h) * 0.25
    roundness = blob_roundness(b)

    # Filled silhouettes:
    # rectangle ~= 1.00 bbox fill, circle ~= 0.78, triangle ~= 0.50.
    # Roundness is used if the firmware exposes it, otherwise fill ratio dominates.
    if fill < 0.62:
        return "TRI", fill
    if aspect_close and (roundness >= 0.65 or fill < 0.88):
        return "CIRCLE", fill
    return "RECT", fill


def is_valid_blob(b):
    w = b.w()
    h = b.h()
    if w < MIN_BLOB_W or h < MIN_BLOB_H:
        return False
    if w > MAX_BLOB_W or h > MAX_BLOB_H:
        return False
    if b.x() < EDGE_MARGIN or b.y() < EDGE_MARGIN:
        return False
    if b.x() + w > VIEW_W - EDGE_MARGIN:
        return False
    if b.y() + h > VIEW_H - EDGE_MARGIN:
        return False

    pixels = blob_pixels(b)
    fill = float(pixels) / float(w * h)
    if fill < MIN_FILL or fill > MAX_FILL:
        return False
    return True


def draw_menu(img, mode, status):
    # Draw menu into the right strip of the same camera image.
    # It is scaled together with the preview, so only one Display.show_image() is needed.
    try:
        img.draw_rectangle(MENU_IMG_X, 0, MENU_IMG_W, PH,
                           color=(0, 0, 0), fill=True)
    except Exception:
        try:
            for x in range(MENU_IMG_X, PW):
                img.draw_line(x, 0, x, PH - 1, color=(0, 0, 0))
        except Exception:
            img.draw_rectangle(MENU_IMG_X, 0, MENU_IMG_W, PH, color=(0, 0, 0))
    draw_text(img, MENU_IMG_X + 3, 2, "MODE", color=(0, 255, 0), size=7)
    for label, sx, sy, w, h in MENU_BUTTONS:
        x = sx
        y = sy
        active = (label == mode)
        color = (0, 255, 0) if active else (120, 120, 120)
        img.draw_rectangle(x, y, w, h, color=color, thickness=2)
        draw_text(img, x + 18, y + 14, label, color=color, size=18)

    x, y, w, h = CAL_BTN
    img.draw_rectangle(x, y, w, h, color=(0, 120, 255), thickness=2)
    draw_text(img, x + 28, y + 17, "CAL", color=(0, 120, 255), size=18)

    draw_text(img, MENU_IMG_X + 8, 420, status, color=(0, 255, 0), size=10)


def draw_sample_box(img):
    x, y, w, h = SAMPLE_ROI
    img.draw_rectangle(x, y, w, h, color=(0, 120, 255), thickness=2)
    img.draw_cross(PW // 2, PH // 2, color=(0, 120, 255), size=8)


def point_in_rect(px, py, rect):
    x, y, w, h = rect
    return x <= px < x + w and y <= py < y + h


def screen_to_image(tx, ty):
    return int(tx), int(ty)


def menu_hit(tx, ty):
    for label, x, y, w, h in MENU_BUTTONS:
        if point_in_rect(tx, ty, (x, y, w, h)):
            return label
    return None


def read_touch_xy(tp):
    if tp is None:
        return None
    try:
        pts = tp.read()
    except Exception:
        return None
    if not pts:
        return None

    p = pts[0]
    try:
        return int(p.x), int(p.y)
    except Exception:
        pass
    try:
        return int(p.x()), int(p.y())
    except Exception:
        pass
    try:
        return int(p[0]), int(p[1])
    except Exception:
        return None


def show_frame(img):
    Display.show_image(img, x=0, y=0)


def checksum_text(th):
    return "%d,%d,%d,%d,%d,%d" % (th[0], th[1], th[2], th[3], th[4], th[5])


def detect_shapes(img, mode):
    blobs = img.find_blobs([active_threshold],
                           roi=(0, 0, VIEW_W, VIEW_H),
                           x_stride=DETECT_X_STRIDE,
                           y_stride=DETECT_Y_STRIDE,
                           pixels_threshold=MIN_PIXELS,
                           area_threshold=MIN_AREA,
                           merge=False,
                           margin=0)

    results = []
    rect_count = 0
    tri_count = 0
    circle_count = 0

    if blobs:
        blobs = sorted(blobs, key=lambda b: blob_pixels(b), reverse=True)
        for b in blobs[:MAX_TARGETS]:
            if not is_valid_blob(b):
                continue
            shape, fill = classify_blob(b)
            if mode != "ALL" and shape != mode and not (mode == "CIR" and shape == "CIRCLE"):
                continue
            if shape == "RECT":
                color = (0, 255, 0)
                rect_count += 1
            elif shape == "TRI":
                color = (255, 200, 0)
                tri_count += 1
            elif shape == "CIRCLE":
                color = (255, 0, 0)
                circle_count += 1
            else:
                color = (180, 180, 180)

            results.append((shape, color, b.x(), b.y(), b.w(), b.h(), b.cx(), b.cy()))

    return results, rect_count, tri_count, circle_count


def draw_results(img, results):
    for shape, color, x, y, w, h, cx, cy in results:
        img.draw_rectangle(x, y, w, h, color=color, thickness=2)
        img.draw_cross(cx, cy, color=color, size=10)
        draw_text(img, x, max(28, y - 14), shape, color=color, size=14)


sensor = None
touch = None
display_inited = False
media_inited = False
sensor_running = False

try:
    sensor = Sensor(id=2)
    sensor.reset()
    sensor.set_framesize(width=PW, height=PH)
    sensor.set_pixformat(Sensor.RGB565)
    sensor.set_hmirror(False)
    sensor.set_vflip(False)

    Display.init(Display.ST7701, width=DW, height=DH)
    display_inited = True
    MediaManager.init()
    media_inited = True
    sensor.run()
    sensor_running = True

    if TOUCH:
        try:
            touch = TOUCH(0)
            print("Touch OK: tap CAL to calibrate")
        except Exception as e:
            touch = None
            print("Touch init failed: %s" % str(e))
    else:
        print("Touch module unavailable; threshold uses default value")

    for _ in range(10):
        tmp = sensor.snapshot()
        del tmp
        time.sleep_ms(50)
    gc.collect()

    clock = time.clock()
    fc = 0
    last_pressed = False
    last_report_ms = 0
    mode = "ALL"
    last_results = []
    rect_count = 0
    tri_count = 0
    circle_count = 0
    force_detect = True

    print("Shape detector started")
    print("LAB threshold: (%s)" % checksum_text(active_threshold))

    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot()

        # Touch calibration.
        pressed = False
        xy = read_touch_xy(touch)
        if xy:
            tx, ty = xy[0], xy[1]
            hit = menu_hit(tx, ty)
            if hit:
                pressed = True
                if not last_pressed:
                    mode = hit
                    force_detect = True
                    print("Mode: %s" % mode)
            elif point_in_rect(tx, ty, CAL_BTN):
                pressed = True

        if pressed and not last_pressed:
            if xy:
                tx, ty = xy[0], xy[1]
                if point_in_rect(tx, ty, CAL_BTN):
                    active_threshold = make_threshold_from_roi(img)
                    force_detect = True
                    print("CAL threshold: (%s)" % checksum_text(active_threshold))
        last_pressed = pressed

        draw_sample_box(img)

        if force_detect or (fc % DETECT_EVERY == 0):
            last_results, rect_count, tri_count, circle_count = detect_shapes(img, mode)
            force_detect = False

        draw_results(img, last_results)

        status = "%s R:%d T:%d C:%d FPS:%d" % (
            mode, rect_count, tri_count, circle_count, max(1, clock.fps()))
        draw_text(img, 4, PH - 18, status, color=(0, 255, 0), size=14)
        draw_text(img, 4, 4, "Put color in box",
                  color=(0, 255, 0), size=12)
        draw_menu(img, mode, status)

        show_frame(img)

        now = time.ticks_ms()
        if STATUS_PRINT_MS and time.ticks_diff(now, last_report_ms) > STATUS_PRINT_MS:
            last_report_ms = now
            print("%s TH=(%s)" % (status, checksum_text(active_threshold)))

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
