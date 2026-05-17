"""
K230 摄像头测试 — A4黑框 + 红色靶心 + OLED显示
QVGA 320×240 采集, 640×480 IDE显示, SSD1306 OLED 状态屏
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import I2C
import time, os, gc

# ===== 一、摄像头初始化 (顺序不可变) =====
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=320, height=240)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.VIRT, width=640, height=480, to_ide=True)
MediaManager.init()
sensor.run()

# ===== 二、OLED SSD1306 I2C0 (与GC2093共用, 64字节小包+重试防冲突) =====
OLED_ADDR = 0x3C
OLED_W = 128; OLED_H = 64; OLED_PAGES = OLED_H // 8
oled_fb = bytearray(OLED_W * OLED_PAGES)
i2c = I2C(0, freq=400000)
print("I2C0:", i2c.scan())

def oled_cmd(c):
    """发命令, 带重试防总线冲突"""
    for _ in range(3):
        try:
            i2c.writeto(OLED_ADDR, bytearray([0x00, c]))
            return
        except OSError:
            time.sleep_us(100)

def oled_data(data):
    """发数据, 分小包 + 延时防止阻塞GC2093"""
    for i in range(0, len(data), 64):  # 64字节小包
        chunk = data[i:i+64]
        for _ in range(3):
            try:
                i2c.writeto(OLED_ADDR, bytearray([0x40]) + chunk)
                break
            except OSError:
                time.sleep_us(200)
        time.sleep_us(50)  # 包间延时, 释放总线

def oled_init():
    for c in bytes([0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0x00,0x40,
                     0x8D,0x14,0x20,0x00,0xA1,0xC8,0xDA,0x12,
                     0x81,0xCF,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF]):
        oled_cmd(c)

def oled_refresh():
    oled_cmd(0x21); oled_cmd(0x00); oled_cmd(0x7F)
    oled_cmd(0x22); oled_cmd(0x00); oled_cmd(0x07)
    oled_data(oled_fb)

def oled_cls():
    for i in range(len(oled_fb)): oled_fb[i] = 0

def oled_px(x, y, c):
    if 0 <= x < OLED_W and 0 <= y < OLED_H:
        idx = x + (y//8)*OLED_W
        if c: oled_fb[idx] |= (1 << (y&7))
        else:  oled_fb[idx] &= ~(1 << (y&7))

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

# ===== 三、阈值 =====
TAPE_GRAY  = (0, 109)
RED_TARGET = [(52,100,24,127,-49,41), (29,73,19,127,-57,89)]

# ===== 四、A4 约束 =====
IW, IH = 320, 240
A4_AREA_MIN = IW * IH * 0.03
A4_AREA_MAX = IW * IH * 0.85
STABLE_FRAMES = 3

# ===== 五、检测状态 =====
a4_corners = None; a4_ok = False; a4_stable = 0; a4_last = None
target_ok = False; target_cx = 0; target_cy = 0
tx_cm = 0.0; ty_cm = 0.0  # 靶心物理坐标
clock = time.clock(); fc = 0

def pixel_to_cm(px, py):
    """像素→cm, 相对A4中心"""
    if a4_ok and a4_corners:
        xs = [c[0] for c in a4_corners]; ys = [c[1] for c in a4_corners]
        bw = max(xs) - min(xs); bh = max(ys) - min(ys)
        if bw > 0 and bh > 0:
            cx = (min(xs) + max(xs)) // 2
            cy = (min(ys) + max(ys)) // 2
            return (px-cx)*50.0/bw, -(py-cy)*50.0/bh
    return (px-160)*50.0/320, -(py-120)*50.0/240

def a4_filter_valid(rects):
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

def target_in_center(cx, cy, corners, m=0.3):
    if corners is None: return True
    xs=[c[0] for c in corners]; ys=[c[1] for c in corners]
    cw=max(xs)-min(xs); ch=max(ys)-min(ys)
    mx=m*cw/2; my=m*ch/2; ccx=(min(xs)+max(xs))/2; ccy=(min(ys)+max(ys))/2
    return abs(cx-ccx)<cw/2-mx and abs(cy-ccy)<ch/2-my

# ===== 六、OLED 启动画面 =====
oled_init()
oled_cls()
oled_str(0, 0,  "K230 25E Test")
oled_str(0, 12, "GC2093 QVGA")
oled_str(0, 24, "A4 + RED Target")
oled_str(0, 36, "OLED SSD1306")
oled_str(0, 55, "I2C0 0x3C OK")
oled_refresh()
time.sleep_ms(1000)

print("QVGA 320×240 + OLED, 开始检测...")

# ===== 七、主循环 =====
try:
    while True:
        os.exitpoint()
        clock.tick(); fc += 1
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # ---- A4 黑胶带边框 ----
        gray = img.to_grayscale(copy=True)
        bin_img = gray.binary([TAPE_GRAY])
        bin_img.open(1)

        rects = a4_filter_valid(bin_img.find_rects(threshold=10000))
        if rects:
            best = max(rects, key=lambda r: r.w()*r.h())
            nc = [(c[0],c[1]) for c in best.corners()]
            if corners_near(nc, a4_last): a4_stable += 1
            else: a4_stable = 1; a4_last = nc
            if a4_stable >= STABLE_FRAMES: a4_corners = nc; a4_ok = True
        else:
            a4_stable = max(0, a4_stable-1)
            if a4_stable == 0: a4_ok = False; a4_corners = None

        if a4_ok and a4_corners:
            for i in range(4):
                img.draw_line(a4_corners[i][0], a4_corners[i][1],
                              a4_corners[(i+1)%4][0], a4_corners[(i+1)%4][1],
                              color=(255,0,0), thickness=2)
            ca = sum(c[0] for c in a4_corners)//4
            cb = sum(c[1] for c in a4_corners)//4
            img.draw_cross(ca, cb, color=(0,0,255), size=10, thickness=2)

        # ---- 红色靶心 ----
        if a4_ok and a4_corners:
            xs=[c[0] for c in a4_corners]; ys=[c[1] for c in a4_corners]; mg=4
            roi=(min(xs)+mg, min(ys)+mg, max(xs)-min(xs)-2*mg, max(ys)-min(ys)-2*mg)
            blobs = img.find_blobs(RED_TARGET, roi=roi, pixels_threshold=15, merge=True)
        else:
            blobs = img.find_blobs(RED_TARGET, pixels_threshold=40, merge=True)

        target_ok = False
        if blobs:
            for b in sorted(blobs, key=lambda x: x.area(), reverse=True):
                if b.density() < 0.35: continue
                bx=b.x()+b.w()//2; by=b.y()+b.h()//2
                if a4_ok and not target_in_center(bx, by, a4_corners, 0.35): continue
                target_cx=bx; target_cy=by; target_ok=True
                tx_cm, ty_cm = pixel_to_cm(bx, by)
                img.draw_rectangle(b.x(),b.y(),b.w(),b.h(), color=(0,255,0), thickness=1)
                img.draw_cross(bx, by, color=(0,255,0), size=8, thickness=1)
                break

        # ---- IDE UI ----
        fps = clock.fps()
        bar_h = 30
        img.draw_rectangle(0, 0, IW, bar_h, color=(0,0,0), thickness=-1, fill=True)
        if a4_ok and target_ok:
            img.draw_string_advanced(3, 3, 25, f"A4+RED {fps:.0f}fps", color=(0,255,0))
        elif a4_ok:
            img.draw_string_advanced(3, 3, 25, f"A4 OK {fps:.0f}fps", color=(255,255,0))
        else:
            img.draw_string_advanced(3, 3, 25, f"SEARCH {fps:.0f}fps", color=(255,0,0))

        Display.show_image(img)

        # ---- OLED 刷新 (每8帧, 降低I2C占用) ----
        if fc % 8 == 0:
            oled_cls()
            oled_str(0, 0, "25E Vision")
            if target_ok:
                oled_str(0, 12, "T:%+2.1f,%+2.1f" % (tx_cm, ty_cm))
            else:
                oled_str(0, 12, "T: ---")
            if a4_ok:
                oled_str(0, 24, "A4 LOCK")
            else:
                oled_str(0, 24, "A4: search")
            oled_str(0, 36, "FPS:%.0f" % fps)
            oled_str(0, 55, "UART:wait")
            oled_refresh()

        if fc % 300 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("用户停止")
except BaseException as e:
    print(f"异常: {e}")
finally:
    sensor.stop(); Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP); time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完毕")
