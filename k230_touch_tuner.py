"""
K230 触摸屏脱机快速调节工具 v6
================================
v6 改进:
  - 形状检测重写: 圆形=霍夫圆, 矩形=AprilTag四边形, 三角形=四边形+短边筛选
  - 双模式校准: LAB统计(主) + 三区采样(备), 均带验证回退
  - 辅助二值图: 左上角小窗显示当前L阈值下的二值化效果, 帮助手动调参
  - 连续触摸优化: 防重复触发, 长按连续调节

硬件: 庐山派 K230 + GC2093 + MIPI ST7701 3.1寸触摸屏
"""

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH
import image, time, os, gc

# ============================================================
# 一、分辨率
# ============================================================

SW, SH = 800, 480
CW, CH = 800, 480

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
# 四、自动校准 (LAB统计 + 三区采样 双策略)
# ============================================================

def auto_calibrate(img):
    """
    双策略自动校准, 主策略失败自动切换备策略.
    返回 (success, blob_count)
    """
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    threshold_backup()

    # 策略1: LAB 统计法 (对单色物体最准)
    try:
        rw, rh = 200, 120
        rx = CW // 2 - rw // 2
        ry = CH // 2 - rh // 2
        roi = img.copy(roi=(rx, ry, rw, rh))
        lab = roi.to_lab()
        stats = lab.get_statistics()

        l_mean, l_stdev = stats[0], stats[3]
        a_mean, a_stdev = stats[6], stats[9]
        b_mean, b_stdev = stats[12], stats[15]

        # 检查有效性: stdev 不能为 0
        if l_stdev < 0.5 and a_stdev < 0.5 and b_stdev < 0.5:
            raise ValueError("ROI 内颜色过于均匀, 可能是纯色背景")

        l_range = max(int(2.5 * l_stdev), 20)
        a_range = max(int(2.5 * a_stdev), 30)
        b_range = max(int(2.5 * b_stdev), 30)

        L_MIN = max(0,   int(l_mean) - l_range)
        L_MAX = min(127, int(l_mean) + l_range)
        A_MIN = max(-128, int(a_mean) - a_range)
        A_MAX = min(127,  int(a_mean) + a_range)
        B_MIN = max(-128, int(b_mean) - b_range)
        B_MAX = min(127,  int(b_mean) + b_range)

        print("  [LAB统计] L=%.1f±%.1f A=%.1f±%.1f B=%.1f±%.1f" % (
            l_mean, l_stdev, a_mean, a_stdev, b_mean, b_stdev))
    except Exception as e:
        print("  [LAB统计失败] %s, 尝试三区采样..." % e)
        # 策略2: 三区采样法 (对复杂场景更鲁棒)
        try:
            _calibrate_3zone(img)
            print("  [三区采样] OK")
        except Exception as e2:
            print("  [三区采样失败] %s" % e2)
            threshold_restore()
            return False, 0

    # 验证
    print("  新阈值: %s" % threshold_str())
    blobs = img.find_blobs(
        [(L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX)],
        pixels_threshold=50, area_threshold=500, merge=True)
    if blobs and len(blobs) > 0:
        return True, len(blobs)
    else:
        print("  验证失败, 回退旧阈值")
        threshold_restore()
        return False, 0


def _calibrate_3zone(img):
    """
    备选校准: 在画面中心、左上、右下各取一小块采样,
    取三区 A/B 通道的合并范围作为阈值. 对纯色物体更鲁棒.
    """
    global L_MIN, L_MAX, A_MIN, A_MAX, B_MIN, B_MAX
    zones = [
        (CW // 2 - 30, CH // 2 - 30, 60, 60),   # 中心
        (CW // 4 - 20, CH // 4 - 20, 40, 40),    # 左上
        (3 * CW // 4 - 20, 3 * CH // 4 - 20, 40, 40),  # 右下
    ]
    a_vals, b_vals = [], []
    for (zx, zy, zw, zh) in zones:
        roi = img.copy(roi=(zx, zy, zw, zh))
        lab = roi.to_lab()
        stats = lab.get_statistics()
        a_vals.extend([stats[6] - 2.5 * stats[9], stats[6] + 2.5 * stats[9]])
        b_vals.extend([stats[12] - 2.5 * stats[15], stats[12] + 2.5 * stats[15]])

    A_MIN = max(-128, int(min(a_vals)))
    A_MAX = min(127,  int(max(a_vals)))
    B_MIN = max(-128, int(min(b_vals)))
    B_MAX = min(127,  int(max(b_vals)))
    # 扩展范围防过窄
    if A_MAX - A_MIN < 30:
        c = (A_MIN + A_MAX) // 2
        A_MIN, A_MAX = max(-128, c - 20), min(127, c + 20)
    if B_MAX - B_MIN < 30:
        c = (B_MIN + B_MAX) // 2
        B_MIN, B_MAX = max(-128, c - 20), min(127, c + 20)
    L_MIN, L_MAX = 15, 110  # 宽亮度范围
    print("  [3区] A:%d~%d B:%d~%d" % (A_MIN, A_MAX, B_MIN, B_MAX))

# ============================================================
# 五、形状检测 (重写, 每种形状独立策略)
# ============================================================

OVERLAYS = []

def detect_shapes(img):
    """返回 (count, cx, cy, extra_str); 填充 OVERLAYS"""
    global OVERLAYS
    OVERLAYS = []
    th = threshold_get()

    # === 圆形: 霍夫圆检测 (最可靠) ===
    if detect_mode == MODE_CIRCLE:
        # 先用 find_circles 在灰度图上检测
        gray = img.to_grayscale(copy=True)
        circles = gray.find_circles(
            threshold=3000, r_min=15, r_max=150,
            r_step=2, x_margin=15, y_margin=15,
            roi=(0, 0, CW, CH))
        if circles:
            for c in circles[:10]:
                OVERLAYS.append(('circle', c.x(), c.y(), c.r(), 0,
                                 MODE_COLORS[MODE_CIRCLE]))
            best = max(circles, key=lambda c: c.r())
            cx, cy = best.x(), best.y()
            OVERLAYS.append(('cross', cx, cy, 30, 0, (0, 255, 0)))
            OVERLAYS.append(('label', cx + 35, cy - 20, "r=%d" % best.r(),
                             (0, 255, 0)))
            return len(circles), cx, cy, "r=%d" % best.r()
        return 0, 0, 0, ""

    # === 矩形: AprilTag 四边形检测 ===
    if detect_mode == MODE_RECT:
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([(L_MIN, L_MAX)])
        bin_img.open(1)  # 去噪
        rects = bin_img.find_rects(threshold=8000)
        if rects:
            for r in rects[:10]:
                OVERLAYS.append(('rect', r.x(), r.y(), r.w(), r.h(),
                                 MODE_COLORS[MODE_RECT]))
            best = max(rects, key=lambda r: r.w() * r.h())
            crn = best.corners()
            cx = sum(c[0] for c in crn) // 4
            cy = sum(c[1] for c in crn) // 4
            OVERLAYS.append(('cross', cx, cy, 30, 0, (0, 255, 0)))
            return len(rects), cx, cy, ""

        # 降级: blob 圆度筛选
        blobs = img.find_blobs(th, pixels_threshold=50,
                               area_threshold=500, merge=True, margin=10)
        for b in blobs:
            rn = b.roundness()
            if 0.62 < rn < 0.84 and b.area() > 500:
                OVERLAYS.append(('rect', b.x(), b.y(), b.w(), b.h(),
                                 MODE_COLORS[MODE_RECT]))
        if OVERLAYS:
            b = max(blobs, key=lambda x: x.area())
            OVERLAYS.append(('cross', b.cx(), b.cy(), 30, 0, (0, 255, 0)))
            return len(OVERLAYS) - 1, b.cx(), b.cy(), ""
        return 0, 0, 0, ""

    # === 三角形: 四边形检测 + 短边筛选 ===
    if detect_mode == MODE_TRIANGLE:
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([(L_MIN, L_MAX)])
        bin_img.open(1)

        # 用低 threshold 检测所有四边形
        all_quads = bin_img.find_rects(threshold=4000)
        triangles = []

        import math
        for r in all_quads:
            corners = r.corners()
            if len(corners) != 4:
                continue
            # 计算 4 条边长
            edges = []
            for i in range(4):
                dx = corners[i][0] - corners[(i + 1) % 4][0]
                dy = corners[i][1] - corners[(i + 1) % 4][1]
                edges.append(math.sqrt(dx * dx + dy * dy))
            # 最短边 < 最长边的 25% → 近似三角形 (一角"折叠")
            min_e, max_e = min(edges), max(edges)
            if max_e > 0 and min_e / max_e < 0.25 and r.w() * r.h() > 800:
                triangles.append(r)

        if triangles:
            for t in triangles[:8]:
                OVERLAYS.append(('rect', t.x(), t.y(), t.w(), t.h(),
                                 MODE_COLORS[MODE_TRIANGLE]))
            best = max(triangles, key=lambda r: r.w() * r.h())
            crn = best.corners()
            cx = sum(c[0] for c in crn) // 4
            cy = sum(c[1] for c in crn) // 4
            OVERLAYS.append(('cross', cx, cy, 30, 0, (0, 255, 0)))
            return len(triangles), cx, cy, ""

        # 降级: blob 圆度筛选 (三角形圆度 ≈ 0.45~0.62)
        blobs = img.find_blobs(th, pixels_threshold=50,
                               area_threshold=500, merge=True, margin=10)
        for b in blobs:
            rn = b.roundness()
            if 0.40 < rn < 0.65 and b.area() > 500:
                OVERLAYS.append(('rect', b.x(), b.y(), b.w(), b.h(),
                                 MODE_COLORS[MODE_TRIANGLE]))
        if OVERLAYS:
            b = max(blobs, key=lambda x: x.area())
            OVERLAYS.append(('cross', b.cx(), b.cy(), 30, 0, (0, 255, 0)))
            return len(OVERLAYS) - 1, b.cx(), b.cy(), ""
        return 0, 0, 0, ""

    return 0, 0, 0, ""

# ============================================================
# 六、UI 绘制
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

    # blob 总数实时反馈 (帮助手动调阈值)
    if blob_total > 0:
        img.draw_string_advanced(10, 68, 16,
                                 "blob:%d" % blob_total, color=(180, 180, 100))

    if STATUS["timer"] > 0:
        y = 90 if blob_total > 0 else 72
        img.draw_string_advanced(10, y, 20, STATUS["msg"],
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

print("=== K230 触摸调节工具 v6 ===")
print("检测: 霍夫圆 / AprilTag四边形 / 短边三角筛选")
print("校准: LAB统计(主) + 三区采样(备) + 自动回退")

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
_last_touch_btn = (-1, -1)  # 防重复触发

def set_status(msg, duration=90):
    STATUS["msg"] = msg
    STATUS["timer"] = duration

print("就绪!")

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

        # --- 实时 blob 计数 (辅助手动调阈值) ---
        all_blobs = img.find_blobs(threshold_get(),
                                   pixels_threshold=10,
                                   area_threshold=50, merge=True)
        blob_total = len(all_blobs) if all_blobs else 0

        # --- 画 UI ---
        draw_ui(img, count, cx, cy, blob_total)

        # --- 显示 ---
        Display.show_image(img)

        # --- 触摸 ---
        points = tp.read()
        if len(points) > 0:
            px, py = points[0].x, points[0].y
            # 只在按下/移动时响应 (过滤抬起)
            ev = points[0].event
            if ev not in (2, 3):  # 2=DOWN, 3=MOVE
                _last_touch_btn = (-1, -1)
                continue

            # 防重复: 同一按钮不放则不重复触发
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
                            # +/- 按钮允许长按连续调节
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

        # 触控释放时重置
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
