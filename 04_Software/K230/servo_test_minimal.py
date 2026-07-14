"""
最小舵机测试 v2 — 完全照抄07激光笔与舵机控制.py的引脚配置
GPIO33=3.3V高电平  GPIO46=PWM2 舵机信号
07例程确认可用: fpioa.set_function(46, FPIOA.PWM2)
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import FPIOA, Pin, PWM
import time, os

sensor = None

try:
    # ===== 一、FPIOA (照抄07例程) =====
    fpioa = FPIOA()
    fpioa.help()   # 打印所有FPIOA功能, 确认PWM2可用

    # GPIO33 输出高电平 — 照抄07例程
    fpioa.set_function(33, FPIOA.GPIO33)
    pin33 = Pin(33, Pin.OUT)
    pin33.value(1)

    # GPIO46 → PWM2 — 07例程第23行确认可用
    fpioa.set_function(46, FPIOA.PWM2)
    pwm = PWM(2, 50)               # ch2, 50Hz
    pwm.duty(1.5 / 20 * 100)       # 1.5ms → 居中
    pwm.enable(1)

    print("舵机初始化: GPIO33=3.3V  GPIO46=PWM2 50Hz")
    print("0°→180°来回扫描...")

    # ===== 二、摄像头 =====
    sensor = Sensor(width=1920, height=1080)
    sensor.reset()
    sensor.set_framesize(width=320, height=240)
    sensor.set_pixformat(Sensor.RGB565)
    Display.init(Display.ST7701, to_ide=True, width=800, height=480)
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    angle = 90
    direction = 1

    while True:
        os.exitpoint()
        clock.tick()

        # 角度 0°→180° 来回扫描, 每次 ±2°
        angle = angle + direction * 2
        if angle >= 180:
            angle = 180; direction = -1
        elif angle <= 0:
            angle = 0; direction = 1

        # duty = (0.5 + angle*2/180) / 20 * 100
        duty = round((0.5 + angle * 2.0 / 180) / 20 * 100, 1)
        pwm.duty(duty)
        print("%d deg -> %.1f%%" % (angle, duty))

        # 显示状态
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        img.draw_string_advanced(10, 10, 20,
                                 "Servo:%d deg" % angle, color=(0,255,0))
        img.draw_string_advanced(10, 40, 15,
                                 "GPIO33=3.3V GPIO46=PWM2", color=(255,200,0))
        img.draw_string_advanced(10, 60, 15,
                                 "duty=%.1f%%" % duty, color=(255,200,0))

        if img.height() > 480 or img.width() > 800:
            scale = max(img.height()//480, img.width()//800) + 1
            img.midpoint_pool(scale, scale)
        img.compress_for_ide()
        Display.show_image(img, x=(800-img.width())//2, y=(480-img.height())//2)

        time.sleep_ms(50)   # 50ms × 2° = ~40°/s

except KeyboardInterrupt:
    print("用户停止")
except BaseException as e:
    print("异常: %s" % str(e))
finally:
    if sensor is not None:
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完成")
