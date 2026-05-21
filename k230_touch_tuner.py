"""
K230 触摸屏脱机快速调节工具 v5
================================
功能: 触摸切换形状 / 一键校准阈值 / 手动微调 / 全屏预览

v5 架构 (最简可靠):
  单通道 800x480 RGB565 → snapshot → 检测 + UI绘制 → Display.show_image 直出
  无 bind_layer, 无 OSD层, 无多通道, 800x480 与 LCD 同尺寸零缩放

硬件: 庐山派 K230 + GC2093 + MIPI ST7701 3.1寸触摸屏
"""

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
import image, time, os, gc

# ============================================================
# 一、分辨率 (等于 LCD 物理分辨率, 零缩放)
# ============================================================

SW, SH = 800, 480
CW, CH = 800, 480

# ============================================================
# 二、检测模式
# ============================================================

MODE_TRIANGLE = 0
MODE_RECT     = 1
MODE_CIRCLE   = 2

MODE_NAMES  = ["三角形", "矩形", "圆形"]
MODE_COLORS = [(255, 165, 0), (255, 60, 60), (60, 200, 255)]

detect_mode = MODE_RECT

# ============================================================
# 三、LAB 阈值 (初始值, 现场一键校准)
# ============================================================

L_MIN, L_MAX = 20, 100
A_MIN, A_MAX = 15, 127
B_MIN, B_MAX = -20, 80
_BACKUP = None

def threshold_get():
    return [(L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)]

def threshold_backup():
    global _BACKUP
    _BACKUP = (L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)

def threshold_restore():
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    if _BACKUP:
        L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX = _BACKUP

def threshold_str():
    return "L:%d~%d  A:%d~%d  B:%d~%d" % (
        L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)

def threshold_adjust(channel, delta):
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    if channel == 0:
        L_MIN = max(0, L_MIN + delta)
        L_MAX = max(L_MIN + 5, min(127, L_MAX + delta))
    elif channel == 1:
        A_MIN = max(-128, A_MIN + delta)
        A_MAX = max(A_MIN + 5, min(127, A_MAX + delta))
    else:
        B_MIN = max(-128, B_MIN + delta)
        B_MAX = max(B_MIN + 5, min(127, B_MAX + delta))

# ============================================================
# 四、自动阈值校准
# ============================================================

def auto_calibrate(img):
    """
    一键校准: 采样画面中央矩形区域 → LAB统计 → 设阈值 → find_blobs验证.
    成功返回(True, blob数量), 失败自动回退.
    """
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX

    threshold_backup()

    try:
        # 画面中央 200x120 区域采样 (800x480 的 ~25%)
        rx = CW // 2 - 100
        ry = CH // 2 - 60
        rw, rh = 200, 120
        roi = img.copy(roi=(rx, ry, rw, rh))

        # 统计 LAB 均值/标准差
        lab = roi.to_lab()
        stats = lab.get_statistics()
        l_mean, l_stdev = stats[0], stats[3]
        a_mean, a_stdev = stats[6], stats[9]
        b_mean, b_stdev = stats[12], stats[15]

        # 阈值 = mean ± 2.0*stdev, 最小扩展防抖
        l_range = max(int(2.0 * l_stdev), 20)
        a_range = max(int(2.0 * a_stdev), 30)
        b_range = max(int(2.0 * b_stdev), 30)

        L_MIN = max(0,   int(l_mean) - l_range)
        L_MAX = min(127, int(l_mean) + l_range)
        A_MIN = max(-128, int(a_mean) - a_range)
        A_MAX = min(127,  int(a_mean) + a_range)
        B_MIN = max(-128, int(b_mean) - b_range)
        B_MAX = min(127,  int(b_mean) + b_range)

        print("  采样LAB: L=%.1f±%.1f A=%.1f±%.1f B=%.1f±%.1f" % (
            l_mean, l_stdev, a_mean, a_stdev, b_mean, b_stdev))
        print("  新阈值: %s" % threshold_str())

        # 验证: 用新阈值检测
        blobs = img.find_blobs(
            [(L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)],
            pixels_threshold=50, area_threshold=500, merge=True)

        if blobs and len(blobs) > 0:
            return True, len(blobs)
        else:
            print("  验证失败, 回退旧阈值")
            threshold_restore()
            return False, 0

    except Exception as e:
        print("  校准异常: %s" % str(e))
        threshold_restore()
        return False, 0

# ============================================================
# 五、形状检测 (在 800x480 图像上)
# ============================================================

OVERLAYS = []

def detect_shapes(img):
    """返回 (count, cx, cy, extra_str); 填充 OVERLAYS"""
    global OVERLAYS
    OVERLAYS = []
    th = threshold_get()

    if detect_mode == MODE_CIRCLE:
        circles = img.find_circles(threshold=3500, r_min=12, r_max=150,
                                   r_step=3, x_margin=15, y_margin=15,
                                   roi=(0, 0, CW, CH))
        if circles:
            for c in circles[:10]:
                OVERLAYS.append(('circle', c.x(), c.y(), c.r(), 0,
                                 MODE_COLORS[MODE_CIRCLE]))
            best = max(circles, key=lambda c: c.r())
            cx, cy = best.x(), best.y()
            OVERLAYS.append(('cross', cx, cy, 30, 0, (0, 255, 0)))
            OVERLAYS.append(('ctext', cx + 35, cy - 20, 0, 0,
                             "r=%d" % best.r(), (0, 255, 0)))
            return len(circles), cx, cy, "r=%d" % best.r()

    # 矩形/三角形: find_blobs
    blobs = img.find_blobs(th, pixels_threshold=50,
                           area_threshold=400, merge=True, margin=10)
    if not blobs and detect_mode == MODE_RECT:
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([(L_MIN, L_MAX)])
        bin_img.open(2)
        rects = bin_img.find_rects(threshold=15000)
        if rects:
            for r in rects[:8]:
                OVERLAYS.append(('rect', r.x(), r.y(), r.w(), r.h(),
                                 MODE_COLORS[MODE_RECT]))
            best = max(rects, key=lambda r: r.w() * r.h())
            crn = best.corners()
            cx = sum(c[0] for c in crn) // 4
            cy = sum(c[1] for c in crn) // 4
            OVERLAYS.append(('cross', cx, cy, 30, 0, (0, 255, 0)))
            return len(rects), cx, cy, ""
        return 0, 0, 0, ""

    if not blobs:
        return 0, 0, 0, ""

    candidates = []
    for b in blobs:
        rn = b.roundness()
        ar = b.area()
        if detect_mode == MODE_RECT:
            if 0.55 < rn < 0.86 and ar > 500:
                candidates.append(b)
        elif detect_mode == MODE_TRIANGLE:
            if 0.38 < rn < 0.68 and ar > 500:
                candidates.append(b)
        else:
            if rn > 0.72 and ar > 400:
                candidates.append(b)

    if not candidates:
        return 0, 0, 0, ""

    for b in candidates[:8]:
        OVERLAYS.append(('rect', b.x(), b.y(), b.w(), b.h(),
                         MODE_COLORS[detect_mode]))
    best = max(candidates, key=lambda b: b.area())
    cx, cy = best.cx(), best.cy()
    OVERLAYS.append(('cross', cx, cy, 30, 0, (0, 255, 0)))
    OVERLAYS.append(('ctext', cx + 35, cy - 15, 0, 0,
                     "%.2f" % best.roundness(), (0, 255, 0)))
    return len(candidates), cx, cy, ""

# ============================================================
# 六、UI 绘制 (直接在 800x480 图像上)
# ============================================================

BAR_TOP = SH - 56
BAR_H   = 56

BTN_SHP_W, BTN_SHP_H = 140, 36
BTN_SHP_Y = BAR_TOP + 4
BTN_SHP_X0 = 10
BTN_SHP_GAP = 6

BTN_CAL_W, BTN_CAL_H = 100, 36
BTN_CAL_X = BTN_SHP_X0 + 3 * (BTN_SHP_W + BTN_SHP_GAP)
BTN_CAL_Y = BAR_TOP + 4

ADJ_X0 = BTN_CAL_X + BTN_CAL_W + 30
ADJ_Y  = BAR_TOP + 4
ADJ_W, ADJ_H = 34, 16

def adj_btn(ch, pm):
    return (ADJ_X0 + ch * 76 + pm * 38, ADJ_Y, ADJ_W, ADJ_H)

def in_rect(px, py, r):
    x, y, w, h = r
    return x <= px <= x + w and y <= py <= y + h

def draw_ui(img, count, cx, cy):
    """在 800x480 图像上画检测叠加 + 底部 UI"""

    # --- 检测叠加 ---
    for ov in OVERLAYS:
        kind = ov[0]
        if kind == 'rect':
            _, rx, ry, rw, rh, color = ov
            img.draw_rectangle(rx, ry, rw, rh, color=color, thickness=3)
        elif kind == 'circle':
            _, cx2, cy2, rr, _, color = ov
            img.draw_circle(cx2, cy2, rr, color=color, thickness=3)
        elif kind == 'cross':
            _, cx2, cy2, sz, _, color = ov
            img.draw_cross(cx2, cy2, color=color, size=sz)
        elif kind == 'ctext':
            _, tx, ty, _, _, str_val, color = ov
            img.draw_string_advanced(tx, ty, 24, str_val, color=color)

    # --- 状态文字 ---
    if count > 0:
        info = "%s x%d" % (MODE_NAMES[detect_mode], count)
        img.draw_string_advanced(10, 10, 30, info, color=(0, 255, 0))
        img.draw_string_advanced(10, 44, 20,
                                 "(%d,%d)" % (cx, cy), color=(200, 200, 200))
    else:
        img.draw_string_advanced(10, 10, 30, MODE_NAMES[detect_mode],
                                 color=MODE_COLORS[detect_mode])
        img.draw_string_advanced(10, 44, 20, "无目标", color=(255, 100, 100))

    if STATUS["timer"] > 0:
        img.draw_string_advanced(10, 72, 22, STATUS["msg"],
                                 color=(255, 255, 0))
        STATUS["timer"] -= 1

    fps_s = "FPS:%d" % CLOCK.fps()
    img.draw_string_advanced(SW - 80, 10, 20, fps_s, color=(180, 180, 180))

    # --- 底部控件条 ---
    img.draw_rectangle(0, BAR_TOP, SW, BAR_H, color=(22, 24, 34), fill=True)
    img.draw_line(0, BAR_TOP, SW, BAR_TOP, color=(90, 90, 135), thickness=2)

    for i in range(3):
        x = BTN_SHP_X0 + i * (BTN_SHP_W + BTN_SHP_GAP)
        y = BTN_SHP_Y
        sel = (i == detect_mode)
        bg = MODE_COLORS[i] if sel else (55, 55, 72)
        bd = (255, 255, 255) if sel else (110, 110, 135)
        img.draw_rectangle(x, y, BTN_SHP_W, BTN_SHP_H, color=bg, fill=True)
        img.draw_rectangle(x, y, BTN_SHP_W, BTN_SHP_H, color=bd, thickness=2)
        tw = len(MODE_NAMES[i]) * 18
        img.draw_string_advanced(x + (BTN_SHP_W - tw) // 2, y + 8,
                                 18, MODE_NAMES[i], color=(255, 255, 255))

    x, y = BTN_CAL_X, BTN_CAL_Y
    img.draw_rectangle(x, y, BTN_CAL_W, BTN_CAL_H,
                       color=(0, 80, 190), fill=True)
    img.draw_rectangle(x, y, BTN_CAL_W, BTN_CAL_H,
                       color=(110, 190, 255), thickness=2)
    img.draw_string_advanced(x + 8, y + 8, 18, "校准", color=(255, 255, 255))

    img.draw_string_advanced(ADJ_X0, BAR_TOP - 5, 18, threshold_str(),
                             color=(255, 255, 160))

    for ch in range(3):
        label = "LAB"[ch]
        for pm in range(2):
            rx, ry, rw, rh = adj_btn(ch, pm)
            sign = "-" if pm == 0 else "+"
            bg = (120, 40, 40) if pm == 0 else (40, 100, 40)
            bd = (200, 100, 100) if pm == 0 else (100, 210, 100)
            img.draw_rectangle(rx, ry, rw, rh, color=bg, fill=True)
            img.draw_rectangle(rx, ry, rw, rh, color=bd, thickness=1)
            img.draw_string_advanced(rx + 5, ry - 2, 16,
                                     "%s%s" % (label, sign),
                                     color=(255, 255, 255))

# ============================================================
# 七、初始化
# ============================================================

print("=== K230 触摸调节工具 v5 ===")
print("架构: 800x480 单通道 RGB565 → 检测+UI → 直出 零缩放")

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=CW, height=CH)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.ST7701, width=SW, height=SH, to_ide=True)
MediaManager.init()
sensor.run()

tp = TOUCH(0)
CLOCK = time.clock()
STATUS = {"msg": "", "timer": 0}
fc = 0

def set_status(msg, duration=90):
    STATUS["msg"] = msg
    STATUS["timer"] = duration

print("就绪! 触摸底栏: [三][矩][圆] | [校准] | L/A/B +/-")

# ============================================================
# 八、主循环
# ============================================================

try:
    while True:
        os.exitpoint()
        CLOCK.tick()
        fc += 1

        # --- 抓帧 ---
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # --- 检测 ---
        count, cx, cy, extra = detect_shapes(img)

        # --- 画 UI (直接画在摄像头图像上) ---
        draw_ui(img, count, cx, cy)

        # --- 显示 (800x480 → 800x480, 零缩放) ---
        Display.show_image(img)

        # --- 触摸 ---
        points = tp.read()
        if len(points) > 0:
            px, py = points[0].x, points[0].y
            handled = False

            for i in range(3):
                x = BTN_SHP_X0 + i * (BTN_SHP_W + BTN_SHP_GAP)
                if in_rect(px, py, (x, BTN_SHP_Y, BTN_SHP_W, BTN_SHP_H)):
                    detect_mode = i
                    set_status(">> %s 模式" % MODE_NAMES[i])
                    handled = True
                    break

            if not handled and in_rect(px, py, (BTN_CAL_X, BTN_CAL_Y,
                                                 BTN_CAL_W, BTN_CAL_H)):
                ok, cnt = auto_calibrate(img)
                if ok:
                    set_status("校准OK! %d个目标  %s" % (cnt, threshold_str()),
                               duration=150)
                else:
                    set_status("校准失败, 已回退原阈值")
                handled = True

            if not handled:
                for ch in range(3):
                    for pm, delta in [(0, -5), (1, 5)]:
                        if in_rect(px, py, adj_btn(ch, pm)):
                            threshold_adjust(ch, delta)
                            set_status("%s: %d~%d" % (
                                "LAB"[ch],
                                [L_MIN, A_MIN, B_MIN][ch],
                                [L_MAX, A_MAX, B_MAX][ch]),
                                duration=45)
                            handled = True
                            break
                    if handled:
                        break

        if fc % 150 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\n用户中断")
except BaseException as e:
    print("异常: %s" % str(e))
    import sys
    sys.print_exception(e)
finally:
    sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完成")
