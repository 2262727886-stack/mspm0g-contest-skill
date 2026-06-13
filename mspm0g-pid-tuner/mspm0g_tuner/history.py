"""Tuning history with rollback support"""
from collections import deque
from typing import Dict

class TuningHistory:
    def __init__(self, max_records: int = 5):
        self._records = deque(maxlen=max_records)
        self._best_pid: Dict = {}; self._best_metrics: Dict = {}; self._best_round: int = -1

    def record(self, round_num: int, pid: Dict, metrics: Dict, analysis: str):
        self._records.append({"round":round_num,"p":pid.get("p",0),"i":pid.get("i",0),"d":pid.get("d",0),
            "avg_error":metrics.get("avg_error",0),"overshoot":metrics.get("overshoot",0),
            "status":metrics.get("status","?"),"analysis":analysis[:200]})
        if metrics.get("status") == "STABLE":
            cs = metrics.get("avg_error",999) + metrics.get("steady_state_error",999)*2
            bs = self._best_metrics.get("avg_error",999) + self._best_metrics.get("steady_state_error",999)*2 if self._best_metrics else 999
            if cs < bs: self._best_pid = dict(pid); self._best_metrics = dict(metrics); self._best_round = round_num

    @property
    def best_pid(self) -> Dict: return dict(self._best_pid)
    @property
    def best_metrics(self) -> Dict: return dict(self._best_metrics)

    def to_prompt_text(self) -> str:
        if not self._records: return ""
        lines = ["## Tuning History"]
        for r in self._records:
            lines.append(f"- R{r['round']}: P={r['p']:.3f} I={r['i']:.3f} | Err={r['avg_error']:.1f} Over={r['overshoot']:.1f}% {r['status']} | {r['analysis']}")
        if self._best_pid:
            lines.append(f"\n**Best**: R{self._best_round} P={self._best_pid.get('p',0):.3f} I={self._best_pid.get('i',0):.3f}")
        return "\n".join(lines)
