"""
K230 三角形识别 — 最小可实现单元
================================
算法: blob颜色 → 原地灰度二值 → 逐blob用 find_rects(roi=...) → 短边筛选
零 copy: find_rects 自带 roi 参数限定检测区域, 背景不参与, 无额外内存

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
# 二、三角形检测 (零copy: find_rects roi参数限定区域)
# ============================================================

def find_triangles(img, blob_regions, threshold, min_area=80, edge_ratio=0.25):
    """
    在 img 上原地检测三角形 (img: RGB565 → GRAYSCALE → BINARY).
    blob_regions: 预检测的 [(x,y,w,h), ...] 颜色区域列表.
    零 copy: 用 find_rects(roi=blob区域) 限定检测范围.
    返回 [(cx, cy, x, y, w, h), ...]
    """
    L_lo = threshold[0][0]
    L_hi = threshold[0][1]

    if not blob_regions:
        return []

    # Step 2: 原地灰度 + 二值 (全帧, 0额外内存)
    img.to_grayscale()
    img.binary([(L_lo, L_hi)])
    # img.open(1) — 省略以节省 fast frame buffer stack

    # Step 3: 逐blob区域做几何检测 (用 find_rects 自带 roi, 零copy)
    result = []
    for (bx, by, bw, bh) in blob_regions[:8]:  # 最多8个blob
        quads = img.find_rects(roi=(bx, by, bw, bh),
                               threshold=max(100, bw * bh // 15))
        if not quads:
            continue

        for r in quads:
            c = r.corners()
            if len(c) != 4:
                continue

            # 4边长度
            e = []
            for i in range(4):
                dx = c[i][0] - c[(i+1)%4][0]
                dy = c[i][1] - c[(i+1)%4][1]
                e.append(math.sqrt(dx*dx + dy*dy))

            mx, mn = max(e), min(e)
            if mx == 0 or mn/mx >= edge_ratio:
                continue

            # 重心 (ROI内坐标即全图坐标, find_rects返回绝对坐标)
            cx = sum(p[0] for p in c) // 4
            cy = sum(p[1] for p in c) // 4
            rx, ry = r.x(), r.y()
            rw, rh = r.w(), r.h()

            if rw * rh >= min_area:
                result.append((cx, cy, rx, ry, rw, rh))

    result.sort(key=lambda t: t[5]*t[6], reverse=True)
    return result


# ============================================================
# 三、初始化
# ============================================================

print("=== K230 三角形检测 ===")
print("算法: blob→灰度二值→find_rects(roi=blob)  零copy")

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=320, height=240)  # QVGA: to_grayscale不崩溃
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

        # 一次 find_blobs: 画黄框 + 收集区域 (RGB565状态)
        blobs = img.find_blobs(THRESHOLD, pixels_threshold=10,
                               area_threshold=60, merge=True, margin=5)
        blob_regions = []
        if blobs:
            for b in blobs:
                if b.w() * b.h() >= 80:
                    blob_regions.append((b.x(), b.y(), b.w(), b.h()))
                    img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                       color=(255, 200, 0), thickness=1)

        # 三角形检测 (会修改 img 为灰度→二值, 用 roi 参数限定范围)
        tris = find_triangles(img, blob_regions, THRESHOLD)

        # 画三角形 (在二值图上用白色画)
        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            c = 255 if i == 0 else 200
            img.draw_rectangle(x, y, w, h, color=c, thickness=1)
            img.draw_cross(cx, cy, color=c, size=10)
            img.draw_string_advanced(cx+12, cy-6, 12, "T%d"%(i+1), color=c)

        if tris:
            s = "Tri x%d (%d,%d)" % (len(tris), tris[0][0], tris[0][1])
            img.draw_string_advanced(4, 4, 14, s, color=255)
        else:
            img.draw_string_advanced(4, 4, 14, "No Triangle", color=200)

        info = "blob:%d FPS:%d" % (len(blob_regions), max(1, clock.fps()))
        img.draw_string_advanced(4, 20, 12, info, color=160)

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
