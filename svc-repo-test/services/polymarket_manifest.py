from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

try:
    from services.llm_catalog import CANONICAL_ROUTES
except ImportError:
    from llm_catalog import CANONICAL_ROUTES

VERIFICATION_SNAPSHOT: Mapping[str, Any] = {
    "checked_at": "2026-09-25",
    "source": "polymarket_local_selftest",
    "providers": {
        "groq": {"model": "qwen/qwen3.8-27b", "status": "connected"},
        "cerebras": {"model": "gpt-oss-120b", "status": "http_error", "http_status": 402},
        "ollama": {"model": "qwen2.5:7b", "status": "model_unavailable", "http_status": 404},
        "sambanova": {"status": "no_key"},
        "nvidia": {"status": "partial", "transient_statuses": [429, "timeout"]},
    },
    "checks": {
        "research_tests": "passed",
        "paper_smoke": "passed",
        "compile": "passed",
        "live_orders": False,
    },
}


def get_polymarket_manifest(verification: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "source": "repository_manifest",
        "mode": "paper_only",
        "execution_enabled": False,
        "runtime_state": "unknown",
        "data_access": "none",
        "roles": [
            "market-data",
            "probability",
            "edge-refutation",
            "risk",
            "execution",
            "calibration",
            "reporting",
            "maintenance",
        ],
        "models": [
            {"route": route.route_id, "provider": route.provider, "wire_model": route.wire_model}
            for route in CANONICAL_ROUTES
        ],
        "verification": deepcopy(dict(verification or VERIFICATION_SNAPSHOT)),
    }