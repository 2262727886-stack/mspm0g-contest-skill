"""K230 摄像头物理屏测试 — ST7701 MIPI 屏 800x480 直出"""
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

# 2. 初始化
print("init sensor...")
sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=800, height=480)   # 匹配 ST7701 物理屏
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

print("init display ST7701...")
Display.init(Display.ST7701, width=800, height=480)  # 物理屏, 不加 to_ide

print("init media...")
MediaManager.init()

print("run sensor...")
sensor.run()
time.sleep_ms(500)

print("OK — screen should show camera + red crosshair")
clock = time.clock()
fc = 0

while True:
    os.exitpoint()
    clock.tick()
    fc += 1

    img = sensor.snapshot()

    # 画面中央红色十字
    img.draw_cross(400, 240, color=(255, 0, 0), size=40, thickness=3)
    # 左上角帧号
    img.draw_string_advanced(10, 10, 28, str(fc), color=(0, 255, 0))

    Display.show_image(img)

    if fc % 100 == 0:
        print("FPS: %d  mem: %d" % (clock.fps(), gc.mem_free()))
        gc.collect()
