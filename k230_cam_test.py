"""
K230 摄像头最小测试 — 严格按已验证的初始化顺序
"""
from media.sensor import *
from media.display import *
from media.media import *
import time, os

print("1/7 创建Sensor...")
sensor = Sensor(width=1920, height=1080)

print("2/7 reset...")
sensor.reset()

print("3/7 set_framesize...")
sensor.set_framesize(width=640, height=480)

print("4/7 set_pixformat...")
sensor.set_pixformat(Sensor.RGB565)

print("5/7 Display.init...")
Display.init(Display.VIRT, width=640, height=480, to_ide=True)

print("6/7 MediaManager.init...")
MediaManager.init()

print("7/7 sensor.run...")
sensor.run()

print("=== 进入主循环 ===")
clock = time.clock()

try:
    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        fps = clock.fps()
        img.draw_string_advanced(10, 10, 40,
            f"K230 {fps:.0f}fps", color=(0,255,0))

        Display.show_image(img)

        if int(time.ticks_ms()) % 2000 < 10:
            print(f"fps={fps:.0f}")

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
