"""
K230 25E 视觉端 — A4黑框检测 + OLED + UART
QVGA 320×240, GC2093, SSD1306 I2C0, UART2→M0G
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import I2C, UART, FPIOA
import struct, time, os, gc

# ============================================================
# 一、硬件初始化
# ============================================================

# FPIOA: UART2 → M0G UART3
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

# 摄像头 (顺序不可变)
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=320, height=240)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)
Display.init(Display.VIRT, width=320, height=240, to_ide=True)
MediaManager.init()
sensor.run()

# UART2
uart = UART(UART.UART2, baudrate=115200,
            bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
            stop=UART.STOPBITS_ONE)

# ============================================================
# 二、OLED SSD1306 I2C0
# ============================================================
OLED_ADDR = 0x3C
OLED_W, OLED_H = 128, 64
OLED_PAGES = OLED_H // 8
oled_fb = bytearray(OLED_W * OLED_PAGES)
i2c = I2C(0, freq=400000)

def oled_cmd(c):
    for _ in range(3):
        try:
            i2c.writeto(OLED_ADDR, bytearray([0x00, c]))
            return
        except OSError:
            time.sleep_us(100)

def oled_data(data):
    for i in range(0, len(data), 64):
        chunk = data[i:i+64]
        for _ in range(3):
            try:
                i2c.writeto(OLED_ADDR, bytearray([0x40]) + chunk)
                break
            except OSError:
                time.sleep_us(200)
        time.sleep_us(50)

def oled_init():
    for c in bytes([0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0x00,0x40,
                     0x8D,0x14,0x20,0x00,0xA1,0xC8,0xDA,0x12,
                     0x81,0xCF,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF]):
        oled_cmd(c)

def oled_refresh():
    for page in range(OLED_PAGES):
        oled_cmd(0xB0 | page)
        oled_cmd(0x00); oled_cmd(0x10)
        oled_data(oled_fb[page*OLED_W : (page+1)*OLED_W])

def oled_cls():
    for i in range(len(oled_fb)): oled_fb[i] = 0

def oled_px(x, y, c):
    if 0 <= x < OLED_W and 0 <= y < OLED_H:
        idx = x + (y // 8) * OLED_W
        if c: oled_fb[idx] |= (1 << (y & 7))
        else:  oled_fb[idx] &= ~(1 << (y & 7))

# 6x8 ASCII 字模
_F6 = [b'\x00\x00\x00\x00\x00\x00',b'\x00\x00\x5f\x00\x00\x00',b'\x00\x03\x00\x03\x00\x00',b'\x14\x7f\x14\x7f\x14\x00',b'\x24\x2a\x7f\x2a\x12\x00',b'\x23\x13\x08\x64\x62\x00',b'\x36\x49\x55\x22\x50\x00',b'\x00\x05\x03\x00\x00\x00',b'\x00\x1c\x22\x41\x00\x00',b'\x00\x41\x22\x1c\x00\x00',b'\x14\x08\x3e\x08\x14\x00',b'\x08\x08\x3e\x08\x08\x00',b'\x00\x50\x30\x00\x00\x00',b'\x08\x08\x08\x08\x08\x00',b'\x00\x60\x60\x00\x00\x00',b'\x20\x10\x08\x04\x02\x00',b'\x3e\x51\x49\x45\x3e\x00',b'\x00\x42\x7f\x40\x00\x00',b'\x42\x61\x51\x49\x46\x00',b'\x21\x41\x45\x4b\x31\x00',b'\x18\x14\x12\x7f\x10\x00',b'\x27\x45\x45\x45\x39\x00',b'\x3c\x4a\x49\x49\x30\x00',b'\x01\x01\x79\x05\x03\x00',b'\x36\x49\x49\x49\x36\x00',b'\x06\x49\x49\x29\x1e\x00',b'\x00\x36\x36\x00\x00\x00',b'\x00\x56\x36\x00\x00\x00',b'\x08\x14\x22\x41\x00\x00',b'\x14\x14\x14\x14\x14\x00',b'\x41\x22\x14\x08\x00\x00',b'\x02\x01\x51\x09\x06\x00',b'\x3e\x41\x5d\x55\x1e\x00',b'\x7e\x11\x11\x11\x7e\x00',b'\x7f\x49\x49\x49\x36\x00',b'\x3e\x41\x41\x41\x22\x00',b'\x7f\x41\x41\x22\x1c\x00',b'\x7f\x49\x49\x49\x41\x00',b'\x7f\x09\x09\x09\x01\x00',b'\x3e\x41\x49\x49\x7a\x00',b'\x7f\x08\x08\x08\x7f\x00',b'\x00\x41\x7f\x41\x00\x00',b'\x30\x40\x41\x3f\x01\x00',b'\x7f\x08\x14\x22\x41\x00',b'\x7f\x40\x40\x40\x40\x00',b'\x7f\x02\x0c\x02\x7f\x00',b'\x7f\x04\x08\x10\x7f\x00',b'\x3e\x41\x41\x41\x3e\x00',b'\x7f\x09\x09\x09\x06\x00',b'\x3e\x41\x51\x21\x5e\x00',b'\x7f\x09\x19\x29\x46\x00',b'\x46\x49\x49\x49\x31\x00',b'\x01\x01\x7f\x01\x01\x00',b'\x3f\x40\x40\x40\x3f\x00',b'\x0f\x30\x40\x30\x0f\x00',b'\x7f\x20\x18\x20\x7f\x00',b'\x63\x14\x08\x14\x63\x00',b'\x07\x08\x70\x08\x07\x00',b'\x61\x51\x49\x45\x43\x00',b'\x00\x7f\x41\x41\x00\x00',b'\x02\x04\x08\x10\x20\x00',b'\x00\x41\x41\x7f\x00\x00',b'\x04\x02\x01\x02\x04\x00',b'\x40\x40\x40\x40\x40\x00',b'\x00\x01\x02\x04\x00\x00',b'\x20\x54\x54\x54\x78\x00',b'\x7f\x48\x44\x44\x38\x00',b'\x38\x44\x44\x44\x20\x00',b'\x38\x44\x44\x48\x7f\x00',b'\x38\x54\x54\x54\x18\x00',b'\x08\x7e\x09\x01\x02\x00',b'\x0c\x52\x52\x52\x3e\x00',b'\x7f\x08\x04\x04\x78\x00',b'\x00\x44\x7d\x40\x00\x00',b'\x20\x40\x44\x3d\x00\x00',b'\x7f\x10\x28\x44\x00\x00',b'\x00\x41\x7f\x40\x00\x00',b'\x7c\x04\x18\x04\x78\x00',b'\x7c\x08\x04\x04\x78\x00',b'\x38\x44\x44\x44\x38\x00',b'\x7c\x14\x14\x14\x08\x00',b'\x08\x14\x14\x18\x7c\x00',b'\x7c\x08\x04\x04\x08\x00',b'\x48\x54\x54\x54\x20\x00',b'\x04\x3f\x44\x40\x20\x00',b'\x3c\x40\x40\x20\x7c\x00',b'\x1c\x20\x40\x20\x1c\x00',b'\x3c\x40\x30\x40\x3c\x00',b'\x44\x28\x10\x28\x44\x00',b'\x0c\x50\x50\x50\x3c\x00',b'\x44\x64\x54\x4c\x44\x00',b'\x08\x36\x41\x00\x00\x00',b'\x00\x00\x77\x00\x00\x00',b'\x00\x41\x36\x08\x00\x00',b'\x08\x04\x08\x10\x08\x00']

def oled_ch(x, y, ch):
    if ch < 0x20 or ch > 0x7E: return
    g = _F6[ch - 0x20]
    for col in range(6):
        d = g[col]
        for row in range(8):
            oled_px(x+col, y+row, (d>>row)&1)

def oled_str(x, y, s):
    cx, cy = x, y
    for c in s:
        if c == '\n': cx = x; cy += 9; continue
        if cy >= OLED_H: return
        oled_ch(cx, cy, ord(c))
        cx += 6
        if cx > OLED_W - 6: cx = x; cy += 9

# ============================================================
# 三、UART 帧协议
# ============================================================
def uart_send(cmd, x_cm, y_cm, extra=0):
    """10字节帧: A5 5A CMD X(LE) Y(LE) EXTRA(LE) XOR"""
    buf = bytearray(10)
    buf[0]=0xA5; buf[1]=0x5A; buf[2]=cmd
    struct.pack_into('<h', buf, 3, int(x_cm*10))
    struct.pack_into('<h', buf, 5, int(y_cm*10))
    struct.pack_into('<H', buf, 7, extra & 0xFFFF)
    cs = 0
    for i in range(9): cs ^= buf[i]
    buf[9] = cs
    uart.write(buf)

# ============================================================
# 四、检测参数与状态
# ============================================================
IW, IH = 320, 240
A4_AREA_MIN = IW * IH * 0.03
A4_AREA_MAX = IW * IH * 0.85
STABLE = 3                # A4锁定需连续帧数

TAPE_GRAY = (0, 109)      # 黑胶带灰度 (启动自动校准)
DEFAULT_TAPE = (0, 100)   # 校准失败回退值

a4_corners = None; a4_ok = False; a4_stable = 0; a4_last = None
a4_cx = 0; a4_cy = 0       # A4几何中心
tx_cm = 0.0; ty_cm = 0.0   # 靶心物理坐标
clock = time.clock(); fc = 0
last_uart_ms = 0

def pixel_to_cm(px, py):
    if a4_ok and a4_corners:
        xs = [c[0] for c in a4_corners]; ys = [c[1] for c in a4_corners]
        bw, bh = max(xs)-min(xs), max(ys)-min(ys)
        if bw > 0 and bh > 0:
            cx = (min(xs)+max(xs))//2; cy = (min(ys)+max(ys))//2
            return (px-cx)*50.0/bw, -(py-cy)*50.0/bh
    return (px-160)*50.0/320, -(py-120)*50.0/240

def a4_filter(rects):
    """长宽比+面积过滤"""
    good = []
    for r in rects:
        w, h = r.w(), r.h()
        if w <= 0 or h <= 0: continue
        ratio = max(w,h)/min(w,h); area = w*h
        if 1.15 < ratio < 1.80 and A4_AREA_MIN < area < A4_AREA_MAX:
            good.append(r)
    return good

def corners_near(c1, c2, d=15):
    if c1 is None or c2 is None: return False
    for p,q in zip(c1,c2):
        if abs(p[0]-q[0])>d or abs(p[1]-q[1])>d: return False
    return True

# ============================================================
# 五、自动阈值校准 (带验证回退)
# ============================================================
def auto_calibrate():
    global TAPE_GRAY

    oled_cls()
    oled_str(0, 0,  "Auto Calibrate...")
    oled_str(0, 20, "Aim at target")
    oled_str(0, 35, "Hold still 2s")
    oled_refresh()

    gray_vals = []
    last_img = None

    for i in range(30):
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        last_img = img
        gray = img.to_grayscale(copy=True)
        hist = gray.get_histogram()
        otsu = hist.get_threshold()
        otsu_val = otsu.value() if hasattr(otsu, 'value') else int(otsu)
        if 50 < otsu_val < 180:
            gray_vals.append(otsu_val)
        img.draw_string_advanced(10, 110, 30, f"CAL {i+1}/30", color=(255,255,0))
        Display.show_image(img)
        time.sleep_ms(20)

    if len(gray_vals) >= 5:
        otsu_avg = sum(gray_vals) // len(gray_vals)
        if 50 < otsu_avg < 180:
            TAPE_GRAY = (0, min(otsu_avg + 15, 200))

    # 验证
    verified = False
    if last_img:
        for _ in range(5):
            os.exitpoint()
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            gray = img.to_grayscale(copy=True)
            bin_img = gray.binary([TAPE_GRAY]); bin_img.open(1)
            rects = [r for r in bin_img.find_rects(threshold=10000)
                     if r.w()*r.h() > IW*IH*0.03]
            if rects:
                verified = True; break
            time.sleep_ms(30)

    oled_cls()
    if verified:
        oled_str(0, 0,  "Calibration OK")
    else:
        oled_str(0, 0,  "No target found")
        TAPE_GRAY = DEFAULT_TAPE
    oled_str(0, 14, f"Tape: 0-{TAPE_GRAY[1]}")
    oled_str(0, 30, "Ready!")
    oled_refresh()
    time.sleep_ms(1000)

# ============================================================
# 六、启动
# ============================================================
oled_init()
oled_cls()
oled_str(0, 0,  "K230 25E Boot")
oled_str(0, 12, "GC2093 QVGA")
oled_str(0, 24, "A4 Geometric")
oled_str(0, 36, "OLED SSD1306")
oled_str(0, 55, "I2C0 OK")
oled_refresh()
time.sleep_ms(1000)

print("I2C0:", i2c.scan())
auto_calibrate()
print("Ready. QVGA + OLED + UART2")

# ============================================================
# 七、主循环
# ============================================================
try:
    while True:
        os.exitpoint()
        clock.tick(); fc += 1
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # ---- A4 边框检测 ----
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([TAPE_GRAY]); bin_img.open(1)

        rects = a4_filter(bin_img.find_rects(threshold=10000))
        if rects:
            best = max(rects, key=lambda r: r.w()*r.h())
            nc = [(c[0],c[1]) for c in best.corners()]
            if corners_near(nc, a4_last): a4_stable += 1
            else: a4_stable = 1; a4_last = nc
            if a4_stable >= STABLE:
                a4_corners = nc; a4_ok = True
        else:
            a4_stable = max(0, a4_stable-1)
            if a4_stable == 0: a4_ok = False; a4_corners = None

        # ---- 靶心 = A4几何中心 ----
        if a4_ok:
            a4_cx = sum(c[0] for c in a4_corners) // 4
            a4_cy = sum(c[1] for c in a4_corners) // 4
            tx_cm, ty_cm = pixel_to_cm(a4_cx, a4_cy)
            # 蓝色边框 + 中心
            for i in range(4):
                img.draw_line(a4_corners[i][0], a4_corners[i][1],
                              a4_corners[(i+1)%4][0], a4_corners[(i+1)%4][1],
                              color=(255,0,0), thickness=2)
            img.draw_cross(a4_cx, a4_cy, color=(0,0,255), size=10, thickness=2)
            # 绿色准星 (同源, 绝对稳定)
            img.draw_cross(a4_cx, a4_cy, color=(0,255,0), size=14, thickness=2)

        # ---- IDE 状态栏 ----
        fps = clock.fps()
        img.draw_rectangle(0, 0, IW, 26, color=(0,0,0), thickness=-1, fill=True)
        status = "A4 LOCK" if a4_ok else "SEARCH"
        color  = (0,255,0) if a4_ok else (255,0,0)
        img.draw_string_advanced(3, 3, 22, f"{status} {fps:.0f}fps", color=color)

        # ---- UART 发送 (50ms) ----
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_uart_ms) > 50:
            last_uart_ms = now_ms
            if a4_ok: uart_send(0x01, tx_cm, ty_cm, 0)
            else:     uart_send(0x04, 0, 0, 0)

        Display.show_image(img)

        # ---- OLED 刷新 (每20帧) ----
        if fc % 20 == 0:
            time.sleep_us(500)
            oled_cls()
            if a4_ok:
                oled_str(0, 0,  "25E LOCK")
                oled_str(0, 12, "X:%+2.1f Y:%+2.1f" % (tx_cm, ty_cm))
            else:
                oled_str(0, 0,  "25E SEARCH")
                oled_str(0, 12, "---")
            oled_str(0, 28, "FPS:%.0f" % fps)
            oled_str(0, 42, "UART->M0G")
            oled_refresh()

        if fc % 300 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("stop")
except BaseException as e:
    print(f"err: {e}")
finally:
    sensor.stop(); Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP); time.sleep_ms(100)
    MediaManager.deinit()
    print("done")
