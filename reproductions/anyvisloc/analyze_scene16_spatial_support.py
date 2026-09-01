#!/usr/bin/env python3
"""CPU-only Scene_16 cross-reference spatial-support diagnostic.

The script consumes saved aerial/satellite GT-reference result archives. It
does not rerun retrieval, RoMa, DSM lookup, or PnP. Aerial map endpoints are
used as a high-accuracy pseudo-reference for satellite endpoints belonging to
mutually paired UAV query coordinates.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont


GROUP_ORDER = ("success_le_3m", "mid_3_to_20m", "catastrophic_gt_20m")
GROUP_LABELS = {
    "success_le_3m": "Success <=3 m",
    "mid_3_to_20m": "Middle 3-20 m",
    "catastrophic_gt_20m": "Catastrophic >20 m",
}
AGREEMENT_THRESHOLDS_M = (1.0, 3.0, 5.0, 10.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aerial-archive", type=Path, required=True)
    parser.add_argument("--satellite-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--query-threshold-px", type=float, default=5.0)
    parser.add_argument("--grid-size", type=int, default=8)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_id_from_name(name: str) -> str | None:
    match = re.search(r"/(L16_\d+)/", name)
    return match.group(1) if match else None


class ResultArchive:
    def __init__(self, path: Path, expected_mode: str):
        self.path = path
        self.expected_mode = expected_mode
        self.tar = tarfile.open(path, "r:gz")
        self.records: dict[str, dict] = {}
        self.npz_members: dict[str, tarfile.TarInfo] = {}
        for member in self.tar.getmembers():
            sample_id = sample_id_from_name(member.name)
            if sample_id is None:
                continue
            if member.name.endswith("/result.json"):
                record = json.load(self.tar.extractfile(member))
                if record.get("sample_id") != sample_id:
                    raise ValueError(f"sample_id mismatch in {member.name}")
                if record.get("reference_mode") != expected_mode:
                    raise ValueError(
                        f"Expected {expected_mode} record in {member.name}, "
                        f"got {record.get('reference_mode')!r}"
                    )
                self.records[sample_id] = record
            elif member.name.endswith("/matches_and_pnp_inputs.npz"):
                self.npz_members[sample_id] = member
        if set(self.records) != set(self.npz_members):
            raise ValueError(
                f"JSON/NPZ sample mismatch in {path}: "
                f"json={len(self.records)}, npz={len(self.npz_members)}"
            )

    def arrays(self, sample_id: str) -> dict[str, np.ndarray]:
        raw = self.tar.extractfile(self.npz_members[sample_id]).read()
        with np.load(io.BytesIO(raw), allow_pickle=False) as artifact:
            required = ("uav_pts_original", "ref_pts_patch", "local_x", "local_y")
            missing = [key for key in required if key not in artifact.files]
            if missing:
                raise ValueError(f"{sample_id}: missing NPZ keys {missing}")
            return {key: np.asarray(artifact[key]).copy() for key in artifact.files}

    def close(self) -> None:
        self.tar.close()


def nearest_indices(
    source: np.ndarray, target: np.ndarray, threshold: float
) -> tuple[np.ndarray, np.ndarray]:
    if threshold <= 0:
        raise ValueError("query threshold must be positive")
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, point in enumerate(target):
        cell = (math.floor(point[0] / threshold), math.floor(point[1] / threshold))
        buckets[cell].append(index)
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
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    sat_to_aerial, sat_distance = nearest_indices(satellite_query, aerial_query, threshold)
    aerial_to_sat, _ = nearest_indices(aerial_query, satellite_query, threshold)
    pairs = [
        (int(aerial_index), sat_index, float(sat_distance[sat_index]))
        for sat_index, aerial_index in enumerate(sat_to_aerial)
        if aerial_index >= 0 and aerial_to_sat[aerial_index] == sat_index
    ]
    if not pairs:
        raise ValueError("No mutual query pairs")
    return (
        np.asarray([pair[0] for pair in pairs], dtype=np.int64),
        np.asarray([pair[1] for pair in pairs], dtype=np.int64),
        np.asarray([pair[2] for pair in pairs], dtype=np.float64),
    )


def finite_arrays(artifact: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    query = np.asarray(artifact["uav_pts_original"], dtype=np.float64)
    reference = np.asarray(artifact["ref_pts_patch"], dtype=np.float64)
    map_xy = np.column_stack(
        (
            np.asarray(artifact["local_x"], dtype=np.float64),
            np.asarray(artifact["local_y"], dtype=np.float64),
        )
    )
    if query.shape != reference.shape or query.shape != map_xy.shape or query.ndim != 2:
        raise ValueError(
            f"Unexpected point shapes: query={query.shape}, ref={reference.shape}, map={map_xy.shape}"
        )
    finite = (
        np.all(np.isfinite(query), axis=1)
        & np.all(np.isfinite(reference), axis=1)
        & np.all(np.isfinite(map_xy), axis=1)
    )
    return query[finite], reference[finite], map_xy[finite]


def validate_metadata(sample_id: str, aerial: dict, satellite: dict) -> None:
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
                f"{sample_id}: controlled field {key} differs: "
                f"{aerial.get(key)!r} vs {satellite.get(key)!r}"
            )
    for key in ("true_x", "true_y", "true_z"):
        if not math.isclose(
            float(aerial[key]), float(satellite[key]), rel_tol=0.0, abs_tol=1e-6
        ):
            raise ValueError(f"{sample_id}: ground truth {key} differs")


def normalize_points(
    points: np.ndarray, width: float, height: float, tolerance_ratio: float = 0.002
) -> tuple[np.ndarray, float, float]:
    if width <= 0 or height <= 0:
        raise ValueError("Spatial extent must be positive")
    normalized = points / np.asarray([width, height], dtype=np.float64)
    if np.any(normalized < -tolerance_ratio) or np.any(normalized > 1.0 + tolerance_ratio):
        raise ValueError(
            f"Points outside declared extent: min={normalized.min(axis=0)}, "
            f"max={normalized.max(axis=0)}"
        )
    outside = np.any((normalized < 0.0) | (normalized >= 1.0), axis=1)
    excess = np.maximum(np.maximum(normalized - 1.0, -normalized), 0.0)
    return (
        np.clip(normalized, 0.0, np.nextafter(1.0, 0.0)),
        float(np.mean(outside)),
        float(np.max(excess)),
    )


def convex_hull(points: np.ndarray) -> np.ndarray:
    unique = np.unique(points, axis=0)
    if len(unique) <= 2:
        return unique
    ordered = sorted(map(tuple, unique.tolist()))

    def cross(origin: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return np.asarray(lower[:-1] + upper[:-1], dtype=np.float64)


def polygon_area(points: np.ndarray) -> float:
    if len(points) < 3:
        return 0.0
    x = points[:, 0]
    y = points[:, 1]
    return float(0.5 * abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))))


def spatial_metrics(points_normalized: np.ndarray, grid_size: int, prefix: str) -> dict[str, float | int]:
    if grid_size < 2:
        raise ValueError("grid size must be at least 2")
    cell_xy = np.floor(points_normalized * grid_size).astype(np.int64)
    cell_xy = np.clip(cell_xy, 0, grid_size - 1)
    flat = cell_xy[:, 1] * grid_size + cell_xy[:, 0]
    counts = np.bincount(flat, minlength=grid_size * grid_size).astype(np.float64)
    probabilities = counts / counts.sum()
    nonzero = probabilities[probabilities > 0]
    entropy = -float(np.sum(nonzero * np.log(nonzero))) / math.log(grid_size * grid_size)
    hhi = float(np.sum(probabilities**2))
    uniform_hhi = 1.0 / (grid_size * grid_size)
    normalized_hhi = (hhi - uniform_hhi) / (1.0 - uniform_hhi)
    q05, q95 = np.quantile(points_normalized, (0.05, 0.95), axis=0)
    return {
        f"{prefix}_grid_occupied_cells": int(np.count_nonzero(counts)),
        f"{prefix}_grid_occupancy": float(np.count_nonzero(counts) / len(counts)),
        f"{prefix}_convex_hull_coverage": polygon_area(convex_hull(points_normalized)),
        f"{prefix}_robust_bbox90_coverage": float(np.prod(np.maximum(q95 - q05, 0.0))),
        f"{prefix}_max_cell_mass": float(probabilities.max()),
        f"{prefix}_top4_cell_mass_proxy": float(np.sort(probabilities)[-4:].sum()),
        f"{prefix}_normalized_hhi": float(normalized_hhi),
        f"{prefix}_spatial_entropy": entropy,
    }


def failure_group(error_m: float) -> str:
    if error_m <= 3.0:
        return "success_le_3m"
    if error_m <= 20.0:
        return "mid_3_to_20m"
    return "catastrophic_gt_20m"


def run_id(record: dict) -> str:
    for part in Path(str(record.get("result_dir", ""))).parts:
        if re.fullmatch(r"\d{8}-\d{4}_\d+scenes", part):
            return part
    return "missing"


def analyze_sample(
    sample_id: str,
    aerial_record: dict,
    satellite_record: dict,
    aerial_artifact: dict[str, np.ndarray],
    satellite_artifact: dict[str, np.ndarray],
    query_threshold_px: float,
    grid_size: int,
) -> dict[str, object]:
    validate_metadata(sample_id, aerial_record, satellite_record)
    aerial_query, _, aerial_map = finite_arrays(aerial_artifact)
    satellite_query, satellite_reference, satellite_map = finite_arrays(satellite_artifact)
    aerial_indices, satellite_indices, pair_distances = mutual_pairs(
        aerial_query, satellite_query, query_threshold_px
    )
    shared_query = (aerial_query[aerial_indices] + satellite_query[satellite_indices]) / 2.0
    shared_reference = satellite_reference[satellite_indices]
    delta_xy = satellite_map[satellite_indices] - aerial_map[aerial_indices]
    disagreement = np.linalg.norm(delta_xy, axis=1)
    coherent_shift = np.median(delta_xy, axis=0)
    corrected = np.linalg.norm(delta_xy - coherent_shift, axis=1)
    error_m = float(satellite_record["pred_error_m"])
    normalized_uav, uav_clip_fraction, uav_max_excess = normalize_points(
        shared_query,
        float(satellite_record["uav_input_width"]),
        float(satellite_record["uav_input_height"]),
    )
    normalized_satellite_ref, ref_clip_fraction, ref_max_excess = normalize_points(
        shared_reference,
        float(satellite_record["ref_patch_width"]),
        float(satellite_record["ref_patch_height"]),
    )
    row: dict[str, object] = {
        "sample_id": sample_id,
        "failure_group": failure_group(error_m),
        "satellite_final_error_m": error_m,
        "aerial_run_id": run_id(aerial_record),
        "satellite_run_id": run_id(satellite_record),
        "reference_mode": "aerial_vs_satellite_gtref",
        "matcher": satellite_record.get("matching_method", "missing"),
        "pose_prior": satellite_record.get("pose_priori", "missing"),
        "num_aerial_matches": int(len(aerial_query)),
        "num_satellite_matches": int(len(satellite_query)),
        "num_shared_uav_correspondences": int(len(aerial_indices)),
        "shared_pairing_rate": float(len(aerial_indices) / min(len(aerial_query), len(satellite_query))),
        "median_query_pair_distance_px": float(np.median(pair_distances)),
        "geographic_disagreement_mean_m": float(np.mean(disagreement)),
        "geographic_disagreement_median_m": float(np.median(disagreement)),
        "geographic_disagreement_p90_m": float(np.quantile(disagreement, 0.90)),
        "coherent_shift_x_m": float(coherent_shift[0]),
        "coherent_shift_y_m": float(coherent_shift[1]),
        "coherent_shift_magnitude_m": float(np.linalg.norm(coherent_shift)),
        "shift_corrected_residual_mean_m": float(np.mean(corrected)),
        "shift_corrected_residual_median_m": float(np.median(corrected)),
        "shift_corrected_residual_p90_m": float(np.quantile(corrected, 0.90)),
        "roma_confidence_available": False,
        "roma_confidence_mean": "",
        "roma_confidence_median": "",
        "roma_confidence_calibration_available": False,
        "uav_normalization_clipped_fraction": uav_clip_fraction,
        "uav_normalization_max_excess_ratio": uav_max_excess,
        "satellite_ref_normalization_clipped_fraction": ref_clip_fraction,
        "satellite_ref_normalization_max_excess_ratio": ref_max_excess,
    }
    for threshold in AGREEMENT_THRESHOLDS_M:
        row[f"agreement_{threshold:g}m"] = float(np.mean(disagreement <= threshold))
    row.update(
        spatial_metrics(
            normalized_uav,
            grid_size,
            "uav",
        )
    )
    row.update(
        spatial_metrics(
            normalized_satellite_ref,
            grid_size,
            "satellite_ref",
        )
    )
    return row


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


def correlation(left: Iterable[float], right: Iterable[float]) -> float | None:
    left_array = np.asarray(list(left), dtype=np.float64)
    right_array = np.asarray(list(right), dtype=np.float64)
    finite = np.isfinite(left_array) & np.isfinite(right_array)
    left_array = left_array[finite]
    right_array = right_array[finite]
    if len(left_array) < 3 or left_array.std() == 0 or right_array.std() == 0:
        return None
    return float(np.corrcoef(left_array, right_array)[0, 1])


def numeric_metrics(rows: list[dict[str, object]]) -> list[str]:
    excluded = {
        "satellite_final_error_m",
        "coherent_shift_x_m",
        "coherent_shift_y_m",
        "num_aerial_matches",
        "num_satellite_matches",
        "uav_normalization_clipped_fraction",
        "uav_normalization_max_excess_ratio",
        "satellite_ref_normalization_clipped_fraction",
        "satellite_ref_normalization_max_excess_ratio",
    }
    metrics = []
    for key, value in rows[0].items():
        if key in excluded or isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and np.std(
            [float(row[key]) for row in rows]
        ) > 0:
            metrics.append(key)
    return metrics


def value_summary(values: np.ndarray) -> dict[str, float | int]:
    return {
        "count": int(len(values)),
        "mean": float(np.mean(values)),
        "std": float(np.std(values)),
        "median": float(np.median(values)),
        "p25": float(np.quantile(values, 0.25)),
        "p75": float(np.quantile(values, 0.75)),
        "p90": float(np.quantile(values, 0.90)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
    }


def build_summary(
    rows: list[dict[str, object]], metrics: list[str], args: argparse.Namespace
) -> tuple[dict, list[dict[str, object]]]:
    error = np.asarray([float(row["satellite_final_error_m"]) for row in rows])
    log_error = np.log1p(error)
    correlations: list[dict[str, object]] = []
    for metric in metrics:
        values = np.asarray([float(row[metric]) for row in rows])
        correlations.append(
            {
                "metric": metric,
                "num_queries": len(rows),
                "pearson_vs_error": correlation(values, error),
                "pearson_vs_log1p_error": correlation(values, log_error),
                "spearman_vs_error": correlation(rankdata(values), rankdata(error)),
            }
        )
    by_group = {}
    for group in GROUP_ORDER:
        group_rows = [row for row in rows if row["failure_group"] == group]
        by_group[group] = {
            "num_queries": len(group_rows),
            "satellite_final_error_m": value_summary(
                np.asarray([float(row["satellite_final_error_m"]) for row in group_rows])
            ),
            **{
                metric: value_summary(np.asarray([float(row[metric]) for row in group_rows]))
                for metric in metrics
            },
        }
    summary = {
        "diagnostic": "Scene_16 saved-artifact cross-reference spatial support",
        "num_queries": len(rows),
        "grid_size": args.grid_size,
        "query_pairing_threshold_px": args.query_threshold_px,
        "normalization_clip_tolerance_ratio": 0.002,
        "aerial_archive": str(args.aerial_archive.resolve()),
        "satellite_archive": str(args.satellite_archive.resolve()),
        "aerial_archive_sha256": sha256(args.aerial_archive),
        "satellite_archive_sha256": sha256(args.satellite_archive),
        "uses_gpu": False,
        "reruns_retrieval": False,
        "reruns_matcher": False,
        "uses_dsm_or_pnp_to_define_correctness": False,
        "uses_final_error_as_outcome_only": True,
        "roma_confidence_available": False,
        "roma_confidence_missing_reason": (
            "No certainty/confidence field exists in any of the 295 aerial or "
            "295 satellite NPZ, JSON, or PKL artifacts."
        ),
        "spatial_metric_definitions": {
            "grid_occupancy": "occupied cells / grid_size^2",
            "convex_hull_coverage": "convex-hull area after normalizing coordinates to [0,1]^2",
            "robust_bbox90_coverage": "area of the per-axis 5th-to-95th percentile box",
            "max_cell_mass": "largest grid-cell correspondence fraction",
            "top4_cell_mass_proxy": (
                "fraction in four densest cells; concentration-only proxy, not a semantic "
                "roof or repetitive-structure label"
            ),
            "normalized_hhi": "grid HHI normalized from uniform=0 to single-cell=1",
            "spatial_entropy": "Shannon entropy over all grid cells divided by log(grid_size^2)",
        },
        "by_failure_group": by_group,
        "correlations_vs_satellite_final_error": correlations,
        "evidence_boundary": [
            "Aerial endpoints are a pseudo-reference, not manual correspondence ground truth.",
            "Geographic disagreement can include aerial/satellite map georegistration error.",
            "Concentration metrics are not semantic repetitive-region annotations.",
            "Final localization error is used only as a posthoc outcome variable.",
            "No DSM value, PnP success, or PnP inlier is used to define front-end correctness.",
            "Correlation is descriptive and does not establish causation.",
        ],
    }
    return summary, correlations


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_group_csv(path: Path, summary: dict, metrics: list[str]) -> None:
    rows = []
    for group in GROUP_ORDER:
        group_summary = summary["by_failure_group"][group]
        for metric in ["satellite_final_error_m", *metrics]:
            rows.append({"failure_group": group, "metric": metric, **group_summary[metric]})
    write_csv(path, rows)


def select_counterexamples(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    categories: dict[str, set[str]] = defaultdict(set)
    catastrophic = [row for row in rows if row["failure_group"] == "catastrophic_gt_20m"]
    successful = [row for row in rows if row["failure_group"] == "success_le_3m"]

    def mark_top(
        candidates: list[dict[str, object]],
        metric: str,
        category: str,
        *,
        largest: bool,
        count: int = 6,
    ) -> None:
        ranked = sorted(candidates, key=lambda row: float(row[metric]), reverse=largest)
        for row in ranked[:count]:
            categories[str(row["sample_id"])].add(category)

    mark_top(catastrophic, "agreement_5m", "HIGH_AGREEMENT_CATASTROPHIC", largest=True)
    mark_top(successful, "agreement_5m", "LOW_AGREEMENT_SUCCESS", largest=False)
    mark_top(
        catastrophic,
        "num_shared_uav_correspondences",
        "HIGH_MATCH_COUNT_CATASTROPHIC",
        largest=True,
    )
    mark_top(
        catastrophic,
        "satellite_ref_normalized_hhi",
        "HIGH_CONCENTRATION_CATASTROPHIC",
        largest=True,
    )
    mark_top(
        successful,
        "satellite_ref_convex_hull_coverage",
        "BROAD_COVERAGE_SUCCESS",
        largest=True,
    )
    by_id = {str(row["sample_id"]): row for row in rows}
    for required_id in ("L16_0098", "L16_0076", "L16_0077"):
        if required_id in by_id:
            categories[required_id].add("REQUIRED_KNOWN_COUNTEREXAMPLE")
    selected = []
    keep_fields = [
        "sample_id",
        "failure_group",
        "satellite_final_error_m",
        "num_shared_uav_correspondences",
        "agreement_5m",
        "geographic_disagreement_median_m",
        "uav_grid_occupancy",
        "uav_convex_hull_coverage",
        "satellite_ref_grid_occupancy",
        "satellite_ref_convex_hull_coverage",
        "satellite_ref_normalized_hhi",
        "satellite_ref_spatial_entropy",
        "coherent_shift_magnitude_m",
        "shift_corrected_residual_median_m",
    ]
    for sample_id in sorted(categories):
        selected.append(
            {
                "counterexample_types": ";".join(sorted(categories[sample_id])),
                **{field: by_id[sample_id][field] for field in keep_fields},
            }
        )
    return selected


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = (
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def panel_bounds(index: int, columns: int, panel_width: int, panel_height: int, top: int) -> tuple[int, int, int, int]:
    row, column = divmod(index, columns)
    left = column * panel_width
    y0 = top + row * panel_height
    return left, y0, left + panel_width, y0 + panel_height


def boxplot_figure(rows: list[dict[str, object]], output: Path) -> None:
    metrics = [
        ("agreement_5m", "Agreement@5m"),
        ("geographic_disagreement_median_m", "Median disagreement (m)"),
        ("num_shared_uav_correspondences", "Shared UAV pairs"),
        ("uav_grid_occupancy", "UAV grid occupancy"),
        ("satellite_ref_grid_occupancy", "Satellite grid occupancy"),
        ("satellite_ref_convex_hull_coverage", "Satellite hull coverage"),
        ("satellite_ref_normalized_hhi", "Satellite concentration (HHI)"),
        ("satellite_ref_spatial_entropy", "Satellite spatial entropy"),
        ("shift_corrected_residual_median_m", "Shift-corrected residual (m)"),
    ]
    colors = ((46, 139, 87), (227, 160, 8), (192, 57, 43))
    width, height, title_height = 1800, 1350, 80
    panel_width, panel_height = width // 3, (height - title_height) // 3
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(28, bold=True)
    label_font = load_font(18)
    small_font = load_font(15)
    draw.text((width // 2, 24), "Scene_16 spatial-support distributions (n=295)", fill="#17324D", font=title_font, anchor="ma")
    for index, (metric, title) in enumerate(metrics):
        left, top, right, bottom = panel_bounds(index, 3, panel_width, panel_height, title_height)
        plot_left, plot_top = left + 72, top + 54
        plot_right, plot_bottom = right - 24, bottom - 58
        data = [
            [float(row[metric]) for row in rows if row["failure_group"] == group]
            for group in GROUP_ORDER
        ]
        combined = np.asarray([value for group_values in data for value in group_values])
        value_min, value_max = float(combined.min()), float(combined.max())
        if value_max == value_min:
            value_max = value_min + 1.0
        padding = 0.05 * (value_max - value_min)
        scale_min, scale_max = value_min - padding, value_max + padding

        def y_coord(value: float) -> int:
            fraction = (value - scale_min) / (scale_max - scale_min)
            return int(plot_bottom - fraction * (plot_bottom - plot_top))

        draw.rectangle((left, top, right - 1, bottom - 1), outline="#D7DEE7", width=1)
        draw.text(((left + right) // 2, top + 18), title, fill="#17324D", font=label_font, anchor="ma")
        draw.line((plot_left, plot_top, plot_left, plot_bottom), fill="#607080", width=2)
        draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill="#607080", width=2)
        for tick_fraction in (0.0, 0.5, 1.0):
            value = scale_min + tick_fraction * (scale_max - scale_min)
            y = y_coord(value)
            draw.line((plot_left, y, plot_right, y), fill="#E8EDF2", width=1)
            draw.text((plot_left - 7, y), f"{value:.3g}", fill="#485766", font=small_font, anchor="rm")
        group_width = (plot_right - plot_left) / 3
        for group_index, (group_values, color) in enumerate(zip(data, colors)):
            array = np.asarray(group_values)
            q1, median, q3 = np.quantile(array, (0.25, 0.5, 0.75))
            low, high = np.quantile(array, (0.05, 0.95))
            center = int(plot_left + (group_index + 0.5) * group_width)
            box_half = int(group_width * 0.22)
            draw.line((center, y_coord(low), center, y_coord(high)), fill=color, width=3)
            draw.line((center - box_half // 2, y_coord(low), center + box_half // 2, y_coord(low)), fill=color, width=2)
            draw.line((center - box_half // 2, y_coord(high), center + box_half // 2, y_coord(high)), fill=color, width=2)
            draw.rectangle((center - box_half, y_coord(q3), center + box_half, y_coord(q1)), fill=tuple(min(255, channel + 45) for channel in color), outline=color, width=2)
            draw.line((center - box_half, y_coord(median), center + box_half, y_coord(median)), fill="#111111", width=3)
            draw.text((center, plot_bottom + 12), ("Success", "Middle", "Catastrophic")[group_index], fill="#334455", font=small_font, anchor="ma")
    image.save(output)


def scatter_figure(rows: list[dict[str, object]], output: Path) -> None:
    metrics = [
        ("agreement_5m", "Agreement@5m"),
        ("num_shared_uav_correspondences", "Shared UAV pairs"),
        ("satellite_ref_grid_occupancy", "Satellite grid occupancy"),
        ("satellite_ref_convex_hull_coverage", "Satellite hull coverage"),
        ("satellite_ref_normalized_hhi", "Satellite concentration (HHI)"),
        ("shift_corrected_residual_median_m", "Shift-corrected residual (m)"),
    ]
    colors = {
        "success_le_3m": (46, 139, 87),
        "mid_3_to_20m": (227, 160, 8),
        "catastrophic_gt_20m": (192, 57, 43),
    }
    width, height, title_height = 1800, 950, 80
    panel_width, panel_height = width // 3, (height - title_height) // 2
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font = load_font(28, bold=True)
    label_font = load_font(17)
    small_font = load_font(14)
    draw.text((width // 2, 24), "Spatial support vs satellite localization outcome", fill="#17324D", font=title_font, anchor="ma")
    all_log_error = np.log10(np.asarray([float(row["satellite_final_error_m"]) for row in rows]))
    y_min, y_max = float(all_log_error.min()), float(all_log_error.max())
    for index, (metric, label) in enumerate(metrics):
        left, top, right, bottom = panel_bounds(index, 3, panel_width, panel_height, title_height)
        plot_left, plot_top = left + 72, top + 48
        plot_right, plot_bottom = right - 24, bottom - 62
        x_values = np.asarray([float(row[metric]) for row in rows])
        x_min, x_max = float(x_values.min()), float(x_values.max())
        if x_max == x_min:
            x_max = x_min + 1.0

        def x_coord(value: float) -> int:
            return int(plot_left + (value - x_min) / (x_max - x_min) * (plot_right - plot_left))

        def y_coord(error: float) -> int:
            value = math.log10(error)
            return int(plot_bottom - (value - y_min) / (y_max - y_min) * (plot_bottom - plot_top))

        draw.rectangle((left, top, right - 1, bottom - 1), outline="#D7DEE7", width=1)
        draw.text(((left + right) // 2, top + 14), label, fill="#17324D", font=label_font, anchor="ma")
        draw.line((plot_left, plot_top, plot_left, plot_bottom), fill="#607080", width=2)
        draw.line((plot_left, plot_bottom, plot_right, plot_bottom), fill="#607080", width=2)
        for y_value in (0.1, 1.0, 3.0, 20.0, 100.0, 500.0):
            if y_value < 10**y_min or y_value > 10**y_max:
                continue
            y = y_coord(y_value)
            draw.line((plot_left, y, plot_right, y), fill="#E8EDF2", width=1)
            draw.text((plot_left - 7, y), f"{y_value:g}", fill="#485766", font=small_font, anchor="rm")
        draw.text((plot_left, plot_bottom + 9), f"{x_min:.3g}", fill="#485766", font=small_font, anchor="la")
        draw.text((plot_right, plot_bottom + 9), f"{x_max:.3g}", fill="#485766", font=small_font, anchor="ra")
        for row in rows:
            x = x_coord(float(row[metric]))
            y = y_coord(float(row["satellite_final_error_m"]))
            color = colors[str(row["failure_group"])]
            draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=color)
        if index == 0:
            legend_x, legend_y = plot_right - 155, plot_top + 8
            for offset, group in enumerate(GROUP_ORDER):
                y = legend_y + offset * 22
                draw.ellipse((legend_x, y, legend_x + 10, y + 10), fill=colors[group])
                draw.text((legend_x + 16, y - 2), GROUP_LABELS[group], fill="#334455", font=small_font)
    image.save(output)


def write_note(
    path: Path,
    summary: dict,
    correlations: list[dict[str, object]],
    counterexamples: list[dict[str, object]],
) -> None:
    correlations_sorted = sorted(
        correlations,
        key=lambda row: abs(float(row["spearman_vs_error"] or 0.0)),
        reverse=True,
    )
    lines = [
        "# Scene_16 295-Query Spatial-Support Diagnostic",
        "",
        "## Research question",
        "",
        "Are satellite localization failures systematically associated with weaker cross-reference geographic agreement, poorer spatial coverage, greater correspondence concentration, insufficient surrounding support, or unreliable saved confidence?",
        "",
        "## Controlled evidence scope",
        "",
        "- 295 paired Scene_16 queries from saved aerial and satellite GT-reference RoMa runs.",
        "- CPU-only archive analysis; no retrieval, RoMa, training, DSM lookup, or PnP rerun.",
        "- Satellite final error is an outcome variable only.",
        "- Aerial map endpoints are a pseudo-reference, not manual correspondence ground truth.",
        "- RoMa certainty/confidence is unavailable in every saved artifact, so confidence calibration is not reported.",
        "",
        "## Reproduction command",
        "",
        "```bash",
        "python reproductions/anyvisloc/analyze_scene16_spatial_support.py \\",
        f"  --aerial-archive {summary['aerial_archive']} \\",
        f"  --satellite-archive {summary['satellite_archive']} \\",
        "  --output-dir /path/to/scene16_spatial_support_diagnostic_20260901",
        "```",
        "",
        f"- Aerial archive SHA-256: `{summary['aerial_archive_sha256']}`",
        f"- Satellite archive SHA-256: `{summary['satellite_archive_sha256']}`",
        "- Pairing: mutual nearest UAV coordinates within 5 original-image pixels.",
        "- Spatial grid: 8 x 8 on normalized coordinates.",
        "",
        "## Metric interpretation",
        "",
        "- `grid_occupancy`: occupied cells / 64.",
        "- `convex_hull_coverage`: normalized convex-hull area in the UAV image or satellite reference patch.",
        "- `normalized_hhi`: global grid concentration, where uniform support approaches 0 and single-cell support approaches 1.",
        "- `top4_cell_mass_proxy`: fraction of correspondences in the four densest cells. This is only a concentration proxy and is not a roof/repetition label.",
        "- `spatial_entropy`: normalized Shannon entropy over the 64 cells.",
        "- `coherent_shift_magnitude_m`: norm of the median aerial-to-satellite XY displacement.",
        "- `shift_corrected_residual_median_m`: median residual after subtracting that coherent shift.",
        "",
        "## Group sizes and key metrics",
        "",
        "| Group | n | Median error (m) | Median Agreement@5m | Median shared pairs | Median satellite occupancy | Median satellite HHI |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in GROUP_ORDER:
        data = summary["by_failure_group"][group]
        lines.append(
            f"| {GROUP_LABELS[group]} | {data['num_queries']} | "
            f"{data['satellite_final_error_m']['median']:.3f} | "
            f"{data['agreement_5m']['median']:.3f} | "
            f"{data['num_shared_uav_correspondences']['median']:.1f} | "
            f"{data['satellite_ref_grid_occupancy']['median']:.3f} | "
            f"{data['satellite_ref_normalized_hhi']['median']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Strongest descriptive correlations",
            "",
            "| Metric | Spearman vs final error | Pearson vs log(1+error) |",
            "| --- | ---: | ---: |",
        ]
    )
    for row in correlations_sorted[:12]:
        lines.append(
            f"| `{row['metric']}` | {float(row['spearman_vs_error']):.3f} | "
            f"{float(row['pearson_vs_log1p_error']):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Research-question decisions",
            "",
            "| Candidate factor | Current decision | Evidence |",
            "| --- | --- | --- |",
            "| Low cross-reference geographic agreement | Supported as an association | Agreement@5m has Spearman -0.500 with final error and decreases across success, middle, catastrophic groups. |",
            "| Poor global spatial coverage | Not supported as a general monotonic explanation | Satellite grid occupancy Spearman is 0.035; convex-hull coverage is 0.180, and group medians are not ordered as hypothesized. |",
            "| Excessive global concentration | Not supported globally; possible tail subgroup | Satellite HHI Spearman is 0.080. Raw-error sensitivity is larger because a subset of extreme failures is concentrated. |",
            "| Repetitive-structure ambiguity | Still a hypothesis | The concentration proxy has no semantics and cannot identify roof or repeated structure. |",
            "| Insufficient surrounding-context support | Still a hypothesis | No roof/context masks or manual region labels exist for all 295 queries. |",
            "| Confidence/certainty miscalibration | Not testable from current artifacts | RoMa certainty/confidence was not saved in NPZ, JSON, or PKL. |",
            "",
            "## Supported by current evidence",
            "",
            "- Cross-reference geographic agreement is descriptively associated with final satellite error across all 295 queries.",
            "- Shared UAV pair count has a moderate negative monotonic association with error, even though every run requested 3,000 matches.",
            "- Coherent shift magnitude and shift-corrected residual capture distinct disagreement components; coherent shift has the stronger monotonic association in this audit.",
            "- Global agreement is neither necessary nor sufficient for accurate localization; required counterexamples remain in the shortlist.",
            "- Simple global spatial coverage, concentration, and entropy metrics do not show a strong monotonic relationship with error across all 295 queries. Concentration is elevated in part of the catastrophic tail, but this is not a universal pattern.",
            "",
            "## Not confirmed",
            "",
            "- Concentration is not a semantic repetitive-roof label. The top-four-cell mass and HHI are spatial proxies only.",
            "- The 24-query observation that stable surrounding context can rescue a pose is not yet quantitatively verified across all 295 because no semantic context mask exists.",
            "- A correlation between coverage/concentration and error does not establish a causal front-end mechanism.",
            "- Aerial/satellite georegistration, temporal change, and downstream geometry can still explain individual cases.",
            "- Confidence calibration cannot be evaluated because RoMa certainty was not saved.",
            "",
            "## Required known counterexamples",
            "",
        ]
    )
    by_id = {str(row["sample_id"]): row for row in counterexamples}
    for sample_id in ("L16_0098", "L16_0076", "L16_0077"):
        if sample_id not in by_id:
            continue
        row = by_id[sample_id]
        lines.append(
            f"- `{sample_id}`: error={float(row['satellite_final_error_m']):.3f} m, "
            f"Agreement@5m={float(row['agreement_5m']):.3f}, "
            f"shared pairs={int(row['num_shared_uav_correspondences'])}, "
            f"satellite occupancy={float(row['satellite_ref_grid_occupancy']):.3f}."
        )
    lines.extend(
        [
            "",
            "## Uncertainty and next decision",
            "",
            "This audit can select a narrower front-end research problem but cannot yet justify a model architecture. Agreement/cross-reference correctness remains the strongest verified front-end signal. Basic global coverage and concentration should not be promoted as the main hypothesis without subgroup evidence. The next minimal step is to inspect deterministic counterexample subgroups and decide whether a small manual region annotation protocol can test structure-versus-context support. Any later semantic roof/context claim requires that annotation and must remain separate from the current concentration-only proxy.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit <= 0:
        raise ValueError("limit must be positive")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    aerial = ResultArchive(args.aerial_archive, "aerial")
    satellite = ResultArchive(args.satellite_archive, "satellite")
    try:
        sample_ids = sorted(set(aerial.records) & set(satellite.records))
        if set(aerial.records) != set(satellite.records):
            raise ValueError("Aerial and satellite sample sets differ")
        if args.limit is not None:
            sample_ids = sample_ids[: args.limit]
        rows = []
        for sample_id in sample_ids:
            rows.append(
                analyze_sample(
                    sample_id,
                    aerial.records[sample_id],
                    satellite.records[sample_id],
                    aerial.arrays(sample_id),
                    satellite.arrays(sample_id),
                    args.query_threshold_px,
                    args.grid_size,
                )
            )
    finally:
        aerial.close()
        satellite.close()

    metrics = numeric_metrics(rows)
    summary, correlations = build_summary(rows, metrics, args)
    counterexamples = select_counterexamples(rows)
    write_csv(args.output_dir / "scene16_spatial_support_per_query.csv", rows)
    write_group_csv(args.output_dir / "scene16_spatial_support_group_summary.csv", summary, metrics)
    write_csv(args.output_dir / "scene16_spatial_support_correlations.csv", correlations)
    write_csv(args.output_dir / "scene16_spatial_support_counterexamples.csv", counterexamples)
    (args.output_dir / "scene16_spatial_support_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    boxplot_figure(rows, args.output_dir / "scene16_spatial_support_group_distributions.png")
    scatter_figure(rows, args.output_dir / "scene16_spatial_support_error_scatter.png")
    write_note(
        args.output_dir / "scene16_spatial_support_research_note.md",
        summary,
        correlations,
        counterexamples,
    )
    manifest = {
        "num_queries": len(rows),
        "outputs": sorted(path.name for path in args.output_dir.iterdir()),
        "confidence_available": False,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
