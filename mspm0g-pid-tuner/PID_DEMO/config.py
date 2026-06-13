"""Configuration system. Priority: env vars > config.json > defaults"""
import json, os

DEFAULT_CONFIG = {
    "SERIAL_PORT": "AUTO", "BAUD_RATE": 115200,
    "LLM_API_KEY": "sk-your-key-here", "LLM_API_BASE_URL": "https://api.deepseek.com",
    "LLM_MODEL_NAME": "deepseek-v4-pro", "LLM_PROVIDER": "openai",
    "TUNING_MODE": "speed_pi", "BUFFER_SIZE": 100, "MAX_TUNING_ROUNDS": 30,
    "LLM_REQUEST_TIMEOUT": 60, "LLM_DEBUG_OUTPUT": False,
    "GOOD_ENOUGH_AVG_ERROR": 3.0, "GOOD_ENOUGH_STEADY_STATE_ERROR": 1.5,
    "GOOD_ENOUGH_OVERSHOOT": 10.0, "REQUIRED_STABLE_ROUNDS": 3,
    "PID_LIMITS": {
        "p": {"min": 0.1, "max": 50.0, "max_increase_ratio": 3.0},
        "i": {"min": 0.0, "max": 20.0, "max_increase_ratio": 5.0},
        "d": {"min": 0.0, "max": 5.0, "max_increase_ratio": 3.0},
    },
    "PID_MAX_INCREASE_RATIO": 0.0,
    "SIM_MOTOR_PARAMS": {
        "base_speed": 50, "max_speed": 120, "deadzone": 800,
        "inertia": 4, "noise": 0.5, "control_limit": 1200,
    },
    "HTTP_PROXY": "", "HTTPS_PROXY": "", "ALL_PROXY": "", "NO_PROXY": "",
    "CSV_EXPORT_PATH": "",
}

CONFIG = dict(DEFAULT_CONFIG)

def load_config(config_path="config.json"):
    global CONFIG
    CONFIG = dict(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                CONFIG.update(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WARN] Config read failed: {e}")
    else:
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            print(f"[INFO] Generated default config: {config_path}")
        except IOError: pass
    for ek, ck in {"LLM_API_KEY":"LLM_API_KEY","LLM_API_BASE_URL":"LLM_API_BASE_URL","LLM_MODEL_NAME":"LLM_MODEL_NAME","SERIAL_PORT":"SERIAL_PORT","HTTP_PROXY":"HTTP_PROXY","HTTPS_PROXY":"HTTPS_PROXY"}.items():
        if os.environ.get(ek): CONFIG[ck] = os.environ[ek]
    for pk in ("HTTP_PROXY","HTTPS_PROXY","ALL_PROXY"):
        if CONFIG.get(pk) and not os.environ.get(pk): os.environ[pk] = CONFIG[pk]
    return CONFIG
