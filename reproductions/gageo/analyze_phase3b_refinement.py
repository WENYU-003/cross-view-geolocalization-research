#!/usr/bin/env python3
"""Analyze per-sample Pi3 stage-11 to final-spatial refinement gains.

The script consumes the frozen-checkpoint Phase-3B per-sample CSV. It reports
within-sample gains and a size/shape-stratified Ground severe-vs-success
comparison. It performs no model inference.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path


COHORTS = ("ground_severe", "ground_success", "drone_success")
METRICS = ("hit1", "hit4", "hit8", "gt_rank", "gt_vs_wrong_margin", "return_margin")
STAGE11 = "pi3_stage_11_spatial"
FINAL = "pi3_final_spatial"


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] * (upper - position) + ordered[upper] * (position - lower)


def percentile_interval(values: list[float]) -> list[float]:
    return [quantile(values, 0.025), quantile(values, 0.975)]


def bootstrap_stat(
    values: list[float],
    statistic,
    iterations: int,
    rng: random.Random,
) -> list[float]:
    n = len(values)
    draws = []
    for _ in range(iterations):
        sample = [values[rng.randrange(n)] for _ in range(n)]
        draws.append(float(statistic(sample)))
    return percentile_interval(draws)


def summarize_gain(
    values: list[float],
    metric: str,
    iterations: int,
    rng: random.Random,
) -> dict[str, object]:
    if metric == "gt_rank":
        improved = sum(value < 0 for value in values)
        degraded = sum(value > 0 for value in values)
    else:
        improved = sum(value > 0 for value in values)
        degraded = sum(value < 0 for value in values)
    tied = len(values) - improved - degraded
    q1, median, q3 = quantile(values, 0.25), quantile(values, 0.5), quantile(values, 0.75)
    return {
        "n": len(values),
        "gain_definition": "final_spatial - stage11_spatial",
        "direction_note": "lower rank is better" if metric == "gt_rank" else "higher is better",
        "mean": statistics.mean(values),
        "mean_bootstrap_ci95": bootstrap_stat(values, statistics.mean, iterations, rng),
        "median": median,
        "median_bootstrap_ci95": bootstrap_stat(values, statistics.median, iterations, rng),
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "proportion_improved": improved / len(values),
        "proportion_degraded": degraded / len(values),
        "proportion_tied": tied / len(values),
    }


def stratified_bootstrap_difference(
    severe: list[dict[str, object]],
    success: list[dict[str, object]],
    metric: str,
    statistic,
    iterations: int,
    rng: random.Random,
) -> list[float]:
    severe_strata: dict[tuple[str, str], list[float]] = defaultdict(list)
    success_strata: dict[tuple[str, str], list[float]] = defaultdict(list)
    for record in severe:
        severe_strata[record["stratum"]].append(float(record[metric]))
    for record in success:
        success_strata[record["stratum"]].append(float(record[metric]))
    if set(severe_strata) != set(success_strata):
        raise ValueError("Ground cohort strata do not match")
    draws = []
    for _ in range(iterations):
        severe_draw: list[float] = []
        success_draw: list[float] = []
        for stratum in severe_strata:
            a, b = severe_strata[stratum], success_strata[stratum]
            severe_draw.extend(a[rng.randrange(len(a))] for _ in range(len(a)))
            success_draw.extend(b[rng.randrange(len(b))] for _ in range(len(b)))
        draws.append(float(statistic(success_draw) - statistic(severe_draw)))
    return percentile_interval(draws)


def load_gains(path: Path) -> tuple[dict[str, list[dict[str, object]]], dict[str, object]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_rows = 570 * 8
    if len(rows) != expected_rows:
        raise ValueError(f"Expected {expected_rows} layer rows, found {len(rows)}")

    by_sample: dict[tuple[str, int], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        sample_key = (row["cohort"], int(row["index"]))
        if row["layer"] in by_sample[sample_key]:
            raise ValueError(f"Duplicate layer for {sample_key}: {row['layer']}")
        by_sample[sample_key][row["layer"]] = row

    output: dict[str, list[dict[str, object]]] = {cohort: [] for cohort in COHORTS}
    runtime_checks = {
        "det_nonzero_difference_count": 0,
        "det_max_absolute_difference": 0.0,
        "mask_nonzero_difference_count": 0,
        "mask_max_absolute_difference": 0.0,
        "interpretation": "Numerical provenance audit only; cohort membership is validated separately.",
    }
    for (cohort, index), layers in by_sample.items():
        if cohort not in output:
            raise ValueError(f"Unexpected cohort: {cohort}")
        if STAGE11 not in layers or FINAL not in layers:
            raise ValueError(f"Missing spatial layer for cohort={cohort}, index={index}")
        stage11, final = layers[STAGE11], layers[FINAL]
        det_difference = abs(float(final["saved_det_iou"]) - float(final["runtime_det_iou"]))
        mask_difference = abs(float(final["saved_mask_iou"]) - float(final["runtime_mask_iou"]))
        if det_difference > 0:
            runtime_checks["det_nonzero_difference_count"] += 1
        if mask_difference > 0:
            runtime_checks["mask_nonzero_difference_count"] += 1
        runtime_checks["det_max_absolute_difference"] = max(
            float(runtime_checks["det_max_absolute_difference"]), det_difference
        )
        runtime_checks["mask_max_absolute_difference"] = max(
            float(runtime_checks["mask_max_absolute_difference"]), mask_difference
        )
        record: dict[str, object] = {
            "index": index,
            "control_id": int(stage11["control_id"]),
            "stratum": (stage11["size_category"], stage11["shape_category"]),
        }
        for metric in METRICS:
            if stage11[metric] == "" or final[metric] == "":
                raise ValueError(f"Missing {metric} for cohort={cohort}, index={index}")
            record[metric] = float(final[metric]) - float(stage11[metric])
        output[cohort].append(record)

    for cohort, records in output.items():
        if len(records) != 190:
            raise ValueError(f"Expected 190 samples for {cohort}, found {len(records)}")
        if len({int(record["index"]) for record in records}) != 190:
            raise ValueError(f"Duplicate sample index in {cohort}")
    return output, runtime_checks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--bootstrap-iterations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20270901)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gains, runtime_checks = load_gains(args.input)
    rng = random.Random(args.seed)
    summary: dict[str, object] = {
        "source": str(args.input),
        "bootstrap_iterations": args.bootstrap_iterations,
        "bootstrap_seed": args.seed,
        "runtime_provenance_checks": runtime_checks,
        "within_cohort_refinement_gain": {},
        "ground_success_minus_ground_severe": {},
        "matched_comparison_note": (
            "control_id matches size/shape/city but not the same scene or target; primary cohort comparison uses "
            "independent resampling within matched size×shape strata, not arbitrary pairwise signed-rank tests."
        ),
    }
    within = summary["within_cohort_refinement_gain"]
    for cohort in COHORTS:
        within[cohort] = {}
        for metric in METRICS:
            values = [float(record[metric]) for record in gains[cohort]]
            within[cohort][metric] = summarize_gain(values, metric, args.bootstrap_iterations, rng)

    comparison = summary["ground_success_minus_ground_severe"]
    severe, success = gains["ground_severe"], gains["ground_success"]
    for metric in METRICS:
        severe_values = [float(record[metric]) for record in severe]
        success_values = [float(record[metric]) for record in success]
        comparison[metric] = {
            "difference_definition": "ground_success_gain - ground_severe_gain",
            "mean_difference": statistics.mean(success_values) - statistics.mean(severe_values),
            "mean_difference_stratified_bootstrap_ci95": stratified_bootstrap_difference(
                severe, success, metric, statistics.mean, args.bootstrap_iterations, rng
            ),
            "median_difference": statistics.median(success_values) - statistics.median(severe_values),
            "median_difference_stratified_bootstrap_ci95": stratified_bootstrap_difference(
                severe, success, metric, statistics.median, args.bootstrap_iterations, rng
            ),
        }

    rendered = json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
        print(f"Wrote {args.output}")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
