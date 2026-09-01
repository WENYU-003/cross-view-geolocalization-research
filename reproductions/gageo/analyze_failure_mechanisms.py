#!/usr/bin/env python3
"""Analyze GAGeo failure mechanisms from tracked Phase-2 artifacts only.

The analysis controls task differences by saved size/shape strata, measures the
catastrophic lower tail, checks bbox/mask error coupling, and compares prompt
effects from the grouped JSON files. It performs no model inference.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def pearson(xs: list[float], ys: list[float]) -> float:
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    return numerator / (denom_x * denom_y)


def risk_ratio(a: int, n_a: int, b: int, n_b: int) -> dict[str, float]:
    ratio = (a / n_a) / (b / n_b)
    standard_error = math.sqrt(1 / a - 1 / n_a + 1 / b - 1 / n_b)
    return {
        "ground_rate": a / n_a,
        "drone_rate": b / n_b,
        "risk_difference": a / n_a - b / n_b,
        "risk_ratio": ratio,
        "rr_ci95_low": math.exp(math.log(ratio) - 1.96 * standard_error),
        "rr_ci95_high": math.exp(math.log(ratio) + 1.96 * standard_error),
    }


def is_severe(row: dict[str, str]) -> bool:
    return float(row["det_iou"]) == 0.0 and float(row["mask_iou"]) == 0.0


def task_tail(rows: list[dict[str, str]], task: str, size: str | None = None) -> dict:
    selected = [
        row for row in rows
        if row["task_type"] == task and (size is None or row["size_category"] == size)
    ]
    output = {"count": len(selected), "severe": sum(is_severe(row) for row in selected)}
    for metric in ("det_iou", "mask_iou"):
        values = [float(row[metric]) for row in selected]
        output[metric] = {
            "mean": statistics.mean(values),
            "q01": quantile(values, 0.01),
            "q05": quantile(values, 0.05),
            "q10": quantile(values, 0.10),
            "q25": quantile(values, 0.25),
            "median": quantile(values, 0.50),
        }
    return output


def zero_and_head_coupling(rows: list[dict[str, str]], task: str) -> dict:
    selected = rows if task == "overall" else [row for row in rows if row["task_type"] == task]
    det = [float(row["det_iou"]) for row in selected]
    mask = [float(row["mask_iou"]) for row in selected]
    det_zero = sum(value == 0.0 for value in det)
    mask_zero = sum(value == 0.0 for value in mask)
    both_zero = sum(x == 0.0 and y == 0.0 for x, y in zip(det, mask))
    return {
        "count": len(selected),
        "det_zero": det_zero,
        "mask_zero": mask_zero,
        "both_zero": both_zero,
        "p_mask_zero_given_det_zero": both_zero / det_zero,
        "p_det_zero_given_mask_zero": both_zero / mask_zero,
        "det_mask_pearson": pearson(det, mask),
    }


def grouped_record(results_dir: Path, prompt: str, group: str) -> dict:
    payload = json.loads((results_dir / f"unseen_test_{prompt}.json").read_text(encoding="utf-8"))
    return payload["unseen_test"][prompt][group]


def prompt_effects(results_dir: Path) -> dict:
    output = {}
    for task in ("drone", "ground"):
        output[task] = {}
        for size in (None, "small", "medium", "large"):
            label = size or "all"
            group = f"task/{task}" if size is None else f"task×size/{task}/{size}"
            point = grouped_record(results_dir, "point", group)
            mask = grouped_record(results_dir, "mask", group)
            output[task][label] = {
                "mask_minus_point_det_avg_acc_pp": 100.0 * (mask["det_avg_acc"] - point["det_avg_acc"]),
                "mask_minus_point_model_miou_pp": 100.0 * (mask["model_miou"] - point["model_miou"]),
                "mask_minus_point_rotation_error_deg": mask["rotation_error_deg"] - point["rotation_error_deg"],
                "mask_minus_point_pos_err_px": mask["pos_err_px"] - point["pos_err_px"],
            }
    return output


def geometry_by_size(results_dir: Path) -> dict:
    output = {}
    for size in ("small", "medium", "large"):
        drone = grouped_record(results_dir, "point", f"task×size/drone/{size}")
        ground = grouped_record(results_dir, "point", f"task×size/ground/{size}")
        output[size] = {
            "ground_minus_drone_det_avg_acc_pp": 100.0 * (ground["det_avg_acc"] - drone["det_avg_acc"]),
            "ground_minus_drone_model_miou_pp": 100.0 * (ground["model_miou"] - drone["model_miou"]),
            "ground_minus_drone_rotation_error_deg": ground["rotation_error_deg"] - drone["rotation_error_deg"],
            "ground_minus_drone_pos_err_px": ground["pos_err_px"] - drone["pos_err_px"],
        }
    return output


def severe_effects(rows: list[dict[str, str]]) -> dict:
    output = {}
    strata = {
        "overall": (lambda row: True),
        "small": (lambda row: row["size_category"] == "small"),
        "medium": (lambda row: row["size_category"] == "medium"),
        "large": (lambda row: row["size_category"] == "large"),
        "regular": (lambda row: row["shape_category"] == "regular"),
        "irregular": (lambda row: row["shape_category"] == "irregular"),
    }
    for label, condition in strata.items():
        ground = [row for row in rows if row["task_type"] == "ground" and condition(row)]
        drone = [row for row in rows if row["task_type"] == "drone" and condition(row)]
        output[label] = risk_ratio(
            sum(is_severe(row) for row in ground), len(ground),
            sum(is_severe(row) for row in drone), len(drone),
        )

    ground_size_standardized = statistics.mean(output[size]["ground_rate"] for size in ("small", "medium", "large"))
    drone_size_standardized = statistics.mean(output[size]["drone_rate"] for size in ("small", "medium", "large"))
    output["equal_size_standardization"] = {
        "ground_rate": ground_size_standardized,
        "drone_rate": drone_size_standardized,
        "risk_ratio": ground_size_standardized / drone_size_standardized,
    }
    return output


def parse_args() -> argparse.Namespace:
    default_dir = Path(__file__).resolve().parent / "results"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=default_dir)
    parser.add_argument("--output", type=Path, default=None, help="Optional derived JSON output path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    with (results_dir / "failure_cmaloc_unseen_point.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    summary = {
        "source_rows": len(rows),
        "cities": dict(Counter(row["city"] for row in rows)),
        "severe_effects": severe_effects(rows),
        "error_tails": {
            task: {size: task_tail(rows, task, None if size == "all" else size) for size in ("all", "small", "medium", "large")}
            for task in ("drone", "ground")
        },
        "head_coupling": {task: zero_and_head_coupling(rows, task) for task in ("overall", "drone", "ground")},
        "prompt_effects": prompt_effects(results_dir),
        "geometry_by_size": geometry_by_size(results_dir),
    }
    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output is not None:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote derived summary: {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
