"""
K230 三角形识别 — 最小可实现单元
================================
算法: find_blobs(LAB颜色) → 逐blob裁剪ROI → ROI内几何检测 → 短边筛选
关键: 几何检测仅在颜色确认的blob区域内进行, 背景区域不参与

硬件: 庐山派 K230 + GC2093 + MIPI ST7701
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

# ============================================================
# 一、阈值
# ============================================================

THRESHOLD = [(20, 100, 15, 127, -20, 80)]

# ============================================================
# 二、三角形检测 (逐blob ROI, 背景不参与几何检测)
# ============================================================

def find_triangles(img, threshold, min_area=500, edge_ratio=0.25):
    """
    返回 [(cx, cy, x, y, w, h), ...] — 全图坐标
    策略: find_blobs → 每个blob裁剪ROI → ROI内几何检测 → 坐标还原
    背景区域完全不参与 find_rects, 从根本上消除背景误检
    """
    L_lo = threshold[0][0]
    L_hi = threshold[0][1]

    # Step 1: 颜色blob (全图, RGB565)
    blobs = img.find_blobs(threshold, pixels_threshold=50,
                           area_threshold=400, merge=True, margin=10)
    if not blobs:
        return []

    result = []

    # Step 2: 逐blob处理 — 只在颜色区域做几何检测
    for b in blobs:
        bx, by = b.x(), b.y()
        bw, bh = b.w(), b.h()

        # 面积过滤
        if bw * bh < min_area:
            continue

        # 裁剪 ROI (仅blob区域, 通常 < 100KB, 远小于全帧768KB)
        try:
            roi = img.copy(roi=(bx, by, bw, bh))
        except:
            continue  # ROI 裁剪失败则跳过此blob

        # ROI内: 灰度 → 二值 → find_rects
        roi.to_grayscale()
        roi.binary([(L_lo, L_hi)])
        roi.open(1)

        quads = roi.find_rects(threshold=max(500, bw * bh // 20))
        if not quads:
            continue

        # Step 3: ROI内短边筛选 → 三角形候选
        for r in quads:
            c = r.corners()
            if len(c) != 4:
                continue

            e = []
            for i in range(4):
                dx = c[i][0] - c[(i+1)%4][0]
                dy = c[i][1] - c[(i+1)%4][1]
                e.append(math.sqrt(dx*dx + dy*dy))

            mx, mn = max(e), min(e)
            if mx == 0 or mn/mx >= edge_ratio:
                continue

            # ROI坐标 → 全图坐标
            cx = bx + sum(p[0] for p in c) // 4
            cy = by + sum(p[1] for p in c) // 4
            rx = bx + r.x()
            ry = by + r.y()
            rw = r.w()
            rh = r.h()

            if rw * rh >= min_area:
                result.append((cx, cy, rx, ry, rw, rh))

    result.sort(key=lambda t: t[5]*t[6], reverse=True)
    return result


# ============================================================
# 三、初始化
# ============================================================

print("=== K230 三角形检测 ===")
print("算法: blob颜色ROI → 逐ROI几何检测 → 短边筛选")

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=800, height=480)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.ST7701, width=800, height=480, to_ide=True)
MediaManager.init()
sensor.run()

clock = time.clock()
fc = 0

# ============================================================
# 四、主循环
# ============================================================

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # 检测 (img 保持 RGB565, 不被修改)
        tris = find_triangles(img, THRESHOLD)

        # 画结果
        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            color = (0, 255, 0) if i == 0 else (255, 165, 0)
            img.draw_rectangle(x, y, w, h, color=color, thickness=3)
            img.draw_cross(cx, cy, color=(0, 255, 0), size=18)
            img.draw_string_advanced(cx + 22, cy - 10, 18,
                                     "T%d" % (i + 1), color=(0, 255, 0))

        # 也画出所有blob (辅助调试)
        blobs = img.find_blobs(THRESHOLD, pixels_threshold=50,
                               area_threshold=400, merge=True, margin=10)
        if blobs:
            for b in blobs:
                img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                   color=(255, 255, 0), thickness=1)

        if tris:
            s = "Tri x%d (%d,%d)" % (len(tris), tris[0][0], tris[0][1])
            img.draw_string_advanced(10, 10, 24, s, color=(0, 255, 0))
        else:
            img.draw_string_advanced(10, 10, 24, "No Triangle",
                                     color=(255, 100, 100))

        fps_s = "FPS:%d" % max(1, clock.fps())
        img.draw_string_advanced(700, 10, 18, fps_s, color=(180, 180, 180))

        Display.show_image(img)

        if fc % 80 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\n中断")
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
