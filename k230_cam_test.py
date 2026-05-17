"""
K230 摄像头测试 — A4黑框 + 红色靶心 (高帧率版)
QVGA 320×240 采集, 640×480 显示
"""
from media.sensor import *
from media.display import *
from media.media import *
import time, os, gc

# ===== 一、初始化: QVGA 高帧率 (skill铁律: 默认320×240) =====
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=320, height=240)   # QVGA → 高帧率
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

# Display 独立于采集, 640×480 显示更清晰
Display.init(Display.VIRT, width=640, height=480, to_ide=True)
MediaManager.init()
sensor.run()

# ===== 二、阈值 =====
TAPE_GRAY  = (0, 109)
RED_TARGET = [(52,100,24,127,-49,41),
              (29,73,19,127,-57,89)]

# ===== 三、A4 约束 (适配 320×240) =====
IW, IH = 320, 240
A4_RATIO_MIN = 1.15
A4_RATIO_MAX = 1.80
A4_AREA_MIN  = IW * IH * 0.03    # 2304px
A4_AREA_MAX  = IW * IH * 0.85    # 65280px
STABLE_FRAMES = 3

# ===== 四、检测状态 =====
a4_corners = None
a4_ok      = False
a4_stable  = 0
a4_last    = None
target_ok  = False
target_cx  = 0
target_cy  = 0
clock = time.clock()
fc = 0

print("QVGA 320×240 高帧率模式, 开始检测...")

def a4_filter_valid(rects):
    """长宽比 + 面积过滤"""
    good = []
    for r in rects:
        w, h = r.w(), r.h()
        if w <= 0 or h <= 0:
            continue
        ratio = max(w, h) / min(w, h)
        area  = w * h
        if A4_RATIO_MIN < ratio < A4_RATIO_MAX and \
           A4_AREA_MIN < area < A4_AREA_MAX:
            good.append(r)
    return good

def corners_near(c1, c2, max_dist=15):
    if c1 is None or c2 is None:
        return False
    for p, q in zip(c1, c2):
        if abs(p[0]-q[0]) > max_dist or abs(p[1]-q[1]) > max_dist:
            return False
    return True

def target_in_center(cx, cy, corners, margin=0.3):
    if corners is None:
        return True
    xs = [c[0] for c in corners]; ys = [c[1] for c in corners]
    x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
    cw, ch = x1 - x0, y1 - y0
    mx, my = margin * cw / 2, margin * ch / 2
    ccx, ccy = (x0+x1)/2, (y0+y1)/2
    return abs(cx-ccx) < cw/2-mx and abs(cy-ccy) < ch/2-my

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # ======== A4 黑胶带边框 ========
        gray = img.to_grayscale(copy=True)
        # QVGA 分辨率低, 不模糊直接二值化
        bin_img = gray.binary([TAPE_GRAY])
        bin_img.open(1)                    # 轻量开运算: 去小噪点即可

        all_r = bin_img.find_rects(threshold=10000)
        rects = a4_filter_valid(all_r)

        if rects:
            best = max(rects, key=lambda r: r.w() * r.h())
            new_corners = [(c[0], c[1]) for c in best.corners()]

            if corners_near(new_corners, a4_last):
                a4_stable += 1
            else:
                a4_stable = 1
                a4_last = new_corners

            if a4_stable >= STABLE_FRAMES:
                a4_corners = new_corners
                a4_ok = True
        else:
            a4_stable = max(0, a4_stable - 1)
            if a4_stable == 0:
                a4_ok = False
                a4_corners = None

        # 画 A4 边框
        if a4_ok and a4_corners:
            for i in range(4):
                img.draw_line(a4_corners[i][0], a4_corners[i][1],
                              a4_corners[(i+1)%4][0], a4_corners[(i+1)%4][1],
                              color=(255,0,0), thickness=2)
            cx_a4 = sum(c[0] for c in a4_corners) // 4
            cy_a4 = sum(c[1] for c in a4_corners) // 4
            img.draw_cross(cx_a4, cy_a4, color=(0,0,255), size=10, thickness=2)

        # ======== 红色靶心 ========
        if a4_ok and a4_corners:
            xs = [c[0] for c in a4_corners]; ys = [c[1] for c in a4_corners]
            margin = 4
            roi = (min(xs)+margin, min(ys)+margin,
                   max(xs)-min(xs)-2*margin, max(ys)-min(ys)-2*margin)
            blobs = img.find_blobs(RED_TARGET, roi=roi,
                                   pixels_threshold=15, merge=True)
        else:
            blobs = img.find_blobs(RED_TARGET, pixels_threshold=40, merge=True)

        target_ok = False
        if blobs:
            for b in sorted(blobs, key=lambda x: x.area(), reverse=True):
                if b.density() < 0.35:
                    continue
                bx = b.x() + b.w() // 2
                by = b.y() + b.h() // 2
                if a4_ok and not target_in_center(bx, by, a4_corners, 0.35):
                    continue
                target_cx, target_cy = bx, by
                target_ok = True
                img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                   color=(0,255,0), thickness=1)
                img.draw_cross(bx, by, color=(0,255,0), size=8, thickness=1)
                break

        # ======== UI ========
        fps = clock.fps()
        bar_h = 30
        img.draw_rectangle(0, 0, IW, bar_h, color=(0,0,0), thickness=-1, fill=True)

        if a4_ok and target_ok:
            img.draw_string_advanced(3, 3, 25,
                f"A4+RED {fps:.0f}fps", color=(0,255,0))
        elif a4_ok:
            img.draw_string_advanced(3, 3, 25,
                f"A4 OK  {fps:.0f}fps", color=(255,255,0))
        else:
            img.draw_string_advanced(3, 3, 25,
                f"SEARCH {fps:.0f}fps", color=(255,0,0))

        Display.show_image(img)

        if fc % 300 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("用户停止")
except BaseException as e:
    print(f"异常: {e}")
finally:
    sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完毕")
