import threading


RUN_STATE = {
    "running": False,
    "step": None,
    "lines": [],
    "status": None,
    "progress": {"current": 0, "total": 0, "pct": 0.0, "label": ""},
    "lock": threading.Lock(),
}
