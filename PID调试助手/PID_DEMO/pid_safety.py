"""PID safety guardrails for MSPM0G3507 speed loop"""
from typing import Dict, Tuple, Optional

DEFAULT_LIMITS = {
    "p": {"min": 0.1, "max": 50.0, "max_increase_ratio": 3.0},
    "i": {"min": 0.0, "max": 20.0, "max_increase_ratio": 5.0},
    "d": {"min": 0.0, "max": 5.0, "max_increase_ratio": 3.0},
}

def apply_pid_guardrails(current: Dict, candidate: Dict, limits: Optional[Dict] = None) -> Tuple[Dict, str]:
    if limits is None: limits = DEFAULT_LIMITS
    safe = {"p": 0.0, "i": 0.0, "d": 0.0}; notes = []
    for key in ("p", "i", "d"):
        lim = limits.get(key, {}); val = candidate.get(key, 0.0); cur = current.get(key, 0.0)
        val = max(lim.get("min", 0.0), min(lim.get("max", 999.0), val))
        ratio = lim.get("max_increase_ratio", 3.0)
        if cur > 0.01 and abs(val - cur) > cur * ratio:
            direction = 1 if val > cur else -1
            val = cur + direction * cur * ratio
            notes.append(f"{key}: {cur:.3f}->{val:.3f} (x{ratio})")
        safe[key] = val
    return safe, "; ".join(notes) if notes else "no adjustment"

def build_fallback_suggestion(current: Dict, metrics: Dict) -> Dict:
    p, i, d = current.get("p", 3.0), current.get("i", 1.0), current.get("d", 0.0)
    status = metrics.get("status", "STABLE")
    if status == "OSCILLATING": p *= 0.7; d = 0.5
    elif status == "OVERSHOOTING": p *= 0.8; i *= 0.5
    elif status == "SLOW_RESPONSE": p *= 1.3; i = min(i * 1.5, 1.0) if i < 1.0 else i
    else: p *= 0.95
    return {"p": max(0.1, round(p, 3)), "i": max(0.0, round(i, 3)), "d": max(0.0, round(d, 3))}

def should_rollback(current: Dict, best: Dict) -> bool:
    if not best: return False
    cs = current.get("avg_error",0) + current.get("steady_state_error",0)*2
    bs = best.get("avg_error",0) + best.get("steady_state_error",0)*2
    return cs > bs * 1.5

def is_good_enough(metrics: Dict, config: Dict) -> bool:
    return (metrics.get("status") == "STABLE"
        and metrics.get("avg_error", 999) <= config.get("GOOD_ENOUGH_AVG_ERROR", 3.0)
        and metrics.get("steady_state_error", 999) <= config.get("GOOD_ENOUGH_STEADY_STATE_ERROR", 1.5)
        and metrics.get("overshoot", 999) <= config.get("GOOD_ENOUGH_OVERSHOOT", 10.0))
