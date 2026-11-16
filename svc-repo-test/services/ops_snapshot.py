import time
from typing import Any


def read_ops_snapshot(config: Any, health_input: Any = None, metrics_input: Any = None) -> dict[str, Any]:
    return {
        "timestamp": time.time(),
        "config": config if isinstance(config, dict) else {},
        "health": health_input,
        "metrics": metrics_input,
    }