"""Fail CI if Git tracks credentials or generated business-data artifacts.

This is a repository hygiene policy, not a comprehensive secret scanner.
It does not read Google Cloud accounts, generate tokens or upload source data.
"""
from __future__ import annotations

from pathlib import Path, PurePosixPath
import re
import subprocess


FORBIDDEN_EXTENSIONS = {".pem", ".p12", ".pfx", ".key", ".duckdb", ".sqlite", ".db"}
FORBIDDEN_FILENAMES = {".env", ".env.local", ".env.production", ".env.prod"}
KEY_MATERIAL = re.compile(
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb'"private_key"\s*:\s*"-----BEGIN',
    flags=re.IGNORECASE,
)


def violation_for_path(path: str) -> str | None:
    path = path.replace("\\", "/")
    pure = PurePosixPath(path)
    name = pure.name.lower()
    parts = {part.lower() for part in pure.parts}
    if "target" in parts:
        return "Generated target/ data must stay outside Git"
    if name.startswith("gha-creds-") and name.endswith(".json"):
        return "Temporary GitHub OIDC credential file"
    if name in FORBIDDEN_FILENAMES:
        return "Environment secret file"
    if pure.suffix.lower() in FORBIDDEN_EXTENSIONS:
        return "Binary key or local source database artifact"
    if name in ("service-account.json", "service_account.json", "credentials.json"):
        return "Service account / credential JSON file"
    return None


def audit(root: Path, tracked: list[str] | None = None) -> list[str]:
    """Only inspect tracked Git paths; allow synthetic committed seeds."""
    root = Path(root)
    if tracked is None:
        listing = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            check=True, capture_output=True,
        )
        tracked = [x.decode("utf-8") for x in listing.stdout.split(b"\0") if x]
    failures = []
    for path in tracked:
        reason = violation_for_path(path)
        if reason:
            failures.append(f"{path}: {reason}")
            continue
        file = root / path
        if (file.suffix.lower() in {".json", ".yml", ".yaml", ".toml", ".txt", ".py"}
                and file.is_file() and file.stat().st_size <= 2_000_000):
            if KEY_MATERIAL.search(file.read_bytes()):
                failures.append(f"{path}: Embedded private key material")
    return failures


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        problems = audit(root)
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        print("BLOCKED: unable to inspect Git-tracked project files")
        return 2
    if problems:
        print("BLOCKED: credential or raw source artifact committed")
        for finding in problems:
            print(" - " + finding)
        return 2
    print("PASS: no tracked local DuckDB, target data or key material")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
