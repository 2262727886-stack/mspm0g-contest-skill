"""
K230 矩形/三角形/圆形识别 + 触摸菜单 + 一键LAB校准
=================================================
适用: 庐山派 + GC2093 + ST7701 3.1寸触摸屏
原理: find_blobs → 外接框填充率 + 圆度 分类形状
  - 矩形: 填充率 > 0.82, 圆度低
  - 三角形: 填充率 0.30~0.68
  - 圆形: 圆度 > 0.65
一键校准: 触摸 CAL 按钮 → 采样屏幕中心区域 → 自动计算 LAB 阈值
"""

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
import image, time, os, gc

# ===== 屏幕布局 =====
PW, PH = 800, 480
VIEW_W = 680
MENU_X = VIEW_W
MENU_W = PW - MENU_X

# ===== 检测参数 =====
DETECT_EVERY = 2
GC_EVERY_FRAMES = 300
MAX_TARGETS = 10

# ===== 默认 LAB 阈值 (红色物体, 现场必须 CAL 校准) =====
DEFAULT_THRESHOLD = [(30, 100, 15, 127, 15, 127)]

# ===== 形状分类参数 =====
FILL_RECT_MIN  = 0.82   # 矩形最小填充率
FILL_TRI_MIN   = 0.30   # 三角形最小填充率
FILL_TRI_MAX   = 0.68   # 三角形最大填充率
ROUND_CIRC_MIN = 0.65   # 圆形最小圆度
FILL_CIRC_MIN  = 0.65   # 圆形辅助最小填充率
FILL_CIRC_MAX  = 0.90   # 圆形辅助最大填充率

# ===== 菜单按钮布局 =====
BTN_W = MENU_W - 20
BTN_H = 48
BTN_X = MENU_X + 10

BTN = {
    "CAL":  (BTN_X, 50),
    "ALL":  (BTN_X, 114),
    "RECT": (BTN_X, 178),
    "TRI":  (BTN_X, 242),
    "CIRC": (BTN_X, 306),
}

# ===== 全局状态 =====
threshold = list(DEFAULT_THRESHOLD)
shape_mode = "ALL"          # "ALL", "RECT", "TRI", "CIRC"
cal_status = ""
cal_timer = 0

# ===== 形状分类 =====
def classify_shape(b):
    """根据 blob 外接框填充率 + 圆度 分类"""
    area = b.pixels()
    bbox_area = b.w() * b.h()
    if bbox_area <= 0:
        return "UNKN"
    fill = area / bbox_area
    rnd = b.roundness()

    if FILL_TRI_MIN <= fill <= FILL_TRI_MAX and rnd < 0.65:
        return "TRI"
    if rnd >= ROUND_CIRC_MIN or (FILL_CIRC_MIN <= fill <= FILL_CIRC_MAX and rnd > 0.45):
        return "CIRC"
    if fill >= FILL_RECT_MIN and rnd < 0.55:
        return "RECT"
    # 兜底
    if fill >= FILL_RECT_MIN:
        return "RECT"
    if fill <= FILL_TRI_MAX and fill >= FILL_TRI_MIN:
        return "TRI"
    if rnd >= ROUND_CIRC_MIN:
        return "CIRC"
    return "UNKN"


def shape_color(shape):
    """形状 → BGR565 绘制颜色"""
    if shape == "RECT": return (0, 255, 0)
    if shape == "TRI":  return (255, 255, 0)
    if shape == "CIRC": return (0, 255, 255)
    return (255, 0, 0)


# ===== 一键 LAB 校准 (稳定版: RGB 统计 + 颜色推断) =====
# ⚠️ K230 CanMV 固件上 to_lab() / get_pixel() 可能不可用。
# 已实测验证: img.copy(roi=...).get_statistics() → RGB均值 → 推 LAB 阈值 稳定可用。

# 颜色预设表: (主导色判定条件, LAB阈值)
# L 通道由 ROI 平均亮度动态计算; A/B 从预设表查询
COLOR_PRESETS = {
    "red":    {"a_lo":  15, "a_hi": 127, "b_lo":  10, "b_hi": 127,
               "test": lambda rm,gm,bm: rm>gm+25 and rm>bm+25},
    "green":  {"a_lo":-128, "a_hi":  -8, "b_lo":-128, "b_hi": 127,
               "test": lambda rm,gm,bm: gm>rm+25 and gm>bm+25},
    "blue":   {"a_lo":-128, "a_hi": 127, "b_lo":-128, "b_hi": -20,
               "test": lambda rm,gm,bm: bm>rm+25 and bm>gm+25},
    "yellow": {"a_lo":-128, "a_hi": 127, "b_lo":  15, "b_hi": 127,
               "test": lambda rm,gm,bm: rm>140 and gm>110 and bm<90},
    "orange": {"a_lo":  15, "a_hi": 127, "b_lo":  15, "b_hi": 127,
               "test": lambda rm,gm,bm: rm>160 and gm>60 and gm<140 and bm<80},
    "purple": {"a_lo":  15, "a_hi": 127, "b_lo":-128, "b_hi": -20,
               "test": lambda rm,gm,bm: rm>100 and bm>100 and gm<80},
    "white":  {"a_lo":-128, "a_hi": 127, "b_lo":-128, "b_hi": 127,
               "test": lambda rm,gm,bm: rm>180 and gm>180 and bm>180},
    "black":  {"a_lo":-128, "a_hi": 127, "b_lo":-128, "b_hi": 127,
               "test": lambda rm,gm,bm: rm<60 and gm<60 and bm<60},
}


def auto_calibrate(img):
    """稳定校准: ROI→get_statistics→RGB均值→颜色预设→LAB阈值"""
    global threshold, cal_status, cal_timer

    cx, cy = VIEW_W // 2, PH // 2
    rw, rh = 60, 45
    rx = max(0, cx - rw // 2)
    ry = max(0, cy - rh // 2)
    rw = min(rw, VIEW_W - rx)
    rh = min(rh, PH - ry)

    try:
        roi = img.copy(roi=(rx, ry, rw, rh))
        if roi is None:
            cal_status = "CAL FAIL"; cal_timer = 60; return
    except Exception as e:
        cal_status = "CAL FAIL"; cal_timer = 60
        print("CAL copy err: %s" % str(e))
        return

    try:
        s = roi.get_statistics()
        del roi
        # RGB565 statistics → 8-bit范围 0~255
        # 索引: 0=r_mean, 1=r_median, 2=r_mode, 3=r_stdev, 4=r_min, 5=r_max
        #       6=g_mean, 7=g_median, 8=g_mode, 9=g_stdev, 10=g_min, 11=g_max
        #      12=b_mean,13=b_median,14=b_mode,15=b_stdev,16=b_min,17=b_max
        rm, gm, bm = s[0], s[6], s[12]
        rmx, gmx, bmx = s[5], s[11], s[17]  # max 用于 L 上限
        rmn, gmn, bmn = s[4], s[10], s[16]  # min 用于 L 下限

        # L 范围: 从 RGB min/max 平均值换算
        bright_lo = (rmn + gmn + bmn) / 3.0
        bright_hi = (rmx + gmx + bmx) / 3.0
        L_lo = max(0,   int(bright_lo * 0.65))
        L_hi = min(100, int(bright_hi * 1.35))
        if L_hi - L_lo < 15: L_lo, L_hi = max(0,L_lo-8), min(100,L_hi+8)

        # 选颜色预设 (按顺序匹配，第一个命中)
        name = "general"
        A_lo, A_hi = -128, 127
        B_lo, B_hi = -128, 127
        bright = (rm + gm + bm) / 3.0

        for cname, info in COLOR_PRESETS.items():
            try:
                if info["test"](rm, gm, bm):
                    A_lo, A_hi = info["a_lo"], info["a_hi"]
                    B_lo, B_hi = info["b_lo"], info["b_hi"]
                    name = cname
                    break
            except Exception:
                continue

        threshold = [(L_lo, L_hi, A_lo, A_hi, B_lo, B_hi)]
        cal_status = "CAL OK"
        cal_timer = 90
        print("CAL[%s]: L(%d,%d) A(%d,%d) B(%d,%d) rgb=(%d,%d,%d)" %
              (name, L_lo, L_hi, A_lo, A_hi, B_lo, B_hi, rm, gm, bm))

    except Exception as e:
        cal_status = "CAL FAIL"; cal_timer = 60
        print("CAL err: %s" % str(e))


# ===== 菜单绘制 =====
def in_rect(px, py, x, y, w, h):
    return x <= px <= x + w and y <= py <= y + h


def draw_btn(img, x, y, w, h, text, color, fill=False):
    try:
        img.draw_rectangle(x, y, w, h, color=color, thickness=2, fill=fill)
        img.draw_string_advanced(x + 8, y + 12, 18, text, color=color)
    except Exception:
        pass


def draw_menu(img, fps):
    """右侧触摸菜单栏"""
    try:
        img.draw_rectangle(MENU_X, 0, MENU_W, PH, color=(0, 0, 0), fill=True)
    except Exception:
        for x in range(MENU_X, PW):
            img.draw_line(x, 0, x, PH - 1, color=(0, 0, 0))

    img.draw_string_advanced(MENU_X + 12, 6, 20, "SHAPE", color=(0, 255, 255))

    # 各按钮
    for name, (bx, by) in BTN.items():
        if name == shape_mode or (name == "ALL" and shape_mode == "ALL"):
            c = (0, 255, 0)
        elif name == "CAL":
            c = (0, 200, 255) if cal_status == "" else (255, 255, 0)
        else:
            c = (150, 150, 150)
        draw_btn(img, bx, by, BTN_W, BTN_H, name, c)

    # 校准状态
    if cal_status:
        img.draw_string_advanced(MENU_X + 6, 370, 14, cal_status,
                                 color=(255, 255, 0))

    # FPS + 阈值简略
    img.draw_string_advanced(MENU_X + 8, PH - 30, 14,
                             "FPS:%d" % max(1, fps), color=(0, 255, 0))
    if threshold:
        t = threshold[0]
        img.draw_string_advanced(MENU_X + 4, PH - 56, 11,
                                 "L%d-%d A%d-%d" % (t[0], t[1], t[2], t[3]),
                                 color=(120, 120, 120))


# ============================================================
# 主程序初始化
# ============================================================
sensor = None
tp = None
display_ok = False
media_ok = False
sensor_ok = False

try:
    sensor = Sensor(id=2)
    sensor.reset()
    sensor.set_framesize(width=PW, height=PH)
    sensor.set_pixformat(Sensor.RGB565)
    sensor.set_hmirror(False)
    sensor.set_vflip(False)

    Display.init(Display.ST7701, width=PW, height=PH)
    display_ok = True
    MediaManager.init()
    media_ok = True
    sensor.run()
    sensor_ok = True

    try:
        tp = TOUCH(0)
        print("Touch OK")
    except Exception as e:
        print("No touch: %s" % str(e))

    print("Shape Detect Ready")
    print("Default threshold: %s" % str(threshold[0]))

    clock = time.clock()
    fc = 0
    last_blobs = []
    last_touch_fc = -100

    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot()

        # --- 触摸菜单 ---
        if tp and (fc - last_touch_fc) > 25:
            for p in tp.read():
                if p.event not in (2, 3):  # 仅 DOWN / MOVE
                    continue
                px, py = p.x, p.y

                if in_rect(px, py, BTN_X, BTN["CAL"][1], BTN_W, BTN_H):
                    auto_calibrate(img)
                    last_touch_fc = fc
                elif in_rect(px, py, BTN_X, BTN["ALL"][1], BTN_W, BTN_H):
                    shape_mode = "ALL"; last_touch_fc = fc
                elif in_rect(px, py, BTN_X, BTN["RECT"][1], BTN_W, BTN_H):
                    shape_mode = "RECT"; last_touch_fc = fc
                elif in_rect(px, py, BTN_X, BTN["TRI"][1], BTN_W, BTN_H):
                    shape_mode = "TRI"; last_touch_fc = fc
                elif in_rect(px, py, BTN_X, BTN["CIRC"][1], BTN_W, BTN_H):
                    shape_mode = "CIRC"; last_touch_fc = fc

        # --- 形状识别 (隔帧) ---
        if fc % DETECT_EVERY == 0 and threshold:
            try:
                last_blobs = img.find_blobs(
                    threshold,
                    roi=(0, 0, VIEW_W, PH),
                    x_stride=5, y_stride=5,
                    pixels_threshold=80,
                    area_threshold=120,
                    merge=False, margin=0
                )
            except Exception:
                last_blobs = []

        # --- 绘制结果 ---
        if last_blobs:
            sorted_blobs = sorted(last_blobs,
                                  key=lambda x: x.pixels(), reverse=True)
            for b in sorted_blobs[:MAX_TARGETS]:
                shape = classify_shape(b)

                # 按模式过滤
                if shape_mode == "RECT" and shape != "RECT":
                    continue
                if shape_mode == "TRI" and shape != "TRI":
                    continue
                if shape_mode == "CIRC" and shape != "CIRC":
                    continue

                c = shape_color(shape)
                fill = b.pixels() / max(1, b.w() * b.h())
                label = "%s %.2f" % (shape, fill)

                img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                   color=c, thickness=2)
                img.draw_cross(b.cx(), b.cy(), color=c, size=8, thickness=1)
                img.draw_string_advanced(b.x(), max(0, b.y() - 20), 14,
                                         label, color=c)

        # --- 菜单 + 显示 ---
        draw_menu(img, clock.fps())

        if cal_timer > 0:
            cal_timer -= 1
            if cal_timer == 0:
                cal_status = ""

        Display.show_image(img)
        del img

        if fc % GC_EVERY_FRAMES == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\nInterrupted")
except BaseException as e:
    print("Error: %s" % str(e))
    import sys
    sys.print_exception(e)
finally:
    if sensor_ok and sensor:
        sensor.stop()
    if display_ok:
        Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    if media_ok:
        MediaManager.deinit()
    print("Cleaned up")
