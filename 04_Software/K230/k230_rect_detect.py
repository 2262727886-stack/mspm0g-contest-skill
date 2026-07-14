"""
K230 矩形检测 + 触摸屏阈值调节 + 单舵机控制 (高性能版)
=====================================================
硬件: K230 + GC2093 + ST7701(800x480) + TOUCH
舵机: GPIO37=3.3V  GPIO42=PWM0

帧率优化: QVGA 320x240 采集, 直接在摄像头帧上绘制, 不创建额外画布
"""

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH, I2C, FPIOA, Pin, PWM
import image, time, os, gc

# ============================================================
# 一、背光
# ============================================================
GP7101_ADDR = 0x58
try:
    i2c3 = I2C(3, freq=400000)
    i2c3.writeto(GP7101_ADDR, bytes([0x00, 0x00, 23]))
except:
    i2c3 = None

def backlight(pct):
    if i2c3 is None: return
    duty = int(max(0, min(100, pct)) * 4095 / 100)
    try:
        i2c3.writeto(GP7101_ADDR, bytes([0x02, (duty>>8)&0xFF, duty&0xFF]))
    except: pass

backlight(80)

# ============================================================
# 二、舵机 — 硬件 PWM0 @ GPIO42
# ============================================================
fpioa = FPIOA()
fpioa.set_function(37, FPIOA.GPIO37)
vcc = Pin(37, Pin.OUT)
vcc.value(1)

fpioa.set_function(42, FPIOA.PWM0)
pwm = PWM(0, 50)               # ch0, 50Hz
pwm.duty(1.5 / 20 * 100)       # 1.5ms = 90°
pwm.enable(1)

SERVO_ANGLE = 90
AUTO_AIM = False


def servo_set(angle):
    """0~180° → duty% → 脉宽 0.5~2.5ms @ 50Hz"""
    global SERVO_ANGLE
    SERVO_ANGLE = max(0, min(180, angle))
    pwm.duty(round((0.5 + SERVO_ANGLE * 2.0 / 180) / 20 * 100, 1))


# ============================================================
# 三、摄像头 + 显示屏
# ============================================================
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=320, height=240)    # QVGA 高帧率
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.ST7701, to_ide=True, width=800, height=480)
MediaManager.init()
sensor.run()

tp = TOUCH(0)

clock = time.clock()
fc = 0

# ============================================================
# 四、可调参数
# ============================================================
GRAY_LO, GRAY_HI = 0, 109
RECT_THRESHOLD = 10000
L_LO, L_HI = 30, 100
A_LO, A_HI = 20, 127
B_LO, B_HI = 20, 127

MODE = 'gray'          # 'gray' | 'lab' | 'servo'
PAGE = 'main'          # 'main' 检测画面 | 'adj' 调参面板
selected = None
touch_held = False
touch_cnt = 0          # 长按计数器


def show_img(img):
    """参考14_脱机调整阈值.py的标准显示流程"""
    if img.height() > 480 or img.width() > 800:
        scale = max(img.height() // 480, img.width() // 800) + 1
        img.midpoint_pool(scale, scale)
    img.compress_for_ide()
    Display.show_image(img, x=(800-img.width())//2, y=(480-img.height())//2)


# ============================================================
# 五、参数表
# ============================================================
_THRESH_PARAMS = [
    ("GRAY_LO",  "gray_lo",    0,      255,    5),
    ("GRAY_HI",  "gray_hi",    0,      255,    5),
    ("RECT_THR", "rect_thr",   1000,   50000,  500),
    ("L_LO",     "L_lo",       0,      100,    2),
    ("L_HI",     "L_hi",       0,      100,    2),
    ("A_LO",     "A_lo",     -128,    127,    2),
    ("A_HI",     "A_hi",     -128,    127,    2),
    ("B_LO",     "B_lo",     -128,    127,    2),
    ("B_HI",     "B_hi",     -128,    127,    2),
]

_SERVO_PARAMS = [
    ("SERVO",    "servo",      0,       180,    2),
    ("AUTO_AIM", "auto_aim",   0,       1,      1),
]


def get_param(sname):
    global GRAY_LO, GRAY_HI, RECT_THRESHOLD, L_LO, L_HI, A_LO, A_HI, B_LO, B_HI
    global SERVO_ANGLE, AUTO_AIM
    lut = {
        "gray_lo": GRAY_LO, "gray_hi": GRAY_HI, "rect_thr": RECT_THRESHOLD,
        "L_lo": L_LO, "L_hi": L_HI, "A_lo": A_LO, "A_hi": A_HI,
        "B_lo": B_LO, "B_hi": B_HI,
        "servo": SERVO_ANGLE, "auto_aim": 1 if AUTO_AIM else 0,
    }
    return lut.get(sname, 0)


def set_param(sname, val):
    global GRAY_LO, GRAY_HI, RECT_THRESHOLD, L_LO, L_HI, A_LO, A_HI, B_LO, B_HI
    global SERVO_ANGLE, AUTO_AIM
    if sname == "gray_lo":      GRAY_LO = val
    elif sname == "gray_hi":    GRAY_HI = val
    elif sname == "rect_thr":   RECT_THRESHOLD = val
    elif sname == "L_lo":       L_LO = val
    elif sname == "L_hi":       L_HI = val
    elif sname == "A_lo":       A_LO = val
    elif sname == "A_hi":       A_HI = val
    elif sname == "B_lo":       B_LO = val
    elif sname == "B_hi":       B_HI = val
    elif sname == "servo":      servo_set(val)
    elif sname == "auto_aim":   AUTO_AIM = (val != 0)


def reset_defaults():
    global GRAY_LO, GRAY_HI, RECT_THRESHOLD, L_LO, L_HI
    global A_LO, A_HI, B_LO, B_HI, MODE, AUTO_AIM
    GRAY_LO, GRAY_HI = 0, 109
    RECT_THRESHOLD = 10000
    L_LO, L_HI = 30, 100
    A_LO, A_HI = 20, 127
    B_LO, B_HI = 20, 127
    MODE = "gray"
    AUTO_AIM = False
    servo_set(90)


# ============================================================
# 六、矩形检测
# ============================================================
def filter_rects(rects, img_w, img_h):
    good = []
    for r in rects:
        w, h = r.w(), r.h()
        if w <= 0 or h <= 0: continue
        ratio = max(w, h) / float(min(w, h))
        area = w * h
        if 1.10 < ratio < 1.90 and img_w*img_h*0.03 < area < img_w*img_h*0.90:
            good.append(r)
    return good


def detect_rects_gray(img):
    gray = img.to_grayscale(copy=True)
    bin_img = gray.binary([(GRAY_LO, GRAY_HI)])
    bin_img.open(1)
    rects = bin_img.find_rects(threshold=RECT_THRESHOLD)
    return filter_rects(rects, img.width(), img.height()) if rects else []


def detect_rects_lab(img):
    blobs = img.find_blobs([(L_LO, L_HI, A_LO, A_HI, B_LO, B_HI)],
                           pixels_threshold=80, area_threshold=150, merge=True)
    rects = []
    for b in blobs:
        r = b.rect()
        w, h = r.w(), r.h()
        if w <= 0 or h <= 0: continue
        if max(w, h) / float(min(w, h)) > 3.5: continue
        fill = b.area() / float(w * h) if w*h > 0 else 0.0
        if fill > 0.25: rects.append(r)
    return rects


# ============================================================
# 七、自动瞄准
# ============================================================
def auto_aim_update(rects, img_w, img_h):
    if not rects or not AUTO_AIM or MODE != "servo": return
    best = max(rects, key=lambda r: r.w() * r.h())
    cx = best.x() + best.w() // 2
    dx = cx - img_w // 2
    if abs(dx) < 10: return
    corr = max(-3, min(3, -dx * 0.15))
    servo_set(SERVO_ANGLE + corr)


# ============================================================
# 八、UI 绘制
# ============================================================

# 调整面板布局常量
DW, DH = 800, 480
PANEL_X = 570
PANEL_W = DW - PANEL_X
BTN_X = PANEL_X + 8
BTN_W = PANEL_W - 16
BTN_H = 26
BTN_GAP = 2
BTN_TOP = 50


def draw_adjust_panel(img):
    """全屏调参面板 — 仅在PAGE='adj'时调用"""
    # 背景
    img.draw_rectangle(0, 0, DW, DH, color=(40, 42, 50), fill=True)

    # 左侧预览区 (摄像头画面缩略)
    # (由调用者先画好cam_img到左侧)

    # 右侧控制面板
    img.draw_rectangle(PANEL_X, 0, PANEL_W, DH, color=(28, 30, 38), fill=True)
    img.draw_string_advanced(PANEL_X+8, 6, 20, "ADJUST", color=(255, 255, 255))

    if MODE == "gray":     mc, mt = (0, 255, 0), "GRAY"
    elif MODE == "lab":    mc, mt = (255, 180, 0), "LAB"
    else:                  mc, mt = (0, 180, 255), "SERVO"
    img.draw_string_advanced(PANEL_X+8, 30, 14, "MODE:%s" % mt, color=mc)

    param_list = _THRESH_PARAMS if MODE in ("gray", "lab") else _SERVO_PARAMS

    y = BTN_TOP
    for label, sname, vmin, vmax, step in param_list:
        val = get_param(sname)
        bg = (60, 95, 60) if selected == sname else (44, 46, 50)
        img.draw_rectangle(BTN_X, y, BTN_W, BTN_H, color=bg, fill=True)
        img.draw_string_advanced(BTN_X+4, y+5, 12, label, color=(200, 200, 200))
        vc = (0, 255, 0) if selected == sname else (255, 255, 255)
        if sname == "auto_aim":
            vs = "ON" if val else "OFF"
        else:
            vs = "%d" % val
        img.draw_string_advanced(BTN_X+95, y+5, 13, vs, color=vc)
        img.draw_string_advanced(BTN_X+155, y+5, 10, "[%d,%d]" % (vmin, vmax),
                                 color=(110, 110, 110))
        y += BTN_H + BTN_GAP

    y += 6
    img.draw_rectangle(BTN_X, y, BTN_W, BTN_H+4, color=(0, 70, 135), fill=True)
    img.draw_string_advanced(BTN_X+10, y+4, 14, "[ MODE: %s ]" % mt, color=(255, 255, 255))
    y += BTN_H + BTN_GAP + 12
    img.draw_rectangle(BTN_X, y, BTN_W, BTN_H+4, color=(145, 25, 25), fill=True)
    img.draw_string_advanced(BTN_X+53, y+4, 16, "[ RESET ]", color=(255, 255, 255))
    y += BTN_H + BTN_GAP + 16

    # 舵机进度条
    bar_w = BTN_W - 50
    img.draw_string_advanced(BTN_X, y-2, 11, "Servo", color=(180, 180, 180))
    img.draw_rectangle(BTN_X+32, y+1, bar_w, 10, color=(60, 60, 60), fill=True)
    fill_w = int(bar_w * SERVO_ANGLE / 180)
    if fill_w > 0:
        img.draw_rectangle(BTN_X+32, y+1, fill_w, 10, color=(0, 200, 255), fill=True)
    img.draw_string_advanced(BTN_X+36+bar_w, y-2, 11, "%3d" % SERVO_ANGLE, color=(255, 255, 255))


def draw_osd(img, rects_count, fps):
    """主画面 OSD 叠加 — 轻量, 直接画在摄像头帧上"""
    auto_str = " [AUTO]" if AUTO_AIM and MODE == "servo" else ""
    info = "FPS:%02d %s %dr%s" % (fps, MODE[:3].upper(), rects_count, auto_str)
    img.draw_string_advanced(2, 2, 14, info, color=(0, 255, 0))
    # 舵机角度显示
    img.draw_string_advanced(2, img.height()-20, 14, "S:%d" % SERVO_ANGLE, color=(255, 200, 0))


# ============================================================
# 九、触摸处理
# ============================================================
def handle_adj_touch(x, y):
    """调参面板触摸"""
    global selected, MODE
    if x < PANEL_X:
        selected = None
        return

    param_list = _THRESH_PARAMS if MODE in ("gray", "lab") else _SERVO_PARAMS
    row_y = BTN_TOP
    for label, sname, vmin, vmax, step in param_list:
        if BTN_X <= x <= BTN_X+BTN_W and row_y <= y <= row_y+BTN_H:
            selected = sname
            val = get_param(sname)
            if x < BTN_X + BTN_W // 2:
                val = max(vmin, val - step)
            else:
                val = min(vmax, val + step)
            set_param(sname, val)
            return
        row_y += BTN_H + BTN_GAP

    row_y += 6
    if BTN_X <= x <= BTN_X+BTN_W and row_y <= y <= row_y+BTN_H+4:
        MODE = {"gray": "lab", "lab": "servo", "servo": "gray"}[MODE]
        selected = None
        return

    row_y += BTN_H + BTN_GAP + 12
    if BTN_X <= x <= BTN_X+BTN_W and row_y <= y <= row_y+BTN_H+4:
        reset_defaults()
        selected = None


# ============================================================
# 十、主循环
# ============================================================
print("=" * 50)
print("K230 矩形检测 + 舵机")
print("  GPIO37=3.3V  GPIO42=PWM0")
print("  长按屏幕 → 打开调参面板")
print("  短按屏幕 → 关闭调参面板")
print("=" * 50)

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        # 捕获帧
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 矩形检测
        if MODE == "gray":
            rects = detect_rects_gray(img)
        elif MODE == "lab":
            rects = detect_rects_lab(img)
        else:
            rects = detect_rects_gray(img)

        # 自动瞄准 (每 6 帧)
        if fc % 6 == 0:
            auto_aim_update(rects, img.width(), img.height())

        # 绘制检测结果 (直接画在摄像头帧上)
        for i, r in enumerate(rects):
            color = (0, 255, 0) if i == 0 else (0, 200, 200)
            thick = 3 if i == 0 else 1
            img.draw_rectangle(r.x(), r.y(), r.w(), r.h(), color=color, thickness=thick)
            cx, cy = r.x()+r.w()//2, r.y()+r.h()//2
            img.draw_cross(cx, cy, color=color, size=8, thickness=1)
            img.draw_string_advanced(r.x(), r.y()-10, 12, "%dx%d" % (r.w(), r.h()), color=color)
            if AUTO_AIM and MODE == "servo" and i == 0:
                img.draw_line(img.width()//2, img.height()//2, cx, cy,
                              color=(255, 255, 0), thickness=1)

        img.draw_cross(img.width()//2, img.height()//2, color=(128, 128, 128), size=5, thickness=1)

        # 触摸处理
        try:
            pts = tp.read()
            if len(pts) > 0:
                touch_cnt += 1
                if not touch_held:
                    touch_held = True
                    if PAGE == 'adj':
                        handle_adj_touch(pts[0].x, pts[0].y)
                # 长按 > 15 帧进入调参面板
                if touch_cnt > 15 and PAGE == 'main':
                    PAGE = 'adj'
                    touch_cnt = 0
            else:
                # 短按松开: main→adj 切换
                if touch_held and touch_cnt <= 15:
                    PAGE = 'adj' if PAGE == 'main' else 'main'
                touch_held = False
                touch_cnt = max(0, touch_cnt - 2)
        except:
            touch_held = False
            touch_cnt = 0

        # 显示
        if PAGE == 'main':
            # 主画面: 摄像头帧 + OSD 直接显示
            draw_osd(img, len(rects), clock.fps())
            show_img(img)
        else:
            # 调参面板: 全屏 800×480 画布 (只在调参时创建, 帧率低但可接受)
            canvas = image.Image(DW, DH, image.RGB565)
            # 左侧放缩小的摄像头预览
            cam_copy = img.copy()
            canvas.draw_image(cam_copy, (PANEL_X-cam_copy.width())//2,
                              (DH-cam_copy.height())//2)
            draw_adjust_panel(canvas)
            show_img(canvas)

        if fc % 200 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("用户中断")
except BaseException as e:
    print("异常: %s" % str(e))
finally:
    if 'sensor' in dir() and sensor is not None:
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完成")
