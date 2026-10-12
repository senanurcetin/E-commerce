#!/usr/bin/env python3
"""Offline policy checks for repository-level GitHub Copilot agent profiles.

This checks this project's explicitly selected agent permissions, not a live
Copilot session or every possible YAML feature. It requires no dependencies,
credentials, CI service or network access.

Usage:
    python scripts/check_copilot_agents.py
    python scripts/check_copilot_agents.py --root ../another-repository
"""
import argparse
import json
import re
from pathlib import Path

ALLOWED_TOOLS = {"read", "search", "edit", "execute"}
REQUIRED_TRUE = (
    "user-invocable",
    "disable-model-invocation",
    "include-custom-instructions",
)
PROPERTY = re.compile(r"^([A-Za-z][A-Za-z0-9-]*):\s*(.*?)\s*$")


def parse_frontmatter(path: Path) -> tuple[dict[str, str], list[str], str]:
    """Read top-level scalar fields from the current flat-profile policy format.

    Nested YAML is intentionally not interpreted. If profile requirements change,
    this policy checker must be updated rather than claiming full YAML parsing.
    """
    errors: list[str] = []
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        return {}, [f"{path.name}: cannot read profile: {exc}"], ""
    lines = source.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, [f"{path.name}: missing opening YAML frontmatter marker"], ""
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        return {}, [f"{path.name}: missing closing YAML frontmatter marker"], ""
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = PROPERTY.fullmatch(line)
        if match is None:
            errors.append(f"{path.name}: unsupported/non-flat frontmatter line: {line!r}")
            continue
        key, value = match.groups()
        if key in fields:
            errors.append(f"{path.name}: duplicate frontmatter field: {key}")
        fields[key] = value
    return fields, errors, "\n".join(lines[end + 1 :]).strip()


def check_repository(root: Path) -> list[str]:
    errors: list[str] = []
    instructions = root / ".github" / "copilot-instructions.md"
    if not instructions.is_file():
        errors.append("missing .github/copilot-instructions.md")
    agents_dir = root / ".github" / "agents"
    profiles = sorted(agents_dir.glob("*.md"))
    if not profiles:
        return errors + ["no custom agent profiles found in .github/agents/"]
    seen_names: set[str] = set()
    for path in profiles:
        fields, malformed, body = parse_frontmatter(path)
        errors.extend(malformed)
        for required in ("name", "description"):
            if not fields.get(required, "").strip().strip('"').strip("'"):
                errors.append(f"{path.name}: missing or empty {required}")
        if len(body) < 80:
            errors.append(f"{path.name}: agent prompt is missing or too short")
        name = fields.get("name", "").strip().strip('"').strip("'")
        if name:
            normalized = name.casefold()
            if normalized in seen_names:
                errors.append(f"{path.name}: duplicate agent name: {name}")
            seen_names.add(normalized)
        for required in REQUIRED_TRUE:
            if fields.get(required) != "true":
                errors.append(f"{path.name}: {required} must be true for this repository policy")
        raw_tools = fields.get("tools")
        if raw_tools is None:
            errors.append(f"{path.name}: explicit tools allowlist required")
            continue
        try:
            tools = json.loads(raw_tools)
        except (TypeError, ValueError):
            errors.append(f"{path.name}: tools must be a JSON-style YAML string array")
            continue
        if not isinstance(tools, list) or not tools or not all(
            isinstance(tool, str) for tool in tools
        ):
            errors.append(f"{path.name}: tools must be a nonempty list of strings")
            continue
        unknown = set(tools) - ALLOWED_TOOLS
        if unknown:
            errors.append(f"{path.name}: unauthorized tool aliases: {sorted(unknown)}")
        if len(tools) != len(set(tools)):
            errors.append(f"{path.name}: duplicated tool names")
        if not {"read", "search"}.issubset(tools):
            errors.append(f"{path.name}: both read and search are required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    errors = check_repository(root)
    if errors:
        print(f"Copilot profile policy FAILED ({len(errors)} issues):")
        for error in errors:
            print(f" - {error}")
        return 1
    print(
        "Copilot profile policy OK: "
        f"{len(list((root / '.github' / 'agents').glob('*.md')))} profiles "
        "(static configuration only; no Copilot execution)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
