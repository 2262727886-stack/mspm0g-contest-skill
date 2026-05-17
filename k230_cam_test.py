"""
K230 摄像头测试 — A4黑框 + 红色靶心检测
基于已验证的初始化顺序
"""
from media.sensor import *
from media.display import *
from media.media import *
import time, os, gc

# ===== 一、初始化 (顺序不可变) =====
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=640, height=480)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.VIRT, width=640, height=480, to_ide=True)
MediaManager.init()
sensor.run()

# ===== 二、阈值 (现场用 IDE 阈值编辑器校准) =====
TAPE_GRAY = (0, 109)       # 黑胶带灰度
RED_TARGET = [(52,100,24,127,-49,41),
              (29,73,19,127,-57,89)]

# ===== 三、检测变量 =====
a4_corners = None
a4_ok = False
clock = time.clock()
fc = 0

print("初始化完成, 开始检测...")

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # ---- A4 黑胶带边框 ----
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([TAPE_GRAY])
        bin_img.open(2)
        all_r = bin_img.find_rects(threshold=8000)
        min_a = img.width() * img.height() * 0.03
        rects = [r for r in all_r if r.w() * r.h() > min_a]

        if rects:
            a4_ok = True
            if len(rects) == 2:
                c1, c2 = rects[0].corners(), rects[1].corners()
                a4_corners = []
                for p in c1:
                    ds = [(p[0]-q[0])**2+(p[1]-q[1])**2 for q in c2]
                    n = ds.index(min(ds))
                    a4_corners.append(((p[0]+c2[n][0])//2, (p[1]+c2[n][1])//2))
            else:
                a4_corners = [(c[0], c[1]) for c in rects[0].corners()]
        else:
            a4_ok = False

        # 画 A4 边框 + 中心
        if a4_ok:
            for i in range(4):
                img.draw_line(a4_corners[i][0], a4_corners[i][1],
                              a4_corners[(i+1)%4][0], a4_corners[(i+1)%4][1],
                              color=(255,0,0), thickness=3)
            cx_a4 = sum(c[0] for c in a4_corners) // 4
            cy_a4 = sum(c[1] for c in a4_corners) // 4
            img.draw_cross(cx_a4, cy_a4, color=(0,0,255), size=15, thickness=2)

        # ---- 红色靶心 ----
        if a4_ok:
            xs = [c[0] for c in a4_corners]
            ys = [c[1] for c in a4_corners]
            blobs = img.find_blobs(RED_TARGET,
                                   roi=(min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)),
                                   pixels_threshold=50, merge=True)
        else:
            blobs = img.find_blobs(RED_TARGET, pixels_threshold=50, merge=True)

        if blobs:
            b = blobs[0]
            img.draw_rectangle(b.x(), b.y(), b.w(), b.h(),
                               color=(0,255,0), thickness=2)
            img.draw_cross(b.x()+b.w()//2, b.y()+b.h()//2,
                           color=(0,255,0), size=10, thickness=2)

        # ---- UI 叠加 ----
        fps = clock.fps()
        w, h = img.width(), img.height()
        bar_h = 50
        img.draw_rectangle(0, 0, w, bar_h, color=(0,0,0), thickness=-1, fill=True)
        img.draw_rectangle(0, h-bar_h, w, bar_h, color=(0,0,0), thickness=-1, fill=True)

        if a4_ok and blobs:
            img.draw_string_advanced(5, 5, 35,
                f"A4+RED  {fps:.0f}fps", color=(0,255,0))
        elif a4_ok:
            img.draw_string_advanced(5, 5, 35,
                f"A4 OK   {fps:.0f}fps", color=(255,255,0))
        else:
            img.draw_string_advanced(5, 5, 35,
                f"SEARCH  {fps:.0f}fps", color=(255,0,0))
        img.draw_string_advanced(5, h-bar_h+5, 20,
            f"TAPE:{TAPE_GRAY}  RED:2groups", color=(180,180,180))

        Display.show_image(img)

        if fc % 200 == 0:
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
