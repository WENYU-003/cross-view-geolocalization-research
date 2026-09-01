#!/usr/bin/env python3
"""Build a DSM-free 24-query geometric correspondence audit.

The input evidence bundles do not contain RGB imagery or RoMa certainty maps.
Accordingly, this script visualizes only quantities that are present in the raw
artifacts: query coordinates, aerial/satellite map endpoints, mutual-pair
disagreement, robust shift, and shift-corrected residual. Semantic failure
labels remain explicitly unresolved until the original images are supplied.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import tarfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from analyze_cross_reference_2d import mutual_pairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aerial-archive", type=Path, required=True)
    parser.add_argument("--satellite-archive", type=Path, required=True)
    parser.add_argument("--shortlist", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--query-threshold-px", type=float, default=5.0)
    parser.add_argument("--max-lines", type=int, default=180)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


class EvidenceArchive:
    def __init__(self, path: Path):
        self.path = path
        self.tar = tarfile.open(path, "r:gz")
        self.members: dict[tuple[str, str], tarfile.TarInfo] = {}
        for member in self.tar.getmembers():
            parts = Path(member.name).parts
            if len(parts) < 2:
                continue
            filename = parts[-1]
            sample_id = parts[-2]
            if sample_id.startswith("L16_") and filename in {
                "result.json",
                "matches_and_pnp_inputs.npz",
            }:
                self.members[(sample_id, filename)] = member

    def read_bytes(self, sample_id: str, filename: str) -> bytes:
        member = self.members.get((sample_id, filename))
        if member is None:
            raise FileNotFoundError(f"{sample_id}/{filename} missing in {self.path}")
        stream = self.tar.extractfile(member)
        if stream is None:
            raise FileNotFoundError(member.name)
        return stream.read()

    def result(self, sample_id: str) -> dict:
        return json.loads(self.read_bytes(sample_id, "result.json"))

    def arrays(self, sample_id: str) -> dict[str, np.ndarray]:
        raw = self.read_bytes(sample_id, "matches_and_pnp_inputs.npz")
        with np.load(io.BytesIO(raw)) as artifact:
            keys = ("uav_pts_original", "local_x", "local_y")
            missing = [key for key in keys if key not in artifact.files]
            if missing:
                raise ValueError(f"{sample_id}: missing NPZ fields {missing}")
            return {key: np.asarray(artifact[key]).copy() for key in keys}

    def close(self) -> None:
        self.tar.close()


def load_shortlist(path: Path, limit: int | None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if limit is not None:
        rows = rows[:limit]
    if not rows:
        raise ValueError("shortlist is empty")
    return rows


def finite_points(arrays: dict[str, np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    query = np.asarray(arrays["uav_pts_original"], dtype=np.float64)
    map_xy = np.column_stack(
        (
            np.asarray(arrays["local_x"], dtype=np.float64),
            np.asarray(arrays["local_y"], dtype=np.float64),
        )
    )
    finite = np.all(np.isfinite(query), axis=1) & np.all(np.isfinite(map_xy), axis=1)
    return query[finite], map_xy[finite]


def validate_metadata(sample_id: str, aerial: dict, satellite: dict) -> None:
    if aerial.get("sample_id") != sample_id or satellite.get("sample_id") != sample_id:
        raise ValueError(f"{sample_id}: result.json identity mismatch")
    expected = {
        "scene_name",
        "matching_method",
        "pose_priori",
        "match_keypoints",
        "resize_ratio",
        "uav_input_width",
        "uav_input_height",
    }
    for key in expected:
        if aerial.get(key) != satellite.get(key):
            raise ValueError(f"{sample_id}: controlled field {key} differs")


def candidate_pattern(shift_norm: float, residual_median: float, agreement_5m: float) -> str:
    if shift_norm >= 5.0 and residual_median <= 3.0:
        return "COHERENT_SHIFT_CANDIDATE"
    if residual_median >= 5.0 or agreement_5m < 0.30:
        return "INCONSISTENT_CORRESPONDENCE_CANDIDATE"
    if shift_norm >= 3.0:
        return "MIXED_SHIFT_AND_RESIDUAL_CANDIDATE"
    return "RELATIVELY_CONSISTENT_2D_CANDIDATE"


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def map_points(points: np.ndarray, box: tuple[int, int, int, int], bounds: tuple[float, float, float, float]) -> np.ndarray:
    left, top, right, bottom = box
    x_min, x_max, y_min, y_max = bounds
    x_span = max(x_max - x_min, 1e-9)
    y_span = max(y_max - y_min, 1e-9)
    mapped = np.empty_like(points, dtype=np.float64)
    mapped[:, 0] = left + (points[:, 0] - x_min) / x_span * (right - left)
    mapped[:, 1] = bottom - (points[:, 1] - y_min) / y_span * (bottom - top)
    return mapped


def robust_bounds(points: np.ndarray, padding: float = 0.08) -> tuple[float, float, float, float]:
    x_min, y_min = np.quantile(points, 0.01, axis=0)
    x_max, y_max = np.quantile(points, 0.99, axis=0)
    x_pad = max((x_max - x_min) * padding, 1.0)
    y_pad = max((y_max - y_min) * padding, 1.0)
    return float(x_min - x_pad), float(x_max + x_pad), float(y_min - y_pad), float(y_max + y_pad)


def draw_panel_frame(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str, font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    draw.rectangle(box, outline="#8b98a5", width=2)
    draw.text((left + 12, top + 8), title, fill="#17324d", font=font)
    return left + 20, top + 52, right - 20, bottom - 24


def draw_scatter(draw: ImageDraw.ImageDraw, points: np.ndarray, color: str, radius: int = 2) -> None:
    for x, y in points:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def plot_case(
    output_path: Path,
    row: dict[str, str],
    aerial_result: dict,
    satellite_result: dict,
    aerial_query: np.ndarray,
    aerial_map: np.ndarray,
    satellite_query: np.ndarray,
    satellite_map: np.ndarray,
    pairs: list[tuple[int, int, float]],
    max_lines: int,
) -> dict[str, float | str | int]:
    a_idx = np.asarray([pair[0] for pair in pairs], dtype=np.int64)
    s_idx = np.asarray([pair[1] for pair in pairs], dtype=np.int64)
    delta = satellite_map[s_idx] - aerial_map[a_idx]
    raw_error = np.linalg.norm(delta, axis=1)
    shift = np.median(delta, axis=0)
    residual = np.linalg.norm(delta - shift, axis=1)
    agreement_3m = float(np.mean(raw_error <= 3.0))
    agreement_5m = float(np.mean(raw_error <= 5.0))
    shift_norm = float(np.linalg.norm(shift))
    residual_median = float(np.median(residual))
    pattern = candidate_pattern(shift_norm, residual_median, agreement_5m)

    image = Image.new("RGB", (1600, 1200), "white")
    draw = ImageDraw.Draw(image, "RGBA")
    title_font = load_font(25, bold=True)
    subtitle_font = load_font(18)
    panel_font = load_font(20, bold=True)
    small_font = load_font(16)
    title = f"{row['sample_id']} | {row['failure_group']} | satellite error={float(row['satellite_final_error_m']):.3f} m"
    subtitle = (
        f"pairs={len(pairs)} | Agree@3={agreement_3m:.2%} | Agree@5={agreement_5m:.2%} | "
        f"shift={shift_norm:.3f} m | residual median={residual_median:.3f} m"
    )
    draw.text((60, 28), title, fill="#102a43", font=title_font)
    draw.text((60, 66), subtitle, fill="#334e68", font=subtitle_font)
    draw.text((60, 96), f"Geometry-only candidate: {pattern}; semantic labels require RGB review", fill="#8a5a00", font=subtitle_font)

    boxes = [
        (50, 145, 785, 630),
        (815, 145, 1550, 630),
        (50, 660, 785, 1145),
        (815, 660, 1550, 1145),
    ]

    plot_box = draw_panel_frame(draw, boxes[0], "UAV query-coordinate coverage (RGB unavailable)", panel_font)
    query_bounds = (0.0, float(aerial_result["uav_input_width"]), 0.0, float(aerial_result["uav_input_height"]))
    aerial_q_plot = map_points(aerial_query[::3], plot_box, query_bounds)
    satellite_q_plot = map_points(satellite_query[::3], plot_box, query_bounds)
    draw_scatter(draw, aerial_q_plot, "#168aad88", radius=2)
    draw_scatter(draw, satellite_q_plot, "#d1495b88", radius=2)
    draw.text((plot_box[0], plot_box[3] - 20), "blue=aerial-run query pts; red=satellite-run query pts", fill="#52606d", font=small_font)

    plot_box = draw_panel_frame(draw, boxes[1], "Paired endpoints in map XY (no DSM Z)", panel_font)
    select = np.linspace(0, len(pairs) - 1, min(max_lines, len(pairs)), dtype=int)
    combined_map = np.vstack(
        (
            aerial_map[a_idx],
            satellite_map[s_idx],
            [[aerial_result["true_x"], aerial_result["true_y"]]],
            [[satellite_result["pred_x"], satellite_result["pred_y"]]],
        )
    )
    map_bounds_xy = robust_bounds(combined_map)
    aerial_mapped = map_points(aerial_map[a_idx], plot_box, map_bounds_xy)
    satellite_mapped = map_points(satellite_map[s_idx], plot_box, map_bounds_xy)
    for index in select:
        draw.line(
            (tuple(aerial_mapped[index]), tuple(satellite_mapped[index])),
            fill="#7b879466",
            width=1,
        )
    draw_scatter(draw, aerial_mapped[::2], "#168aadaa", radius=2)
    draw_scatter(draw, satellite_mapped[::2], "#d1495baa", radius=2)
    gt = map_points(np.asarray([[aerial_result["true_x"], aerial_result["true_y"]]], dtype=float), plot_box, map_bounds_xy)[0]
    pred = map_points(np.asarray([[satellite_result["pred_x"], satellite_result["pred_y"]]], dtype=float), plot_box, map_bounds_xy)[0]
    draw.ellipse((gt[0] - 7, gt[1] - 7, gt[0] + 7, gt[1] + 7), fill="#2a9d8f", outline="black")
    draw.line((pred[0] - 8, pred[1] - 8, pred[0] + 8, pred[1] + 8), fill="#9b2226", width=4)
    draw.line((pred[0] - 8, pred[1] + 8, pred[0] + 8, pred[1] - 8), fill="#9b2226", width=4)
    draw.text((plot_box[0], plot_box[3] - 20), "blue=aerial; red=satellite; green=GT; red X=satellite pose", fill="#52606d", font=small_font)

    plot_box = draw_panel_frame(draw, boxes[2], "Satellite - aerial endpoint displacement", panel_font)
    delta_bounds = robust_bounds(np.vstack((delta, shift.reshape(1, 2))))
    delta_mapped = map_points(delta[::2], plot_box, delta_bounds)
    draw_scatter(draw, delta_mapped, "#6c757d77", radius=2)
    shift_point = map_points(shift.reshape(1, 2), plot_box, delta_bounds)[0]
    draw.ellipse((shift_point[0] - 8, shift_point[1] - 8, shift_point[0] + 8, shift_point[1] + 8), fill="#e76f51", outline="black")
    draw.text((plot_box[0], plot_box[3] - 20), "orange=median coherent shift; axes are delta X/Y in meters", fill="#52606d", font=small_font)

    plot_box = draw_panel_frame(draw, boxes[3], "Raw vs shift-corrected disagreement histogram", panel_font)
    upper = float(max(np.quantile(raw_error, 0.98), np.quantile(residual, 0.98), 1.0))
    bins = np.linspace(0, upper, 28)
    raw_counts, _ = np.histogram(raw_error, bins=bins)
    residual_counts, _ = np.histogram(residual, bins=bins)
    max_count = max(int(raw_counts.max()), int(residual_counts.max()), 1)
    bar_width = (plot_box[2] - plot_box[0]) / len(raw_counts)
    for index, (raw_count, residual_count) in enumerate(zip(raw_counts, residual_counts)):
        x0 = plot_box[0] + index * bar_width
        x1 = x0 + bar_width * 0.45
        x2 = x0 + bar_width * 0.50
        x3 = x0 + bar_width * 0.95
        raw_height = (plot_box[3] - plot_box[1] - 28) * raw_count / max_count
        residual_height = (plot_box[3] - plot_box[1] - 28) * residual_count / max_count
        draw.rectangle((x0, plot_box[3] - 28 - raw_height, x1, plot_box[3] - 28), fill="#d1495baa")
        draw.rectangle((x2, plot_box[3] - 28 - residual_height, x3, plot_box[3] - 28), fill="#168aadaa")
    draw.text((plot_box[0], plot_box[3] - 20), f"red=raw; blue=shift-corrected; x range 0-{upper:.1f} m", fill="#52606d", font=small_font)

    image.save(output_path, format="PNG", optimize=True)

    return {
        "sample_id": row["sample_id"],
        "failure_group": row["failure_group"],
        "satellite_final_error_m": float(row["satellite_final_error_m"]),
        "num_mutual_query_pairs": len(pairs),
        "agreement_3m_recomputed": agreement_3m,
        "agreement_5m_recomputed": agreement_5m,
        "robust_shift_norm_m_recomputed": shift_norm,
        "shift_corrected_median_residual_m_recomputed": residual_median,
        "geometry_only_candidate_pattern": pattern,
        "appearance_domain_gap": "NEEDS_RGB",
        "scale_resolution_gap": "NEEDS_RGB",
        "repetitive_structure": "NEEDS_RGB",
        "visibility_occlusion": "NEEDS_RGB",
        "temporal_change": "NEEDS_RGB",
        "map_georegistration_confounder": "NEEDS_RGB_OR_LANDMARKS",
        "manual_primary_label": "UNREVIEWED",
        "manual_secondary_label": "UNREVIEWED",
        "reviewer_notes": "",
        "panel_path": str(output_path),
    }


def main() -> None:
    args = parse_args()
    rows = load_shortlist(args.shortlist, args.limit)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    panel_dir = args.output_dir / "panels"
    panel_dir.mkdir(exist_ok=True)
    aerial_archive = EvidenceArchive(args.aerial_archive)
    satellite_archive = EvidenceArchive(args.satellite_archive)
    audit_rows: list[dict] = []
    try:
        for row in rows:
            sample_id = row["sample_id"]
            aerial_result = aerial_archive.result(sample_id)
            satellite_result = satellite_archive.result(sample_id)
            validate_metadata(sample_id, aerial_result, satellite_result)
            aerial_query, aerial_map = finite_points(aerial_archive.arrays(sample_id))
            satellite_query, satellite_map = finite_points(satellite_archive.arrays(sample_id))
            pairs = mutual_pairs(aerial_query, satellite_query, args.query_threshold_px)
            if not pairs:
                raise ValueError(f"{sample_id}: no mutual query pairs")
            panel_path = panel_dir / f"{row['failure_group']}__{sample_id}.png"
            audit = plot_case(
                panel_path,
                row,
                aerial_result,
                satellite_result,
                aerial_query,
                aerial_map,
                satellite_query,
                satellite_map,
                pairs,
                args.max_lines,
            )
            for field in (
                "agreement_3m",
                "agreement_5m",
                "robust_shift_norm_m",
                "shift_corrected_median_residual_m",
            ):
                recomputed = float(audit[f"{field}_recomputed"])
                expected = float(row[field])
                if not np.isclose(recomputed, expected, rtol=0.0, atol=1e-6):
                    raise ValueError(
                        f"{sample_id}: {field} mismatch: shortlist={expected}, recomputed={recomputed}"
                    )
            audit_rows.append(audit)
    finally:
        aerial_archive.close()
        satellite_archive.close()

    output_csv = args.output_dir / "manual_failure_taxonomy.csv"
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_rows[0]))
        writer.writeheader()
        writer.writerows(audit_rows)

    counts: dict[str, int] = {}
    for row in audit_rows:
        pattern = str(row["geometry_only_candidate_pattern"])
        counts[pattern] = counts.get(pattern, 0) + 1
    manifest = {
        "research_question": "Which front-end failure mechanisms explain satellite-specific correspondence degradation?",
        "scope": "DSM-free geometry-only audit; RGB semantics and RoMa certainty unavailable",
        "num_cases": len(audit_rows),
        "failure_group_counts": {
            group: sum(row["failure_group"] == group for row in audit_rows)
            for group in sorted({str(row["failure_group"]) for row in audit_rows})
        },
        "geometry_only_candidate_pattern_counts": counts,
        "query_threshold_px": args.query_threshold_px,
        "aerial_archive": str(args.aerial_archive),
        "satellite_archive": str(args.satellite_archive),
        "shortlist": str(args.shortlist),
        "remaining_evidence_gap": [
            "original UAV RGB",
            "aerial reference RGB",
            "satellite reference RGB",
            "RoMa certainty/confidence",
            "manual cross-view landmark labels",
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
