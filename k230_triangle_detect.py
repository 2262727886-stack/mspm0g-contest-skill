"""
K230 三角形识别 — 最小可实现单元
================================
参照 LCKFB 官方特征检测例程: find_rects 直接跑在 RGB565 上, 无需灰度/二值化
算法: find_blobs(颜色区域) → 逐blob find_rects(roi=blob, RGB565直检) → 短边筛选

硬件: 庐山派 K230 + GC2093 + MIPI ST7701
参考: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-feature-detect.html
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

# ============================================================
# 一、阈值
# ============================================================

THRESHOLD = [(20, 100, 15, 127, -20, 80)]

PW, PH = 640, 480          # 摄像头分辨率
DW, DH = 800, 480          # 显示屏分辨率

# ============================================================
# 二、三角形检测 (RGB565 直检, 零色彩转换)
# ============================================================

def find_triangles(img, threshold, min_area=500, edge_ratio=0.25):
    """
    在 RGB565 图像上检测三角形.
    ⚠️ 不调用 to_grayscale/binary — find_rects 原生支持 RGB565.
    返回 [(cx, cy, x, y, w, h), ...]
    """
    # Step 1: 颜色blob (RGB565)
    blobs = img.find_blobs(threshold, pixels_threshold=50,
                           area_threshold=400, merge=True, margin=10)

    result = []
    for b in blobs:
        bx, by = b.x(), b.y()
        bw, bh = b.w(), b.h()
        if bw * bh < min_area:
            continue

        # Step 2: find_rects 直接在 RGB565 的 blob 区域内检测 (零色彩转换!)
        quads = img.find_rects(roi=(bx, by, bw, bh),
                               threshold=max(500, bw * bh // 20))
        if not quads:
            continue

        # Step 3: 短边筛选
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
            if r.w() * r.h() >= min_area:
                result.append((cx, cy, r.x(), r.y(), r.w(), r.h()))

    result.sort(key=lambda t: t[5]*t[6], reverse=True)
    return result


# ============================================================
# 三、初始化
# ============================================================

print("=== K230 三角形检测 ===")
print("参照: LCKFB 官方 find_rects RGB565 直检, 零灰度转换")

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=PW, height=PH, chn=CAM_CHN_ID_0)
sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.ST7701, width=DW, height=DH, to_ide=True)
MediaManager.init()
sensor.run()

clock = time.clock()
fc = 0

# 显示居中偏移
ox = (DW - PW) // 2
oy = (DH - PH) // 2

# ============================================================
# 四、主循环
# ============================================================

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        # img 始终保持 RGB565, 不被修改

        # --- 找颜色区域 (黄框) ---
        blobs = img.find_blobs(THRESHOLD, pixels_threshold=50,
                               area_threshold=400, merge=True, margin=10)
        if blobs:
            for b in blobs:
                if b.w() * b.h() >= 500:
                    img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                       color=(255, 200, 0), thickness=2)

        # --- 三角形检测 (直接在 RGB565 上) ---
        tris = find_triangles(img, THRESHOLD)

        # --- 画三角形 ---
        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            color = (0, 255, 0) if i == 0 else (255, 165, 0)
            img.draw_rectangle(x, y, w, h, color=color, thickness=3)
            img.draw_cross(cx, cy, color=(0, 255, 0), size=20)
            img.draw_string_advanced(cx + 24, cy - 12, 20,
                                     "T%d" % (i + 1), color=(0, 255, 0))

        # --- 状态 ---
        if tris:
            s = "Tri x%d (%d,%d)" % (len(tris), tris[0][0], tris[0][1])
            img.draw_string_advanced(10, 10, 28, s, color=(0, 255, 0))
        else:
            img.draw_string_advanced(10, 10, 28, "No Triangle",
                                     color=(255, 100, 100))

        s2 = "blob:%d FPS:%d" % (len(blobs) if blobs else 0, max(1, clock.fps()))
        img.draw_string_advanced(10, 44, 20, s2, color=(200, 200, 200))

        # 居中显示
        Display.show_image(img, x=ox, y=oy)

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
