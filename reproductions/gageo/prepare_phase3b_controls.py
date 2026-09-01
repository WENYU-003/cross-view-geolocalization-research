#!/usr/bin/env python3
"""Prepare controlled Phase-3B statistics and deterministic audit cohorts.

This script uses only the tracked unseen-test Point-Prompt per-sample CSV. It
does not perform inference and does not claim layer-wise or taxonomy results.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path


MATCH_FIELDS = ("size_category", "shape_category", "city")


def severe(row: dict[str, str]) -> bool:
    return float(row["det_iou"]) == 0.0 and float(row["mask_iou"]) == 0.0


def successful(row: dict[str, str]) -> bool:
    """Strict positive control: both localization outputs overlap GT well."""
    return float(row["det_iou"]) >= 0.5 and float(row["mask_iou"]) >= 0.5


def key(row: dict[str, str]) -> tuple[str, ...]:
    return tuple(row[field] for field in MATCH_FIELDS)


def rr_ci(a: int, n_a: int, b: int, n_b: int) -> dict[str, float | bool]:
    """Risk ratio and Wald log CI; use Haldane correction when a cell is zero."""
    corrected = min(a, n_a - a, b, n_b - b) == 0
    aa, ga, bb, gb = float(a), float(n_a - a), float(b), float(n_b - b)
    if corrected:
        aa, ga, bb, gb = aa + 0.5, ga + 0.5, bb + 0.5, gb + 0.5
    risk_a = aa / (aa + ga)
    risk_b = bb / (bb + gb)
    ratio = risk_a / risk_b
    se = math.sqrt(1.0 / aa - 1.0 / (aa + ga) + 1.0 / bb - 1.0 / (bb + gb))
    return {
        "ground_rate_raw": a / n_a,
        "drone_rate_raw": b / n_b,
        "risk_ratio": ratio,
        "rr_ci95_low": math.exp(math.log(ratio) - 1.96 * se),
        "rr_ci95_high": math.exp(math.log(ratio) + 1.96 * se),
        "zero_cell_corrected": corrected,
    }


def controlled_strata(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    for size in ("small", "medium", "large"):
        for shape in ("regular", "irregular"):
            selected = [r for r in rows if r["size_category"] == size and r["shape_category"] == shape]
            ground = [r for r in selected if r["task_type"] == "ground"]
            drone = [r for r in selected if r["task_type"] == "drone"]
            a, b = sum(severe(r) for r in ground), sum(severe(r) for r in drone)
            stats = rr_ci(a, len(ground), b, len(drone))
            output.append({
                "size": size,
                "shape": shape,
                "ground_severe": a,
                "ground_total": len(ground),
                "drone_severe": b,
                "drone_total": len(drone),
                **stats,
            })
    return output


def sorted_pool(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda r: (r["mono_filename"], r["sat_filename"], int(r["index"])))


def build_matches(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    failures = sorted_pool([r for r in rows if r["task_type"] == "ground" and severe(r)])
    pools: dict[tuple[str, tuple[str, ...]], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not successful(row):
            continue
        pools[(row["task_type"], key(row))].append(row)
    pools = {k: sorted_pool(v) for k, v in pools.items()}
    offsets: dict[tuple[str, tuple[str, ...]], int] = defaultdict(int)
    matches: list[dict[str, str]] = []
    for control_id, failure in enumerate(failures, start=1):
        chosen = {}
        for cohort, task in (("ground_success", "ground"), ("drone_success", "drone")):
            pool_key = (task, key(failure))
            pool = pools.get(pool_key, [])
            if not pool:
                raise RuntimeError(f"No {cohort} match for stratum {key(failure)}")
            position = offsets[pool_key]
            if position >= len(pool):
                raise RuntimeError(f"Insufficient unique {cohort} matches for stratum {key(failure)}")
            chosen[cohort] = pool[position]
            offsets[pool_key] += 1

        for cohort, row in (("ground_severe", failure), *chosen.items()):
            matches.append({
                "control_id": str(control_id),
                "cohort": cohort,
                "index": row["index"],
                "task_type": row["task_type"],
                "size_category": row["size_category"],
                "shape_category": row["shape_category"],
                "city": row["city"],
                "prompt_type": "point",
                "split": "unseen_test",
                "mono_filename": row["mono_filename"],
                "sat_filename": row["sat_filename"],
                "det_iou": row["det_iou"],
                "mask_iou": row["mask_iou"],
            })
    return matches


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=here / "results" / "failure_cmaloc_unseen_point.csv")
    parser.add_argument("--output-dir", type=Path, default=here / "phase3b")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with args.input.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 4197:
        raise ValueError(f"Expected 4197 rows, found {len(rows)}")

    matches = build_matches(rows)
    failures = [row for row in matches if row["cohort"] == "ground_severe"]
    audit_rows = []
    for row in failures:
        audit_rows.append({
            **row,
            "audit_label": "",
            "audit_confidence": "",
            "annotation_valid": "",
            "notes": "",
            "panel_path": "",
        })

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "matched_control_manifest.csv", matches)
    write_csv(args.output_dir / "ground_severe_taxonomy_audit.csv", audit_rows)
    summary = {
        "source_artifact": args.input.name,
        "sample_count": len(rows),
        "prompt_type": "point",
        "split": "unseen_test",
        "matched_fields": list(MATCH_FIELDS),
        "fixed_fields": {"city": "Losangeles", "prompt_type": "point", "split": "unseen_test"},
        "controlled_strata": controlled_strata(rows),
        "cohort_counts": {"ground_severe": 190, "ground_success": 190, "drone_success": 190},
        "success_control_definition": "det_iou >= 0.5 and mask_iou >= 0.5",
        "identifiability_limit": (
            "After exact matching, the tracked CSV has no additional input, pose, patch-area, or annotation-quality "
            "variable that can distinguish Ground severe failures from Ground successes."
        ),
    }
    (args.output_dir / "matched_control_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(matches)} matched cohort rows and {len(audit_rows)} audit rows to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
