"""
K230 三角形识别 — 复刻 LCKFB 官方 find_rects 例程
================================
完全参照 https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-feature-detect.html
逐步叠加: 基础find_rects → blob颜色过滤 → 短边三角筛选
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

PW, PH = 400, 240          # 官方例程分辨率
DW, DH = 800, 480
ox = (DW - PW) // 2
oy = (DH - PH) // 2

THRESHOLD = [(20, 100, 15, 127, -20, 80)]

# ============================================================
print("=== K230 三角形检测 (官方例程复刻) ===")

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

# ============================================================
try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # ---- 第1步: 颜色blob (仅一次) ----
        blobs = img.find_blobs(THRESHOLD, pixels_threshold=20,
                               area_threshold=100, merge=True, margin=5)

        # ---- 第2步: 全图找四边形 + 短边筛选 ----
        rects = img.find_rects(threshold=5000)  # 官方例程, 无roi
        tris = []
        if rects:
            for r in rects:
                c = r.corners()
                if len(c) != 4:
                    continue
                e = []
                for i in range(4):
                    dx = c[i][0] - c[(i+1)%4][0]
                    dy = c[i][1] - c[(i+1)%4][1]
                    e.append(math.sqrt(dx*dx + dy*dy))
                mx, mn = max(e), min(e)
                if mx > 0 and mn/mx < 0.25 and r.w()*r.h() >= 200:
                    cx = sum(p[0] for p in c) // 4
                    cy = sum(p[1] for p in c) // 4
                    # 颜色验证
                    ok = True
                    if blobs:
                        ok = False
                        for b in blobs:
                            if (b.x() <= cx <= b.x()+b.w() and
                                b.y() <= cy <= b.y()+b.h()):
                                ok = True
                                break
                    if ok:
                        tris.append((cx, cy, r.x(), r.y(), r.w(), r.h()))

        # ---- 第3步: 画图 ----
        if blobs:
            for b in blobs:
                if b.w()*b.h() >= 200:
                    img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                       color=(255, 200, 0), thickness=1)

        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            c = (0, 255, 0) if i == 0 else (200, 120, 0)
            img.draw_rectangle(x, y, w, h, color=c, thickness=2)
            img.draw_cross(cx, cy, color=(0, 255, 0), size=14)
            img.draw_string_advanced(cx+16, cy-8, 14, "T%d"%(i+1), color=c)

        if tris:
            img.draw_string_advanced(4, 4, 16,
                "Tri x%d" % len(tris), color=(0,255,0))
        else:
            img.draw_string_advanced(4, 4, 16, "NoTri", color=(255,100,100))

        img.draw_string_advanced(4, 22, 14,
            "FPS:%d" % max(1,clock.fps()), color=200)

        Display.show_image(img, x=ox, y=oy)

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
