"""Core tuning engine for MSPM0G3507 PID tuning"""
import time
from typing import Dict, Optional, Callable
from .buffer import SpeedBuffer
from .history import TuningHistory
from .pid_safety import apply_pid_guardrails, build_fallback_suggestion, should_rollback, is_good_enough
from .llm.client import LLMTuner

def run_tuning_engine(bridge, config: Dict, current_pid: Dict[str, float],
                      on_round_complete=None, on_sample=None, abort_check=None) -> Dict[str, float]:
    max_rounds = config.get("MAX_TUNING_ROUNDS", 30)
    buffer_size = config.get("BUFFER_SIZE", 100)
    stable_needed = config.get("REQUIRED_STABLE_ROUNDS", 3)
    buffer = SpeedBuffer(max_size=buffer_size)
    history = TuningHistory()
    tuner = LLMTuner(config)
    safe_pid = dict(current_pid); stable_count = 0

    print(f"\n{'='*60}\nMSPM0G3507 PID Tuning Start\nInitial: P={current_pid['p']:.3f} I={current_pid['i']:.3f}\nMax Rounds: {max_rounds}\n{'='*60}")

    for rnd in range(1, max_rounds + 1):
        if abort_check and abort_check(): print("\n[INFO] Aborted"); break
        print(f"\n--- Round {rnd}/{max_rounds} ---")
        buffer.reset(); t0 = time.time()
        if hasattr(bridge, "flush"):
            bridge.flush()
        while len(buffer) < buffer_size and time.time() - t0 < 15.0:
            s = bridge.read_sample()
            if s: buffer.add(s);
            if s and on_sample: on_sample(s)
            else: time.sleep(0.002)

        if len(buffer) < 10: print(f"  Insufficient data ({len(buffer)}), skip"); continue
        metrics = buffer.calculate_metrics()
        print(f"  AvgErr={metrics['avg_error']:.1f} Over={metrics['overshoot']:.1f}% SS={metrics['steady_state_error']:.1f} [{metrics['status']}]")

        if should_rollback(metrics, history.best_metrics) and history.best_pid:
            safe_pid = history.best_pid
            print(f"  [ROLLBACK] -> P={safe_pid['p']:.3f} I={safe_pid['i']:.3f}")
            bridge.set_pid(safe_pid["p"], safe_pid["i"]); stable_count = 0; continue

        if is_good_enough(metrics, config):
            stable_count += 1
            print(f"  Stable {stable_count}/{stable_needed}")
            if stable_count >= stable_needed:
                print(f"\n[CONVERGED] P={safe_pid['p']:.3f} I={safe_pid['i']:.3f}"); break
        else: stable_count = 0

        data_block = buffer.to_prompt_data()
        result = tuner.analyze(data_block, history.to_prompt_text(), config.get("TUNING_MODE","speed_pi"))
        if not result or result.get("p", -1) < 0: result = build_fallback_suggestion(safe_pid, metrics)
        candidate = {"p": result.get("p", safe_pid["p"]), "i": result.get("i", safe_pid["i"]), "d": result.get("d", 0.0)}
        safe_pid, notes = apply_pid_guardrails(safe_pid, candidate)
        if notes != "no adjustment": print(f"  [GUARD] {notes}")
        print(f"  [APPLY] P={safe_pid['p']:.3f} I={safe_pid['i']:.3f} | {result.get('analysis_summary','')}")
        bridge.set_pid(safe_pid["p"], safe_pid["i"])
        time.sleep(0.12)
        if hasattr(bridge, "flush"):
            bridge.flush()
        history.record(rnd, safe_pid, metrics, result.get("analysis_summary", ""))
        if on_round_complete: on_round_complete(rnd, safe_pid, metrics, result)
        time.sleep(0.1)   # 短暂等待 MCU 应用新 PID

    print(f"\n{'='*60}\nDone. Final PID: P={safe_pid['p']:.3f} I={safe_pid['i']:.3f}\n{'='*60}")
    return safe_pid
