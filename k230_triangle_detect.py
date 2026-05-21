"""
K230 三角形检测 — 诊断 v2
=========================
修复: 去掉显式 chn=CAM_CHN_ID_0, 用默认通道
诊断: STAGE 0→4 逐步叠加, 定位崩溃点
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

PW, PH = 400, 240
DW, DH = 800, 480
ox = (DW - PW) // 2
oy = (DH - PH) // 2

STAGE = 0  # 0=纯显示 1=只snapshot 2=+blob 3=+rect 4=+三角
THRESHOLD = [(20, 100, 15, 127, -20, 80)]

print("=== 诊断 Stage=%d ===" % STAGE)

sensor = Sensor(id=2)
sensor.reset()
# ⚠️ 不传 chn, 用默认通道 CAM_CHN_ID_0
sensor.set_framesize(width=PW, height=PH)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.ST7701, width=DW, height=DH)
MediaManager.init()
sensor.run()

# 稳定期
for _ in range(10):
    sensor.snapshot()
    time.sleep_ms(50)

clock = time.clock()
fc = 0
print("启动 OK, Stage=%d (0=显示 1=抓帧 2=blob 3=rect 4=三角)" % STAGE)

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        # ⚠️ 不传 chn, 用默认
        img = sensor.snapshot()

        if STAGE == 0:
            # 纯显示, 零处理
            pass

        elif STAGE >= 1:
            # 画个十字确认抓到帧
            img.draw_cross(PW//2, PH//2, color=(0, 255, 0), size=20)

        blobs = None
        rects = None
        tris = []

        if STAGE >= 2:
            blobs = img.find_blobs(THRESHOLD, pixels_threshold=20,
                                   area_threshold=100, merge=True, margin=5)
            if blobs:
                for b in blobs:
                    if b.w() * b.h() >= 200:
                        img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                                           color=(255, 200, 0), thickness=1)

        if STAGE >= 3:
            rects = img.find_rects(threshold=5000)

        if STAGE >= 4 and rects:
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
                    ok = True
                    if blobs:
                        ok = False
                        for b in blobs:
                            if b.x()<=cx<=b.x()+b.w() and b.y()<=cy<=b.y()+b.h():
                                ok = True; break
                    if ok:
                        tris.append((cx, cy, r.x(), r.y(), r.w(), r.h()))

        # 画三角形
        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            c = (0, 255, 0) if i == 0 else (200, 120, 0)
            img.draw_rectangle(x, y, w, h, color=c, thickness=2)
            img.draw_cross(cx, cy, color=(0, 255, 0), size=14)

        # 状态栏
        parts = ["S%d" % STAGE]
        if STAGE >= 2 and blobs is not None:
            parts.append("B:%d" % len(blobs))
        if STAGE >= 3 and rects is not None:
            parts.append("R:%d" % len(rects))
        if STAGE >= 4:
            parts.append("T:%d" % len(tris))
        parts.append("FPS:%d" % max(1, clock.fps()))
        img.draw_string_advanced(4, 4, 16, " ".join(parts), color=(0, 255, 0))

        Display.show_image(img, x=ox, y=oy)

        if fc % 80 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\n中断")
except BaseException as e:
    print("Stage%d 崩溃: %s" % (STAGE, str(e)))
    import sys
    sys.print_exception(e)
finally:
    sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完成")
