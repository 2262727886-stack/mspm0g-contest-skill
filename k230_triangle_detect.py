"""
K230 三角形识别 — 最小可实现单元
================================
纯三角形检测, 无 UI/无校准/无多余模块.
算法: 颜色blob预过滤 → find_rects 低阈值 → 短边筛选 → 颜色重心验证
运行: 拷贝到 K230 SD 卡, CanMV IDE 执行

硬件: 庐山派 K230 + GC2093 + MIPI ST7701
"""

from media.sensor import *
from media.display import *
from media.media import *
import image, time, os, gc, math

# ============================================================
# 一、参数 (现场修改)
# ============================================================

# LAB 阈值 — 对准三角形物体后用 IDE 阈值编辑器校准
THRESHOLD = [(20, 100, 15, 127, -20, 80)]  # 默认红色物体

# ============================================================
# 二、三角形检测核心
# ============================================================

def find_triangles(img, threshold, min_area=500, short_edge_ratio=0.25):
    """
    在图像中检测三角形.

    算法:
      1. find_blobs 用 LAB 阈值找颜色区域
      2. 灰度 → 二值化 → find_rects 低阈值 → 得到所有四边形
      3. 对每个四边形计算 4 条边, 如果最短边 < 最长边 × short_edge_ratio
         → 判定为三角形 (四边形检测器把三角形一角视为"折叠边")
      4. 颜色验证: 四边形重心必须在 blob 区域内

    参数:
      threshold:    LAB 阈值, 格式 [(L_min,L_max,A_min,A_max,B_min,B_max)]
      min_area:     最小面积 (过滤噪点)
      short_edge_ratio: 短边/长边比值上限, 越小越严格

    返回: [(cx, cy, x, y, w, h), ...]  三角形中心 + 外接矩形
    """
    # Step 1: 颜色 blob 检测
    blobs = img.find_blobs(threshold, pixels_threshold=30,
                           area_threshold=200, merge=True, margin=10)

    # Step 2: 灰度 → 二值化 → 四边形检测 (低阈值, 收集所有候选)
    gray = img.to_grayscale(copy=True)
    L_min = threshold[0][0]
    L_max = threshold[0][1]
    bin_img = gray.binary([(L_min, L_max)])
    bin_img.open(1)  # 去噪

    all_quads = bin_img.find_rects(threshold=3000)  # 低阈值=多检出

    if not all_quads:
        return []

    # Step 3: 短边筛选 + 颜色验证
    triangles = []
    for r in all_quads:
        corners = r.corners()
        if len(corners) != 4:
            continue

        # 计算 4 条边长 (欧氏距离)
        edges = []
        for i in range(4):
            dx = corners[i][0] - corners[(i + 1) % 4][0]
            dy = corners[i][1] - corners[(i + 1) % 4][1]
            edges.append(math.sqrt(dx * dx + dy * dy))

        min_e, max_e = min(edges), max(edges)
        if max_e == 0:
            continue

        # 最短边 < 最长边的 short_edge_ratio → 三角形 (四边形一角折叠)
        if min_e / max_e >= short_edge_ratio:
            continue

        # Step 4: 颜色重心验证
        rcx = sum(c[0] for c in corners) // 4
        rcy = sum(c[1] for c in corners) // 4

        if blobs:  # 有颜色区域 → 重心必须在其中
            in_blob = False
            for b in blobs:
                if (b.x() <= rcx <= b.x() + b.w() and
                    b.y() <= rcy <= b.y() + b.h()):
                    in_blob = True
                    break
            if not in_blob:
                continue

        if r.w() * r.h() < min_area:
            continue

        triangles.append((rcx, rcy, r.x(), r.y(), r.w(), r.h()))

    # 按面积排序, 最大优先
    triangles.sort(key=lambda t: t[5] * t[6], reverse=True)
    return triangles


# ============================================================
# 三、初始化
# ============================================================

print("=== K230 三角形检测 ===")

sensor = Sensor(id=2)
sensor.reset()
sensor.set_framesize(width=640, height=480)   # VGA: 节省显存, 防崩溃
sensor.set_pixformat(Sensor.RGB565)
sensor.set_hmirror(False)
sensor.set_vflip(False)

Display.init(Display.ST7701, width=800, height=480, to_ide=True)
MediaManager.init()
sensor.run()

clock = time.clock()
fc = 0

print("启动完成, 对准三角形物体")
print("阈值: %s" % str(THRESHOLD))

# ============================================================
# 四、主循环
# ============================================================

try:
    while True:
        os.exitpoint()
        clock.tick()
        fc += 1

        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        # --- 三角形检测 ---
        tris = find_triangles(img, THRESHOLD)

        # --- 画检测结果 ---
        for i, (cx, cy, x, y, w, h) in enumerate(tris):
            # 外接矩形
            color = (0, 255, 0) if i == 0 else (255, 165, 0)
            img.draw_rectangle(x, y, w, h, color=color, thickness=2)
            # 中心十字
            img.draw_cross(cx, cy, color=(0, 255, 0), size=15)
            # 标签
            img.draw_string_advanced(cx + 18, cy - 10, 18,
                                     "T%d" % (i + 1), color=(0, 255, 0))

        # --- 状态 ---
        if tris:
            best = tris[0]
            s = "三角形 x%d  (%d,%d)" % (len(tris), best[0], best[1])
            img.draw_string_advanced(10, 10, 24, s, color=(0, 255, 0))
        else:
            img.draw_string_advanced(10, 10, 24, "无三角形",
                                     color=(255, 100, 100))

        fps_s = "FPS:%d" % max(1, clock.fps())
        img.draw_string_advanced(600, 10, 18, fps_s, color=(180, 180, 180))

        # --- 缩放 → 显示 ---
        try:
            img.resize(800, 480)
        except:
            pass
        Display.show_image(img)

        if fc % 100 == 0:
            gc.collect()

except KeyboardInterrupt:
    print("\n中断")
except BaseException as e:
    print("异常: %s" % str(e))
    import sys
    sys.print_exception(e)
finally:
    sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    print("清理完成")
