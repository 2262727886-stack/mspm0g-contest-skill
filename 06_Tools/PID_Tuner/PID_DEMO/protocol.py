"""MSPM0G3507 PID tuner UART protocol shared by GUI and firmware docs."""

BAUD_RATE = 115200
LINE_ENDING = "\r\n"

CSV_FIELDS = (
    "timestamp_ms",
    "speed_L",
    "speed_R",
    "target_L",
    "target_R",
    "pwm_L",
    "pwm_R",
    "Kp",
    "Ki",
)

COMMANDS = {
    "set_pid": "SET P:{p:.4f} I:{i:.4f}",
    "set_pid_d": "SET P:{p:.4f} I:{i:.4f} D:{d:.4f}",
    "target": "TARGET L:{left:d} R:{right:d}",
    "status": "STATUS",
    "reset": "RESET",
    "stop": "STOP",
}

ACK_PATTERNS = {
    "target": r"OK\s+TARGET\s+L=(-?\d+)\s+R=(-?\d+)",
    "status_target": r"TL=(-?\d+)\s+TR=(-?\d+)",
}

PROTOCOL_SUMMARY = (
    "UART 115200 8N1; MCU->PC CSV: "
    + ",".join(CSV_FIELDS)
    + "; PC->MCU commands: SET, TARGET, STATUS, RESET, STOP."
)

def frame(command: str) -> bytes:
    return (command + LINE_ENDING).encode("ascii")
