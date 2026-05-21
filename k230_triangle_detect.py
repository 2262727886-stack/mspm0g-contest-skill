"""
K230 三角形检测 — 逐步排查版
============================
诊断 fast frame buffer stack OOM: 逐步叠加功能定位崩溃点
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

PW, PH = 400, 240
DW, DH = 800, 480
ox = (DW - PW) // 2
oy = (DH - PH) // 2

# === 诊断开关: 逐步开启 ===
STAGE = 4                     # 1=纯显示 2=+blob 3=+rect 4=+三角筛选
THRESHOLD = [(20, 100, 15, 127, -20, 80)]

print("=== 诊断模式 Stage=%d ===" % STAGE)

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=PW, height=PH, chn=CAM_CHN_ID_0)
sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
sensor.set_hmirror(False)
sensor.set_vflip(False)

# ⚠️ 去掉 to_ide=True, 省一个 IDE 回传 buffer
Display.init(Display.ST7701, width=DW, height=DH)
MediaManager.init()
sensor.run()

# 让系统稳定
for _ in range(10):
    sensor.snapshot(chn=CAM_CHN_ID_0)
    time.sleep_ms(50)

clock = time.clock()
fc = 0

print("启动 OK, Stage=%d" % STAGE)

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        if STAGE >= 2:
            # ---- blob ----
            blobs = img.find_blobs(THRESHOLD, pixels_threshold=20,
                                   area_threshold=100, merge=True, margin=5)
            if blobs:
                for b in blobs:
                    if b.w()*b.h() >= 200:
                        img.draw_rectangle(b.x(),b.y(),b.w(),b.h(),
                                           color=(255,200,0), thickness=1)

        tris = []
        if STAGE >= 3:
            # ---- find_rects (官方例程, 全图) ----
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
                        cx = sum(p[0] for p in c)//4
                        cy = sum(p[1] for p in c)//4
                        if STAGE >= 4:
                            ok = True
                            if blobs:
                                ok = False
                                for b in blobs:
                                    if b.x()<=cx<=b.x()+b.w() and b.y()<=cy<=b.y()+b.h():
                                        ok = True; break
                            if ok:
                                tris.append((cx,cy,r.x(),r.y(),r.w(),r.h()))
            elif STAGE == 3 and rects:
                # Stage3: 画所有四边形
                for r in rects:
                    img.draw_rectangle(r.x(),r.y(),r.w(),r.h(),
                                       color=(0,255,0), thickness=2)

        # ---- 画三角形 ----
        for i, (cx,cy,x,y,w,h) in enumerate(tris):
            c = (0,255,0) if i==0 else (200,120,0)
            img.draw_rectangle(x,y,w,h, color=c, thickness=2)
            img.draw_cross(cx,cy, color=(0,255,0), size=14)

        # ---- 状态 ----
        s = "S%d " % STAGE
        if STAGE >= 4:
            s += "Tri:%d" % len(tris)
        elif STAGE == 3:
            s += "Rect:%d" % (len(rects) if rects else 0)
        elif STAGE >= 2:
            s += "Blob:%d" % (len(blobs) if blobs else 0)
        s += " FPS:%d" % max(1, clock.fps())
        img.draw_string_advanced(4, 4, 16, s, color=(0,255,0))

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
