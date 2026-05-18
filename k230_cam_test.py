"""
K230 摄像头测试 — A4黑框 + 红色靶心 + OLED显示
QVGA 320×240 采集, 640×480 IDE显示, SSD1306 OLED 状态屏
"""
from media.sensor import *
from media.display import *
from media.media import *
from machine import I2C, UART, FPIOA
import struct, time, os, gc

# ===== 一、FPIOA: UART2 → M0G =====
fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)  # K230 TX → M0G PB3 (UART3_RX)
fpioa.set_function(12, FPIOA.UART2_RXD)  # K230 RX ← M0G PB2 (UART3_TX)

# ===== 二、摄像头初始化 (顺序不可变) =====
sensor = Sensor(width=1920, height=1080)
sensor.reset()
sensor.set_framesize(width=320, height=240)
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.VIRT, width=320, height=240, to_ide=True)
MediaManager.init()
sensor.run()

# ===== 三、UART2 K230→M0G =====
uart = UART(UART.UART2, baudrate=115200,
            bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
            stop=UART.STOPBITS_ONE)
last_uart_ms = 0

def uart_send(cmd, x_cm, y_cm, extra=0):
    """10字节帧: |A5|5A|CMD|X(2B小端)|Y(2B)|EXTRA(2B)|XOR|"""
    buf = bytearray(10)
    buf[0]=0xA5; buf[1]=0x5A; buf[2]=cmd
    struct.pack_into('<h', buf, 3, int(x_cm*10))
    struct.pack_into('<h', buf, 5, int(y_cm*10))
    struct.pack_into('<H', buf, 7, extra & 0xFFFF)
    cs = 0
    for i in range(9): cs ^= buf[i]
    buf[9] = cs
    uart.write(buf)

# ===== 四、OLED SSD1306 I2C0 =====
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
    # 水平寻址模式, 确保列地址自动推进
    for c in bytes([0xAE,0xD5,0x80,0xA8,0x3F,0xD3,0x00,0x40,
                     0x8D,0x14,0x20,0x00,0xA1,0xC8,0xDA,0x12,
                     0x81,0xCF,0xD9,0xF1,0xDB,0x40,0xA4,0xA6,0xAF]):
        oled_cmd(c)

def oled_refresh():
    """逐页写入,每页重置列指针 — 防I2C丢字节导致平移"""
    for page in range(OLED_PAGES):          # 8页
        oled_cmd(0xB0 | page)               # 设置页地址 (0xB0~0xB7)
        oled_cmd(0x00)                      # 列低4位 = 0
        oled_cmd(0x10)                      # 列高4位 = 0 → 列=0
        # 发送本页128字节
        page_data = oled_fb[page*OLED_W : (page+1)*OLED_W]
        oled_data(page_data)

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

# 16×16 中文点阵 (纵向取模, 字节倒序, 阴码)
# 用 PCtoLCD2002 生成后替换此表
_HZ16 = {
    # 视: 16×16 宋体
    '视': bytes([0x00,0x00,0x00,0x00,0xFC,0x0F,0x04,0x08,0x04,0x08,0xFC,0x0F,0x04,0x08,0x04,0x08,
                 0xFC,0x0F,0x00,0x00,0xFE,0x1F,0x40,0x00,0x80,0x00,0xFE,0x3F,0x00,0x00,0x00,0x00]),
    # 觉
    '觉': bytes([0x00,0x00,0xF8,0x07,0x08,0x05,0x08,0x05,0xF8,0x07,0x00,0x00,0xFE,0x1F,0x40,0x00,
                 0x80,0x00,0xFE,0x3F,0x00,0x00,0xF8,0x07,0x88,0x04,0x88,0x04,0xF8,0x07,0x00,0x00]),
    # 靶
    '靶': bytes([0x00,0x00,0xFE,0x1F,0x20,0x02,0x20,0x02,0xFE,0x1F,0x00,0x00,0xFC,0x0F,0x04,0x08,
                 0x04,0x08,0xFC,0x0F,0x00,0x00,0xFE,0x1F,0x02,0x10,0x02,0x10,0xFE,0x1F,0x00,0x00]),
    # 心
    '心': bytes([0x00,0x00,0x00,0x00,0x80,0x00,0x80,0x00,0x80,0x00,0x80,0x10,0x80,0x08,0x80,0x04,
                 0x80,0x03,0x00,0x01,0x00,0x01,0x00,0x01,0x80,0x00,0x00,0x00,0x00,0x00,0x00,0x00]),
    # 锁
    '锁': bytes([0x00,0x00,0xF8,0x07,0x08,0x04,0x08,0x04,0xF8,0x07,0x00,0x10,0xFC,0x1F,0x24,0x02,
                 0x24,0x02,0xFC,0x1F,0x20,0x10,0xFE,0x1F,0x22,0x10,0x22,0x10,0xFE,0x1F,0x00,0x00]),
    # 定
    '定': bytes([0x00,0x00,0xFE,0x0F,0x02,0x08,0x02,0x08,0xFE,0x0F,0x00,0x00,0xFC,0x0F,0x04,0x08,
                 0x04,0x08,0xFC,0x0F,0x80,0x00,0x80,0x10,0x80,0x08,0x80,0x07,0x00,0x00,0x00,0x00]),
    # 搜
    '搜': bytes([0x00,0x00,0xFC,0x0F,0x44,0x08,0x44,0x08,0xFC,0x0F,0x00,0x00,0xFE,0x1F,0x40,0x00,
                 0x80,0x00,0xFE,0x3F,0x00,0x00,0xFC,0x0F,0x44,0x08,0x44,0x08,0xFC,0x0F,0x00,0x00]),
    # 索
    '索': bytes([0x00,0x00,0xFE,0x0F,0x02,0x08,0x02,0x08,0xFE,0x0F,0x00,0x00,0xFC,0x0F,0x94,0x04,
                 0x94,0x04,0xFC,0x0F,0x80,0x00,0x80,0x08,0x80,0x04,0x80,0x03,0x00,0x00,0x00,0x00]),
    # 校
    '校': bytes([0x00,0x00,0xF8,0x07,0x08,0x04,0x08,0x04,0xF8,0x07,0x00,0x00,0xFC,0x0F,0x24,0x08,
                 0x24,0x08,0xFC,0x0F,0x80,0x00,0x80,0x10,0x80,0x08,0x80,0x07,0x00,0x00,0x00,0x00]),
    # 准
    '准': bytes([0x00,0x00,0x80,0x00,0x80,0x00,0xFC,0x0F,0x84,0x08,0x84,0x08,0xFC,0x0F,0x80,0x00,
                 0x80,0x00,0xFE,0x1F,0x80,0x00,0x80,0x00,0x80,0x00,0x80,0x00,0x00,0x00,0x00,0x00]),
    # 就
    '就': bytes([0x00,0x00,0xFE,0x0F,0x42,0x08,0x42,0x08,0xFE,0x0F,0x00,0x00,0xFC,0x0F,0x04,0x08,
                 0x04,0x08,0xFC,0x0F,0x80,0x00,0x80,0x10,0x80,0x08,0x80,0x07,0x00,0x00,0x00,0x00]),
    # 绪
    '绪': bytes([0x00,0x00,0xFC,0x0F,0x44,0x08,0x44,0x08,0xFC,0x0F,0x00,0x00,0xFE,0x0F,0x02,0x08,
                 0x02,0x08,0xFE,0x0F,0x00,0x00,0xFC,0x0F,0x04,0x08,0x04,0x08,0xFC,0x0F,0x00,0x00]),
    # 标
    '标': bytes([0x00,0x00,0xF8,0x07,0x08,0x04,0x08,0x04,0xF8,0x07,0x00,0x00,0xFC,0x0F,0x84,0x00,
                 0x84,0x00,0xFC,0x0F,0x80,0x00,0x80,0x08,0x80,0x04,0x80,0x03,0x00,0x00,0x00,0x00]),
    # 坐
    '坐': bytes([0x00,0x00,0x80,0x00,0x80,0x00,0x80,0x10,0x80,0x08,0x80,0x04,0x80,0x03,0x80,0x00,
                 0x80,0x00,0x80,0x10,0x80,0x08,0x80,0x04,0x80,0x03,0x80,0x00,0x00,0x00,0x00,0x00]),
}

def oled_hz16(x, y, ch):
    """画16×16中文汉字"""
    if ch not in _HZ16:
        return
    data = _HZ16[ch]
    for col in range(16):
        lo = data[col*2]       # 上半列 (row 0~7)
        hi = data[col*2 + 1]   # 下半列 (row 8~15)
        for row in range(8):
            oled_px(x + col, y + row,      (lo >> row) & 1)
            oled_px(x + col, y + row + 8,  (hi >> row) & 1)

def oled_puts_cn(x, y, s):
    """混合中英文显示: 中文16×16, 英文6×8"""
    cx, cy = x, y
    for ch in s:
        if ch == '\n':
            cx = x; cy += 17; continue
        if cy >= OLED_H: return
        if ord(ch) > 127:
            # 中文: 占16px宽
            oled_hz16(cx, cy, ch)
            cx += 16
        else:
            oled_ch(cx, cy + 4, ord(ch))  # 英文垂直居中于中文
            cx += 6
        if cx > OLED_W - 16:
            cx = x; cy += 17

# ===== 五、阈值 (自动校准填充) =====
TAPE_GRAY  = (0, 109)      # 黑胶带灰度, 启动后自动校准
RED_TARGET = [(30, 90, 10, 127, -60, 60)]  # 红色靶心LAB, 启动后自动校准

# ===== 六、A4 约束 =====
IW, IH = 320, 240
A4_AREA_MIN = IW * IH * 0.03
A4_AREA_MAX = IW * IH * 0.85
STABLE_FRAMES = 3

# ===== 七、检测状态 =====
a4_corners = None; a4_ok = False; a4_stable = 0; a4_last = None
target_ok = False; target_cx = 0; target_cy = 0
tx_cm = 0.0; ty_cm = 0.0
# 时间平滑 (EMA 低通滤波)
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

# ===== 八、自动阈值校准 (带验证) =====
DEFAULT_TAPE  = (0, 100)      # 安全默认: 宽黑胶带范围
DEFAULT_RED   = [(20, 90, 10, 127, -80, 80)]  # 安全默认: 宽红色范围

def try_detect_a4(img):
    """快速检测A4边框是否存在 (简化版, 仅验证用)"""
    gray = img.to_grayscale(copy=True)
    bin_img = gray.binary([TAPE_GRAY])
    bin_img.open(1)
    rects = [r for r in bin_img.find_rects(threshold=10000)
             if r.w()*r.h() > IW*IH*0.03]
    return len(rects) > 0

def auto_calibrate():
    """上电校准 + 验证: 失败自动回退安全默认值"""
    global TAPE_GRAY, RED_TARGET

    oled_cls()
    oled_puts_cn(0, 0,  "自动校准中")
    oled_str(0, 20, "Aim at target")
    oled_str(0, 35, "Hold still 2s")
    oled_refresh()

    gray_vals = []
    red_labs = []
    last_img = None

    for i in range(30):
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        last_img = img

        # 灰度 Otsu
        gray = img.to_grayscale(copy=True)
        hist = gray.get_histogram()
        otsu = hist.get_threshold()
        otsu_val = otsu.value() if hasattr(otsu, 'value') else int(otsu)
        if 50 < otsu_val < 180:      # 合理范围
            gray_vals.append(otsu_val)

        # 红色中心采样
        cx, cy = IW//2, IH//2
        try:
            stat = img.get_statistics(roi=(cx-50, cy-40, 100, 80))
            if stat.a_mean() > 5 and stat.a_stdev() > 3:
                red_labs.append((stat.l_mean(), stat.a_mean(), stat.b_mean(),
                                 stat.l_stdev(), stat.a_stdev(), stat.b_stdev()))
        except:
            pass

        img.draw_string_advanced(10, 110, 30, f"CAL {i+1}/30", color=(255,255,0))
        Display.show_image(img)
        time.sleep_ms(20)

    # 应用阈值
    cal_ok_tape = False
    if len(gray_vals) >= 5:
        otsu_avg = sum(gray_vals) // len(gray_vals)
        if 50 < otsu_avg < 180:
            TAPE_GRAY = (0, min(otsu_avg + 15, 200))
            cal_ok_tape = True

    cal_ok_red = False
    if len(red_labs) >= 5:
        ls=[r[0] for r in red_labs]; la=[r[1] for r in red_labs]; bs=[r[2] for r in red_labs]
        l_avg=sum(ls)//len(ls); a_avg=sum(la)//len(la); b_avg=sum(bs)//len(bs)
        l_r=max(20, min(ls)//2); a_r=max(25, int(sum(r[4] for r in red_labs)/len(red_labs)*2.5))
        b_r=max(35, int(sum(r[5] for r in red_labs)/len(red_labs)*2.5))
        RED_TARGET=[(max(0,l_avg-l_r),min(100,l_avg+l_r),
                      max(0,a_avg-a_r),min(127,a_avg+a_r),
                      max(-128,b_avg-b_r),min(127,b_avg+b_r))]
        cal_ok_red = True

    # ---- 验证: 用新阈值试检测A4 ----
    verified = False
    if last_img and cal_ok_tape:
        for _ in range(5):  # 试5帧
            os.exitpoint()
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            if try_detect_a4(img):
                verified = True
                break
            time.sleep_ms(30)

    # ---- 根据验证结果决定用哪个阈值 ----
    oled_cls()
    if verified:
        oled_puts_cn(0, 0,  "校准成功")
    else:
        oled_puts_cn(0, 0,  "无目标")
        TAPE_GRAY = DEFAULT_TAPE
        RED_TARGET = DEFAULT_RED
    oled_str(0, 20, f"Tape: 0-{TAPE_GRAY[1]}")
    oled_str(0, 34, "Red: %s" % ("OK" if cal_ok_red else "default"))
    oled_str(0, 48, "Ready!")
    oled_refresh()
    time.sleep_ms(1000)

# ===== 九、OLED 启动画面 =====
oled_init()
oled_cls()
oled_puts_cn(0, 0,  "视觉就绪")
oled_str(0, 20,  "GC2093 QVGA")
oled_str(0, 32,  "A4 Geometric")
oled_str(0, 44,  "OLED SSD1306")
oled_str(0, 55,  "I2C0 OK")
oled_refresh()
time.sleep_ms(1000)

# 自动校准阈值 (靶面对准摄像头, 保持静止2秒)
auto_calibrate()

print("QVGA 320×240 + OLED, 开始检测...")

# ===== 十、主循环 =====
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

        # ---- 靶心 = A4几何中心 (蓝色/绿色共用同一计算源) ----
        if a4_ok and a4_corners:
            target_cx = sum(c[0] for c in a4_corners) // 4
            target_cy = sum(c[1] for c in a4_corners) // 4
            target_ok = True
            tx_cm, ty_cm = pixel_to_cm(target_cx, target_cy)
            # 绿色准星 (与蓝色同源, 绝对稳定)
            img.draw_cross(target_cx, target_cy, color=(0,255,0), size=14, thickness=2)
        else:
            target_ok = False

        # ---- IDE UI ----
        fps = clock.fps()
        bar_h = 30
        img.draw_rectangle(0, 0, IW, bar_h, color=(0,0,0), thickness=-1, fill=True)
        if a4_ok:
            img.draw_string_advanced(3, 3, 25, f"A4 LOCK {fps:.0f}fps", color=(0,255,0))
        else:
            img.draw_string_advanced(3, 3, 25, f"SEARCH {fps:.0f}fps", color=(255,0,0))

        # ---- UART 发送 (每50ms) ----
        now_ms = time.ticks_ms()
        if time.ticks_diff(now_ms, last_uart_ms) > 50:
            last_uart_ms = now_ms
            if a4_ok:
                uart_send(0x01, tx_cm, ty_cm, 0)  # CMD_TARGET
            else:
                uart_send(0x04, 0, 0, 0)           # CMD_LOST

        Display.show_image(img)

        # ---- OLED 刷新 (每20帧≈0.3s, 逐页写入防I2C乱序) ----
        if fc % 20 == 0:
            time.sleep_us(500)  # 等 GC2093 I2C 释放
            oled_cls()
            if a4_ok:
                oled_puts_cn(0, 0,  "靶心锁定")
                oled_str(0, 20, "X:%+2.1f Y:%+2.1f" % (tx_cm, ty_cm))
            else:
                oled_puts_cn(0, 0,  "搜索中")
                oled_str(0, 20, "---")
            oled_str(0, 36, "FPS:%.0f UART" % fps)
            oled_puts_cn(0, 52, "就绪")
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
