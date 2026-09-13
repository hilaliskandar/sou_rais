from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "harness" / "rmrp"
ARTIFACTS = ROOT / "artifacts" / "m4a1_rmrp_planning"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(name: str, command: list[str]) -> tuple[int, Path]:
    path = ARTIFACTS / f"{name}.txt"
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    path.write_text(completed.stdout + ("\n[stderr]\n" + completed.stderr if completed.stderr else ""), encoding="utf-8")
    return completed.returncode, path


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HARNESS / "municipios.csv", ROOT / "municipios.csv")
    shutil.copy2(HARNESS / "config.json", ROOT / "config.json")

    base = {
        "gate": "M4A1-T2B-LIVE-PLAN-DRYRUN",
        "capability_id": "employment.municipal_structure",
        "territory_id": "rmrp",
        "municipalities": 34,
        "live_acquisition_executed": False,
        "config_sha256": sha256(ROOT / "config.json"),
        "municipios_sha256": sha256(ROOT / "municipios.csv"),
        "producer_commit": os.getenv("GITHUB_SHA", "UNKNOWN"),
    }

    project = os.getenv("BIGQUERY_PROJECT", "").strip()
    service_account = os.getenv("GCP_SERVICE_ACCOUNT_JSON", "").strip()
    if not project or not service_account:
        manifest = {
            **base,
            "status": "FAILED_CONFIG",
            "credential_available": False,
            "live_plan_executed": False,
            "transferability_state": "UNTESTED",
            "next_action": "configure BIGQUERY_PROJECT and GCP_SERVICE_ACCOUNT_JSON in sou_rais repository secrets",
        }
        (ARTIFACTS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    credential = ARTIFACTS / "gcp-service-account.json"
    credential.write_text(service_account, encoding="utf-8")
    os.chmod(credential, 0o600)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(credential)

    commands = [
        ("doctor", ["sou-rais", "doctor"]),
        ("config", ["sou-rais", "config"]),
        ("plan", ["sou-rais", "plan"]),
        ("download_dry_run", ["sou-rais", "download", "all", "--dry-run"]),
    ]
    results = {}
    failed_stage = None
    for name, command in commands:
        returncode, path = run(name, command)
        results[name] = {"returncode": returncode, "sha256": sha256(path), "bytes": path.stat().st_size}
        if returncode != 0:
            failed_stage = name
            break

    credential.unlink(missing_ok=True)

    if failed_stage:
        manifest = {
            **base,
            "status": "FAILED_CODE_OR_SOURCE",
            "credential_available": True,
            "live_plan_executed": False,
            "failed_stage": failed_stage,
            "results": results,
            "transferability_state": "UNTESTED",
            "next_action": "classify failed stage before any producer change",
        }
    else:
        manifest = {
            **base,
            "status": "SUCCESS",
            "credential_available": True,
            "live_plan_executed": True,
            "commands": [" ".join(command) for _, command in commands],
            "results": results,
            "transferability_state": "HARNESS_VALIDATED",
            "promotion_scope": "planning_and_dryrun_only",
            "next_gate": "M4A1-T2C-CONTROLLED-ACQUISITION-AND-ANALYTICS",
        }

    (ARTIFACTS / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
