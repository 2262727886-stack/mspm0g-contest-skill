"""Serial bridge for MSPM0G3507 UART communication (115200 8N1)"""
import serial, serial.tools.list_ports, time, re
from typing import Dict, List, Optional

class SerialBridge:
    def __init__(self, port="AUTO", baud=115200, timeout=1.0):
        self.port = port; self.baud = baud; self.timeout = timeout
        self._ser = None; self._line_buf = ""

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
            raw = self._ser.readline()
            if not raw: return None
            line = raw.decode("utf-8", errors="replace").strip().replace("\r","")
            if not line: return None
            parts = line.split(",")
            if len(parts) < 8: return None
            try: vals = [float(p) for p in parts[:8]]
            except ValueError: return None
            return {"timestamp_ms":vals[0],"speed_L":vals[1],"speed_R":vals[2],
                    "target_L":vals[3],"target_R":vals[4],
                    "pwm_L":vals[5],"pwm_R":vals[6],
                    "Kp":vals[7],"Ki":float(parts[8]) if len(parts)>8 else 0.0}
        except: return None

    def read_samples(self, count: int, timeout_s: float = 5.0) -> List[Dict]:
        samples = []; start = time.time()
        while len(samples) < count and time.time() - start < timeout_s:
            s = self.read_sample()
            if s: samples.append(s)
            else: time.sleep(0.001)
        return samples

    def set_pid(self, p: float, i: float, d: float = 0.0) -> bool:
        cmd = f"SET P:{p:.4f} I:{i:.4f}"
        if d: cmd += f" D:{d:.4f}"
        return self._send(cmd + "\r\n")

    def set_target(self, left: int, right: int) -> bool:
        return self._send(f"TARGET L:{left} R:{right}\r\n")

    def get_status(self) -> Optional[str]:
        self._send("STATUS\r\n"); time.sleep(0.1)
        if self._ser and self._ser.in_waiting:
            return self._ser.read(self._ser.in_waiting).decode("utf-8", errors="replace").strip()
        return None

    def reset_pid(self) -> bool: return self._send("RESET\r\n")

    def _send(self, data: str) -> bool:
        try:
            if self._ser and self._ser.is_open:
                self._ser.write(data.encode()); self._ser.flush(); return True
        except: pass
        return False
