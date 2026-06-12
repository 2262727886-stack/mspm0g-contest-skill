"""Serial bridge for MSPM0G3507 UART communication (115200 8N1)"""
import serial, serial.tools.list_ports, time, re
from typing import Dict, List, Optional
from .protocol import ACK_PATTERNS, COMMANDS, frame

class SerialBridge:
    def __init__(self, port="AUTO", baud=115200, timeout=1.0):
        self.port = port; self.baud = baud; self.timeout = timeout
        self._ser = None; self._line_buf = ""; self.last_probe_lines = []

    def connect(self) -> bool:
        if self.port == "AUTO":
            self.port = self._auto_detect()
            if not self.port: print("[ERROR] No MSPM0G3507 serial port found"); return False
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.1)
            try: self._ser.dtr = False
            except: pass  # 防止 DTR 触发 MCU 复位
            print(f"[INFO] 已连接 {self.port} @ {self.baud}"); time.sleep(0.5)
            self.flush(); return True
        except serial.SerialException as e: print(f"[ERROR] {e}"); return False

    def disconnect(self):
        if self._ser and self._ser.is_open: self._ser.close()

    def _auto_detect(self) -> Optional[str]:
        for p in serial.tools.list_ports.comports():
            desc=(p.description or "")+(p.manufacturer or "")
            if any(k in desc for k in ["XDS110","TI","CH340","CH341","USB-SERIAL","USB Serial"]):
                print(f"[INFO] 检测到: {p.device} ({p.description})"); return p.device
        ports = list(serial.tools.list_ports.comports())
        if ports:
            for i, p in enumerate(ports): print(f"  [{i}] {p.device} - {p.description}")
            try: return ports[int(input("选择端口序号: "))].device
            except: pass
        return None

    def flush(self):
        """清空接收缓冲"""
        if self._ser and self._ser.is_open:
            try: self._ser.reset_input_buffer()
            except: pass
            self._line_buf = ""

    def read_sample(self) -> Optional[Dict[str, float]]:
        if not (self._ser and self._ser.is_open): return None
        try:
            line = self.read_line()
            if not line: return None
            parts = line.split(",")
            if len(parts) < 8:
                # 数据格式不对，记录最后几行用于调试
                self.last_probe_lines.append(line)
                self.last_probe_lines = self.last_probe_lines[-5:]
                return None
            try: vals = [float(p) for p in parts[:8]]
            except ValueError: return None
            return {"timestamp_ms":vals[0],"speed_L":vals[1],"speed_R":vals[2],
                    "target_L":vals[3],"target_R":vals[4],
                    "pwm_L":vals[5],"pwm_R":vals[6],
                    "Kp":vals[7],"Ki":float(parts[8]) if len(parts)>8 else 0.0}
        except: return None

    def read_line(self) -> Optional[str]:
        if not (self._ser and self._ser.is_open): return None
        try:
            # 使用更短的超时
            old_timeout = self._ser.timeout
            self._ser.timeout = 0.05  # 50ms 超时
            raw = self._ser.readline()
            self._ser.timeout = old_timeout
            if not raw: return None
            line = raw.decode("utf-8", errors="replace").strip().replace("\r","")
            return line or None
        except Exception as e:
            return None

    @staticmethod
    def _line_has_target(line: str, left: int, right: int) -> bool:
        parts = line.split(",")
        if len(parts) >= 5:
            try:
                return int(float(parts[3])) == int(left) and int(float(parts[4])) == int(right)
            except ValueError:
                return False
        ok = re.search(ACK_PATTERNS["target"], line)
        if ok:
            return int(ok.group(1)) == int(left) and int(ok.group(2)) == int(right)
        status = re.search(ACK_PATTERNS["status_target"], line)
        if status:
            return int(status.group(1)) == int(left) and int(status.group(2)) == int(right)
        return False

    def read_samples(self, count: int, timeout_s: float = 5.0) -> List[Dict]:
        samples = []; start = time.time()
        while len(samples) < count and time.time() - start < timeout_s:
            s = self.read_sample()
            if s: samples.append(s)
            else: time.sleep(0.001)
        return samples

    def wait_for_target(self, left: int, right: int, timeout_s: float = 2.0) -> bool:
        """等待 MCU 文本或 CSV 回显目标值，避免自动调参混入旧目标数据。"""
        self.last_probe_lines = []
        start = time.time()
        while time.time() - start < timeout_s:
            line = self.read_line()
            if not line:
                time.sleep(0.002); continue
            self.last_probe_lines.append(line)
            self.last_probe_lines = self.last_probe_lines[-8:]
            if self._line_has_target(line, left, right):
                return True
        return False

    def set_pid(self, p: float, i: float, d: float = 0.0) -> bool:
        key = "set_pid_d" if d else "set_pid"
        return self._send(frame(COMMANDS[key].format(p=p, i=i, d=d)))

    def set_target(self, left: int, right: int) -> bool:
        return self._send(frame(COMMANDS["target"].format(left=left, right=right)))

    def set_target_checked(self, left: int, right: int, timeout_s: float = 2.0) -> bool:
        if not self.set_target(left, right): return False
        if self.wait_for_target(left, right, min(timeout_s, 1.0)): return True
        self._send(frame(COMMANDS["status"]))
        return self.wait_for_target(left, right, timeout_s)

    def get_status(self) -> Optional[str]:
        self._send(frame(COMMANDS["status"])); time.sleep(0.1)
        if self._ser and self._ser.in_waiting:
            return self._ser.read(self._ser.in_waiting).decode("utf-8", errors="replace").strip()
        return None

    def reset_pid(self) -> bool: return self._send(frame(COMMANDS["reset"]))

    def _send(self, data) -> bool:
        try:
            if self._ser and self._ser.is_open:
                self._ser.write(data if isinstance(data, bytes) else data.encode()); self._ser.flush(); return True
        except: pass
        return False
