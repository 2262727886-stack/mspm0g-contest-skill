"""
SimAdapter — CarSimulator 包装为 SerialBridge 兼容接口
"""
import time
from typing import Dict, Optional
from .car_model import CarSimulator

class SimAdapter:
    def __init__(self, kp=3.0, ki=1.0, target=60, motor_params: Optional[Dict] = None):
        self.sim = CarSimulator(motor_params=motor_params)
        self.sim.target = target
        self.sim.set_pid(kp, ki, 0)
        self._connected = True
        self._last_read = 0.0

    def read_sample(self):
        # 模拟真实 20ms 采样周期 (MCU 50Hz)
        now = time.monotonic()
        elapsed = now - self._last_read
        if elapsed < 0.02:
            time.sleep(0.02 - elapsed)
        self._last_read = time.monotonic()

        s = self.sim.step()
        return {
            "timestamp_ms": s["timestamp_ms"],
            "speed_L": s["speed_L"],
            "speed_R": s["speed_R"],
            "target_L": s["target_L"],
            "target_R": s["target_R"],
            "pwm_L": s["pwm_L"],
            "pwm_R": s["pwm_R"],
            "Kp": s["Kp"],
            "Ki": s["Ki"],
        }

    def set_pid(self, p, i, d=0.0):
        self.sim.set_pid(p, i, d)
        return True

    def set_target(self, left, right):
        self.sim.target = left
        return True

    def get_status(self):
        return f"Sim PID: P={self.sim.kp:.3f} I={self.sim.ki:.3f}"

    def disconnect(self):
        self._connected = False
