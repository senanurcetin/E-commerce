#!/usr/bin/env python3
"""Inspect notebook output size and optionally create a non-destructive clean copy."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def cells_signature(notebook: dict) -> list[tuple[str, str]]:
    """Preserve every cell's type and original source exactly."""
    return [
        (cell.get("cell_type", ""), json.dumps(cell.get("source", ""), ensure_ascii=False))
        for cell in notebook.get("cells", [])
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", type=Path,
        default=Path("notebooks/olist-ecommerce-analysis.ipynb"),
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Write a NEW notebook with code-cell outputs and execution counters cleared.",
    )
    parser.add_argument(
        "--dest", type=Path,
        help="Required with --clean. Do not point at the original notebook.",
    )
    parser.add_argument(
        "--acknowledge-output-loss", action="store_true",
        help="Required before generating a copy without embedded Plotly charts.",
    )
    args = parser.parse_args()
    if args.clean != (args.dest is not None):
        parser.error("--clean requires --dest, and --dest requires --clean")
    if args.dest and args.source.resolve() == args.dest.resolve():
        parser.error("Never overwrite the original notebook; choose a different --dest")

    raw = args.source.read_bytes()
    original = json.loads(raw)
    if not isinstance(original.get("cells"), list):
        parser.error("The input is not a notebook with a cell list")

    n_code = n_outputs = n_images = n_plotly_html = 0
    output_bytes = 0
    for cell in original["cells"]:
        if cell.get("cell_type") != "code":
            continue
        n_code += 1
        for item in cell.get("outputs", []):
            n_outputs += 1
            if "image/png" in item.get("data", {}):
                n_images += 1
            if "text/html" in item.get("data", {}):
                html = item["data"]["text/html"]
                html = "".join(html) if isinstance(html, list) else str(html)
                if "Plotly" in html or "plotly" in html:
                    n_plotly_html += 1
            output_bytes += len(json.dumps(item, ensure_ascii=False).encode("utf-8"))

    print(f"Original file: {len(raw):,} bytes")
    print(f"Code cells: {n_code}; outputs: {n_outputs}; embedded PNG outputs: {n_images}")
    print(f"Serialized output payload estimate: {output_bytes:,} bytes")
    print(f"Plotly HTML output(s) retained: {n_plotly_html}")
    if not args.clean:
        print("No file changed. Review plots before deciding which evidence to retain.")
        return

    if n_plotly_html and not args.acknowledge_output_loss:
        parser.error(
            f"Refusing to remove {n_plotly_html} interactive Plotly outputs. "
            "The charts are project evidence, not just caches. Use "
            "--acknowledge-output-loss only for an explicitly reviewed "
            "temporary copy; never commit it as a replacement without "
            "an equivalent chart-preserving export."
        )

    before = cells_signature(original)
    for cell in original["cells"]:
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None

    assert cells_signature(original) == before, "Code or markdown source changed unexpectedly"
    args.dest.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(original, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    args.dest.write_bytes(serialized)
    reloaded = json.loads(args.dest.read_text(encoding="utf-8"))
    assert cells_signature(reloaded) == before, "Source verification failed after writing"
    print(f"Clean COPY: {args.dest} ({len(serialized):,} bytes)")
    print("Original remains untouched. Review both notebooks before replacing/committing.")


if __name__ == "__main__":
    main()
