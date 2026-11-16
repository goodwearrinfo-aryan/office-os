from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any


GIT_TIMEOUT_SECONDS = 5
COMMIT_FIELD_SEPARATOR = "\x1f"


def run_git(repo_path: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), *args],
            check=False,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    output = result.stdout.strip()
    return output or None


def status_metadata(status_output: str | None) -> dict[str, object]:
    if status_output is None:
        return {
            "working_tree": "unknown",
            "dirty": None,
            "ahead": 0,
            "behind": 0,
            "tracking": "unknown",
        }
    lines = status_output.splitlines()
    branch_line = next((line for line in lines if line.startswith("##")), "")
    ahead_match = re.search(r"ahead (\d+)", branch_line)
    behind_match = re.search(r"behind (\d+)", branch_line)
    ahead = int(ahead_match.group(1)) if ahead_match else 0
    behind = int(behind_match.group(1)) if behind_match else 0
    dirty = any(line.strip() for line in lines if not line.startswith("##"))
    return {
        "working_tree": "dirty" if dirty else "clean",
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "tracking": _tracking_label(branch_line, ahead, behind),
    }


def _tracking_label(branch_line: str, ahead: int, behind: int) -> str:
    if "No commits yet" in branch_line:
        return "no commits"
    if "(no branch)" in branch_line:
        return "detached"
    if "..." not in branch_line:
        return "no upstream"
    if "[gone]" in branch_line:
        return "upstream gone"
    if ahead or behind:
        return f"{ahead} ahead / {behind} behind"
    return "up to date"


def repo_git_status(repo_path: Path) -> dict[str, Any]:
    exists = repo_path.is_dir()
    is_git_repo = exists and (repo_path / ".git").exists()
    branch = run_git(repo_path, "rev-parse", "--abbrev-ref", "HEAD") if is_git_repo else None
    commit_line = run_git(repo_path, "log", "-1", f"--format=%H{COMMIT_FIELD_SEPARATOR}%cI") if is_git_repo else None
    commit = None
    last_commit_at = None
    if commit_line:
        commit, _, last_commit_at = commit_line.partition(COMMIT_FIELD_SEPARATOR)
        commit = commit[:12] or None
        last_commit_at = last_commit_at or None
    status = status_metadata(run_git(repo_path, "status", "--porcelain=v1", "--branch") if is_git_repo else None)
    git_status = "ok" if branch and commit else "unavailable"
    return {
        "path": str(repo_path),
        "exists": exists,
        "is_git_repo": is_git_repo,
        "git_status": git_status,
        "branch": branch or "unknown",
        "commit": commit or "unknown",
        "last_commit_at": last_commit_at,
        **status,
    }
