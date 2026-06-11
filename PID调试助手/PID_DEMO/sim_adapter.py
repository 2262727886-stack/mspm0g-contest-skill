"""
SimAdapter — 让 CarSimulator 伪装成 SerialBridge，统一调参引擎接口
参考 llm-pid-tuner 的 BaseTuningEnvironment 抽象模式
"""
from .car_model import CarSimulator

class SimAdapter:
    """将 CarSimulator 包装为与 SerialBridge 兼容的接口"""

    def __init__(self, kp=3.0, ki=1.0, target=60):
        self.sim = CarSimulator()
        self.sim.target = target
        self.sim.set_pid(kp, ki, 0)
        self._connected = True

    def read_sample(self):
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
