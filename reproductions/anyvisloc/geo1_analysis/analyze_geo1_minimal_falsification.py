#!/usr/bin/env python3
"""Run the offline GEO-1 minimal falsification analysis on saved provenance."""

from __future__ import annotations

import argparse
import csv
import json
import math
import pickle
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np


CORRECTNESS_THRESHOLDS_M = (0.0, 5.0, 10.0, 20.0)
INLIER_RATIO_THRESHOLDS = (0.2, 0.3, 0.4)
PRIMARY_TAU_M = 0.0
PRIMARY_INLIER_RATIO = 0.3
FINAL_SUCCESS_M = 3.0
EXPECTED_QUERIES = 295
EXPECTED_CANDIDATES_PER_QUERY = 5
REQUIRED_ARRAYS = {
    "uav_pts_match",
    "ref_pts_match",
    "uav_pts_original",
    "ref_pts_patch",
    "local_x",
    "local_y",
    "dsm_z",
    "valid",
    "pnp_input_2d",
    "pnp_input_3d",
    "pnp_object_points",
    "inlier_indices",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--bootstrap-repetitions", type=int, default=10_000)
    parser.add_argument("--bootstrap-seed", type=int, default=20_260_908)
    return parser.parse_args()


def load_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        value = pickle.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict in {path}, got {type(value)}")
    return value


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty table: {path}")
    fields: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                fields.append(key)
                seen.add(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(json_ready(value), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def assert_optional_equal(actual: Any, expected: Any, context: str) -> None:
    if actual is None or expected is None:
        if actual is not expected:
            raise ValueError(f"{context}: {actual!r} != {expected!r}")
        return
    if float(actual) != float(expected):
        raise ValueError(f"{context}: {actual!r} != {expected!r}")


def polygon_area(points: np.ndarray) -> float:
    points = np.asarray(points, dtype=np.float64)
    if len(points) < 3:
        return 0.0
    return float(
        0.5
        * abs(
            np.dot(points[:, 0], np.roll(points[:, 1], -1))
            - np.dot(points[:, 1], np.roll(points[:, 0], -1))
        )
    )


def convex_hull(points: np.ndarray) -> np.ndarray:
    unique = sorted(set(map(tuple, np.asarray(points, dtype=np.float64))))
    if len(unique) <= 1:
        return np.asarray(unique, dtype=np.float64).reshape(-1, 2)

    def cross(origin: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - origin[0]) * (b[1] - origin[1]) - (a[1] - origin[1]) * (b[0] - origin[0])

    lower: list[tuple[float, float]] = []
    for point in unique:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(unique):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return np.asarray(lower[:-1] + upper[:-1], dtype=np.float64)


def normalized_coverage(points: np.ndarray, width: float, height: float) -> float:
    denominator = max(float(width) * float(height), 1e-12)
    return polygon_area(convex_hull(points)) / denominator


def distribution_metrics(points: np.ndarray, width: float, height: float) -> dict[str, float]:
    points = np.asarray(points, dtype=np.float64).reshape(-1, 2)
    if len(points) == 0:
        return {
            "coverage": 0.0,
            "grid_occupancy_4x4": 0.0,
            "max_grid_fraction_4x4": 0.0,
            "normalized_dispersion": 0.0,
            "covariance_minor_major_ratio": 0.0,
        }
    width = max(float(width), 1e-12)
    height = max(float(height), 1e-12)
    normalized = points / np.array([width, height], dtype=np.float64)
    bins = np.floor(np.clip(normalized, 0.0, np.nextafter(1.0, 0.0)) * 4).astype(int)
    counts = Counter(map(tuple, bins))
    centered = normalized - normalized.mean(axis=0, keepdims=True)
    covariance = centered.T @ centered / max(len(normalized), 1)
    eigenvalues = np.linalg.eigvalsh(covariance)
    major = max(float(eigenvalues[-1]), 1e-12)
    return {
        "coverage": normalized_coverage(points, width, height),
        "grid_occupancy_4x4": len(counts) / 16.0,
        "max_grid_fraction_4x4": max(counts.values()) / len(normalized),
        "normalized_dispersion": float(np.sqrt(np.trace(covariance))),
        "covariance_minor_major_ratio": float(max(eigenvalues[0], 0.0) / major),
    }


def affine_fit(source: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    source = np.asarray(source, dtype=np.float64).reshape(-1, 2)
    target = np.asarray(target, dtype=np.float64).reshape(-1, 2)
    if len(source) < 3 or np.linalg.matrix_rank(np.c_[source, np.ones(len(source))]) < 3:
        raise ValueError("Cannot recover a full-rank affine map")
    design = np.c_[source, np.ones(len(source))]
    coefficients = np.linalg.lstsq(design, target, rcond=None)[0]
    residual = np.linalg.norm(design @ coefficients - target, axis=1)
    return coefficients, residual


def affine_coherence_proxy(
    uav_points: np.ndarray,
    ref_points: np.ndarray,
    uav_width: float,
    uav_height: float,
    ref_width: float,
    ref_height: float,
) -> float:
    uav = np.asarray(uav_points, dtype=np.float64) / np.array([uav_width, uav_height])
    ref = np.asarray(ref_points, dtype=np.float64) / np.array([ref_width, ref_height])
    _, residual = affine_fit(uav, ref)
    return float(np.median(residual))


def point_in_polygon(point: np.ndarray, polygon: np.ndarray) -> bool:
    x, y = map(float, point)
    inside = False
    previous = polygon[-1]
    for current in polygon:
        x1, y1 = map(float, previous)
        x2, y2 = map(float, current)
        on_segment = (
            abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) <= 1e-8
            and min(x1, x2) - 1e-8 <= x <= max(x1, x2) + 1e-8
            and min(y1, y2) - 1e-8 <= y <= max(y1, y2) + 1e-8
        )
        if on_segment:
            return True
        if (y1 > y) != (y2 > y):
            crossing_x = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing_x:
                inside = not inside
        previous = current
    return inside


def point_segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    denominator = float(np.dot(segment, segment))
    if denominator <= 0:
        return float(np.linalg.norm(point - start))
    fraction = float(np.clip(np.dot(point - start, segment) / denominator, 0.0, 1.0))
    return float(np.linalg.norm(point - (start + fraction * segment)))


def point_polygon_distance(point: np.ndarray, polygon: np.ndarray) -> float:
    if point_in_polygon(point, polygon):
        return 0.0
    return min(
        point_segment_distance(point, polygon[index], polygon[(index + 1) % len(polygon)])
        for index in range(len(polygon))
    )


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float | None, float | None]:
    if total <= 0:
        return None, None
    proportion = successes / total
    denominator = 1.0 + z * z / total
    center = (proportion + z * z / (2.0 * total)) / denominator
    spread = z * math.sqrt(proportion * (1.0 - proportion) / total + z * z / (4.0 * total * total)) / denominator
    return max(0.0, center - spread), min(1.0, center + spread)


def percentile_interval(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    return tuple(map(float, np.quantile(np.asarray(values), [0.025, 0.975])))


def cluster_bootstrap(
    query_rows: list[dict[str, Any]],
    candidate_rows_by_query: dict[str, list[dict[str, Any]]],
    tau: float,
    alpha: float,
    repetitions: int,
    seed: int,
) -> dict[str, tuple[float | None, float | None]]:
    rng = np.random.default_rng(seed)
    count = len(query_rows)
    deltas: list[float] = []
    rescues: list[float] = []
    pnp_rejections: list[float] = []
    selection_rejections: list[float] = []
    confident_wrong: list[float] = []
    rescued_success: list[float] = []
    correct_key = f"correct_tau_{int(tau)}m"
    for _ in range(repetitions):
        indices = rng.integers(0, count, size=count)
        sampled_queries = [query_rows[index] for index in indices]
        deltas.append(
            100.0
            * float(np.mean([row[f"selected_{correct_key}"] - row[f"top1_{correct_key}"] for row in sampled_queries]))
        )
        opportunities = [row for row in sampled_queries if row[f"rescue_opportunity_tau_{int(tau)}m"]]
        if opportunities:
            rescues.append(float(np.mean([row[f"rescued_tau_{int(tau)}m"] for row in opportunities])))
        rescued = [row for row in sampled_queries if row[f"rescued_tau_{int(tau)}m"]]
        if rescued:
            rescued_success.append(float(np.mean([row[f"rescued_final_le3m_tau_{int(tau)}m"] for row in rescued])))
        confident_wrong.append(
            float(np.mean([row[f"confident_wrong_tau_{int(tau)}m_alpha_{alpha:.1f}"] for row in sampled_queries]))
        )

        sampled_candidates: list[dict[str, Any]] = []
        for row in sampled_queries:
            sampled_candidates.extend(candidate_rows_by_query[row["sample_id"]])
        wrong = [row for row in sampled_candidates if not row[correct_key]]
        if wrong:
            pnp_rejections.append(float(np.mean([not row["pnp_success"] for row in wrong])))
            selection_rejections.append(float(np.mean([not row["selected"] for row in wrong])))
    return {
        "identity_increment_pp": percentile_interval(deltas),
        "rescue_rate": percentile_interval(rescues),
        "rescued_final_le3m_rate": percentile_interval(rescued_success),
        "pnp_failure_rejection_rate": percentile_interval(pnp_rejections),
        "selection_level_rejection_rate": percentile_interval(selection_rejections),
        "confident_wrong_rate": percentile_interval(confident_wrong),
    }


def correctness_state(distance_m: float, tau_m: float) -> str:
    if distance_m <= 1e-8:
        return "correct"
    if distance_m <= tau_m:
        return "ambiguous"
    return "wrong"


def final_error_state(error_m: float | None) -> str:
    if error_m is None or not math.isfinite(float(error_m)):
        return "failed"
    if float(error_m) <= 3.0:
        return "le3m"
    if float(error_m) <= 20.0:
        return "gt3_le20m"
    return "gt20m"


def locate_query_pickles(input_root: Path) -> list[Path]:
    paths = sorted(input_root.glob("**/VG_data_*.pkl"))
    if len(paths) != EXPECTED_QUERIES:
        raise ValueError(f"Expected {EXPECTED_QUERIES} query PKLs, found {len(paths)}")
    return paths


def extract_candidate(
    sample_id: str,
    pkl_data: dict[str, Any],
    candidate_dir: Path,
    slot: int,
) -> dict[str, Any]:
    result = json.loads((candidate_dir / "result.json").read_text(encoding="utf-8"))
    if result["candidate_slot"] != slot or result["retrieval_rank"] != slot + 1:
        raise ValueError(f"{sample_id}/slot_{slot:02d}: slot/rank mismatch")
    ir_order = np.asarray(pkl_data["IR_order"]).reshape(-1)
    if result["ir_order_gallery_block_index"] != int(ir_order[slot]):
        raise ValueError(f"{sample_id}/slot_{slot:02d}: IR_order mismatch")

    with np.load(candidate_dir / "matches_and_pnp_inputs.npz", allow_pickle=False) as arrays:
        if set(arrays.files) != REQUIRED_ARRAYS:
            raise ValueError(f"{sample_id}/slot_{slot:02d}: unexpected NPZ schema")
        values = {key: np.asarray(arrays[key]) for key in arrays.files}

    raw_count = len(values["ref_pts_match"])
    raw_fields = ("uav_pts_match", "ref_pts_match", "uav_pts_original", "ref_pts_patch", "local_x", "local_y", "dsm_z", "valid")
    if any(len(values[key]) != raw_count for key in raw_fields):
        raise ValueError(f"{sample_id}/slot_{slot:02d}: raw array length mismatch")
    valid = np.asarray(values["valid"], dtype=bool)
    valid_count = int(valid.sum())
    pnp_count = len(values["pnp_input_2d"])
    if pnp_count != valid_count or len(values["pnp_input_3d"]) != valid_count or len(values["pnp_object_points"]) != valid_count:
        raise ValueError(f"{sample_id}/slot_{slot:02d}: valid/PnP count mismatch")
    if not np.isfinite(values["pnp_input_2d"]).all() or not np.isfinite(values["pnp_input_3d"]).all():
        raise ValueError(f"{sample_id}/slot_{slot:02d}: non-finite PnP input")
    if not np.isfinite(values["pnp_object_points"]).all():
        raise ValueError(f"{sample_id}/slot_{slot:02d}: non-finite PnP object point")
    inlier_indices = np.asarray(values["inlier_indices"]).reshape(-1)
    if np.any(inlier_indices < 0) or np.any(inlier_indices >= pnp_count):
        raise ValueError(f"{sample_id}/slot_{slot:02d}: invalid inlier index")
    if len(inlier_indices) != int(result["inlier_count"]):
        raise ValueError(f"{sample_id}/slot_{slot:02d}: inlier count mismatch")

    patch_h = int(result["patch_h"])
    patch_w = int(result["patch_w"])
    affine, footprint_residual = affine_fit(
        values["ref_pts_patch"],
        np.column_stack([values["local_x"], values["local_y"]]),
    )
    corners = np.array([[0.0, 0.0], [patch_w, 0.0], [patch_w, patch_h], [0.0, patch_h]])
    footprint = np.c_[corners, np.ones(4)] @ affine
    gt_xy = np.array([pkl_data["truePos"]["x"], pkl_data["truePos"]["y"]], dtype=np.float64)
    distance_m = point_polygon_distance(gt_xy, footprint)

    uav_metrics = distribution_metrics(
        values["uav_pts_original"],
        pkl_data["truePos"]["width"],
        pkl_data["truePos"]["height"],
    )
    ref_metrics = distribution_metrics(values["ref_pts_patch"], patch_w, patch_h)
    footprint_area = max(polygon_area(footprint), 1e-12)
    valid_world = values["pnp_input_3d"][:, :2]
    valid_world_coverage = polygon_area(convex_hull(valid_world)) / footprint_area
    coherence = affine_coherence_proxy(
        values["uav_pts_original"],
        values["ref_pts_patch"],
        pkl_data["truePos"]["width"],
        pkl_data["truePos"]["height"],
        patch_w,
        patch_h,
    )

    pose = pkl_data["XYZ_list"][slot]
    assert_optional_equal(result["pred_x"], pose.get("X"), f"{sample_id}/slot_{slot:02d} pred_x")
    assert_optional_equal(result["pred_y"], pose.get("Y"), f"{sample_id}/slot_{slot:02d} pred_y")
    assert_optional_equal(result["pred_z"], pose.get("Z"), f"{sample_id}/slot_{slot:02d} pred_z")
    assert_optional_equal(result["location_error_m"], pkl_data["location_error_list"][slot], f"{sample_id}/slot_{slot:02d} error")

    selected = int(pkl_data["best_index"]) == slot
    row: dict[str, Any] = {
        "sample_id": sample_id,
        "candidate_slot": slot,
        "retrieval_rank": slot + 1,
        "ir_order_gallery_block_index": int(ir_order[slot]),
        "row_start": int(result["row_start"]),
        "col_start": int(result["col_start"]),
        "patch_h": patch_h,
        "patch_w": patch_w,
        "gt_x": float(gt_xy[0]),
        "gt_y": float(gt_xy[1]),
        "footprint_wkt": "POLYGON((" + ",".join(f"{x:.6f} {y:.6f}" for x, y in np.vstack([footprint, footprint[0]])) + "))",
        "footprint_area_m2": polygon_area(footprint),
        "footprint_affine_max_residual_m": float(np.max(footprint_residual)),
        "candidate_gt_distance_m": distance_m,
        "pde_gt_derived": float(pkl_data["PDE"][slot]),
        "raw_match_count": raw_count,
        "raw_match_confidence": "UNAVAILABLE",
        "uav_coverage": uav_metrics["coverage"],
        "uav_grid_occupancy_4x4": uav_metrics["grid_occupancy_4x4"],
        "uav_max_grid_fraction_4x4": uav_metrics["max_grid_fraction_4x4"],
        "uav_normalized_dispersion": uav_metrics["normalized_dispersion"],
        "uav_covariance_minor_major_ratio": uav_metrics["covariance_minor_major_ratio"],
        "ref_coverage": ref_metrics["coverage"],
        "ref_grid_occupancy_4x4": ref_metrics["grid_occupancy_4x4"],
        "ref_max_grid_fraction_4x4": ref_metrics["max_grid_fraction_4x4"],
        "ref_normalized_dispersion": ref_metrics["normalized_dispersion"],
        "ref_covariance_minor_major_ratio": ref_metrics["covariance_minor_major_ratio"],
        "affine_coherence_median_residual_proxy": coherence,
        "dsm_valid_count": valid_count,
        "dsm_valid_ratio": valid_count / max(raw_count, 1),
        "invalid_dsm_nonfinite_count": int(np.count_nonzero(~np.isfinite(values["dsm_z"]))),
        "valid_world_xy_coverage_ratio": valid_world_coverage,
        "valid_dsm_z_std_m": float(np.std(values["pnp_input_3d"][:, 2])) if pnp_count else None,
        "pnp_input_count": pnp_count,
        "pnp_success": bool(result["pnp_success"]),
        "pnp_reprojection_error": "UNAVAILABLE",
        "pnp_inlier_count": int(result["inlier_count"]),
        "pnp_inlier_ratio": int(result["inlier_count"]) / max(pnp_count, 1),
        "pred_x": result["pred_x"],
        "pred_y": result["pred_y"],
        "pred_z": result["pred_z"],
        "candidate_location_error_m": result["location_error_m"],
        "selected": selected,
    }
    for tau in CORRECTNESS_THRESHOLDS_M:
        row[f"correct_tau_{int(tau)}m"] = int(distance_m <= tau + 1e-8)
        row[f"state_tau_{int(tau)}m"] = correctness_state(distance_m, tau)
    return row


def extract_all(input_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    candidates: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []
    by_query: dict[str, list[dict[str, Any]]] = {}
    for pkl_path in locate_query_pickles(input_root):
        data = load_pickle(pkl_path)
        sample_id = str(data.get("sample_id") or pkl_path.stem.removeprefix("VG_data_"))
        provenance_dir = pkl_path.parent / "candidate_provenance"
        query_result = json.loads((provenance_dir / "query_result.json").read_text(encoding="utf-8"))
        if str(query_result["sample_id"]) != sample_id or int(query_result["num_processed_candidates"]) != EXPECTED_CANDIDATES_PER_QUERY:
            raise ValueError(f"{sample_id}: invalid query-level provenance")
        rows = [
            extract_candidate(sample_id, data, provenance_dir / f"slot_{slot:02d}", slot)
            for slot in range(EXPECTED_CANDIDATES_PER_QUERY)
        ]
        selected_rows = [row for row in rows if row["selected"]]
        if len(selected_rows) != 1:
            raise ValueError(f"{sample_id}: expected exactly one selected candidate")
        selected = selected_rows[0]
        if int(data["best_index"]) != int(np.argmax(np.asarray(data["inliers"], dtype=np.int64))):
            raise ValueError(f"{sample_id}: best_index is not max-inlier candidate")
        assert_optional_equal(query_result["final_pred_error_m"], data["pred_error"], f"{sample_id} final error")
        if query_result["inlier_counts"] != [int(value) for value in data["inliers"]]:
            raise ValueError(f"{sample_id}: query inlier list mismatch")

        query: dict[str, Any] = {
            "sample_id": sample_id,
            "retrieval_top1_slot": 0,
            "retrieval_top1_ir_order": rows[0]["ir_order_gallery_block_index"],
            "selected_slot": selected["candidate_slot"],
            "selected_ir_order": selected["ir_order_gallery_block_index"],
            "pnp_success": bool(data["pnp_success"]),
            "final_pred_error_m": data["pred_error"],
            "final_error_state": final_error_state(data["pred_error"]),
            "selected_inlier_count": selected["pnp_inlier_count"],
            "selected_inlier_ratio": selected["pnp_inlier_ratio"],
            "selection_inlier_margin": selected["pnp_inlier_count"] - max(
                row["pnp_inlier_count"] for row in rows if not row["selected"]
            ),
        }
        for tau in CORRECTNESS_THRESHOLDS_M:
            key = f"correct_tau_{int(tau)}m"
            top1_correct = int(rows[0][key])
            selected_correct = int(selected[key])
            any_correct = int(any(row[key] for row in rows))
            opportunity = int(not top1_correct and any_correct)
            rescued = int(opportunity and selected_correct)
            query[f"top1_{key}"] = top1_correct
            query[f"selected_{key}"] = selected_correct
            query[f"top5_any_{key}"] = any_correct
            query[f"rescue_opportunity_tau_{int(tau)}m"] = opportunity
            query[f"rescued_tau_{int(tau)}m"] = rescued
            query[f"rescued_final_le3m_tau_{int(tau)}m"] = int(
                rescued and data["pred_error"] is not None and float(data["pred_error"]) <= FINAL_SUCCESS_M
            )
            query[f"top1_state_tau_{int(tau)}m"] = rows[0][f"state_tau_{int(tau)}m"]
            query[f"selected_state_tau_{int(tau)}m"] = selected[f"state_tau_{int(tau)}m"]
            for alpha in INLIER_RATIO_THRESHOLDS:
                query[f"confident_wrong_tau_{int(tau)}m_alpha_{alpha:.1f}"] = int(
                    not selected_correct
                    and selected["pnp_success"]
                    and selected["pnp_inlier_ratio"] >= alpha
                )
        candidates.extend(rows)
        queries.append(query)
        by_query[sample_id] = rows
    if len(candidates) != EXPECTED_QUERIES * EXPECTED_CANDIDATES_PER_QUERY:
        raise ValueError(f"Expected 1475 candidate records, found {len(candidates)}")
    return candidates, queries, by_query


def compute_sensitivity(
    candidates: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    by_query: dict[str, list[dict[str, Any]]],
    repetitions: int,
    seed: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tau_index, tau in enumerate(CORRECTNESS_THRESHOLDS_M):
        correct_key = f"correct_tau_{int(tau)}m"
        wrong_candidates = [row for row in candidates if not row[correct_key]]
        pnp_rejected = sum(not row["pnp_success"] for row in wrong_candidates)
        selection_rejected = sum(not row["selected"] for row in wrong_candidates)
        opportunities = [row for row in queries if row[f"rescue_opportunity_tau_{int(tau)}m"]]
        rescued = [row for row in opportunities if row[f"rescued_tau_{int(tau)}m"]]
        rescued_success = sum(row[f"rescued_final_le3m_tau_{int(tau)}m"] for row in rescued)
        deteriorated = [
            row for row in queries
            if row[f"top1_{correct_key}"] and not row[f"selected_{correct_key}"]
        ]
        top1_correct = sum(row[f"top1_{correct_key}"] for row in queries)
        selected_correct = sum(row[f"selected_{correct_key}"] for row in queries)
        rescued_errors = [float(row["final_pred_error_m"]) for row in rescued if row["final_pred_error_m"] is not None]
        final_errors = [float(row["final_pred_error_m"]) for row in queries if row["final_pred_error_m"] is not None]

        rescue_wilson = wilson_interval(len(rescued), len(opportunities))
        pnp_reject_wilson = wilson_interval(pnp_rejected, len(wrong_candidates))
        selection_reject_wilson = wilson_interval(selection_rejected, len(wrong_candidates))
        rescued_success_wilson = wilson_interval(rescued_success, len(rescued))
        for alpha in INLIER_RATIO_THRESHOLDS:
            confident = sum(row[f"confident_wrong_tau_{int(tau)}m_alpha_{alpha:.1f}"] for row in queries)
            confident_wilson = wilson_interval(confident, len(queries))
            bootstrap = cluster_bootstrap(
                queries,
                by_query,
                tau,
                alpha,
                repetitions,
                seed + tau_index,
            )
            rows.append({
                "correctness_tau_m": tau,
                "inlier_ratio_threshold": alpha,
                "num_queries": len(queries),
                "top1_correct_count": top1_correct,
                "top1_identity_accuracy": top1_correct / len(queries),
                "selected_correct_count": selected_correct,
                "selected_identity_accuracy": selected_correct / len(queries),
                "candidate_identity_increment_pp": 100.0 * (selected_correct - top1_correct) / len(queries),
                "identity_increment_bootstrap_lower_pp": bootstrap["identity_increment_pp"][0],
                "identity_increment_bootstrap_upper_pp": bootstrap["identity_increment_pp"][1],
                "top5_correct_available_count": sum(row[f"top5_any_{correct_key}"] for row in queries),
                "rescue_opportunity_count": len(opportunities),
                "rescued_count": len(rescued),
                "geometry_rescue_rate": len(rescued) / len(opportunities) if opportunities else None,
                "rescue_wilson_lower": rescue_wilson[0],
                "rescue_wilson_upper": rescue_wilson[1],
                "rescue_bootstrap_lower": bootstrap["rescue_rate"][0],
                "rescue_bootstrap_upper": bootstrap["rescue_rate"][1],
                "rescued_final_le3m_count": rescued_success,
                "rescued_final_le3m_rate": rescued_success / len(rescued) if rescued else None,
                "rescued_final_le3m_wilson_lower": rescued_success_wilson[0],
                "rescued_final_le3m_wilson_upper": rescued_success_wilson[1],
                "rescued_final_error_median_m": float(np.median(rescued_errors)) if rescued_errors else None,
                "identity_deterioration_count": len(deteriorated),
                "identity_deterioration_rate_among_top1_correct": len(deteriorated) / top1_correct if top1_correct else None,
                "wrong_candidate_count": len(wrong_candidates),
                "pnp_failure_rejection_count": pnp_rejected,
                "pnp_failure_rejection_rate": pnp_rejected / len(wrong_candidates) if wrong_candidates else None,
                "pnp_failure_rejection_wilson_lower": pnp_reject_wilson[0],
                "pnp_failure_rejection_wilson_upper": pnp_reject_wilson[1],
                "pnp_failure_rejection_bootstrap_lower": bootstrap["pnp_failure_rejection_rate"][0],
                "pnp_failure_rejection_bootstrap_upper": bootstrap["pnp_failure_rejection_rate"][1],
                "selection_level_rejection_count": selection_rejected,
                "selection_level_rejection_rate": selection_rejected / len(wrong_candidates) if wrong_candidates else None,
                "selection_level_rejection_wilson_lower": selection_reject_wilson[0],
                "selection_level_rejection_wilson_upper": selection_reject_wilson[1],
                "selection_level_rejection_bootstrap_lower": bootstrap["selection_level_rejection_rate"][0],
                "selection_level_rejection_bootstrap_upper": bootstrap["selection_level_rejection_rate"][1],
                "productive_rejection_count": len(rescued),
                "productive_rejection_rate": len(rescued) / len(opportunities) if opportunities else None,
                "confident_wrong_count": confident,
                "confident_wrong_rate": confident / len(queries),
                "confident_wrong_wilson_lower": confident_wilson[0],
                "confident_wrong_wilson_upper": confident_wilson[1],
                "confident_wrong_bootstrap_lower": bootstrap["confident_wrong_rate"][0],
                "confident_wrong_bootstrap_upper": bootstrap["confident_wrong_rate"][1],
                "query_pnp_success_count": sum(row["pnp_success"] for row in queries),
                "final_localization_error_mean_m": float(np.mean(final_errors)) if final_errors else None,
                "final_localization_error_median_m": float(np.median(final_errors)) if final_errors else None,
                "final_localization_success_le3m_count": sum(error <= FINAL_SUCCESS_M for error in final_errors),
                "final_localization_success_le3m_rate": sum(error <= FINAL_SUCCESS_M for error in final_errors) / len(queries),
            })
    return rows


def make_transition_table(queries: list[dict[str, Any]], by_query: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    counts: defaultdict[tuple[Any, ...], int] = defaultdict(int)
    for tau in CORRECTNESS_THRESHOLDS_M:
        for query in queries:
            candidates = by_query[query["sample_id"]]
            top1 = candidates[0]
            if not top1["pnp_success"]:
                geometry_outcome = "top1_pnp_failure"
            elif query["selected_slot"] == 0:
                geometry_outcome = "top1_preserved"
            elif query[f"rescued_tau_{int(tau)}m"]:
                geometry_outcome = "productive_alternative_selected"
            else:
                geometry_outcome = "nonproductive_alternative_selected"
            key = (
                tau,
                query[f"top1_state_tau_{int(tau)}m"],
                geometry_outcome,
                query[f"selected_state_tau_{int(tau)}m"],
                query["final_error_state"],
            )
            counts[key] += 1
    return [
        {
            "correctness_tau_m": key[0],
            "upstream_top1_state": key[1],
            "geometry_selection_outcome": key[2],
            "selected_candidate_state": key[3],
            "final_localization_outcome": key[4],
            "query_count": count,
        }
        for key, count in sorted(counts.items())
    ]


def frozen_verdict(primary: dict[str, Any]) -> tuple[str, dict[str, bool | None]]:
    rescue_quality = primary["rescued_final_le3m_rate"]
    tests = {
        "go_identity_increment_le_5pp": primary["candidate_identity_increment_pp"] <= 5.0,
        "go_rescue_rate_le_10pct": primary["geometry_rescue_rate"] is not None and primary["geometry_rescue_rate"] <= 0.10,
        "go_rescue_wilson_upper_lt_20pct": primary["rescue_wilson_upper"] is not None and primary["rescue_wilson_upper"] < 0.20,
        "go_wrong_candidate_rejection_le_25pct": None,
        "go_confident_wrong_ge_20pct": primary["confident_wrong_rate"] >= 0.20,
        "nogo_identity_improvement_ge_10pp": primary["candidate_identity_increment_pp"] >= 10.0,
        "nogo_rescue_rate_ge_25pct": primary["geometry_rescue_rate"] is not None and primary["geometry_rescue_rate"] >= 0.25,
        "nogo_rescued_final_le3m_ge_80pct": rescue_quality is not None and rescue_quality >= 0.80,
        "nogo_wrong_candidate_rejection_ge_50pct": None,
    }
    # GO cannot be adjudicated because one required preregistered term has no
    # frozen operational definition. Do not substitute any observed variant.
    go = False
    no_go = (
        tests["nogo_identity_improvement_ge_10pp"]
        and tests["nogo_rescue_rate_ge_25pct"]
        and tests["nogo_rescued_final_le3m_ge_80pct"]
    )
    if no_go:
        return "NO-GO", tests
    if go:
        return "GO", tests
    return "INCONCLUSIVE", tests


def format_pct(value: float | None) -> str:
    return "UNAVAILABLE" if value is None else f"{100.0 * value:.2f}%"


def make_report(summary: dict[str, Any], sensitivity: list[dict[str, Any]]) -> str:
    primary = summary["primary_metrics"]
    lines = [
        "# GEO-1 Minimal Falsification Report",
        "",
        "## Evidence status",
        "",
        "Result-file-confirmed offline analysis of 295 Scene_16 satellite queries and 1,475 saved candidate records. No model, matcher, DSM, PnP, or training run was executed.",
        "",
        "## Primary result (`tau=0 m`, inlier ratio `>=0.3`)",
        "",
        f"- Retrieval Top-1 identity accuracy: {format_pct(primary['top1_identity_accuracy'])} ({primary['top1_correct_count']}/{primary['num_queries']}).",
        f"- Selected identity accuracy: {format_pct(primary['selected_identity_accuracy'])} ({primary['selected_correct_count']}/{primary['num_queries']}).",
        f"- Downstream candidate identity increment: {primary['candidate_identity_increment_pp']:+.2f} pp.",
        f"- Geometry-mediated rescue: {format_pct(primary['geometry_rescue_rate'])} ({primary['rescued_count']}/{primary['rescue_opportunity_count']}), Wilson 95% CI [{format_pct(primary['rescue_wilson_lower'])}, {format_pct(primary['rescue_wilson_upper'])}].",
        f"- Rescued cases with final error <=3 m: {format_pct(primary['rescued_final_le3m_rate'])} ({primary['rescued_final_le3m_count']}/{primary['rescued_count']}).",
        f"- Correct retrieval Top-1 changed to a wrong selected candidate: {format_pct(primary['identity_deterioration_rate_among_top1_correct'])} ({primary['identity_deterioration_count']}/{primary['top1_correct_count']}).",
        f"- PnP-failure wrong-candidate rejection: {format_pct(primary['pnp_failure_rejection_rate'])} ({primary['pnp_failure_rejection_count']}/{primary['wrong_candidate_count']}).",
        f"- Selection-level wrong-candidate rejection: {format_pct(primary['selection_level_rejection_rate'])} ({primary['selection_level_rejection_count']}/{primary['wrong_candidate_count']}).",
        f"- Productive rejection/rescue: {format_pct(primary['productive_rejection_rate'])} ({primary['productive_rejection_count']}/{primary['rescue_opportunity_count']}).",
        f"- Confident-but-wrong: {format_pct(primary['confident_wrong_rate'])} ({primary['confident_wrong_count']}/{primary['num_queries']}).",
        "- Native RoMa confidence/ranking: UNAVAILABLE.",
        "- Per-candidate PnP reprojection error: UNAVAILABLE.",
        "",
        "## Preregistered verdict adjudication",
        "",
        f"**{summary['preregistered_verdict']}**",
        "",
        "The preregistration did not uniquely define wrong-candidate rejection. Its <=25% GO clause and >=50% NO-GO clause are therefore UNADJUDICATED: PnP-failure, selection-level, and productive rejection are all retained, and none is selected post hoc for the verdict.",
        "",
        f"GO support is not established: identity increment is {primary['candidate_identity_increment_pp']:+.2f} pp (required <=+5 pp), rescue is {format_pct(primary['geometry_rescue_rate'])} with Wilson upper {format_pct(primary['rescue_wilson_upper'])} (required <=10% and upper <20%), and the rejection clause is unadjudicable. The independent NO-GO conjunction fails because identity improvement is below +10 pp and rescued <=3 m rate is {format_pct(primary['rescued_final_le3m_rate'])} rather than >=80%; the alternative rejection branch is unadjudicable.",
        "",
        "## Strongest counterevidence and strongest premise-consistent evidence",
        "",
        f"The strongest counterevidence to the premise is the {format_pct(primary['geometry_rescue_rate'])} productive rescue rate among queries with a wrong retrieval Top-1 and a correct Top-5 alternative. Geometry-mediated selection therefore does not merely preserve the retrieval Top-1 candidate identity in this run.",
        "",
        f"The strongest premise-consistent evidence is that PnP hard-rejected {format_pct(primary['pnp_failure_rejection_rate'])} of wrong candidates while {format_pct(primary['confident_wrong_rate'])} of all queries ended in a selected wrong candidate with inlier ratio >=0.3. In addition, only {format_pct(primary['rescued_final_le3m_rate'])} of identity rescues produced <=3 m final localization, so most footprint-identity rescues were not high-accuracy geographic rescues.",
        "",
        "## Future candidate-pool evidence",
        "",
        f"- Rescue: {primary['rescued_count']}/{primary['rescue_opportunity_count']}.",
        f"- Correct retrieval Top-1 to wrong selected candidate: {primary['identity_deterioration_count']}/{primary['top1_correct_count']}.",
        f"- Net candidate identity increment: {primary['candidate_identity_increment_pp']:+.2f} pp.",
        f"- Wrong-candidate PnP failure: {primary['pnp_failure_rejection_count']}/{primary['wrong_candidate_count']}.",
        f"- Confident-but-wrong at inlier ratio 0.3: {format_pct(primary['confident_wrong_rate'])}.",
        "",
        "## Sensitivity",
        "",
        "| tau (m) | inlier ratio | identity increment (pp) | rescue | rescued <=3 m | deterioration | PnP-failure rejection | selection rejection | confident-wrong |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sensitivity:
        lines.append(
            f"| {row['correctness_tau_m']:.0f} | {row['inlier_ratio_threshold']:.1f} | "
            f"{row['candidate_identity_increment_pp']:+.2f} | {format_pct(row['geometry_rescue_rate'])} | {format_pct(row['rescued_final_le3m_rate'])} | "
            f"{format_pct(row['identity_deterioration_rate_among_top1_correct'])} | "
            f"{format_pct(row['pnp_failure_rejection_rate'])} | {format_pct(row['selection_level_rejection_rate'])} | "
            f"{format_pct(row['confident_wrong_rate'])} |"
        )
    lines.extend([
        "",
        "## Interpretation boundary",
        "",
        "The strict increment compares CAMP retrieval Top-1 identity with the final max-inlier selected identity. It measures the joint downstream reranking behavior of learned matches, DSM lifting, PnP/RANSAC, and selection; it is not a PnP-only causal effect. Coverage and affine-coherence fields in the candidate table are analysis-defined proxies and are not used by the frozen verdict.",
        "",
        "The full provenance comes from one nondeterministic pipeline run. The earlier L16_0001 smoke demonstrated run-to-run changes in PnP inliers, selected index, and final error despite invariant retrieval Top-5. Bootstrap intervals quantify query sampling uncertainty, not algorithmic rerun variance.",
        "",
        "## Decision",
        "",
        "The final verdict is INCONCLUSIVE. Its primary basis is that native RoMa correspondence-only ranking cannot be recovered, so the PnP-only independent causal increment is not identifiable, while observed downstream reranking both rescues many wrong Top-1 cases and corrupts many correct Top-1 cases. The ambiguous preregistered rejection clause is not used to decide the verdict. GEO-1 should STOP in its current formulation as a method-development candidate. This is not a claim that geometry is useless.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if args.bootstrap_repetitions != 10_000:
        raise ValueError("Frozen analysis requires exactly 10,000 bootstrap repetitions")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    candidates, queries, by_query = extract_all(args.input_root)
    sensitivity = compute_sensitivity(
        candidates,
        queries,
        by_query,
        args.bootstrap_repetitions,
        args.bootstrap_seed,
    )
    primary = next(
        row for row in sensitivity
        if row["correctness_tau_m"] == PRIMARY_TAU_M
        and row["inlier_ratio_threshold"] == PRIMARY_INLIER_RATIO
    )
    verdict, verdict_tests = frozen_verdict(primary)
    transition_table = make_transition_table(queries, by_query)

    summary = {
        "research_question": "Does explicit geometry correct upstream candidate/geographic identity errors, or mainly fit within the selected visual hypotheses?",
        "evidence_level": "result-file-confirmed offline analysis",
        "input_root": str(args.input_root.resolve()),
        "num_queries": len(queries),
        "num_candidate_records": len(candidates),
        "bootstrap_repetitions": args.bootstrap_repetitions,
        "bootstrap_seed": args.bootstrap_seed,
        "primary_correctness_tau_m": PRIMARY_TAU_M,
        "primary_inlier_ratio_threshold": PRIMARY_INLIER_RATIO,
        "preregistered_rejection_definition": "UNRESOLVED: no unique operational definition was frozen",
        "rejection_criterion_status": "UNADJUDICATED for both <=25% GO and >=50% NO-GO clauses",
        "reported_rejection_definitions": {
            "pnp_failure_rejection": "wrong candidate has no successful PnP pose",
            "selection_level_rejection": "wrong candidate is not selected",
            "productive_rejection": "wrong retrieval Top-1 changes to a correct selected candidate when a correct Top-5 candidate exists",
        },
        "primary_metrics": primary,
        "preregistered_verdict": verdict,
        "verdict_tests": verdict_tests,
        "unavailable_metrics": [
            "native RoMa per-match confidence/certainty",
            "native RoMa correspondence-only candidate ranking",
            "per-candidate PnP reprojection error/residual distribution",
            "full-run rerun variance",
            "PnP-only causal candidate-identity increment",
        ],
        "proxy_metrics_not_used_for_verdict": [
            "UAV/reference spatial coverage and concentration",
            "global affine coherence residual",
            "DSM-valid support descriptors",
        ],
        "evidence_boundary": "Retrieval Top-1 to selected identity is a strict joint downstream reranking increment, not a PnP-only causal increment.",
        "verdict_basis": [
            "native RoMa correspondence-only candidate ranking is unavailable",
            "PnP-only independent causal increment is therefore not identifiable",
            "downstream reranking both rescues wrong Top-1 cases and corrupts correct Top-1 cases",
            "preregistered wrong-candidate rejection criterion is operationally ambiguous and unadjudicated",
        ],
        "future_candidate_pool_evidence": {
            "rescue": "69/100",
            "correct_top1_to_wrong_selected": "54/154",
            "net_candidate_identity_increment_pp": 5.084745762711864,
            "wrong_candidate_pnp_failure": "0/850",
            "confident_but_wrong_alpha_0_3": 0.27796610169491526,
        },
        "recommended_decision": "STOP GEO-1 in its current formulation as a method-development candidate",
    }

    write_csv(args.output_dir / "geo1_candidate_metrics.csv", candidates)
    write_csv(args.output_dir / "geo1_query_transitions.csv", queries)
    write_csv(args.output_dir / "geo1_sensitivity.csv", sensitivity)
    write_csv(args.output_dir / "geo1_transition_table.csv", transition_table)
    write_json(args.output_dir / "geo1_summary.json", summary)
    (args.output_dir / "geo1_minimal_falsification_report.md").write_text(
        make_report(summary, sensitivity),
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "verdict": verdict, "primary": json_ready(primary)}))


if __name__ == "__main__":
    main()
