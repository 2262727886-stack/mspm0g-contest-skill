"""MSPM0G3507 car simulation — incremental PI with tunable motor physics

Key design: the PID controls PWM, which drives a motor with friction and inertia.
- Reasonable P (3~15) + I (0.5~3) → stable, fast response
- Too much P → overshoot
- Too much I → overshoot/oscillation
- Too much D → noisy response
"""
import random
from typing import Dict, List, Optional

DEFAULT_MOTOR_PARAMS = {
    "base_speed": 50.0,      # base_pwm 时的速度 (脉冲/20ms)
    "max_speed": 120.0,      # 满 PWM 时的最大速度
    "deadzone": 800.0,       # PWM 死区
    "inertia": 4.0,          # 电机惯性 (步数, 越大越慢)
    "noise": 0.5,            # 速度噪声
    "control_limit": 1200.0, # PID 输出限幅
}


class CarSimulator:
    def __init__(self, motor_params: Optional[Dict] = None):
        self.kp = 3.0; self.ki = 1.0; self.kd = 0.0
        self.speed = 0.0; self.target = 60.0
        self.tick_ms = 0
        self._pwm = 0

        self.params = dict(DEFAULT_MOTOR_PARAMS)
        if motor_params:
            self.params.update(motor_params)

        # 增量式 PID 状态
        self._control = 0
        self._last_error = 0
        self._prev_error = 0
        self._limit = self.params["control_limit"]

        # 电机状态
        self._motor_speed = 0.0

    def set_pid(self, p: float, i: float, d: float = 0.0):
        # 只改参数, 不重置控制状态 (避免速度突变产生三角波)
        self.kp = p; self.ki = i; self.kd = d

    def reset(self):
        """显式重置 — 仅在开始全新测试时调用"""
        self._control = 0; self._last_error = 0; self._prev_error = 0
        self._motor_speed = 0.0; self.speed = 0.0

    def step(self) -> Dict[str, float]:
        error = self.target - self.speed
        p = self.params
        limit = self._limit

        # ── 增量式 PID (pid_ctrl.c) ──
        delta_error = error - self._last_error
        d_term = self.kd * (error - 2 * self._last_error + self._prev_error)
        self._control += self.kp * delta_error + self.ki * error + d_term
        self._prev_error = self._last_error
        self._last_error = error
        self._control = max(-limit, min(limit, self._control))

        # PWM
        base_pwm = p["deadzone"]
        self._pwm = max(0, min(4000, base_pwm + self._control))

        # ── 电机模型 ──
        # 真实小车: RUN_DUTY 按目标速度校准, PID 只修正残余误差
        # base_speed ≈ target * 0.85 (前馈, 不是固定值)
        eff = max(0, self._pwm - p["deadzone"])
        calibrated_base = self.target * 0.85  # 前馈: 基础速度 ≈ 85% 目标
        speed_range = p["max_speed"] - p["base_speed"]
        eff_max = max(1, p["control_limit"])
        target_speed = calibrated_base + min(eff, eff_max) * (speed_range / eff_max)

        # 惯性: 速度缓慢跟踪目标 (一阶低通)
        tau = max(1.0, p["inertia"])
        self._motor_speed += (target_speed - self._motor_speed) / tau
        self.speed = self._motor_speed

        # 噪声
        noisy = self.speed + random.gauss(0, p["noise"])
        noisy = max(0, noisy)

        self.tick_ms += 20
        return {
            "timestamp_ms": self.tick_ms,
            "speed_L": noisy,
            "speed_R": noisy + random.gauss(0, 0.3),
            "target_L": self.target, "target_R": self.target,
            "pwm_L": self._pwm, "pwm_R": self._pwm,
            "Kp": self.kp, "Ki": self.ki,
        }

    def collect_samples(self, count: int = 100) -> List[Dict]:
        return [self.step() for _ in range(count)]
