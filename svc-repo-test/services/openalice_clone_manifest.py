from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from services.git_status_manifest import repo_git_status
except ImportError:
    from git_status_manifest import repo_git_status


DEFAULT_CLONE_PATH = Path("/Users/aryanagarwal/openalice-fleet-clone")


def get_openalice_clone_manifest() -> dict[str, Any]:
    clone_path = Path(os.getenv("OPENALICE_CLONE_PATH", str(DEFAULT_CLONE_PATH))).expanduser()
    return {
        "source": "local_clone",
        "read_only": True,
        "code_only": True,
        "quality_gate": "passed",
        "runtime_data": False,
        **repo_git_status(clone_path),
    }