"""简单串口测试脚本"""
import serial
import serial.tools.list_ports
import time

# 列出可用串口
print("可用串口:")
for p in serial.tools.list_ports.comports():
    print(f"  {p.device} - {p.description}")

# 连接串口
port = "COM7"  # 修改为你的串口
baud = 115200

print(f"\n连接 {port} @ {baud}...")
try:
    ser = serial.Serial(port, baud, timeout=0.1)
    print("连接成功!")
except Exception as e:
    print(f"连接失败: {e}")
    exit(1)

# 读取数据
print("\n读取数据 (5秒)...")
start = time.time()
count = 0
while time.time() - start < 5:
    try:
        raw = ser.readline()
        if raw:
            line = raw.decode("utf-8", errors="replace").strip()
            if line:
                count += 1
                if count <= 5:
                    print(f"  [{count}] {line[:60]}")
    except Exception as e:
        print(f"  异常: {e}")
        break

print(f"\n共读取 {count} 行数据")
ser.close()
