"""Update existing NEXUS GitHub Actions WIF provider variables, nothing else.

Run: python scripts/repair_nexus_wif_provider.py --apply
Requires: GitHub CLI authenticated as a repository administrator ('gh auth login').

The script scans existing repository and Environment variable scopes. It only
updates GCP_WIF_PROVIDER when its value exactly matches the incorrect
nexus-main provider resource. It never creates variables or environments,
changes other settings, or grants Google Cloud IAM permissions.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, Sequence

OWNER = "senanurcetin"
BASE = (
    "projects/566421350777/locations/global/"
    "workloadIdentityPools/nexus-gha/providers/"
)
OLD_PROVIDER = BASE + "nexus-main"
NEW_PROVIDER = BASE + "nexus-github-main"
VARIABLE = "GCP_WIF_PROVIDER"

REPOSITORIES = (
    "nexus-commerce-intelligence",
    "nexus-atlas",
    "nexus-devops-intelligence",
    "nexus-web-v2",
    "smart-factory-app",
    "ieee-fraud-detection-analytics",
    "ms-capital-market-forecasting",
    "ot-sentinel",
    "Ops-Copilot",
    "Vision2DCS",
    "gs-quant",
    "datneta-web",
    "football-player-performance-analysis",
)

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Outcome:
    scope: str
    status: str


def run_gh(args: Sequence[str], *, stdin: str | None = None,
           runner: Runner = subprocess.run) -> str:
    result = runner(
        ["gh", *args], input=stdin, text=True,
        capture_output=True, check=False, timeout=50,
    )
    if result.returncode:
        # Error messages may include account details; do not print stderr.
        raise RuntimeError(f"GitHub CLI error {result.returncode}")
    return result.stdout


def flags(repo: str, env: str | None = None) -> list[str]:
    result = ["--repo", f"{OWNER}/{repo}"]
    if env is not None:
        result += ["--env", env]
    return result


def read_var(repo: str, env: str | None = None,
             *, runner: Runner = subprocess.run) -> str | None:
    raw = run_gh(["variable", "list", *flags(repo, env),
                  "--json", "name,value"], runner=runner)
    entries = json.loads(raw)
    if not isinstance(entries, list):
        raise RuntimeError("Unexpected variable list")
    for item in entries:
        if item.get("name") == VARIABLE:
            return str(item.get("value", ""))
    return None


def environments(repo: str, *, runner: Runner = subprocess.run) -> list[str]:
    raw = run_gh([
        "api", f"repos/{OWNER}/{repo}/environments", "--paginate",
        "--jq", ".environments[].name",
    ], runner=runner)
    return sorted({item.strip() for item in raw.splitlines() if item.strip()})


def fix(repo: str, env: str | None, *, apply: bool,
        runner: Runner = subprocess.run) -> Outcome:
    name = f"{OWNER}/{repo} @ {env if env else 'repository'}"
    try:
        current = read_var(repo, env, runner=runner)
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
        return Outcome(name, "ERROR: cannot inspect")
    if current is None:
        return Outcome(name, "SKIP: not configured")
    if current == NEW_PROVIDER:
        return Outcome(name, "OK: already correct")
    if current != OLD_PROVIDER:
        return Outcome(name, "SKIP: different value, preserved")
    if not apply:
        return Outcome(name, "DRY-RUN: old value detected")
    try:
        run_gh(["variable", "set", VARIABLE, *flags(repo, env)],
               stdin=NEW_PROVIDER + "\n", runner=runner)
        verified = read_var(repo, env, runner=runner)
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired):
        return Outcome(name, "ERROR: update/verification failed")
    return Outcome(
        name, "UPDATED" if verified == NEW_PROVIDER
        else "ERROR: verification mismatch",
    )


def main(argv: list[str] | None = None,
         *, runner: Runner = subprocess.run) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes; default is a safe dry-run")
    parser.add_argument("--repo", action="append", choices=REPOSITORIES,
                        help="Limit to one or more known repositories")
    opts = parser.parse_args(argv)
    if runner is subprocess.run and not shutil.which("gh"):
        print("BLOCKED: install GitHub CLI ('gh') and run 'gh auth login'.")
        return 2
    try:
        run_gh(["auth", "status"], runner=runner)
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        print("BLOCKED: authenticate GitHub CLI with repo admin privileges.")
        return 2
    repos = list(dict.fromkeys(opts.repo)) if opts.repo else REPOSITORIES
    results = []
    for repo in repos:
        results.append(fix(repo, None, apply=opts.apply, runner=runner))
        try:
            envs = environments(repo, runner=runner)
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            results.append(Outcome(
                f"{OWNER}/{repo} @ environments", "ERROR: cannot enumerate",
            ))
            continue
        for env in envs:
            results.append(fix(repo, env, apply=opts.apply, runner=runner))
    for item in results:
        print(f"{item.status:38} {item.scope}")
    print(f"Scanned {len(repos)} repositories and {len(results)} scopes. "
          f"Mode: {'APPLY' if opts.apply else 'DRY-RUN'}.")
    print("Note: Google Cloud WIF allowlists/IAM are not modified.")
    return 2 if any(item.status.startswith("ERROR:") for item in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
