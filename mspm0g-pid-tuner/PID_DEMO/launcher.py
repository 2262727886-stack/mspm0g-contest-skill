#!/usr/bin/env python3
"""MSPM0G PID Tuner Launcher"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    print_banner(); mode = "menu"; config_path = "config.json"
    args = sys.argv[1:]
    while args:
        a = args.pop(0)
        if a == "--hardware": mode = "hardware"
        elif a == "--sim": mode = "sim"
        elif a == "--config" and args: config_path = args.pop(0)
        elif a in ("-h","--help"): print_help(); return

    from PID_DEMO.config import load_config
    config = load_config(config_path)
    if mode == "menu": mode = show_menu()
    if mode == "hardware": run_hardware(config)
    elif mode == "sim": run_simulation(config)
    else: print("Goodbye!")

def print_banner():
    print(r"""
  __  __ _____ _____ __  __  ___    _____ ___ ___   _____ _  _ _____ ___
 |  \/  / ____|  __ \  \/  |/ _ \  / ____|__ \__ \ |_   _| | | |_   _| __|
 | \  /| (___ | |__) | \  / | | | | |  __   ) | ) |   | | | |_| | | | | _|
 | |\/| \___ \|  ___/| |\/| | | | | | |_ | / / / /    | | |  _  | | | | |_
 | |  | ____) | |    | |  | | |_| | |__| |/ /_/ /_   _| |_| | | |_| |_|__|
 |_|  |_|_____/|_|    |_|  |_|\___/ \_____|____|____| |_____|_| |_|_____|____|
         MSPM0G3507 Competition Car PID Auto-Tuner
    """)

def show_menu() -> str:
    print("Select mode:\n  [1] Hardware tuning (serial)\n  [2] Simulation (no hardware)\n  [3] Exit")
    try:
        c = input("\nChoice: ").strip()
        if c == "1": return "hardware"
        elif c == "2": return "sim"
    except: pass
    return "quit"

def run_hardware(config):
    print("\n--- Hardware Mode ---\n")
    from PID_DEMO.bridge import SerialBridge
    bridge = SerialBridge(port=config.get("SERIAL_PORT","AUTO"), baud=config.get("BAUD_RATE",115200))
    if not bridge.connect(): return
    status = bridge.get_status()
    if status: print(f"  MCU: {status}")
    try:
        t = int(input("  Target speed (pulse/20ms, default 60): ") or "60")
        bridge.set_target(t, t)
    except: t = 60
    input("\n  Ensure car is lifted/wheels free. Press Enter to start...")
    current = {"p": 3.0, "i": 1.0, "d": 0.0}
    from PID_DEMO.engine import run_tuning_engine
    try:
        final = run_tuning_engine(bridge=bridge, config=config, current_pid=current)
        print(f"\nOptimal PID: P={final['p']:.3f} I={final['i']:.3f}")
        print(f"  #define SPEED_KP  {final['p']:.3f}f")
        print(f"  #define SPEED_KI  {final['i']:.3f}f")
    except KeyboardInterrupt: print("\n[INFO] Interrupted")
    finally: bridge.disconnect()

def run_simulation(config):
    print("\n--- Simulation Mode ---\n")
    from PID_DEMO.car_model import CarSimulator
    from PID_DEMO.buffer import SpeedBuffer
    from PID_DEMO.history import TuningHistory
    from PID_DEMO.pid_safety import apply_pid_guardrails, build_fallback_suggestion, is_good_enough
    from PID_DEMO.llm.client import LLMTuner
    sim = CarSimulator(); tuner = LLMTuner(config); history = TuningHistory()
    current = {"p": 1.0, "i": 0.0, "d": 0.0}; sim.set_pid(**current)
    max_r = config.get("MAX_TUNING_ROUNDS", 15)
    print(f"Initial: P={current['p']:.1f} I={current['i']:.1f} Target={sim.target}\n")
    for rnd in range(1, max_r+1):
        buf = SpeedBuffer(100)
        for s in sim.collect_samples(100): buf.add(s)
        m = buf.calculate_metrics()
        print(f"R{rnd}: Err={m['avg_error']:.1f} Over={m['overshoot']:.1f}% [{m['status']}]")
        if is_good_enough(m, config): print(f"  Converged! P={current['p']:.3f} I={current['i']:.3f}"); break
        res = tuner.analyze(buf.to_prompt_data(), history.to_prompt_text())
        if res.get("p",-1)<0: res = build_fallback_suggestion(current, m)
        cand = {"p":res["p"],"i":res["i"],"d":res.get("d",0)}
        safe, notes = apply_pid_guardrails(current, cand)
        if notes != "no adjustment": print(f"  Guard: {notes}")
        print(f"  -> P={safe['p']:.3f} I={safe['i']:.3f} | {res.get('analysis_summary','')}")
        sim.set_pid(**safe); current = safe
        history.record(rnd, safe, m, res.get("analysis_summary",""))
    print("\nSimulation done!")

def print_help():
    print("MSPM0G PID Tuner\nUsage: python launcher.py [--hardware|--sim] [--config FILE]")

if __name__ == "__main__": main()
