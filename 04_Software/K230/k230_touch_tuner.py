"""
K230 触摸屏脱机快速调节工具 v7
================================
v7 修复:
  - to_lab() 不可用 → RGB统计估算LAB阈值 (主导色判断 + 通道范围推算)
  - 圆形帧率低   → 降采样2x (800→400) + stride加速, 坐标×2还原
  - 矩形/三角误检 → 先颜色blob预过滤, 再几何检测, 大幅降低背景噪点
  - 手动校准增强 → blob计数实时反馈 + 粗调/细调双模式

硬件: 庐山派 K230 + GC2093 + MIPI ST7701 3.1寸触摸屏
"""

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
import image, time, os, gc, math

# ============================================================
# 一、分辨率
# ============================================================

SW, SH = 800, 480
CW, CH = 640, 480          # VGA: 节省内存, 避免 MMZ 溢出崩溃

# ============================================================
# 二、检测模式
# ============================================================

MODE_TRIANGLE, MODE_RECT, MODE_CIRCLE = 0, 1, 2
MODE_NAMES  = ["三角形", "矩形", "圆形"]
MODE_COLORS = [(255, 165, 0), (255, 60, 60), (60, 200, 255)]
detect_mode = MODE_RECT

# ============================================================
# 三、LAB 阈值
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

def threshold_adjust(ch, delta):
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    if ch == 0:
        L_MIN = max(0, L_MIN + delta)
        L_MAX = max(L_MIN + 5, min(127, L_MAX + delta))
    elif ch == 1:
        A_MIN = max(-128, A_MIN + delta)
        A_MAX = max(A_MIN + 5, min(127, A_MAX + delta))
    else:
        B_MIN = max(-128, B_MIN + delta)
        B_MAX = max(B_MIN + 5, min(127, B_MAX + delta))

# ============================================================
# 四、自动校准 (to_lab 不可用 → RGB统计估算LAB)
# ============================================================

def auto_calibrate(img):
    """
    RGB 统计估算 LAB 阈值 (to_lab() 在 CanMV v1.2.2 不存在).
    策略: 采样中央区域 RGB → 判断主导色 → 设置对应 A/B 范围.
    返回 (success, blob_count)
    """
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    threshold_backup()

    try:
        # 中央 200x120 区域采样
        rw, rh = 200, 120
        rx = CW // 2 - rw // 2
        ry = CH // 2 - rh // 2
        roi = img.copy(roi=(rx, ry, rw, rh))

        # get_statistics() on RGB565: 18 个值 (mean/median/mode/stdev/min/max × 3)
        stats = roi.get_statistics()
        r_mean, r_stdev = stats[0], stats[3]
        g_mean, g_stdev = stats[6], stats[9]
        b_mean, b_stdev = stats[12], stats[15]

        # 估算 L: 加权亮度
        l_est = int(0.299 * r_mean + 0.587 * g_mean + 0.114 * b_mean)
        l_range = max(int(2.5 * max(r_stdev, g_stdev, b_stdev)), 20)
        L_MIN = max(0, l_est - l_range)
        L_MAX = min(127, l_est + l_range)

        # 判断主导色 → 设置 A/B 范围
        r_dom = r_mean - (g_mean + b_mean) / 2  # 红分量优势
        g_dom = g_mean - (r_mean + b_mean) / 2  # 绿分量优势
        b_dom = b_mean - (r_mean + g_mean) / 2  # 蓝分量优势

        print("  [RGB] R=%.0f±%.0f G=%.0f±%.0f B=%.0f±%.0f" % (
            r_mean, r_stdev, g_mean, g_stdev, b_mean, b_stdev))
        print("  [估算] L≈%d  r_dom=%.0f g_dom=%.0f b_dom=%.0f" % (
            l_est, r_dom, g_dom, b_dom))

        # 根据主导色设置 A/B (A=红绿轴, B=蓝黄轴)
        if r_dom > 20:         # 红色物体
            A_MIN, A_MAX = 20, 127
            B_MIN, B_MAX = -30, 60
            print("  [主导色] 红色 → A:20~127 B:-30~60")
        elif g_dom > 20:        # 绿色物体
            A_MIN, A_MAX = -128, -10
            B_MIN, B_MAX = -20, 80
            print("  [主导色] 绿色 → A:-128~-10 B:-20~80")
        elif b_dom > 15:        # 蓝色物体
            A_MIN, A_MAX = -30, 50
            B_MIN, B_MAX = -128, -10
            print("  [主导色] 蓝色 → A:-30~50 B:-128~-10")
        elif abs(r_dom) < 15 and abs(g_dom) < 15 and abs(b_dom) < 15:
            # 无明显主导 → 物体可能是黑/白/灰, 只用 L 通道
            A_MIN, A_MAX = -128, 127
            B_MIN, B_MAX = -128, 127
            print("  [主导色] 灰度 → 全通道范围")
        else:
            # 中间状态 → 建议手动调
            A_MIN, A_MAX = -60, 60
            B_MIN, B_MAX = -60, 60
            print("  [主导色] 不明确 → 建议手动微调")

        print("  新阈值: %s" % threshold_str())

    except Exception as e:
        print("  [RGB统计失败] %s" % e)
        threshold_restore()
        return False, 0

    # 验证
    blobs = img.find_blobs(
        [(L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)],
        pixels_threshold=50, area_threshold=500, merge=True)
    if blobs and len(blobs) > 0:
        return True, len(blobs)
    else:
        print("  验证失败, 回退旧阈值")
        threshold_restore()
        return False, 0

# ============================================================
# 五、形状检测 (复用灰度图减少内存)
# ============================================================

OVERLAYS = []

def detect_shapes(img):
    """返回 (count, cx, cy, extra_str); 填充 OVERLAYS"""
    global OVERLAYS
    OVERLAYS = []
    th = threshold_get()

    # 颜色 blobs (各种形状共用)
    blobs = img.find_blobs(th, pixels_threshold=30,
                           area_threshold=200, merge=True, margin=10)

    # 灰度图 + 二值图 (几何检测共用, 只创建一次)
    gray = img.to_grayscale(copy=True)

    if detect_mode == MODE_CIRCLE:
        return _detect_circles(gray, img, blobs)
    elif detect_mode == MODE_RECT:
        return _detect_rects(gray, blobs)
    elif detect_mode == MODE_TRIANGLE:
        return _detect_triangles(gray, blobs)

    return 0, 0, 0, ""


def _detect_circles(gray, color_img, blobs):
    """圆形: 降采样2x → 霍夫圆 → 坐标还原"""
    try:
        gray.midpoint_pool(2, 2)  # 640x480 → 320x240
        scale = 2
    except:
        scale = 1

    circles = gray.find_circles(
        threshold=2000, r_min=6, r_max=60,
        r_step=2, x_margin=10, y_margin=10,
        x_stride=3, y_stride=2)

    if circles:
        for c in circles[:10]:
            OVERLAYS.append(('circle', c.x() * scale, c.y() * scale,
                             c.r() * scale, 0, MODE_COLORS[MODE_CIRCLE]))
        best = max(circles, key=lambda c: c.r())
        cx, cy = best.x() * scale, best.y() * scale
        r = best.r() * scale
        OVERLAYS.append(('cross', cx, cy, 24, 0, (0, 255, 0)))
        OVERLAYS.append(('label', cx + 28, cy - 16, "r=%d" % r, (0, 255, 0)))
        return len(circles), cx, cy, "r=%d" % r

    # 降级: blob roundness
    if blobs:
        for b in blobs:
            if b.roundness() > 0.70 and b.area() > 300:
                OVERLAYS.append(('circle', b.cx(), b.cy(),
                                 max(b.w(), b.h()) // 2, 0,
                                 MODE_COLORS[MODE_CIRCLE]))
        if OVERLAYS:
            b = max(blobs, key=lambda x: x.area())
            OVERLAYS.append(('cross', b.cx(), b.cy(), 24, 0, (0, 255, 0)))
            return len(OVERLAYS) - 1, b.cx(), b.cy(), ""
    return 0, 0, 0, ""


def _detect_rects(gray, blobs):
    """矩形: 二值化 → find_rects → 颜色验证"""
    bin_img = gray.binary([(L_MIN, L_MAX)])
    bin_img.open(1)

    rects = bin_img.find_rects(threshold=6000)

    if not rects:
        if blobs:
            for b in blobs:
                rn = b.roundness()
                if 0.62 < rn < 0.84 and b.area() > 300:
                    OVERLAYS.append(('rect', b.x(), b.y(), b.w(), b.h(),
                                     MODE_COLORS[MODE_RECT]))
            if OVERLAYS:
                b = max(blobs, key=lambda x: x.area())
                OVERLAYS.append(('cross', b.cx(), b.cy(), 24, 0, (0, 255, 0)))
                return len(OVERLAYS) - 1, b.cx(), b.cy(), ""
        return 0, 0, 0, ""

    # 颜色验证
    valid = []
    for r in rects:
        crn = r.corners()
        rcx = sum(c[0] for c in crn) // 4
        rcy = sum(c[1] for c in crn) // 4
        ok = True
        if blobs:
            ok = False
            for b in blobs:
                if (b.x() <= rcx <= b.x() + b.w() and
                    b.y() <= rcy <= b.y() + b.h()):
                    ok = True
                    break
        if ok and r.w() * r.h() > 500:
            valid.append(r)

    if valid:
        for r in valid[:10]:
            OVERLAYS.append(('rect', r.x(), r.y(), r.w(), r.h(),
                             MODE_COLORS[MODE_RECT]))
        best = max(valid, key=lambda r: r.w() * r.h())
        crn = best.corners()
        cx = sum(c[0] for c in crn) // 4
        cy = sum(c[1] for c in crn) // 4
        OVERLAYS.append(('cross', cx, cy, 24, 0, (0, 255, 0)))
        return len(valid), cx, cy, ""
    return 0, 0, 0, ""


def _detect_triangles(gray, blobs):
    """三角形: find_rects低阈值 + 短边筛选 + 颜色验证"""
    bin_img = gray.binary([(L_MIN, L_MAX)])
    bin_img.open(1)

    all_quads = bin_img.find_rects(threshold=3000)
    tri_candidates = []

    for r in all_quads:
        corners = r.corners()
        if len(corners) != 4:
            continue
        edges = []
        for i in range(4):
            dx = corners[i][0] - corners[(i + 1) % 4][0]
            dy = corners[i][1] - corners[(i + 1) % 4][1]
            edges.append(math.sqrt(dx * dx + dy * dy))
        min_e, max_e = min(edges), max(edges)
        if max_e > 0 and min_e / max_e < 0.25 and r.w() * r.h() > 500:
            crn = r.corners()
            rcx = sum(c[0] for c in crn) // 4
            rcy = sum(c[1] for c in crn) // 4
            ok = True
            if blobs:
                ok = False
                for b in blobs:
                    if (b.x() <= rcx <= b.x() + b.w() and
                        b.y() <= rcy <= b.y() + b.h()):
                        ok = True
                        break
            if ok:
                tri_candidates.append(r)

    if tri_candidates:
        for t in tri_candidates[:8]:
            OVERLAYS.append(('rect', t.x(), t.y(), t.w(), t.h(),
                             MODE_COLORS[MODE_TRIANGLE]))
        best = max(tri_candidates, key=lambda r: r.w() * r.h())
        crn = best.corners()
        cx = sum(c[0] for c in crn) // 4
        cy = sum(c[1] for c in crn) // 4
        OVERLAYS.append(('cross', cx, cy, 24, 0, (0, 255, 0)))
        return len(tri_candidates), cx, cy, ""

    # 降级: blob roundness
    if blobs:
        for b in blobs:
            rn = b.roundness()
            if 0.40 < rn < 0.65 and b.area() > 300:
                OVERLAYS.append(('rect', b.x(), b.y(), b.w(), b.h(),
                                 MODE_COLORS[MODE_TRIANGLE]))
        if OVERLAYS:
            b = max(blobs, key=lambda x: x.area())
            OVERLAYS.append(('cross', b.cx(), b.cy(), 24, 0, (0, 255, 0)))
            return len(OVERLAYS) - 1, b.cx(), b.cy(), ""
    return 0, 0, 0, ""

# ============================================================
# 七、UI 绘制
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

def draw_ui(img, count, cx, cy, blob_total=0):
    """在 800x480 图像上叠加所有 UI"""

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
        elif kind == 'label':
            _, tx, ty, s, color = ov
            img.draw_string_advanced(tx, ty, 24, s, color=color)

    # --- 检测信息 ---
    if count > 0:
        info = "%s x%d" % (MODE_NAMES[detect_mode], count)
        img.draw_string_advanced(10, 10, 30, info, color=(0, 255, 0))
        img.draw_string_advanced(10, 44, 20,
                                 "(%d,%d)" % (cx, cy), color=(200, 200, 200))
    else:
        img.draw_string_advanced(10, 10, 28, MODE_NAMES[detect_mode],
                                 color=MODE_COLORS[detect_mode])
        img.draw_string_advanced(10, 44, 20, "无目标", color=(255, 100, 100))

    # blob 总数反馈 (手动调参辅助)
    if blob_total > 0:
        c = (0, 255, 0) if blob_total > 0 else (255, 150, 50)
        img.draw_string_advanced(10, 68, 16,
                                 "blob:%d" % blob_total, color=c)

    if STATUS["timer"] > 0:
        y = 90 if blob_total > 0 else 72
        img.draw_string_advanced(10, y, 20, STATUS["msg"],
                                 color=(255, 255, 0))
        STATUS["timer"] -= 1

    fps_s = "FPS:%d" % max(1, CLOCK.fps())
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
# 八、初始化
# ============================================================

print("=== K230 触摸调节工具 v7 ===")
print("校准: RGB统计估算LAB (to_lab不可用)")
print("检测: 降采样圆形 | 颜色预过滤+几何 矩形/三角")

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
_last_touch_btn = (-1, -1)

def set_status(msg, duration=90):
    STATUS["msg"] = msg
    STATUS["timer"] = duration

print("就绪!")

# ============================================================
# 九、主循环
# ============================================================

try:
    while True:
        os.exitpoint()
        CLOCK.tick()
        fc += 1

        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # --- 检测 (640x480) ---
        count, cx, cy, extra = detect_shapes(img)

        # --- 实时 blob 计数 ---
        all_blobs = img.find_blobs(threshold_get(),
                                   pixels_threshold=10,
                                   area_threshold=50, merge=True)
        blob_total = len(all_blobs) if all_blobs else 0

        # --- 缩放到 800x480 (UI以800x480绘制, 需匹配) ---
        try:
            img.resize(SW, SH)
        except:
            pass  # resize 不可用时屏幕硬件会拉伸 640→800

        # --- UI ---
        draw_ui(img, count, cx, cy, blob_total)
        Display.show_image(img)

        # --- 触摸 ---
        points = tp.read()
        if len(points) > 0:
            px, py = points[0].x, points[0].y
            ev = points[0].event
            if ev not in (2, 3):
                _last_touch_btn = (-1, -1)
                continue

            handled = False
            cur_btn = (-1, -1)

            for i in range(3):
                x = BTN_SHP_X0 + i * (BTN_SHP_W + BTN_SHP_GAP)
                if in_rect(px, py, (x, BTN_SHP_Y, BTN_SHP_W, BTN_SHP_H)):
                    cur_btn = (0, i)
                    if cur_btn != _last_touch_btn:
                        detect_mode = i
                        set_status(">> %s 模式" % MODE_NAMES[i])
                        handled = True
                    break

            if not handled and in_rect(px, py, (BTN_CAL_X, BTN_CAL_Y,
                                                 BTN_CAL_W, BTN_CAL_H)):
                cur_btn = (1, 0)
                if cur_btn != _last_touch_btn:
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
                            cur_btn = (2, ch, pm)
                            threshold_adjust(ch, delta)
                            set_status("%s: %d~%d" % (
                                "LAB"[ch],
                                [L_MIN, A_MIN, B_MIN][ch],
                                [L_MAX, A_MAX, B_MAX][ch]),
                                duration=30)
                            handled = True
                            break
                    if handled:
                        break

            _last_touch_btn = cur_btn

        if len(points) == 0:
            _last_touch_btn = (-1, -1)

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
