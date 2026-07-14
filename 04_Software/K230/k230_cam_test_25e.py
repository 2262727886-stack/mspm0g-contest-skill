"""K230 摄像头最简测试 — 验证 GC2093 是否正常出图"""
from media.sensor import *
from media.display import *
from media.media import *
import time, os, gc

# 1. 清理残留
try:
    MediaManager.deinit()
    time.sleep_ms(300)
except:
    pass

# 2. 摄像头初始化
print("init sensor...")
sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=320, height=240)  # QVGA
sensor.set_pixformat(Sensor.RGB565)
print("init display...")
Display.init(Display.VIRT, width=640, height=480, to_ide=True)
print("init media...")
MediaManager.init()
print("run sensor...")
sensor.run()
time.sleep_ms(500)  # 等第一帧就绪
print("OK, entering loop...")

# 3. 主循环: 只抓帧+显示
fc = 0
clock = time.clock()
while True:
    os.exitpoint()
    clock.tick()
    fc += 1

    img = sensor.snapshot()
    # 画帧号
    img.draw_string_advanced(10, 10, 32, str(fc), color=(0, 255, 0))
    Display.show_image(img)

    if fc % 100 == 0:
        print("FPS: %d  frame: %d" % (clock.fps(), fc))
        gc.collect()
