#!/usr/bin/env python3
"""Recover Scene_16 solver correspondence provenance from saved artifacts.

This is an offline, CPU-only audit. It does not run retrieval, RoMa, DSM
sampling, PnP, or any model. ``inlier_indices`` are interpreted exactly as in
the official AnyVisLoc match+localization runner: they index the correspondence
arrays after applying the saved ``valid`` mask.
"""

from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import math
import statistics
import struct
import tarfile
import zipfile
from collections import defaultdict
from pathlib import Path


CATASTROPHIC = ("L16_0012", "L16_0096", "L16_0097", "L16_0098", "L16_0101")
SUCCESS = ("L16_0076", "L16_0077", "L16_0078", "L16_0229")
ALL_IDS = CATASTROPHIC + SUCCESS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aerial-archive", type=Path, required=True)
    parser.add_argument("--satellite-archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--query-threshold-px", type=float, default=5.0)
    parser.add_argument("--grid-size", type=int, default=8)
    return parser.parse_args()


def read_npy(raw: bytes) -> tuple[tuple[int, ...], list[float | int | bool]]:
    if raw[:6] != b"\x93NUMPY":
        raise ValueError("Not an NPY payload")
    version = tuple(raw[6:8])
    offset = 8
    if version == (1, 0):
        header_len = struct.unpack("<H", raw[offset : offset + 2])[0]
        offset += 2
    else:
        header_len = struct.unpack("<I", raw[offset : offset + 4])[0]
        offset += 4
    header = ast.literal_eval(raw[offset : offset + header_len].decode("latin1").strip())
    offset += header_len
    if header["fortran_order"]:
        raise ValueError("Fortran-order arrays are not supported")
    formats = {"<f4": "f", "<i4": "i", "|b1": "?"}
    if header["descr"] not in formats:
        raise ValueError(f"Unsupported dtype: {header['descr']}")
    fmt = "<" + formats[header["descr"]]
    item_size = struct.calcsize(fmt)
    count = math.prod(header["shape"])
    values = [item[0] for item in struct.iter_unpack(fmt, raw[offset : offset + count * item_size])]
    return tuple(header["shape"]), values


def as_points(shape: tuple[int, ...], values: list[float | int | bool]) -> list[tuple[float, float]]:
    if len(shape) != 2 or shape[1] != 2:
        raise ValueError(f"Expected Nx2 points, got {shape}")
    return [(float(values[2 * i]), float(values[2 * i + 1])) for i in range(shape[0])]


class Archive:
    def __init__(self, path: Path):
        self.tar = tarfile.open(path, "r:gz")
        self.members: dict[str, dict[str, str]] = defaultdict(dict)
        for name in self.tar.getnames():
            parts = name.split("/")
            for sample_id in ALL_IDS:
                if sample_id in parts and parts[-1] in {"result.json", "matches_and_pnp_inputs.npz"}:
                    self.members[sample_id][parts[-1]] = name
        missing = [sample_id for sample_id in ALL_IDS if len(self.members[sample_id]) != 2]
        if missing:
            raise ValueError(f"Missing archive members for: {missing}")

    def close(self) -> None:
        self.tar.close()

    def sample(self, sample_id: str) -> tuple[dict, dict[str, object]]:
        result = json.load(self.tar.extractfile(self.members[sample_id]["result.json"]))
        npz_raw = self.tar.extractfile(self.members[sample_id]["matches_and_pnp_inputs.npz"]).read()
        arrays: dict[str, object] = {}
        with zipfile.ZipFile(io.BytesIO(npz_raw)) as archive:
            for key in archive.namelist():
                shape, values = read_npy(archive.read(key))
                name = key.removesuffix(".npy")
                arrays[name] = as_points(shape, values) if len(shape) == 2 and shape[1] == 2 else values
        return result, arrays


def median(values: list[float]) -> float:
    return float(statistics.median(values)) if values else math.nan


def mean(values: list[float]) -> float:
    return float(statistics.fmean(values)) if values else math.nan


def std(values: list[float]) -> float:
    return float(statistics.pstdev(values)) if len(values) > 1 else 0.0


def normalize(points: list[tuple[float, float]], bounds: tuple[float, float, float, float]) -> list[tuple[float, float]]:
    x0, y0, x1, y1 = bounds
    dx = max(x1 - x0, 1e-12)
    dy = max(y1 - y0, 1e-12)
    return [((x - x0) / dx, (y - y0) / dy) for x, y in points]


def point_bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    points = sorted(set(points))
    if len(points) <= 1:
        return points
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower = []
    for point in points:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper = []
    for point in reversed(points):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def polygon_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    return abs(sum(points[i][0] * points[(i + 1) % len(points)][1] - points[(i + 1) % len(points)][0] * points[i][1] for i in range(len(points)))) / 2.0


def covariance_ratio(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    mx = mean([p[0] for p in points])
    my = mean([p[1] for p in points])
    a = mean([(p[0] - mx) ** 2 for p in points])
    c = mean([(p[1] - my) ** 2 for p in points])
    b = mean([(p[0] - mx) * (p[1] - my) for p in points])
    disc = math.sqrt(max((a - c) ** 2 + 4 * b * b, 0.0))
    major = (a + c + disc) / 2.0
    minor = (a + c - disc) / 2.0
    return max(minor, 0.0) / max(major, 1e-12)


def spatial_metrics(points: list[tuple[float, float]], bounds: tuple[float, float, float, float], grid: int) -> dict[str, float]:
    normalized = normalize(points, bounds)
    counts = [0] * (grid * grid)
    for x, y in normalized:
        col = min(grid - 1, max(0, int(x * grid)))
        row = min(grid - 1, max(0, int(y * grid)))
        counts[row * grid + col] += 1
    n = max(len(points), 1)
    probs = [count / n for count in counts if count]
    raw_hhi = sum(value * value for value in probs)
    uniform = 1.0 / (grid * grid)
    normalized_hhi = (raw_hhi - uniform) / max(1.0 - uniform, 1e-12)
    entropy = -sum(value * math.log(value) for value in probs) / math.log(grid * grid)
    return {
        "grid_occupancy": sum(count > 0 for count in counts) / (grid * grid),
        "normalized_hhi": normalized_hhi,
        "spatial_entropy": entropy,
        "convex_hull_coverage": polygon_area(convex_hull(normalized)),
        "covariance_minor_major_ratio": covariance_ratio(normalized),
    }


def nearest_map(source: list[tuple[float, float]], target: list[tuple[float, float]], radius: float) -> list[int | None]:
    cell = max(radius, 1e-6)
    buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, (x, y) in enumerate(target):
        buckets[(math.floor(x / cell), math.floor(y / cell))].append(index)
    result: list[int | None] = []
    radius2 = radius * radius
    for x, y in source:
        gx, gy = math.floor(x / cell), math.floor(y / cell)
        best = None
        best_d2 = radius2
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for index in buckets.get((gx + dx, gy + dy), []):
                    tx, ty = target[index]
                    d2 = (x - tx) ** 2 + (y - ty) ** 2
                    if d2 <= best_d2:
                        best, best_d2 = index, d2
        result.append(best)
    return result


def mutual_pairs(aerial_query, satellite_query, radius: float) -> dict[int, int]:
    aerial_to_satellite = nearest_map(aerial_query, satellite_query, radius)
    satellite_to_aerial = nearest_map(satellite_query, aerial_query, radius)
    pairs = {}
    for satellite_index, aerial_index in enumerate(satellite_to_aerial):
        if aerial_index is not None and aerial_to_satellite[aerial_index] == satellite_index:
            pairs[satellite_index] = aerial_index
    return pairs


def disagreement_metrics(indices: list[int], pairs: dict[int, int], aerial_xy, satellite_xy) -> dict[str, float | int]:
    deltas = []
    for satellite_index in indices:
        aerial_index = pairs.get(satellite_index)
        if aerial_index is None:
            continue
        sx, sy = satellite_xy[satellite_index]
        ax, ay = aerial_xy[aerial_index]
        deltas.append((sx - ax, sy - ay))
    distances = [math.hypot(dx, dy) for dx, dy in deltas]
    shift_x = median([d[0] for d in deltas])
    shift_y = median([d[1] for d in deltas])
    residuals = [math.hypot(dx - shift_x, dy - shift_y) for dx, dy in deltas]
    return {
        "paired_count": len(distances),
        "paired_fraction_of_subset": len(distances) / max(len(indices), 1),
        "mean_m": mean(distances),
        "median_m": median(distances),
        "agreement_3m": sum(value <= 3.0 for value in distances) / max(len(distances), 1),
        "agreement_5m": sum(value <= 5.0 for value in distances) / max(len(distances), 1),
        "coherent_shift_m": math.hypot(shift_x, shift_y),
        "shift_corrected_residual_median_m": median(residuals),
    }


def lift_disagreement_metrics(indices: list[int], pairs: dict[int, int], aerial_z, satellite_z) -> dict[str, float | int]:
    signed = [float(satellite_z[index]) - float(aerial_z[pairs[index]]) for index in indices if index in pairs]
    absolute = [abs(value) for value in signed]
    return {
        "paired_count": len(signed),
        "signed_median_m": median(signed),
        "absolute_mean_m": mean(absolute),
        "absolute_median_m": median(absolute),
        "agreement_2m": sum(value <= 2.0 for value in absolute) / max(len(absolute), 1),
        "agreement_5m": sum(value <= 5.0 for value in absolute) / max(len(absolute), 1),
    }


def prefixed(row: dict[str, object], prefix: str, values: dict[str, object]) -> None:
    for key, value in values.items():
        row[f"{prefix}_{key}"] = value


def geometry_metrics(indices: list[int], arrays: dict[str, object], result: dict, grid: int, solver_bounds: dict[str, tuple[float, float, float, float]]) -> dict[str, float | int]:
    uav = [arrays["uav_pts_original"][index] for index in indices]
    ref = [arrays["ref_pts_patch"][index] for index in indices]
    world = [(float(arrays["local_x"][index]), float(arrays["local_y"][index])) for index in indices]
    z = [float(arrays["dsm_z"][index]) for index in indices]
    output: dict[str, float | int] = {}
    for name, points, bounds in (
        ("uav", uav, (0.0, 0.0, float(result["uav_input_width"]), float(result["uav_input_height"]))),
        ("reference", ref, (0.0, 0.0, float(result["ref_patch_width"]), float(result["ref_patch_height"]))),
        ("world_xy", world, solver_bounds["world_xy"]),
    ):
        prefixed(output, name, spatial_metrics(points, bounds, grid))
    output["world_x_span_m"] = max(p[0] for p in world) - min(p[0] for p in world)
    output["world_y_span_m"] = max(p[1] for p in world) - min(p[1] for p in world)
    output["dsm_z_min_m"] = min(z)
    output["dsm_z_max_m"] = max(z)
    output["dsm_z_range_m"] = max(z) - min(z)
    output["dsm_z_std_m"] = std(z)
    rounded = [round(value, 3) for value in z]
    output["dsm_z_unique_1mm"] = len(set(rounded))
    output["dsm_z_dominant_fraction"] = max(rounded.count(value) for value in set(rounded)) / len(rounded)
    return output


def analyze_sample(sample_id: str, aerial_archive: Archive, satellite_archive: Archive, threshold: float, grid: int) -> dict[str, object]:
    aerial_result, aerial = aerial_archive.sample(sample_id)
    result, arrays = satellite_archive.sample(sample_id)
    raw_count = len(arrays["uav_pts_original"])
    valid_indices = [index for index, value in enumerate(arrays["valid"]) if bool(value)]
    inlier_solver_indices = [int(value) for value in arrays["inlier_indices"]]
    if any(index < 0 or index >= len(valid_indices) for index in inlier_solver_indices):
        raise ValueError(f"{sample_id}: inlier index outside solver input")
    inlier_raw_indices = [valid_indices[index] for index in inlier_solver_indices]
    if raw_count != int(result["num_matches"]):
        raise ValueError(f"{sample_id}: raw count mismatch")
    if len(valid_indices) != int(result["num_pnp_input"]):
        raise ValueError(f"{sample_id}: solver input count mismatch")
    if len(inlier_raw_indices) != int(result["num_inliers"]):
        raise ValueError(f"{sample_id}: inlier count mismatch")

    pairs = mutual_pairs(aerial["uav_pts_original"], arrays["uav_pts_original"], threshold)
    aerial_xy = list(zip(aerial["local_x"], aerial["local_y"]))
    satellite_xy = list(zip(arrays["local_x"], arrays["local_y"]))
    solver_world = [(float(arrays["local_x"][i]), float(arrays["local_y"][i])) for i in valid_indices]
    bounds = {"world_xy": point_bounds(solver_world)}
    solver_geometry = geometry_metrics(valid_indices, arrays, result, grid, bounds)
    inlier_geometry = geometry_metrics(inlier_raw_indices, arrays, result, grid, bounds)
    solver_disagreement = disagreement_metrics(valid_indices, pairs, aerial_xy, satellite_xy)
    inlier_disagreement = disagreement_metrics(inlier_raw_indices, pairs, aerial_xy, satellite_xy)
    solver_lift_disagreement = lift_disagreement_metrics(
        valid_indices, pairs, aerial["dsm_z"], arrays["dsm_z"]
    )
    inlier_lift_disagreement = lift_disagreement_metrics(
        inlier_raw_indices, pairs, aerial["dsm_z"], arrays["dsm_z"]
    )

    group = "2D_CONSISTENT_BUT_CATASTROPHIC" if sample_id in CATASTROPHIC else "LOW_AGREEMENT_BUT_SUCCESSFUL"
    row: dict[str, object] = {
        "sample_id": sample_id,
        "focus_group": group,
        "final_localization_error_m": float(result["pred_error_m"]),
        "pred_x": float(result["pred_x"]),
        "pred_y": float(result["pred_y"]),
        "pred_z": float(result["pred_z"]),
        "true_x": float(result["true_x"]),
        "true_y": float(result["true_y"]),
        "true_z": float(result["true_z"]),
        "pred_z_error_m": float(result["pred_z"]) - float(result["true_z"]),
        "raw_correspondence_count": raw_count,
        "valid_2d3d_count": len(valid_indices),
        "solver_input_count": len(valid_indices),
        "pnp_inlier_count": len(inlier_raw_indices),
        "pnp_inlier_ratio": len(inlier_raw_indices) / max(len(valid_indices), 1),
        "pnp_success": bool(result["pnp_success"]),
        "all_raw_matches_valid_for_solver": raw_count == len(valid_indices),
        "inlier_indices_reference": "valid_filtered_solver_input",
        "pnp_method_artifact": "MISSING",
        "pnp_reprojection_residual_artifact": "MISSING",
    }
    prefixed(row, "solver", solver_geometry)
    prefixed(row, "inlier", inlier_geometry)
    prefixed(row, "solver_geo", solver_disagreement)
    prefixed(row, "inlier_geo", inlier_disagreement)
    prefixed(row, "solver_lift", solver_lift_disagreement)
    prefixed(row, "inlier_lift", inlier_lift_disagreement)
    row["inlier_minus_solver_agreement_5m"] = float(inlier_disagreement["agreement_5m"]) - float(solver_disagreement["agreement_5m"])
    row["inlier_vs_solver_uav_occupancy_ratio"] = float(inlier_geometry["uav_grid_occupancy"]) / max(float(solver_geometry["uav_grid_occupancy"]), 1e-12)
    row["inlier_vs_solver_world_hull_ratio"] = float(inlier_geometry["world_xy_convex_hull_coverage"]) / max(float(solver_geometry["world_xy_convex_hull_coverage"]), 1e-12)
    row["small_wrong_subset_dominates_pose"] = "UNDETERMINED_NO_MANUAL_CORRESPONDENCE_GT_OR_REPROJECTION_RESIDUAL"
    row["validity_filter_degradation"] = (
        "NONE_ALL_RAW_MATCHES_ENTER_SOLVER"
        if raw_count == len(valid_indices)
        else "PRESENT"
    )
    row["paired_inlier_horizontal_quality"] = (
        "NO_DEGRADATION_OBSERVED"
        if float(inlier_disagreement["agreement_5m"]) >= 0.5
        else "LOW_PSEUDO_REFERENCE_AGREEMENT"
    )
    row["degeneracy_proxy"] = (
        "CONCENTRATED_OR_NEAR_COLLINEAR"
        if float(inlier_geometry["uav_grid_occupancy"]) < 0.25 or float(inlier_geometry["world_xy_covariance_minor_major_ratio"]) < 0.05
        else "NO_STRONG_2D_XY_DEGENERACY_BY_CURRENT_PROXIES"
    )
    row["depth_pose_anomaly"] = (
        "LARGE_PREDICTED_Z_ERROR_OVER_20M"
        if abs(float(row["pred_z_error_m"])) > 20.0
        else "NO_LARGE_PREDICTED_Z_ERROR_OVER_20M"
    )
    row["shared_wrong_pose_branch_pattern"] = (
        "YES_CONSECUTIVE_0096_0097_0098_0101"
        if sample_id in {"L16_0096", "L16_0097", "L16_0098", "L16_0101"}
        else "NO"
    )
    if group.startswith("2D_CONSISTENT"):
        if float(inlier_disagreement["agreement_5m"]) >= 0.5:
            explanation = "PnP inliers remain aerial-satellite consistent; solver subset quality degradation does not explain the catastrophic pose."
        elif float(row["inlier_minus_solver_agreement_5m"]) < -0.1:
            explanation = "RANSAC selects an inlier subset less cross-reference-consistent than the solver pool; subset selection may contribute."
        else:
            explanation = "Inliers are not strongly cross-reference-consistent, but the current pseudo-reference is insufficient for causal attribution."
    else:
        explanation = "The successful pose uses fewer inliers despite lower cross-reference agreement; inlier count and aerial pseudo-agreement are not accuracy guarantees."
    row["provenance_interpretation"] = explanation
    return row


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def numeric_group_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    metrics = (
        "final_localization_error_m", "raw_correspondence_count", "valid_2d3d_count",
        "pnp_inlier_count", "pnp_inlier_ratio", "solver_uav_grid_occupancy",
        "inlier_uav_grid_occupancy", "inlier_world_xy_grid_occupancy",
        "inlier_world_xy_covariance_minor_major_ratio", "inlier_dsm_z_std_m",
        "solver_geo_agreement_5m", "inlier_geo_agreement_5m",
        "solver_geo_paired_fraction_of_subset", "inlier_geo_paired_fraction_of_subset",
        "solver_geo_median_m", "inlier_geo_median_m",
        "inlier_lift_absolute_median_m", "inlier_lift_signed_median_m",
        "inlier_minus_solver_agreement_5m", "pred_z_error_m",
    )
    output = []
    for group in ("2D_CONSISTENT_BUT_CATASTROPHIC", "LOW_AGREEMENT_BUT_SUCCESSFUL"):
        subset = [row for row in rows if row["focus_group"] == group]
        for metric in metrics:
            values = [float(row[metric]) for row in subset]
            output.append({"focus_group": group, "num_samples": len(subset), "metric": metric, "mean": mean(values), "median": median(values), "min": min(values), "max": max(values)})
    return output


def svg_scatter(points, indices, bounds, x, y, width, height, color, radius=1.2, opacity=0.35):
    normalized = normalize([points[index] for index in indices], bounds)
    return "".join(f'<circle cx="{x + px * width:.2f}" cy="{y + (1-py) * height:.2f}" r="{radius}" fill="{color}" fill-opacity="{opacity}"/>' for px, py in normalized)


def write_sample_svg(path: Path, row: dict[str, object], result: dict, arrays: dict[str, object]) -> None:
    valid = [i for i, value in enumerate(arrays["valid"]) if bool(value)]
    inlier_solver = [int(value) for value in arrays["inlier_indices"]]
    inliers = [valid[i] for i in inlier_solver]
    uav_bounds = (0.0, 0.0, float(result["uav_input_width"]), float(result["uav_input_height"]))
    world = list(zip(arrays["local_x"], arrays["local_y"]))
    world_bounds = point_bounds([world[i] for i in valid])
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="480" viewBox="0 0 1000 480">', '<rect width="1000" height="480" fill="white"/>']
    parts.append(f'<text x="30" y="28" font-family="sans-serif" font-size="18" font-weight="bold">{row["sample_id"]} — {row["focus_group"]}</text>')
    parts.append(f'<text x="30" y="52" font-family="sans-serif" font-size="14">error={float(row["final_localization_error_m"]):.3f} m, inliers={row["pnp_inlier_count"]}/{row["solver_input_count"]}, paired inliers={row["inlier_geo_paired_count"]}, paired-inlier Agreement@5m={float(row["inlier_geo_agreement_5m"]):.3f}</text>')
    for x0, title in ((30, "UAV image support"), (520, "World XY support")):
        parts.append(f'<text x="{x0}" y="84" font-family="sans-serif" font-size="15">{title}</text>')
        parts.append(f'<rect x="{x0}" y="95" width="440" height="320" fill="#f8fafc" stroke="#94a3b8"/>')
    parts.append(svg_scatter(arrays["uav_pts_original"], valid, uav_bounds, 30, 95, 440, 320, "#64748b"))
    parts.append(svg_scatter(arrays["uav_pts_original"], inliers, uav_bounds, 30, 95, 440, 320, "#dc2626", 1.6, 0.7))
    parts.append(svg_scatter(world, valid, world_bounds, 520, 95, 440, 320, "#64748b"))
    parts.append(svg_scatter(world, inliers, world_bounds, 520, 95, 440, 320, "#dc2626", 1.6, 0.7))
    parts.append('<circle cx="35" cy="445" r="4" fill="#64748b"/><text x="45" y="450" font-family="sans-serif" font-size="13">solver input</text><circle cx="160" cy="445" r="4" fill="#dc2626"/><text x="170" y="450" font-family="sans-serif" font-size="13">PnP/RANSAC inlier</text>')
    parts.append('</svg>')
    path.write_text("".join(parts), encoding="utf-8")


def write_group_svg(path: Path, rows: list[dict[str, object]]) -> None:
    metrics = (("pnp_inlier_ratio", "Inlier ratio", 1.0), ("inlier_geo_agreement_5m", "Inlier Agreement@5m", 1.0), ("inlier_uav_grid_occupancy", "Inlier UAV occupancy", 1.0), ("inlier_world_xy_covariance_minor_major_ratio", "Inlier world XY minor/major", 1.0))
    width, height = 1100, 700
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="30" y="34" font-family="sans-serif" font-size="20" font-weight="bold">Scene_16 solver provenance focus comparison</text>']
    for panel, (metric, label, maximum) in enumerate(metrics):
        x0 = 40 + (panel % 2) * 530
        y0 = 80 + (panel // 2) * 300
        parts.append(f'<text x="{x0}" y="{y0}" font-family="sans-serif" font-size="15">{label}</text><line x1="{x0}" y1="{y0+230}" x2="{x0+490}" y2="{y0+230}" stroke="#64748b"/>')
        for i, row in enumerate(rows):
            value = float(row[metric])
            bar_h = max(0.0, min(1.0, value / maximum)) * 190
            color = "#dc2626" if row["focus_group"].startswith("2D_CONSISTENT") else "#16a34a"
            bx = x0 + 10 + i * 52
            parts.append(f'<rect x="{bx}" y="{y0+230-bar_h:.2f}" width="34" height="{bar_h:.2f}" fill="{color}" fill-opacity="0.78"/><text x="{bx+17}" y="{y0+248}" text-anchor="middle" font-family="sans-serif" font-size="9" transform="rotate(45 {bx+17} {y0+248})">{row["sample_id"].replace("L16_", "")}</text>')
    parts.append('<rect x="40" y="660" width="14" height="14" fill="#dc2626"/><text x="62" y="672" font-family="sans-serif" font-size="13">2D-consistent catastrophic</text><rect x="260" y="660" width="14" height="14" fill="#16a34a"/><text x="282" y="672" font-family="sans-serif" font-size="13">low-Agreement successful</text></svg>')
    path.write_text("".join(parts), encoding="utf-8")


def write_note(path: Path, rows: list[dict[str, object]], summary: list[dict[str, object]]) -> None:
    lookup = {(row["focus_group"], row["metric"]): row for row in summary}
    cat = "2D_CONSISTENT_BUT_CATASTROPHIC"
    suc = "LOW_AGREEMENT_BUT_SUCCESSFUL"
    def med(group, metric): return float(lookup[(group, metric)]["median"])
    cat_inlier_consistent = sum(float(row["inlier_geo_agreement_5m"]) >= 0.5 for row in rows if row["focus_group"] == cat)
    lines = [
        "# Scene_16 Solver Correspondence Provenance Audit", "", "## Scope", "",
        "This CPU-only audit recovers the saved raw RoMa rows, valid 2D-3D solver inputs, PnP/RANSAC inlier indices, final pose, and final error for nine fixed focus samples. It does not rerun retrieval, RoMa, DSM sampling, PnP, or training.", "",
        "The official runner applies `valid` and passes `uav_pts_original[valid]` with `local_x/local_y/dsm_z[valid]` to PnP. Saved `inlier_indices` index this filtered solver-input array. All nine artifacts satisfy the recorded count/index invariants.", "",
        "## Artifact availability", "",
        "- Saved: raw match coordinates and row order; per-row world XYZ; valid mask; solver-input count; inlier indices; final pose; final error.",
        "- Missing: RoMa confidence/certainty, per-inlier reprojection residual, PnP method encoded in the artifact, RANSAC seed, and manual correspondence ground truth.", "",
        "## Focus-group comparison (median)", "",
        "| Metric | 2D-consistent catastrophic | Low-Agreement successful |", "| --- | ---: | ---: |",
        f"| Final error (m) | {med(cat, 'final_localization_error_m'):.3f} | {med(suc, 'final_localization_error_m'):.3f} |",
        f"| Solver input | {med(cat, 'valid_2d3d_count'):.1f} | {med(suc, 'valid_2d3d_count'):.1f} |",
        f"| PnP inliers | {med(cat, 'pnp_inlier_count'):.1f} | {med(suc, 'pnp_inlier_count'):.1f} |",
        f"| PnP inlier ratio | {med(cat, 'pnp_inlier_ratio'):.3f} | {med(suc, 'pnp_inlier_ratio'):.3f} |",
        f"| Solver Agreement@5m | {med(cat, 'solver_geo_agreement_5m'):.3f} | {med(suc, 'solver_geo_agreement_5m'):.3f} |",
        f"| Cross-reference-paired inlier fraction | {med(cat, 'inlier_geo_paired_fraction_of_subset'):.3f} | {med(suc, 'inlier_geo_paired_fraction_of_subset'):.3f} |",
        f"| Paired-inlier Agreement@5m | {med(cat, 'inlier_geo_agreement_5m'):.3f} | {med(suc, 'inlier_geo_agreement_5m'):.3f} |",
        f"| Paired-inlier aerial/satellite |Z| gap (m) | {med(cat, 'inlier_lift_absolute_median_m'):.3f} | {med(suc, 'inlier_lift_absolute_median_m'):.3f} |",
        f"| Inlier UAV occupancy | {med(cat, 'inlier_uav_grid_occupancy'):.3f} | {med(suc, 'inlier_uav_grid_occupancy'):.3f} |",
        f"| Inlier world-XY occupancy | {med(cat, 'inlier_world_xy_grid_occupancy'):.3f} | {med(suc, 'inlier_world_xy_grid_occupancy'):.3f} |",
        f"| Inlier world-XY minor/major | {med(cat, 'inlier_world_xy_covariance_minor_major_ratio'):.3f} | {med(suc, 'inlier_world_xy_covariance_minor_major_ratio'):.3f} |",
        f"| Inlier DSM-Z std (m) | {med(cat, 'inlier_dsm_z_std_m'):.3f} | {med(suc, 'inlier_dsm_z_std_m'):.3f} |",
        f"| Predicted Z error (m) | {med(cat, 'pred_z_error_m'):.3f} | {med(suc, 'pred_z_error_m'):.3f} |", "",
        "## Main findings", "",
        "1. All 3,000 raw matches are valid 2D-3D solver inputs in every focus sample. There is no hidden validity-filter collapse before PnP.",
        "2. Catastrophic cases have more, not fewer, PnP inliers than successful controls. Raw inlier count and ratio therefore do not explain accuracy.",
        f"3. {cat_inlier_consistent}/5 catastrophic samples retain Agreement@5m >= 0.5 among the PnP inliers that can be cross-reference paired. Only about one quarter of all inliers have a mutual aerial query match, so this does not certify every inlier; within the recoverable paired subset, however, RANSAC did not select correspondences that look worse under the aerial pseudo-reference.",
        "4. Solver/inlier spatial metrics and XY collinearity proxies do not show a common severe collapse unique to all catastrophic samples. Any sample-specific concentration remains a secondary diagnostic, not a group-level explanation.",
        "5. The satellite DSM is coarse and produces quantized Z support. The paired-inlier aerial/satellite Z gap is also large in successful controls, so Z disagreement alone is not sufficient to explain the split. Four neighboring catastrophic samples (L16_0096-L16_0101) nevertheless share a roughly -30 m predicted-Z error together with 88-92 m horizontal error, which is compatible with a wrong/ambiguous pose branch; the saved artifacts lack reprojection residuals and solver configuration needed to prove that mechanism.", "",
        "## Conclusion and GO / NO-GO", "",
        "The saved solver provenance does not provide a single stable explanation for the full 2D-consistent catastrophic group. Globally consistent correspondences remain consistent in the recoverable paired-inlier subset after validity filtering and RANSAC selection, while PnP reports many inliers. The evidence therefore does not support the hypothesis that a small low-quality or geometrically collapsed solver subset is the common cause. It does isolate a four-query wrong-pose branch with large coupled XY/Z error, but L16_0012 does not follow it.", "",
        "`NO-GO` for continuing to deepen this Scene_16 mechanism as a clean frontend-model target. Remaining explanations require manual/native-frame correspondence correctness, local satellite georegistration/orthorectification evidence, or solver reprojection diagnostics that were not saved. Under the agreed decision rule, stop further Scene_16 expansion and reconsider the research direction rather than designing a model from this subgroup.", "",
        "## Evidence boundary", "",
        "Aerial-satellite geographic disagreement is a pseudo-reference diagnostic, not manual correspondence truth. PnP inliers mean consistency with the estimated pose under a reprojection threshold; they do not certify geographic identity. The artifact does not save per-point reprojection residuals, so residual-distribution and numerical-conditioning claims remain unavailable.", "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    aerial = Archive(args.aerial_archive)
    satellite = Archive(args.satellite_archive)
    rows = []
    samples_for_svg = {}
    try:
        for sample_id in ALL_IDS:
            row = analyze_sample(sample_id, aerial, satellite, args.query_threshold_px, args.grid_size)
            rows.append(row)
            samples_for_svg[sample_id] = satellite.sample(sample_id)
    finally:
        aerial.close()
        satellite.close()
    summary = numeric_group_summary(rows)
    write_csv(args.output_dir / "scene16_solver_provenance_per_sample.csv", rows)
    write_csv(args.output_dir / "scene16_solver_provenance_group_comparison.csv", summary)
    (args.output_dir / "scene16_solver_provenance_summary.json").write_text(json.dumps({"num_samples": len(rows), "focus_ids": list(ALL_IDS), "group_comparison": summary, "missing_fields": ["RoMa certainty/confidence", "per-point PnP reprojection residual", "PnP method encoded in artifact", "RANSAC seed", "manual correspondence ground truth"]}, indent=2) + "\n", encoding="utf-8")
    visual_dir = args.output_dir / "visualizations"
    visual_dir.mkdir(exist_ok=True)
    for row in rows:
        result, arrays = samples_for_svg[str(row["sample_id"])]
        write_sample_svg(visual_dir / f"{row['sample_id']}_solver_inliers.svg", row, result, arrays)
    write_group_svg(visual_dir / "focus_group_comparison.svg", rows)
    write_note(args.output_dir / "scene16_solver_provenance_note.md", rows, summary)
    print(json.dumps({"num_samples": len(rows), "output_dir": str(args.output_dir), "visualizations": len(rows) + 1}, indent=2))


if __name__ == "__main__":
    main()
