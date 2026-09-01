#!/usr/bin/env python3
"""Audit aerial/satellite 2D correspondence agreement without DSM or PnP.

For query points occurring in both runs, the script compares the metric map
coordinates predicted by the aerial and satellite matches. It intentionally
does not read ``dsm_z`` or ``inlier_indices`` from the saved NPZ artifacts.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np


DEFAULT_THRESHOLDS_M = (1.0, 3.0, 5.0, 10.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aerial-scene-dir",
        type=Path,
        required=True,
        help="Scene directory containing <sample_id>/result.json and NPZ files.",
    )
    parser.add_argument("--satellite-scene-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--query-threshold-px",
        type=float,
        default=5.0,
        help="Maximum mutual-nearest distance in original UAV-image pixels.",
    )
    parser.add_argument(
        "--agreement-thresholds-m",
        type=float,
        nargs="+",
        default=DEFAULT_THRESHOLDS_M,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional deterministic sample limit for smoke testing.",
    )
    parser.add_argument("--aerial-source-sha256", default=None)
    parser.add_argument("--satellite-source-sha256", default=None)
    return parser.parse_args()


def load_records(scene_dir: Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    for result_path in sorted(scene_dir.glob("*/result.json")):
        record = json.loads(result_path.read_text(encoding="utf-8"))
        sample_id = record.get("sample_id")
        if not sample_id:
            raise ValueError(f"Missing sample_id in {result_path}")
        if sample_id in records:
            raise ValueError(f"Duplicate sample_id {sample_id} in {scene_dir}")
        record["_sample_dir"] = result_path.parent
        records[sample_id] = record
    if not records:
        raise ValueError(f"No per-query result.json files found under {scene_dir}")
    return records


def nearest_indices(
    source: np.ndarray, target: np.ndarray, threshold: float
) -> tuple[np.ndarray, np.ndarray]:
    """Return thresholded nearest target for every source using a spatial hash."""
    if threshold <= 0:
        raise ValueError("query threshold must be positive")
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for target_index, point in enumerate(target):
        cell = (math.floor(point[0] / threshold), math.floor(point[1] / threshold))
        buckets[cell].append(target_index)

    nearest = np.full(len(source), -1, dtype=np.int64)
    distances = np.full(len(source), np.inf, dtype=np.float64)
    threshold_sq = threshold * threshold
    for source_index, point in enumerate(source):
        cell_x = math.floor(point[0] / threshold)
        cell_y = math.floor(point[1] / threshold)
        candidates: list[int] = []
        for offset_x in (-1, 0, 1):
            for offset_y in (-1, 0, 1):
                candidates.extend(buckets.get((cell_x + offset_x, cell_y + offset_y), ()))
        if not candidates:
            continue
        candidate_points = target[candidates]
        squared = np.sum((candidate_points - point) ** 2, axis=1)
        local_index = int(np.argmin(squared))
        if squared[local_index] <= threshold_sq:
            nearest[source_index] = candidates[local_index]
            distances[source_index] = math.sqrt(float(squared[local_index]))
    return nearest, distances


def mutual_pairs(
    aerial_query: np.ndarray, satellite_query: np.ndarray, threshold: float
) -> list[tuple[int, int, float]]:
    satellite_to_aerial, satellite_distance = nearest_indices(
        satellite_query, aerial_query, threshold
    )
    aerial_to_satellite, _ = nearest_indices(aerial_query, satellite_query, threshold)
    pairs: list[tuple[int, int, float]] = []
    for satellite_index, aerial_index in enumerate(satellite_to_aerial):
        if aerial_index < 0:
            continue
        if aerial_to_satellite[aerial_index] == satellite_index:
            pairs.append(
                (int(aerial_index), satellite_index, float(satellite_distance[satellite_index]))
            )
    return pairs


def rankdata(values: np.ndarray) -> np.ndarray:
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    start = 0
    while start < len(values):
        end = start + 1
        while end < len(values) and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = (start + end - 1) / 2.0 + 1.0
        start = end
    return ranks


def spearman(left: Iterable[float], right: Iterable[float]) -> float | None:
    left_array = np.asarray(list(left), dtype=np.float64)
    right_array = np.asarray(list(right), dtype=np.float64)
    if len(left_array) < 2 or left_array.std() == 0 or right_array.std() == 0:
        return None
    return float(np.corrcoef(rankdata(left_array), rankdata(right_array))[0, 1])


def finite_match_arrays(sample_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    artifact_path = sample_dir / "matches_and_pnp_inputs.npz"
    if not artifact_path.exists():
        raise FileNotFoundError(artifact_path)
    with np.load(artifact_path) as artifact:
        required = ("uav_pts_original", "local_x", "local_y")
        missing = [key for key in required if key not in artifact.files]
        if missing:
            raise ValueError(f"Missing {missing} in {artifact_path}")
        query_points = np.asarray(artifact["uav_pts_original"], dtype=np.float64)
        map_points = np.column_stack(
            (
                np.asarray(artifact["local_x"], dtype=np.float64),
                np.asarray(artifact["local_y"], dtype=np.float64),
            )
        )
    if query_points.shape != map_points.shape or query_points.ndim != 2:
        raise ValueError(
            f"Unexpected point shapes in {artifact_path}: "
            f"query={query_points.shape}, map={map_points.shape}"
        )
    finite = np.all(np.isfinite(query_points), axis=1) & np.all(np.isfinite(map_points), axis=1)
    return query_points[finite], map_points[finite]


def failure_group(error_m: float) -> str:
    if error_m <= 3.0:
        return "success_le_3m"
    if error_m <= 20.0:
        return "mid_3_to_20m"
    return "catastrophic_gt_20m"


def validate_pair_metadata(sample_id: str, aerial: dict, satellite: dict) -> None:
    if aerial.get("reference_mode") != "aerial":
        raise ValueError(f"{sample_id}: expected aerial reference record")
    if satellite.get("reference_mode") != "satellite":
        raise ValueError(f"{sample_id}: expected satellite reference record")
    for key in (
        "scene_name",
        "matching_method",
        "pose_priori",
        "match_keypoints",
        "resize_ratio",
        "uav_input_width",
        "uav_input_height",
        "uav_match_width",
        "uav_match_height",
    ):
        if aerial.get(key) != satellite.get(key):
            raise ValueError(
                f"{sample_id}: controlled field {key!r} differs: "
                f"aerial={aerial.get(key)!r}, satellite={satellite.get(key)!r}"
            )
    for key in ("true_x", "true_y", "true_z"):
        if key in aerial and key in satellite and not math.isclose(
            float(aerial[key]), float(satellite[key]), rel_tol=0.0, abs_tol=1e-6
        ):
            raise ValueError(
                f"{sample_id}: ground-truth field {key!r} differs: "
                f"aerial={aerial[key]!r}, satellite={satellite[key]!r}"
            )


def analyze_sample(
    sample_id: str,
    aerial: dict,
    satellite: dict,
    query_threshold_px: float,
    thresholds_m: tuple[float, ...],
) -> dict[str, float | int | str]:
    validate_pair_metadata(sample_id, aerial, satellite)
    aerial_query, aerial_map = finite_match_arrays(aerial["_sample_dir"])
    satellite_query, satellite_map = finite_match_arrays(satellite["_sample_dir"])
    pairs = mutual_pairs(aerial_query, satellite_query, query_threshold_px)
    if not pairs:
        raise ValueError(f"No mutual query-point pairs found for {sample_id}")

    aerial_indices = np.asarray([pair[0] for pair in pairs], dtype=np.int64)
    satellite_indices = np.asarray([pair[1] for pair in pairs], dtype=np.int64)
    query_distances = np.asarray([pair[2] for pair in pairs], dtype=np.float64)
    delta_xy = satellite_map[satellite_indices] - aerial_map[aerial_indices]
    raw_disagreement = np.linalg.norm(delta_xy, axis=1)
    robust_shift = np.median(delta_xy, axis=0)
    residual = np.linalg.norm(delta_xy - robust_shift, axis=1)
    satellite_error = float(satellite["pred_error_m"])

    row: dict[str, float | int | str] = {
        "sample_id": sample_id,
        "aerial_run_id": aerial["_sample_dir"].parents[3].name,
        "satellite_run_id": satellite["_sample_dir"].parents[3].name,
        "num_aerial_matches": len(aerial_query),
        "num_satellite_matches": len(satellite_query),
        "num_mutual_query_pairs": len(pairs),
        "pairing_rate": len(pairs) / min(len(aerial_query), len(satellite_query)),
        "median_query_pair_distance_px": float(np.median(query_distances)),
        "median_xy_disagreement_m": float(np.median(raw_disagreement)),
        "p90_xy_disagreement_m": float(np.quantile(raw_disagreement, 0.90)),
        "robust_shift_x_m": float(robust_shift[0]),
        "robust_shift_y_m": float(robust_shift[1]),
        "robust_shift_norm_m": float(np.linalg.norm(robust_shift)),
        "shift_corrected_median_residual_m": float(np.median(residual)),
        "shift_corrected_p90_residual_m": float(np.quantile(residual, 0.90)),
        "satellite_final_error_m": satellite_error,
        "failure_group": failure_group(satellite_error),
    }
    for threshold in thresholds_m:
        label = f"{threshold:g}m"
        row[f"agreement_{label}"] = float(np.mean(raw_disagreement <= threshold))
        row[f"shift_corrected_agreement_{label}"] = float(np.mean(residual <= threshold))
    return row


def metric_summary(rows: list[dict], metric: str) -> dict[str, float]:
    values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p90": float(np.quantile(values, 0.90)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def build_summary(
    rows: list[dict], thresholds_m: tuple[float, ...], args: argparse.Namespace
) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(row["failure_group"])].append(row)
    key_metrics = [
        "num_mutual_query_pairs",
        "pairing_rate",
        "median_xy_disagreement_m",
        "robust_shift_norm_m",
        "shift_corrected_median_residual_m",
    ]
    for threshold in thresholds_m:
        label = f"{threshold:g}m"
        key_metrics.extend((f"agreement_{label}", f"shift_corrected_agreement_{label}"))
    error = [float(row["satellite_final_error_m"]) for row in rows]
    correlations = {
        metric: spearman((float(row[metric]) for row in rows), error)
        for metric in key_metrics
    }
    return {
        "diagnostic": "DSM-free aerial/satellite cross-reference 2D agreement",
        "uses_dsm_z": False,
        "uses_pnp_or_inliers_to_define_2d_correctness": False,
        "uses_satellite_final_error_for_posthoc_stratification": True,
        "aerial_scene_dir": str(args.aerial_scene_dir.resolve()),
        "satellite_scene_dir": str(args.satellite_scene_dir.resolve()),
        "aerial_source_sha256": args.aerial_source_sha256,
        "satellite_source_sha256": args.satellite_source_sha256,
        "query_threshold_px_original_image": args.query_threshold_px,
        "agreement_thresholds_m": list(thresholds_m),
        "num_queries": len(rows),
        "overall": {metric: metric_summary(rows, metric) for metric in key_metrics},
        "by_failure_group": {
            group: {
                "num_queries": len(group_rows),
                **{metric: metric_summary(group_rows, metric) for metric in key_metrics},
            }
            for group, group_rows in sorted(groups.items())
        },
        "spearman_vs_satellite_final_error": correlations,
        "evidence_boundary": [
            "Aerial correspondences are a high-accuracy pseudo-reference, not manual ground truth.",
            "The XY metric includes aerial/satellite map georegistration differences.",
            "The robust shift separates coherent offset from residual disagreement but cannot identify its cause.",
            "No DSM elevation, PnP result, or PnP inlier label is used to define 2D agreement.",
        ],
    }


def select_representative_cases(rows: list[dict], count_per_group: int = 8) -> list[dict]:
    """Select evenly spaced error quantiles within every predefined group."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        groups[str(row["failure_group"])].append(row)
    selected: list[dict] = []
    for group, group_rows in sorted(groups.items()):
        ordered = sorted(
            group_rows,
            key=lambda row: (float(row["satellite_final_error_m"]), str(row["sample_id"])),
        )
        count = min(count_per_group, len(ordered))
        indices = np.rint(np.linspace(0, len(ordered) - 1, count)).astype(int)
        for quantile_index, row_index in enumerate(indices):
            row = ordered[int(row_index)]
            selected.append(
                {
                    "sample_id": row["sample_id"],
                    "failure_group": group,
                    "selection_rule": "even_error_quantiles_within_group",
                    "selection_quantile": (
                        quantile_index / (count - 1) if count > 1 else 0.5
                    ),
                    "satellite_final_error_m": row["satellite_final_error_m"],
                    "median_xy_disagreement_m": row["median_xy_disagreement_m"],
                    "agreement_3m": row["agreement_3m"],
                    "agreement_5m": row["agreement_5m"],
                    "robust_shift_norm_m": row["robust_shift_norm_m"],
                    "shift_corrected_median_residual_m": row[
                        "shift_corrected_median_residual_m"
                    ],
                }
            )
    return selected


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    thresholds_m = tuple(sorted(set(args.agreement_thresholds_m)))
    aerial_records = load_records(args.aerial_scene_dir)
    satellite_records = load_records(args.satellite_scene_dir)
    if set(aerial_records) != set(satellite_records):
        missing_aerial = sorted(set(satellite_records) - set(aerial_records))
        missing_satellite = sorted(set(aerial_records) - set(satellite_records))
        raise ValueError(
            "Query sets differ: "
            f"missing_aerial={missing_aerial[:10]}, missing_satellite={missing_satellite[:10]}"
        )
    sample_ids = sorted(aerial_records)
    if args.limit is not None:
        if args.limit <= 0:
            raise ValueError("--limit must be positive")
        sample_ids = sample_ids[: args.limit]

    rows = [
        analyze_sample(
            sample_id,
            aerial_records[sample_id],
            satellite_records[sample_id],
            args.query_threshold_px,
            thresholds_m,
        )
        for sample_id in sample_ids
    ]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "cross_reference_2d_query_audit.csv"
    summary_path = args.output_dir / "cross_reference_2d_summary.json"
    shortlist_path = args.output_dir / "representative_case_shortlist.csv"
    write_csv(csv_path, rows)
    write_csv(shortlist_path, select_representative_cases(rows))
    summary = build_summary(rows, thresholds_m, args)
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "csv": str(csv_path),
                "summary": str(summary_path),
                "representative_cases": str(shortlist_path),
                **summary,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
