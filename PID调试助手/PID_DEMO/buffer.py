"""Speed data buffer with metrics calculation for MSPM0G3507 speed PI tuning"""
from typing import Dict, List

class SpeedBuffer:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size; self._data: List[Dict] = []

    def add(self, s: Dict): self._data.append(s); self._data = self._data[-self.max_size:] if len(self._data) > self.max_size else self._data
    def reset(self): self._data.clear()
    def __len__(self): return len(self._data)

    def calculate_metrics(self) -> Dict:
        if len(self._data) < 10: return {"status":"INSUFFICIENT_DATA","avg_error":0,"overshoot":0,"steady_state_error":0,"oscillation_index":0}
        errs = [max(abs(s.get("speed_L",0)-s.get("target_L",0)), abs(s.get("speed_R",0)-s.get("target_R",0))) for s in self._data]
        avg = sum(errs)/len(errs)
        avg_speed = sum((s.get("speed_L",0)+s.get("speed_R",0))/2 for s in self._data)/len(self._data)
        mx = max(max(abs(s.get("speed_L",0)),abs(s.get("speed_R",0))) for s in self._data)
        tgt = max(abs(self._data[0].get("target_L",0)),abs(self._data[0].get("target_R",0))) or 1
        overshoot = max(0,(mx/tgt-1)*100)
        speed_ratio = avg_speed / tgt
        ss = sum(errs[len(errs)*7//10:])/max(1,len(errs)-len(errs)*7//10)
        zc = sum(1 for i in range(1,len(errs)) if (errs[i]-avg)*(errs[i-1]-avg)<0)
        osc = zc/max(1,len(errs))*100
        if speed_ratio > 1.15 or overshoot > 20:
            st = "OVERSPEED"
        elif osc > 25 and avg > 3:
            st = "OSCILLATING"
        elif avg > 10:
            st = "SLOW_RESPONSE"
        else:
            st = "STABLE"
        return {"status":st,"avg_error":round(avg,2),"avg_speed":round(avg_speed,2),"speed_ratio":round(speed_ratio,2),"overshoot":round(overshoot,2),"steady_state_error":round(ss,2),"oscillation_index":round(osc,1),"sample_count":len(self._data)}

    def to_prompt_data(self) -> str:
        if len(self._data) < 5: return "# Insufficient data"
        m = self.calculate_metrics(); last = self._data[-1]
        lines = ["# MSPM0G3507 Speed PI Data", f"Kp={last.get('Kp','?')}, Ki={last.get('Ki','?')}",
                 f"Target: {last.get('target_L','?')} pulse/20ms", "",
                 f"Status: {m['status']}", f"Avg Error: {m['avg_error']}",
                 f"Avg Speed: {m.get('avg_speed', 0)}",
                 f"Speed Ratio: {m.get('speed_ratio', 0)}",
                 f"Overshoot: {m['overshoot']:.1f}%", f"Steady State Error: {m['steady_state_error']}",
                 f"Oscillation: {m['oscillation_index']}", "", "idx,speed_L,target,speed_R"]
        step = max(1, len(self._data)//30)
        for i in range(0, len(self._data), step):
            s = self._data[i]
            lines.append(f"{i},{s.get('speed_L',0):.1f},{s.get('target_L',0):.1f},{s.get('speed_R',0):.1f}")
        return "\n".join(lines)
