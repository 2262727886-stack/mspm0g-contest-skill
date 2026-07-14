"""
K230 摄像头诊断脚本
依次尝试不同的 Sensor 初始化方式, 找出可用配置
"""
from media.sensor import Sensor
import time

print("===== K230 摄像头诊断 =====\n")

# ---- 方法1: 不指定宽高, 仅指定ID ----
print("[1] Sensor(id=0) 无宽高...")
try:
    s = Sensor(id=0)
    s.reset()
    print("    OK! 尝试 snapshot...")
    s.set_pixformat(s.RGB565)
    try:
        s.set_framesize(s.QVGA)
        print("    set_framesize(QVGA) OK")
    except Exception as e:
        print("    set_framesize(QVGA) 失败:", e)
        try:
            s.set_framesize(chn=0, width=320, height=240)
            print("    set_framesize(chn=0, w=320, h=240) OK")
        except Exception as e2:
            print("    set_framesize(chn) 失败:", e2)
    s.run()
    try:
        img = s.snapshot()
        print("    snapshot() OK! size:", img.width(), "x", img.height())
    except Exception as e:
        print("    snapshot() 失败:", e)
        try:
            img = s.snapshot(chn=0)
            print("    snapshot(chn=0) OK! size:", img.width(), "x", img.height())
        except Exception as e2:
            print("    snapshot(chn=0) 失败:", e2)
    s.stop()
except Exception as e:
    print("    失败:", e)

# ---- 方法2: 空构造, 不传参数 ----
print("\n[2] Sensor() 空参数...")
try:
    s = Sensor()
    s.reset()
    print("    OK! id=", s.id() if hasattr(s, 'id') else '?')
    s.set_pixformat(s.RGB565)
    s.set_framesize(s.QVGA)
    s.run()
    img = s.snapshot()
    print("    snapshot() OK! size:", img.width(), "x", img.height())
    s.stop()
except Exception as e:
    print("    失败:", e)

# ---- 方法3: 指定 GC2093 参数 ----
print("\n[3] Sensor(id=0, width=1920, height=1080, fps=30)...")
try:
    s = Sensor(id=0, width=1920, height=1080, fps=30)
    s.reset()
    print("    OK!")
    s.set_pixformat(s.RGB565)
    s.set_framesize(chn=0, width=320, height=240)
    s.run()
    img = s.snapshot(chn=0)
    print("    snapshot(chn=0) OK! size:", img.width(), "x", img.height())
    s.stop()
except Exception as e:
    print("    失败:", e)

# ---- 方法4: 尝试 id=1 ----
print("\n[4] Sensor(id=1)...")
try:
    s = Sensor(id=1)
    s.reset()
    print("    OK!")
    s.set_pixformat(s.RGB565)
    s.set_framesize(s.QVGA)
    s.run()
    img = s.snapshot()
    print("    snapshot() OK! size:", img.width(), "x", img.height())
    s.stop()
except Exception as e:
    print("    失败:", e)

# ---- 方法5: CAM_CHN_ID_0 设置 ----
print("\n[5] Sensor(id=0), chn=CAM_CHN_ID_0...")
try:
    s = Sensor(id=0)
    s.reset()
    s.set_pixformat(s.RGB565, chn=Sensor.CAM_CHN_ID_0)
    s.set_framesize(chn=Sensor.CAM_CHN_ID_0, width=320, height=240)
    s.run()
    img = s.snapshot(chn=Sensor.CAM_CHN_ID_0)
    print("    OK! size:", img.width(), "x", img.height())
    s.stop()
except Exception as e:
    print("    失败:", e)

# ---- 检查可用的 Sensor 属性 ----
print("\n[6] Sensor 类属性检查:")
try:
    s = Sensor(id=0)
    for attr in ['CAM_CHN_ID_0', 'CAM_CHN_ID_1', 'CAM_CHN_ID_2',
                 'RGB565', 'RGB888', 'YUV420SP', 'GRAYSCALE',
                 'QVGA', 'VGA', 'HD', 'FHD']:
        try:
            val = getattr(Sensor, attr, 'N/A')
            print(f"    Sensor.{attr} = {val}")
        except:
            print(f"    Sensor.{attr} = ???")
except Exception as e:
    print("    失败:", e)

# ---- 方法7: OV5647 参数 ----
print("\n[7] Sensor(id=0, width=2592, height=1944) OV5647 参数...")
try:
    s = Sensor(id=0, width=2592, height=1944)
    s.reset()
    s.set_pixformat(s.RGB565)
    s.set_framesize(width=320, height=240)
    s.run()
    img = s.snapshot()
    print("    OK! size:", img.width(), "x", img.height())
    s.stop()
except Exception as e:
    print("    失败:", e)

print("\n===== 诊断完毕 =====")
print("请把上面成功的配置序号告诉我")
