"""Speed data buffer with metrics calculation for MSPM0G3507 speed PI tuning"""
from typing import Dict, List

# 状态中文映射
STATUS_CN = {
    "INSUFFICIENT_DATA": "数据不足",
    "OVERSPEED": "超速",
    "MOTOR_LIMIT": "电机极限",
    "SLOW_RESPONSE": "响应慢",
    "OSCILLATING": "振荡",
    "STABLE": "稳定"
}

class SpeedBuffer:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size; self._data: List[Dict] = []

    def add(self, s: Dict): self._data.append(s); self._data = self._data[-self.max_size:] if len(self._data) > self.max_size else self._data
    def reset(self): self._data.clear()
    def __len__(self): return len(self._data)

    def calculate_metrics(self) -> Dict:
        if len(self._data) < 10: return {"status":"INSUFFICIENT_DATA","status_cn":"数据不足","avg_error":0,"overshoot":0,"steady_state_error":0,"oscillation_index":0}
        errs = [max(abs(s.get("speed_L",0)-s.get("target_L",0)), abs(s.get("speed_R",0)-s.get("target_R",0))) for s in self._data]
        avg = sum(errs)/len(errs)
        avg_speed = sum((s.get("speed_L",0)+s.get("speed_R",0))/2 for s in self._data)/len(self._data)
        avg_target = sum((s.get("target_L",0)+s.get("target_R",0))/2 for s in self._data)/len(self._data)
        avg_pwm = sum((s.get("pwm_L",0)+s.get("pwm_R",0))/2 for s in self._data)/len(self._data)
        mx = max(max(abs(s.get("speed_L",0)),abs(s.get("speed_R",0))) for s in self._data)
        tgt = max(1.0, abs(avg_target))
        overshoot = max(0,(mx/tgt-1)*100)
        speed_ratio = avg_speed / tgt
        ss = sum(errs[len(errs)*7//10:])/max(1,len(errs)-len(errs)*7//10)

        # 计算速度波动（标准差 + 相邻点波动）
        speeds = [(s.get("speed_L",0)+s.get("speed_R",0))/2 for s in self._data]
        avg_spd = sum(speeds)/len(speeds)
        variance = sum((s-avg_spd)**2 for s in speeds)/len(speeds)
        std_dev = variance ** 0.5

        # 相邻采样点间波动 (跳动越小越稳定)
        if len(speeds) > 1:
            fluct = sum(abs(speeds[i]-speeds[i-1]) for i in range(1,len(speeds))) / (len(speeds)-1)
        else:
            fluct = 0

        # 有效值: 速度在 target ± 0.3 内的采样点占比
        valid_threshold = 0.3
        valid_count = sum(1 for s in speeds if abs(s - avg_target) <= valid_threshold)
        valid_ratio = valid_count / len(speeds) if speeds else 0

        # 振荡指标
        osc_ratio = std_dev / tgt * 100

        # 改进的状态判断逻辑
        if speed_ratio > 1.15 or overshoot > 20:
            st = "OVERSPEED"
        elif speed_ratio < 0.6:
            # 速度严重不足（低于目标的60%）- 电机能力不足
            st = "MOTOR_LIMIT"
        elif speed_ratio < 0.8 and std_dev < tgt * 0.1:
            # 速度不足且稳定 - 需要增大P/I
            st = "SLOW_RESPONSE"
        elif osc_ratio > 15 and speed_ratio < 0.9:
            # 速度波动大且未达到目标 - 可能是振荡
            st = "OSCILLATING"
        elif speed_ratio < 0.9:
            # 速度不足
            st = "SLOW_RESPONSE"
        else:
            st = "STABLE"

        return {"status":st,"status_cn":STATUS_CN.get(st,st),"avg_error":round(avg,2),"avg_speed":round(avg_speed,2),"avg_target":round(avg_target,2),"avg_pwm":round(avg_pwm,1),"speed_ratio":round(speed_ratio,2),"overshoot":round(overshoot,2),"steady_state_error":round(ss,2),"oscillation_index":round(osc_ratio,1),"std_dev":round(std_dev,2),"fluctuation":round(fluct,2),"valid_ratio":round(valid_ratio,3),"valid_threshold":round(valid_threshold,1),"sample_count":len(self._data)}

    def to_prompt_data(self) -> str:
        if len(self._data) < 5: return "# Insufficient data"
        m = self.calculate_metrics(); last = self._data[-1]
        lines = ["# MSPM0G3507 Speed PI Data", f"Kp={last.get('Kp','?')}, Ki={last.get('Ki','?')}",
                 f"Target: {last.get('target_L','?')} pulse/20ms", "",
                 f"Status: {m['status']}", f"Avg Error: {m['avg_error']}",
                 f"Avg Speed: {m.get('avg_speed', 0)}",
                 f"Avg Target: {m.get('avg_target', 0)}",
                 f"Avg PWM: {m.get('avg_pwm', 0)}",
                 f"Speed Ratio: {m.get('speed_ratio', 0)}",
                 f"Overshoot: {m['overshoot']:.1f}%", f"Steady State Error: {m['steady_state_error']}",
                 f"Oscillation: {m['oscillation_index']}", "", "idx,speed_L,target,speed_R"]
        step = max(1, len(self._data)//30)
        for i in range(0, len(self._data), step):
            s = self._data[i]
            lines.append(f"{i},{s.get('speed_L',0):.1f},{s.get('target_L',0):.1f},{s.get('speed_R',0):.1f}")
        return "\n".join(lines)
