"""
K230 三角形识别 — 最小可实现单元
================================
800x480 全屏, 原地操作, 零额外内存分配
算法: blob颜色 → 原地灰度 → 原地二值 → find_rects → 短边筛选 → 重心验证

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
# 二、三角形检测 (原地操作, 不创建任何图像副本)
# ============================================================

def find_triangles(img, threshold, min_area=500, edge_ratio=0.25):
    """
    在 img 上原地检测三角形.
    ⚠️ 会修改 img: RGB565 → GRAYSCALE → BINARY
    返回 [(cx, cy, x, y, w, h), ...]
    """
    # Step 1: 颜色blob (RGB565阶段, 先做)
    blobs = img.find_blobs(threshold, pixels_threshold=50,
                           area_threshold=400, merge=True, margin=10)
    L_lo = threshold[0][0]
    L_hi = threshold[0][1]

    # Step 2: 原地灰度 (RGB565 → GRAYSCALE, 不分配新内存)
    img.to_grayscale()

    # Step 3: 原地二值 (GRAYSCALE → BINARY, 不分配新内存)
    img.binary([(L_lo, L_hi)])
    img.open(1)

    # Step 4: 四边形检测
    quads = img.find_rects(threshold=5000)
    if not quads:
        return []

    # Step 5: 短边筛选 + 颜色验证
    result = []
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

        cx = sum(p[0] for p in c) // 4
        cy = sum(p[1] for p in c) // 4

        if blobs:
            ok = False
            for b in blobs:
                if b.x() <= cx <= b.x()+b.w() and b.y() <= cy <= b.y()+b.h():
                    ok = True
                    break
            if not ok:
                continue

        if r.w() * r.h() >= min_area:
            result.append((cx, cy, r.x(), r.y(), r.w(), r.h()))

    result.sort(key=lambda t: t[5]*t[6], reverse=True)
    return result


# ============================================================
# 三、初始化
# ============================================================

print("=== K230 三角形检测 ===")

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=800, height=480)   # 全屏, 与LCD同尺寸
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

        # 检测 (原地修改 img: RGB→灰度→二值)
        tris = find_triangles(img, THRESHOLD)

        # 画结果
        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            c = 255 if i == 0 else 200
            img.draw_rectangle(x, y, w, h, color=c, thickness=2)
            img.draw_cross(cx, cy, color=c, size=16)
            img.draw_string_advanced(cx+18, cy-8, 16, "T%d"%(i+1), color=c)

        if tris:
            s = "Tri x%d (%d,%d)" % (len(tris), tris[0][0], tris[0][1])
            img.draw_string_advanced(10, 10, 22, s, color=255)
        else:
            img.draw_string_advanced(10, 10, 22, "No Triangle", color=200)

        fps_s = "FPS:%d" % max(1, clock.fps())
        img.draw_string_advanced(680, 10, 18, fps_s, color=220)

        Display.show_image(img)

        if fc % 100 == 0:
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
