"""
K230 摄像头测试 — A4黑框 + 红色靶心 (抗背景干扰版)
"""
from media.sensor import *
from media.display import *
from media.media import *
import time, os, gc

# ===== 一、初始化 =====
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=640, height=480)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.VIRT, width=640, height=480, to_ide=True)
MediaManager.init()
sensor.run()

# ===== 二、阈值 =====
TAPE_GRAY  = (0, 109)        # 黑胶带灰度
RED_TARGET = [(52,100,24,127,-49,41),
              (29,73,19,127,-57,89)]

# ===== 三、A4 边框约束 =====
IMG_W, IMG_H = 640, 480
A4_RATIO_MIN = 1.15          # A4 实际 1.414, 允许透视变形
A4_RATIO_MAX = 1.80
A4_AREA_MIN  = IMG_W * IMG_H * 0.03   # 最小占画面3%
A4_AREA_MAX  = IMG_W * IMG_H * 0.85   # 最大85%
STABLE_FRAMES = 3            # 连续N帧稳定才确认

# ===== 四、检测状态 (带时间滤波) =====
a4_corners  = None           # 当前A4角点
a4_ok       = False
a4_stable   = 0              # 连续检测帧数
a4_last     = None           # 上次角点(用于比较)

target_ok    = False
target_cx    = 0
target_cy    = 0
target_ok_cnt = 0

clock = time.clock()
fc = 0

print("初始化完成, 开始检测...")

def a4_filter_valid(rects):
    """过滤掉明显不是A4纸的矩形"""
    good = []
    for r in rects:
        w, h = r.w(), r.h()
        if w <= 0 or h <= 0:
            continue
        ratio = max(w, h) / min(w, h)
        area  = w * h
        # 长宽比 + 面积双约束
        if A4_RATIO_MIN < ratio < A4_RATIO_MAX and \
           A4_AREA_MIN < area < A4_AREA_MAX:
            good.append(r)
    return good

def corners_near(c1, c2, max_dist=20):
    """两组角点是否接近(时间稳定性判断)"""
    if c1 is None or c2 is None:
        return False
    for p, q in zip(c1, c2):
        if abs(p[0]-q[0]) > max_dist or abs(p[1]-q[1]) > max_dist:
            return False
    return True

def target_in_center(cx, cy, corners, margin=0.3):
    """红色目标是否在A4中心区域"""
    if corners is None:
        return True
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    x0, x1 = min(xs), max(xs)
    y0, y1 = min(ys), max(ys)
    cw, ch = x1 - x0, y1 - y0
    # 只接受中心 margin*100% 区域内的目标
    mx = margin * cw / 2
    my = margin * ch / 2
    ccx = (x0 + x1) / 2
    ccy = (y0 + y1) / 2
    return abs(cx - ccx) < cw/2 - mx and abs(cy - ccy) < ch/2 - my

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # ======== A4 黑胶带边框检测 ========
        # 1. 转灰度 + 高斯模糊去噪
        gray = img.to_grayscale(copy=True)
        gray.gaussian(2)                        # 模糊: 降背景纹理干扰

        # 2. 二值化 + 形态学
        bin_img = gray.binary([TAPE_GRAY])
        bin_img.open(3)                         # 开运算: 去小噪点
        bin_img.close(1)                        # 闭运算: 填断线

        # 3. 找矩形 + 过滤
        all_r = bin_img.find_rects(threshold=10000)   # 提高阈值,要明确边缘
        rects = a4_filter_valid(all_r)                # 长宽比+面积过滤

        if rects:
            # 选面积最大的有效矩形
            best = max(rects, key=lambda r: r.w() * r.h())
            new_corners = [(c[0], c[1]) for c in best.corners()]

            # 时间稳定性: 连续稳定才更新
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
                              color=(255,0,0), thickness=3)
            cx_a4 = sum(c[0] for c in a4_corners) // 4
            cy_a4 = sum(c[1] for c in a4_corners) // 4
            img.draw_cross(cx_a4, cy_a4, color=(0,0,255), size=12, thickness=2)

        # ======== 红色靶心检测 ========
        # ROI: 只在A4内部找, 排除边框本身
        if a4_ok and a4_corners:
            xs = [c[0] for c in a4_corners]
            ys = [c[1] for c in a4_corners]
            margin = 8   # 向内缩, 避免黑胶带边沿
            roi = (min(xs)+margin, min(ys)+margin,
                   max(xs)-min(xs)-2*margin, max(ys)-min(ys)-2*margin)
            blobs = img.find_blobs(RED_TARGET, roi=roi,
                                   pixels_threshold=30, merge=True)
        else:
            blobs = img.find_blobs(RED_TARGET, pixels_threshold=80,
                                   merge=True)

        # 过滤: 密度+位置
        target_ok = False
        if blobs:
            for b in sorted(blobs, key=lambda x: x.area(), reverse=True):
                # 密度过滤: 稀疏块多是反光, 不是实心靶心
                if b.density() < 0.35:
                    continue
                # 位置过滤: 必须在A4中央区域
                bx = b.x() + b.w() // 2
                by = b.y() + b.h() // 2
                if a4_ok and not target_in_center(bx, by, a4_corners, 0.35):
                    continue
                # 通过
                target_cx, target_cy = bx, by
                target_ok = True
                img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                   color=(0,255,0), thickness=2)
                img.draw_cross(bx, by, color=(0,255,0), size=10, thickness=2)
                target_ok_cnt += 1
                break

        if not blobs:
            target_ok_cnt = max(0, target_ok_cnt - 1)

        # ======== UI ========
        fps = clock.fps()
        bar_h = 50
        img.draw_rectangle(0, 0, IMG_W, bar_h, color=(0,0,0), thickness=-1, fill=True)
        img.draw_rectangle(0, IMG_H-bar_h, IMG_W, bar_h, color=(0,0,0), thickness=-1, fill=True)

        if a4_ok and target_ok:
            img.draw_string_advanced(5, 5, 35,
                f"A4+RED  {fps:.0f}fps", color=(0,255,0))
        elif a4_ok:
            img.draw_string_advanced(5, 5, 35,
                f"A4 OK   {fps:.0f}fps", color=(255,255,0))
        else:
            img.draw_string_advanced(5, 5, 35,
                f"SEARCH  {fps:.0f}fps", color=(255,0,0))

        # 底部: 显示过滤条件
        stab = f"stb{a4_stable}" if a4_stable < STABLE_FRAMES else "LOCK"
        img.draw_string_advanced(5, IMG_H-bar_h+5, 20,
            f"B:{stab} ratio:{A4_RATIO_MIN}-{A4_RATIO_MAX} dens>0.35",
            color=(180,180,180))

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
