#!/usr/bin/env python3
"""Export CPU-only RGB panels for the fixed Scene_16 24-query audit.

This script does not rerun retrieval, RoMa, DSM lookup, or PnP. It combines the
original UAV image stored in each dataset NPZ with north-up aerial/satellite
map windows and the already-saved correspondence endpoints. The map windows
cover the same metric extent as the recorded reference patch, but they are a
diagnostic geographic view rather than the pose-prior-rotated matcher input.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from analyze_cross_reference_2d import mutual_pairs


Image.MAX_IMAGE_PIXELS = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--aerial-scene-dir", type=Path, required=True)
    parser.add_argument("--satellite-scene-dir", type=Path, required=True)
    parser.add_argument("--shortlist", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--query-threshold-px", type=float, default=5.0)
    parser.add_argument("--agreement-threshold-m", type=float, default=5.0)
    parser.add_argument("--display-pairs", type=int, default=260)
    parser.add_argument("--limit", type=int, default=None)
    return parser.parse_args()


def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def load_rows(path: Path, limit: int | None) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows if limit is None else rows[:limit]


def load_run_sample(scene_dir: Path, sample_id: str) -> tuple[dict, dict[str, np.ndarray]]:
    sample_dir = scene_dir / sample_id
    result = json.loads((sample_dir / "result.json").read_text(encoding="utf-8"))
    with np.load(sample_dir / "matches_and_pnp_inputs.npz") as artifact:
        required = ("uav_pts_original", "local_x", "local_y")
        missing = [key for key in required if key not in artifact.files]
        if missing:
            raise ValueError(f"{sample_id}: missing run fields {missing}")
        arrays = {key: np.asarray(artifact[key]).copy() for key in required}
    return result, arrays


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


def load_uav(dataset_root: Path, scene_name: str, sample_id: str) -> Image.Image:
    path = dataset_root / scene_name / f"{sample_id}.npz"
    with np.load(path, allow_pickle=False) as sample:
        if "image" not in sample.files:
            raise ValueError(f"{path}: missing image field")
        image = np.asarray(sample["image"])
    if image.ndim != 3 or image.shape[2] not in (3, 4) or image.dtype != np.uint8:
        raise ValueError(f"{path}: unexpected image shape/dtype {image.shape}/{image.dtype}")
    return Image.fromarray(image[..., :3], mode="RGB")


def validate_control(sample_id: str, aerial: dict, satellite: dict) -> None:
    for key in (
        "sample_id",
        "scene_name",
        "matching_method",
        "pose_priori",
        "match_keypoints",
        "resize_ratio",
        "uav_input_width",
        "uav_input_height",
    ):
        if aerial.get(key) != satellite.get(key):
            raise ValueError(f"{sample_id}: controlled field {key} differs")
    if aerial.get("reference_mode") != "aerial" or satellite.get("reference_mode") != "satellite":
        raise ValueError(f"{sample_id}: reference-mode identity mismatch")


def metric_crop(image: Image.Image, result: dict) -> tuple[Image.Image, tuple[float, float, float, float]]:
    width_px = float(result["target_patch_size_m"]) / float(result["map_resolution_x_m"])
    height_px = float(result["target_patch_size_m"]) / float(result["map_resolution_y_m"])
    center_x = float(result["crop_center_col"])
    center_y = float(result["crop_center_row"])
    bounds = (
        center_x - width_px / 2.0,
        center_y - height_px / 2.0,
        center_x + width_px / 2.0,
        center_y + height_px / 2.0,
    )
    integer_bounds = tuple(int(round(value)) for value in bounds)
    return image.crop(integer_bounds), bounds


def select_pair_indices(num_pairs: int, maximum: int) -> np.ndarray:
    if num_pairs <= maximum:
        return np.arange(num_pairs, dtype=np.int64)
    return np.linspace(0, num_pairs - 1, maximum, dtype=np.int64)


def resize_for_panel(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[Image.Image, float, float, int, int]:
    left, top, right, bottom = box
    available_w = right - left
    available_h = bottom - top
    scale = min(available_w / image.width, available_h / image.height)
    new_w = max(1, int(round(image.width * scale)))
    new_h = max(1, int(round(image.height * scale)))
    resized = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
    offset_x = left + (available_w - new_w) // 2
    offset_y = top + (available_h - new_h) // 2
    return resized, new_w / image.width, new_h / image.height, offset_x, offset_y


def draw_points(
    draw: ImageDraw.ImageDraw,
    points: np.ndarray,
    agreement: np.ndarray,
    scale_x: float,
    scale_y: float,
    offset_x: int,
    offset_y: int,
) -> None:
    for (x, y), is_agree in zip(points, agreement):
        px = offset_x + x * scale_x
        py = offset_y + y * scale_y
        color = "#26a269" if bool(is_agree) else "#d1495b"
        draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=color, outline="white", width=1)


def make_panel(
    output_path: Path,
    shortlist_row: dict[str, str],
    uav: Image.Image,
    aerial_map: Image.Image,
    satellite_map: Image.Image,
    aerial_result: dict,
    satellite_result: dict,
    aerial_query: np.ndarray,
    aerial_xy: np.ndarray,
    satellite_query: np.ndarray,
    satellite_xy: np.ndarray,
    pairs: list[tuple[int, int, float]],
    agreement_threshold_m: float,
    display_pairs: int,
) -> dict[str, float | int | str]:
    a_idx = np.asarray([pair[0] for pair in pairs], dtype=np.int64)
    s_idx = np.asarray([pair[1] for pair in pairs], dtype=np.int64)
    disagreement = np.linalg.norm(satellite_xy[s_idx] - aerial_xy[a_idx], axis=1)
    agreement = disagreement <= agreement_threshold_m
    chosen = select_pair_indices(len(pairs), display_pairs)

    aerial_crop, aerial_bounds = metric_crop(aerial_map, aerial_result)
    satellite_crop, satellite_bounds = metric_crop(satellite_map, satellite_result)
    aerial_global_px = np.column_stack(
        (
            aerial_xy[a_idx, 0] / float(aerial_result["map_resolution_x_m"]),
            aerial_xy[a_idx, 1] / float(aerial_result["map_resolution_y_m"]),
        )
    )
    satellite_global_px = np.column_stack(
        (
            satellite_xy[s_idx, 0] / float(satellite_result["map_resolution_x_m"]),
            satellite_xy[s_idx, 1] / float(satellite_result["map_resolution_y_m"]),
        )
    )
    aerial_crop_px = aerial_global_px - np.asarray(aerial_bounds[:2])
    satellite_crop_px = satellite_global_px - np.asarray(satellite_bounds[:2])

    canvas = Image.new("RGB", (1800, 1040), "white")
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (45, 25),
        f"{shortlist_row['sample_id']} | {shortlist_row['failure_group']} | satellite error={float(shortlist_row['satellite_final_error_m']):.3f} m",
        fill="#102a43",
        font=font(28, bold=True),
    )
    draw.text(
        (45, 68),
        f"Mutual query pairs={len(pairs)} | map Agreement@{agreement_threshold_m:g}m={float(np.mean(agreement)):.2%} | green=agree, red=disagree",
        fill="#334e68",
        font=font(19),
    )
    draw.text(
        (45, 100),
        "Reference panels are north-up equal-metric geographic windows, not pose-prior-rotated matcher tensors.",
        fill="#8a5a00",
        font=font(18),
    )

    panel_boxes = {
        "uav": (35, 180, 585, 910),
        "aerial": (625, 180, 1175, 910),
        "satellite": (1215, 180, 1765, 910),
    }
    for label, box in panel_boxes.items():
        draw.rectangle(box, outline="#7b8794", width=2)
        draw.text((box[0] + 12, box[1] - 42), label.upper(), fill="#17324d", font=font(22, bold=True))

    uav_view, sx, sy, ox, oy = resize_for_panel(uav, panel_boxes["uav"])
    canvas.paste(uav_view, (ox, oy))
    draw_points(draw, satellite_query[s_idx][chosen], agreement[chosen], sx, sy, ox, oy)

    aerial_view, sx, sy, ox, oy = resize_for_panel(aerial_crop, panel_boxes["aerial"])
    canvas.paste(aerial_view, (ox, oy))
    draw_points(draw, aerial_crop_px[chosen], agreement[chosen], sx, sy, ox, oy)

    satellite_view, sx, sy, ox, oy = resize_for_panel(satellite_crop, panel_boxes["satellite"])
    canvas.paste(satellite_view, (ox, oy))
    draw_points(draw, satellite_crop_px[chosen], agreement[chosen], sx, sy, ox, oy)

    draw.text(
        (45, 950),
        "Manual labels: appearance/domain | scale/resolution | repetition | visibility/occlusion | temporal change | georegistration",
        fill="#52606d",
        font=font(18),
    )
    canvas.save(output_path, "PNG", optimize=True)
    return {
        "sample_id": shortlist_row["sample_id"],
        "failure_group": shortlist_row["failure_group"],
        "satellite_final_error_m": float(shortlist_row["satellite_final_error_m"]),
        "num_mutual_query_pairs": len(pairs),
        f"agreement_{agreement_threshold_m:g}m": float(np.mean(agreement)),
        "appearance_domain_gap": "UNREVIEWED",
        "scale_resolution_gap": "UNREVIEWED",
        "repetitive_structure": "UNREVIEWED",
        "visibility_occlusion": "UNREVIEWED",
        "temporal_change": "UNREVIEWED",
        "map_georegistration_confounder": "UNREVIEWED",
        "primary_failure_label": "UNREVIEWED",
        "secondary_failure_label": "UNREVIEWED",
        "reviewer_notes": "",
        "panel_path": str(output_path),
    }


def main() -> None:
    args = parse_args()
    rows = load_rows(args.shortlist, args.limit)
    if not rows:
        raise ValueError("shortlist is empty")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    panel_dir = args.output_dir / "rgb_panels"
    panel_dir.mkdir(exist_ok=True)

    scene_name = "Scene_16"
    aerial_map_path = args.dataset_root / scene_name / "aerial_map.png"
    satellite_map_path = args.dataset_root / scene_name / "satellite_map.png"
    aerial_map = Image.open(aerial_map_path).convert("RGB")
    satellite_map = Image.open(satellite_map_path).convert("RGB")
    review_rows: list[dict] = []

    for row in rows:
        sample_id = row["sample_id"]
        aerial_result, aerial_arrays = load_run_sample(args.aerial_scene_dir, sample_id)
        satellite_result, satellite_arrays = load_run_sample(args.satellite_scene_dir, sample_id)
        validate_control(sample_id, aerial_result, satellite_result)
        uav = load_uav(args.dataset_root, scene_name, sample_id)
        aerial_query, aerial_xy = finite_points(aerial_arrays)
        satellite_query, satellite_xy = finite_points(satellite_arrays)
        pairs = mutual_pairs(aerial_query, satellite_query, args.query_threshold_px)
        if not pairs:
            raise ValueError(f"{sample_id}: no mutual query pairs")
        output_path = panel_dir / f"{row['failure_group']}__{sample_id}.png"
        review_rows.append(
            make_panel(
                output_path,
                row,
                uav,
                aerial_map,
                satellite_map,
                aerial_result,
                satellite_result,
                aerial_query,
                aerial_xy,
                satellite_query,
                satellite_xy,
                pairs,
                args.agreement_threshold_m,
                args.display_pairs,
            )
        )

    review_path = args.output_dir / "rgb_manual_review.csv"
    with review_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(review_rows[0]))
        writer.writeheader()
        writer.writerows(review_rows)

    manifest = {
        "num_cases": len(review_rows),
        "visualization_type": "north_up_equal_metric_geographic_window_not_exact_matcher_input",
        "uses_gpu": False,
        "reruns_retrieval_or_matching": False,
        "uses_dsm_or_pnp_labels": False,
        "aerial_map": str(aerial_map_path),
        "satellite_map": str(satellite_map_path),
        "review_csv": str(review_path),
    }
    (args.output_dir / "rgb_audit_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
