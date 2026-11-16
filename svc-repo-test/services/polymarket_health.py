from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_TTL_SECONDS = 60
DEFAULT_TIMEOUT_SECONDS = 3

PROVIDER_PROBES: tuple[dict[str, Any], ...] = (
    {
        "name": "groq",
        "url": "https://api.groq.com/openai/v1/models",
        "key_env": "GROQ_API_KEY",
        "model": "qwen/qwen3.8-27b",
    },
    {
        "name": "cerebras",
        "url": "https://api.cerebras.ai/v1/models",
        "key_env": "CEREBRAS_API_KEY",
        "model": "gpt-oss-120b",
    },
    {
        "name": "ollama",
        "url": "http://localhost:11434/api/tags",
        "key_env": None,
        "model": "qwen2.5:7b",
    },
    {
        "name": "sambanova",
        "url": "https://api.sambanova.ai/v1/models",
        "key_env": "SAMBANOVA_API_KEY",
        "model": "unknown",
    },
    {
        "name": "nvidia",
        "url": "https://integrate.api.nvidia.com/v1/models",
        "key_env": "NVIDIA_API_KEY",
        "model": "unknown",
    },
)

_CACHE: dict[str, Any] = {}
_CACHE_LOCK = threading.Lock()


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(ROOT_DIR / ".env.llm")


def _cache_ttl_seconds() -> int:
    try:
        return int(os.getenv("POLYMARKET_LIVE_TTL", str(DEFAULT_TTL_SECONDS)))
    except ValueError:
        return DEFAULT_TTL_SECONDS


def _probe_timeout_seconds() -> int:
    try:
        return int(os.getenv("POLYMARKET_LIVE_TIMEOUT", str(DEFAULT_TIMEOUT_SECONDS)))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _probe_provider(probe: dict[str, Any]) -> dict[str, Any]:
    key_env = probe.get("key_env")
    key = os.getenv(str(key_env)) if key_env else None
    if key_env and not key:
        return {
            "model": str(probe.get("model") or "unknown"),
            "status": "no_key",
            "http_status": None,
            "latency_ms": 0,
        }
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    started = time.monotonic()
    try:
        response = requests.get(str(probe["url"]), headers=headers, timeout=_probe_timeout_seconds())
        latency_ms = int((time.monotonic() - started) * 1000)
        status = "connected" if response.status_code == 200 else "http_error"
        return {
            "model": str(probe.get("model") or "unknown"),
            "status": status,
            "http_status": response.status_code,
            "latency_ms": latency_ms,
        }
    except requests.Timeout:
        return {
            "model": str(probe.get("model") or "unknown"),
            "status": "timeout",
            "http_status": None,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }
    except requests.RequestException:
        return {
            "model": str(probe.get("model") or "unknown"),
            "status": "unreachable",
            "http_status": None,
            "latency_ms": int((time.monotonic() - started) * 1000),
        }


def get_live_polymarket_health(force: bool = False) -> dict[str, Any]:
    with _CACHE_LOCK:
        now = time.time()
        cached = _CACHE
        if not force and cached and now - cached["checked_at_epoch"] < _cache_ttl_seconds():
            return json.loads(json.dumps(cached))
        _load_env()
        providers = {str(probe["name"]): _probe_provider(probe) for probe in PROVIDER_PROBES}
        snapshot = {
            "source": "live_provider_probe",
            "live": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checked_at_epoch": time.time(),
            "cache_ttl_seconds": _cache_ttl_seconds(),
            "timeout_seconds": _probe_timeout_seconds(),
            "execution_enabled": False,
            # String, not a bool: every other producer of this field
            # (polymarket_manifest, dashboard.html) uses "none", and
            # dashboard.html renders `data_access || '-'`, so False would
            # display as a dash instead of "none".
            "data_access": "none",
            "providers": providers,
        }
        _CACHE.clear()
        _CACHE.update(snapshot)
        return json.loads(json.dumps(_CACHE))