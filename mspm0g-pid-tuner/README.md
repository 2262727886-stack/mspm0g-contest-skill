# MSPM0G PID Tuner

[![MCU](https://img.shields.io/badge/MCU-MSPM0G3507-blue)](https://www.ti.com/product/MSPM0G3507)
[![Language](https://img.shields.io/badge/Language-C17%20%2F%20Python%203.10+-yellow)](https://en.wikipedia.org/wiki/C_(programming_language))
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-lightgrey)](https://www.microsoft.com/windows)

**AI-assisted real-time PID tuning for the MSPM0G3507 Tianmengxing competition car.**

The Python tuner reads CSV speed data from the MCU over UART, feeds it to a GPT-class LLM, and the LLM proposes better PI parameters. New parameters are sent back to the MCU, and the cycle repeats until the speed tracking meets the "good enough" criteria — all without human intervention.

---

## Quick Start

### Option A: Pre-built EXE (Windows)

1. Download `mspm0g-pid-tuner.exe` from [Releases](../../releases).
2. Copy `config.example.json` to `config.json` and fill in your OpenAI-compatible API key.
3. Double-click `mspm0g-pid-tuner.exe` (a console window opens and auto-connects).

### Option B: Run from Source (any OS)

```bash
# Clone and enter
git clone <this-repo-url> && cd mspm0g-pid-tuner

# Install dependencies
pip install -r requirements.txt

# Configure (edit config.json with your key)
cp config.example.json config.json

# Launch
python -m mspm0g_tuner.launcher
```

---

## System Architecture

```
┌──────────────────────────────┐      UART0 115200       ┌──────────────────────────────┐
│      MSPM0G3507 (MCU)        │ ◄──────────────────────► │     Python Host (PC)         │
│                              │                          │                              │
│  ┌────────────────────────┐  │   CSV data per 20ms      │  ┌────────────────────────┐  │
│  │ TIMG12 ISR (20ms):     │──┼─────────────────────────►│  │ serial_reader thread   │  │
│  │  read encoders → PI    │  │   timestamp_ms, speed_L, │  │ (pyserial, non-block)  │  │
│  │  → update PWM → CSV out│  │   speed_R, target_L, ... │  └──────────┬─────────────┘  │
│  └────────────────────────┘  │                          │             │                │
│                              │   ◄──────────────────────┼─────────────┘                │
│  ┌────────────────────────┐  │   SET P:3.0 I:1.2        │  ┌────────────────────────┐  │
│  │ UART0 RX ISR:          │  │                          │  │ tuning_loop controller │  │
│  │  parse SET/STATUS/RESET│  │                          │  │  buffer 100 samples    │  │
│  └────────────────────────┘  │                          │  │  compute metrics       │  │
│                              │                          │  │  call LLM API          │  │
│  ┌────────────────────────┐  │                          │  │  send new params       │  │
│  │ PA26 button: start/stop│  │                          │  │  repeat until good     │  │
│  └────────────────────────┘  │                          │  └────────────────────────┘  │
└──────────────────────────────┘                          └──────────────────────────────┘
```

---

## Serial Protocol

### MCU → Host (CSV data line, every 20ms)

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| timestamp_ms | uint32 | ms | System tick counter |
| speed_L | int32 | pulses/20ms | Left wheel pulse count |
| speed_R | int32 | pulses/20ms | Right wheel pulse count |
| target_L | int32 | pulses/20ms | Left wheel target |
| target_R | int32 | pulses/20ms | Right wheel target |
| pwm_L | int32 | 0-4000 | Left PWM duty |
| pwm_R | int32 | 0-4000 | Right PWM duty |
| Kp_L | float | — | Current proportional gain |
| Ki_L | float | — | Current integral gain |

### Host → MCU (commands)

| Command | Action | Example |
|---------|--------|---------|
| `SET P:x I:y` | Update PI gains (clears integrator) | `SET P:3.0 I:1.2` |
| `TARGET L:x R:y` | Set speed target (pulses/20ms) | `TARGET L:100 R:100` |
| `STATUS` | Query current state | `STATUS` |
| `RESET` | Reset to defaults + stop motors | `RESET` |
| `START` | Enable control loop | `START` |
| `STOP` | Disable control loop | `STOP` |

All commands are newline-terminated. Responses are `OK ...` or `ERR ...`.

---

## Tuning Strategy

The LLM-driven tuner uses a **hypothesis-test loop**:

1. **Collect** — Buffer N=100 CSV samples from the MCU at the current PI gains.
2. **Analyze** — Compute rise time, overshoot, steady-state error, and RMSE.
3. **LLM Prompt** — Send the analysis + parameter history to the LLM with:
   - Current P/I values and the metrics they produced.
   - Safety limits (`PID_LIMITS` in config).
   - A request to propose better P/I values.
4. **Apply** — Parse the LLM response, validate bounds, send `SET P:x I:y` to MCU.
5. **Repeat** — Until `GOOD_ENOUGH_*` thresholds are met or `MAX_TUNING_ROUNDS` is reached.

The LLM sees the full tuning history (parameter → performance mapping), enabling it to learn from cumulative data rather than guessing from a single snapshot.

---

## Project Structure

```
mspm0g-pid-tuner/
├── README.md                  ← This file
├── LICENSE                    ← MIT
├── requirements.txt           ← Python dependencies
├── config.example.json        ← Template (copy → config.json)
├── build_exe.bat              ← PyInstaller one-file build script
├── firmware/
│   └── mspm0g_pid_tuner.c     ← MCU firmware (C, SysConfig + driverlib)
└── mspm0g_tuner/
    ├── __init__.py
    ├── launcher.py            ← Entry point
    ├── config.py              ← JSON config loader
    ├── serial_reader.py       ← UART reader (threaded, non-blocking)
    ├── metrics.py             ← Rise time, overshoot, SSE, RMSE
    ├── llm_client.py          ← OpenAI-compatible API client
    └── tuner.py               ← Main tuning loop orchestrator
```

---

## Dependencies

| Component | Dependency | Version |
|-----------|------------|---------|
| Python host | Python | >= 3.10 |
| Python host | pyserial | >= 3.5 |
| Python host | openai (Python SDK) | >= 1.0.0 |
| Python host (build) | PyInstaller | >= 6.0 |
| MCU firmware | TI MSPM0 SDK | 2.10.00.04 |
| MCU firmware | TI Arm Clang Compiler | 3.2.2+ |
| MCU firmware | SysConfig | 1.21+ |
| MCU hardware | MSPM0G3507 LaunchPad | LP-MSPM0G3507 |
| Motor driver | TB6612FNG | — |
| Encoder (left) | TIMG7 QEI mode | MG310 magnetic encoder |
| Encoder (right) | GPIO edge-counting (software 4x) | MG310 magnetic encoder |
| Host LLM | OpenAI GPT-4o (or compatible API) | — |

---

## License

MIT License. See [LICENSE](LICENSE) for details.
