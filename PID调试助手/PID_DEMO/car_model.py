"""MSPM0G3507 car model — position-form PI for visible PID response"""
import random
from typing import Dict, List

class CarSimulator:
    def __init__(self):
        self.kp = 3.0; self.ki = 1.0; self.kd = 0.0
        self.speed = 0.0; self.target = 60.0
        self.integral = 0.0; self.tick_ms = 0
        self.inertia = 0.3
        self.noise = 0.2
        self.deadzone = 400.0
        self._pwm = 0

    def set_pid(self, p: float, i: float, d: float = 0.0):
        self.kp = p; self.ki = i; self.kd = d
        self.integral = 0.0; self._pwm = 0

    def step(self) -> Dict[str, float]:
        error = self.target - self.speed
        # 位置式 PI: output = Kp * error + Ki * integral
        self.integral = max(-1500, min(1500, self.integral + error))
        self._pwm = self.kp * error + self.ki * self.integral
        self._pwm = max(0, min(4000, self._pwm))
        if self._pwm < self.deadzone and self.speed < 5: self._pwm = 0
        alpha = 1.0 - self.inertia
        self.speed = max(0, self.speed * self.inertia + self._pwm * 0.06 * alpha + random.gauss(0, self.noise))
        self.tick_ms += 20
        return {
            "timestamp_ms": self.tick_ms,
            "speed_L": self.speed + random.gauss(0, 0.1),
            "speed_R": self.speed + random.gauss(0, 0.1),
            "target_L": self.target, "target_R": self.target,
            "pwm_L": self._pwm, "pwm_R": self._pwm,
            "Kp": self.kp, "Ki": self.ki,
        }

    def collect_samples(self, count: int = 100) -> List[Dict]:
        return [self.step() for _ in range(count)]
