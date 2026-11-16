from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

try:
    from services.git_status_manifest import repo_git_status
except ImportError:
    from git_status_manifest import repo_git_status


DEFAULT_SOURCE_PATH = Path("/Users/aryanagarwal/openalice-fleet")
DEFAULT_CLONE_PATH = Path("/Users/aryanagarwal/openalice-fleet-clone")

PARITY_FILES: tuple[str, ...] = (
    "office/api.py",
    "office/dashboard.py",
    "office/tests/test_api.py",
    "pytest.ini",
    "scripts/run_quality_gate.py",
    "services/free_harness.py",
    "services/free_harness_server.py",
    "services/git_status_manifest.py",
    "services/llm_catalog.py",
    "services/oa_pubserver.py",
    "services/openalice_clone_manifest.py",
    "services/polymarket_health.py",
    "services/polymarket_manifest.py",
    "services/repo_status_manifest.py",
    "tests/test_free_harness_post.py",
    "tests/test_routing_prefixes.py",
    "tests/test_git_status_manifest.py",
    "tests/test_llm_catalog.py",
    "tests/test_openalice_clone_manifest.py",
    "tests/test_polymarket_health.py",
    "tests/test_polymarket_manifest.py",
    "tests/test_repo_status_manifest.py",
    "ui/public/dashboard.html",
)


def _configured_path(env_name: str, default_path: Path) -> Path:
    return Path(os.getenv(env_name, str(default_path))).expanduser()


def _file_digest(path: Path) -> bytes | None:
    try:
        return hashlib.sha256(path.read_bytes()).digest()
    except (OSError, ValueError):
        return None


def _content_parity(source_path: Path, clone_path: Path) -> dict[str, Any]:
    differing: list[str] = []
    compared = 0
    for relative in PARITY_FILES:
        source_digest = _file_digest(source_path / relative)
        clone_digest = _file_digest(clone_path / relative)
        if source_digest is None and clone_digest is None:
            continue
        compared += 1
        if source_digest != clone_digest:
            differing.append(relative)
    return {
        "content_match": compared > 0 and not differing,
        "files_compared": compared,
        "files_differing": differing,
    }


def get_repo_status_manifest() -> dict[str, Any]:
    source_path = _configured_path("OPENALICE_SOURCE_PATH", DEFAULT_SOURCE_PATH)
    clone_path = _configured_path("OPENALICE_CLONE_PATH", DEFAULT_CLONE_PATH)
    source_status = repo_git_status(source_path)
    clone_status = repo_git_status(clone_path)
    both_available = source_status["git_status"] == "ok" and clone_status["git_status"] == "ok"
    same_commit = both_available and source_status["commit"] == clone_status["commit"]
    parity = _content_parity(source_path, clone_path)
    return {
        "source": "local_git",
        "read_only": True,
        "code_only": True,
        "runtime_data": False,
        "repos": {
            "source": source_status,
            "clone": clone_status,
        },
        "in_sync": same_commit,
        "diverged": both_available and not same_commit,
        "content_parity": parity,
    }
