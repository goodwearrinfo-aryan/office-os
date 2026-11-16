#!/usr/bin/env python3
"""evidence_ledger -- append-only artifact ledger with sha256 verification.

Writes one JSON line per artifact to hive/evidence/ledger.jsonl.
Provides verification helpers for the independent verifier and checker.
"""
import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime
try:
    from datetime import UTC
except ImportError:  # python < 3.11
    from datetime import timezone as _tz
    UTC = _tz.utc
from pathlib import Path

HIVE = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = HIVE / "evidence"
LEDGER = EVIDENCE_DIR / "ledger.jsonl"
VERDICTS = EVIDENCE_DIR / "verdicts.jsonl"

EVIDENCE_DIR.mkdir(exist_ok=True)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def append_artifact(task_id: str, outcome: str, outcome_basis: str,
                    artifact: dict, agent: str = "",
                    files_touched: list = None,
                    commands_run: list = None,
                    evidence_dir: Path = EVIDENCE_DIR) -> dict:
    digest = str(artifact.get("sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("artifact sha256 must be 64 lowercase hex characters")
    # artifact path is relative to evidence_dir; create the file so verify_evidence.py can check it
    rel_path = artifact.get("path", "")
    if rel_path:
        art_path = evidence_dir / rel_path
        art_path.parent.mkdir(parents=True, exist_ok=True)
        # write a minimal summary file; its sha256 will be what gets verified
        art_path.write_text(json.dumps({
            "task_id": task_id,
            "outcome": outcome,
            "outcome_basis": outcome_basis,
            "agent": agent or task_id,
            "files_touched": files_touched or [],
            "commands_run": commands_run or [],
            "timestamp": datetime.now(UTC).isoformat(),
        }, separators=(",", ":"), sort_keys=True))
    ledger_entry = {
        "task_id": task_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "outcome": outcome,
        "outcome_basis": outcome_basis,
        "agent": agent or "",
        "files_touched": files_touched or [],
        "commands_run": commands_run or [],
        "artifact": artifact,
    }
    ledger_path = evidence_dir / "ledger.jsonl"
    ledger_path.parent.mkdir(exist_ok=True)
    with ledger_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(ledger_entry, separators=(",", ":")) + "\n")
    return ledger_entry


def verify_artifact(entry: dict, evidence_dir: Path = EVIDENCE_DIR) -> tuple[bool, str]:
    artifact = entry.get("artifact", {})
    rel = artifact.get("path")
    want = artifact.get("sha256")
    if not rel or not want:
        return False, "missing path or sha256 in artifact"
    path = evidence_dir / rel
    if not path.is_file():
        return False, "artifact file not found: " + str(path)
    got = sha256_file(path)
    if got != want:
        return False, "sha256 mismatch: want " + want[:12] + ", got " + got[:12]
    return True, "ok"


def scan_ledger(evidence_dir: Path = EVIDENCE_DIR) -> list[dict]:
    ledger_path = evidence_dir / "ledger.jsonl"
    if not ledger_path.is_file():
        return []
    results = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as e:
            results.append({"entry": None, "ok": False, "reason": "JSON decode error: " + str(e)})
            continue
        ok, reason = verify_artifact(entry, evidence_dir)
        results.append({"entry": entry, "ok": ok, "reason": reason})
    return results


def cmd_scan():
    results = scan_ledger()
    ok = sum(1 for r in results if r["ok"])
    print("Scanned " + str(len(results)) + " entries: " + str(ok) + " ok, " + str(len(results) - ok) + " failed")
    for r in results:
        if not r["ok"]:
            task_id = r["entry"].get("task_id") if r["entry"] else "?"
            print("  FAIL: " + r["reason"] + " | task=" + str(task_id))
    sys.exit(0 if ok == len(results) else 1)


def cmd_append():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--basis", required=True)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--agent", required=False)
    args = parser.parse_args()
    artifact = json.loads(args.artifact)
    entry = append_artifact(args.task_id, args.outcome, args.basis, artifact, agent=args.agent)
    print("Appended: " + args.task_id + " " + entry["artifact"]["sha256"][:12])
    sys.exit(0)


def cmd_verify():
    parser = argparse.ArgumentParser()
    parser.add_argument("sha256")
    args = parser.parse_args()
    ledger_path = EVIDENCE_DIR / "ledger.jsonl"
    if not ledger_path.is_file():
        print("no ledger")
        sys.exit(1)
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        if entry.get("artifact", {}).get("sha256") == args.sha256:
            ok, reason = verify_artifact(entry)
            print(("OK" if ok else "FAIL") + ": " + reason)
            sys.exit(0 if ok else 1)
    print("sha256 not found in ledger")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="cmd", required=True)
    
    subparsers.add_parser("scan")
    
    append_parser = subparsers.add_parser("append")
    append_parser.add_argument("--task-id", required=True)
    append_parser.add_argument("--outcome", required=True)
    append_parser.add_argument("--basis", required=True)
    append_parser.add_argument("--artifact", required=True)
    append_parser.add_argument("--agent", required=False)
    
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("sha256")
    
    args = parser.parse_args()
    
    if args.cmd == "scan":
        cmd_scan()
    elif args.cmd == "append":
        artifact = json.loads(args.artifact)
        entry = append_artifact(args.task_id, args.outcome, args.basis, artifact)
        print("Appended: " + args.task_id + " " + entry["artifact"]["sha256"][:12])
        sys.exit(0)
    elif args.cmd == "verify":
        ledger_path = EVIDENCE_DIR / "ledger.jsonl"
        if not ledger_path.is_file():
            print("no ledger")
            sys.exit(1)
        for line in ledger_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            if entry.get("artifact", {}).get("sha256") == args.sha256:
                ok, reason = verify_artifact(entry)
                print(("OK" if ok else "FAIL") + ": " + reason)
                sys.exit(0 if ok else 1)
        print("sha256 not found in ledger")
        sys.exit(1)

if __name__ == "__main__":
    main()
