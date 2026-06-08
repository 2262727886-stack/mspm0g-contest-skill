"""
K230 庐山派 MIPI 3.1寸屏 触摸+背光测试
  基于 14_脱机调整阈值.py 的 TOUCH(0) API
  显示: MIPI DSI ST7701 800x480
  触控: machine.TOUCH(0)  ← 官方 API, 不是裸 I2C
  背光: GP7101 I2C→PWM
"""

from media.sensor import *
from media.display import *
from media.media import *
from machine import TOUCH, I2C
import time, os, gc, image

# ===== 一、配置 =====
LCD_W, LCD_H = 800, 480
BL_BRIGHTNESS = 80
GP7101_ADDR = 0x58

# ===== 二、Sensor + Display 初始化 =====
print("初始化 Sensor + Display...")
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=800, height=480)   # 与屏幕同宽, 铺满不挤压
sensor.set_pixformat(Sensor.RGB565)

Display.init(Display.ST7701, to_ide=True, width=800, height=480)
MediaManager.init()
sensor.run()
print("  屏幕: 800x480 ST7701 MIPI DSI")

# ===== 三、TOUCH 触摸屏初始化 =====
print("\n初始化触摸屏...")
tp = TOUCH(0)
print("  TOUCH(0) 初始化完成")

# ===== 四、GP7101 背光 (I2C) =====
print("\n扫描 I2C 背光...")
gp7101_ok = False
for bus in [3, 1, 2, 4, 0]:
    try:
        i2c = I2C(bus, freq=400000)
        devs = i2c.scan()
        if GP7101_ADDR in devs:
            print("  I2C%d 找到 GP7101 @ %s" % (bus, hex(GP7101_ADDR)))
            gp7101_ok = True
            break
    except Exception:
        pass

if gp7101_ok:
    try:
        prescaler = max(1, min(255, 6000000 // (1000 * 256)))
        i2c.writeto(GP7101_ADDR, bytes([0x00, 0x00, prescaler]))
        time.sleep_us(200)
        duty = int(BL_BRIGHTNESS * 4095 / 100)
        i2c.writeto(GP7101_ADDR, bytes([0x02, (duty >> 8) & 0xFF, duty & 0xFF]))
        print("  背光: %d%%" % BL_BRIGHTNESS)
    except OSError as e:
        print("  背光配置失败: %s" % e)
else:
    print("  未找到 GP7101, 背光常亮")

# ===== 五、显示辅助函数 =====
def show_img(img):
    """自动缩放并居中显示 (与例程 14 同款)"""
    if img.height() > 480 or img.width() > 800:
        scale = max(img.height() // 480, img.width() // 800) + 1
        img.midpoint_pool(scale, scale)
    img.compress_for_ide()
    Display.show_image(img, x=(800 - img.width()) // 2, y=(480 - img.height()) // 2)

# ===== 六、主循环 =====
print("\n" + "=" * 50)
print("触摸屏测试  800x480  ST7701")
print("触摸: TOUCH(0) API")
print("=" * 50)

clock = time.clock()
trail = []
last_touch = False
fc = 0
cx, cy = LCD_W // 2, LCD_H // 2

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        # 创建 800x480 画布 (匹配屏幕, 触摸坐标直接对应)
        img = image.Image(LCD_W, LCD_H, image.RGB565)

        # --- 读触摸 (官方 API, 返回屏幕坐标 0-800, 0-480) ---
        points = tp.read()
        has_touch = len(points) > 0

        # --- 轨迹 ---
        if has_touch:
            x, y = points[0].x, points[0].y
            trail.append((x, y))
            if len(trail) > 80:
                trail.pop(0)
        elif last_touch:
            trail.clear()
        last_touch = has_touch

        # --- 绘制 ---
        # 网格
        img.draw_line(cx, 0, cx, LCD_H, color=(0, 50, 0), thickness=1)
        img.draw_line(0, cy, LCD_W, cy, color=(0, 50, 0), thickness=1)
        img.draw_rectangle(0, 0, LCD_W, LCD_H, color=(0, 40, 0), thickness=1)

        # 轨迹
        n = len(trail)
        for i in range(n - 1):
            r = max(0, 255 - i * (200 // max(n, 1)))
            g = min(255, i * (200 // max(n, 1)) + 55)
            img.draw_line(trail[i][0], trail[i][1],
                          trail[i+1][0], trail[i+1][1],
                          color=(r, g, 130), thickness=3)

        # 触摸点 (坐标与画布一致, 无需映射)
        if has_touch:
            for i, p in enumerate(points):
                sz = 20
                img.draw_cross(p.x, p.y, color=(255, 30, 30), size=sz, thickness=3)
                img.draw_circle(p.x, p.y, sz + 4, color=(255, 80, 80), thickness=2)
                info = "P%d:(%d,%d)" % (i, p.x, p.y)
                img.draw_string_advanced(4, LCD_H - 18 - i * 18, 14,
                                         info, color=(255, 255, 0))

        # 状态栏
        img.draw_rectangle(0, 0, LCD_W, 24, color=(0, 0, 0), fill=True)
        status = "TOUCH:%dpts" % len(points) if has_touch else "NO TOUCH"
        info = "%s  BL:%d%%  FPS:%d" % (status, BL_BRIGHTNESS, clock.fps())
        img.draw_string_advanced(4, 3, 18, info, color=(0, 220, 0))

        show_img(img)

        if fc % 300 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\n用户停止")
except BaseException as e:
    print("错误: %s" % e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("测试结束")
