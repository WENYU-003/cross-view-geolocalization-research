#!/usr/bin/env python3
"""Run frozen task-level oracle interventions for GAGeo late refinement.

The runner compares the released model's legitimate pair-stage-11 deep-
supervision predictions with its final predictions. It never feeds stage-11
features into final heads and never trains or modifies GAGeo. GT is used only
for this controlled diagnostic's cohort labels, coherent state selection, and
task metrics.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


PLAN = """Frozen Oracle / Controlled Intervention Test

Required inputs:
  --gageo-root       official GAGeo checkout
  --config           released baseline config with PR-MHA disabled
  --checkpoint       released full GAGeo checkpoint
  --dataset-json     official unseen_test.json
  --image-root       CMA-Loc image root
  --layerwise-csv    full 2,180-Ground Problem Scale layerwise_per_sample.csv
  --matched-manifest optional fixed Phase-3B matched-control manifest

Interventions from one frozen forward:
  A stage11_early_exit: legitimate intermediate_preds[11] task state
  B coherent_oracle: choose the complete stage-11 or final state maximizing
    0.5 * detection_IoU + 0.5 * mask_IoU (no head-wise cherry-picking)
  C d8_selective / rank_worsened_selective: use stage 11 only for the
    corresponding oracle diagnostic cohort; all other samples reuse final
    predictions exactly.

Use --smoke-samples 8 (or 16) for a deterministic mixture containing D8,
rank-worsened non-D8, and non-destructive Ground samples. Omit it for the
formal all-2,180 Ground run.
"""


STATE_NAMES = (
    "baseline_final",
    "stage11_early_exit",
    "coherent_oracle",
    "d8_selective",
    "rank_worsened_selective",
)
METRIC_NAMES = (
    "det_iou",
    "mask_iou",
    "pos_err_px",
    "rotation_error_deg",
    "severe",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--gageo-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--dataset-json", type=Path)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--layerwise-csv", type=Path)
    parser.add_argument("--matched-manifest", type=Path, default=None)
    parser.add_argument("--view-subset", choices=("ground_to_satellite",), default="ground_to_satellite")
    parser.add_argument("--prompt-type", choices=("point",), default="point")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--smoke-samples", type=int, choices=(0, 8, 16), default=0)
    parser.add_argument("--smoke-seed", type=int, default=42)
    parser.add_argument("--baseline-tolerance", type=float, default=1e-5)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    return parser.parse_args()


def require_paths(args: argparse.Namespace) -> None:
    required = (
        "gageo_root", "config", "checkpoint", "dataset_json", "image_root",
        "layerwise_csv", "output_dir",
    )
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        raise SystemExit("Missing arguments: " + ", ".join("--" + x.replace("_", "-") for x in missing))
    for name in required[:-1]:
        path = getattr(args, name)
        if not path.exists():
            raise FileNotFoundError(f"{name} does not exist: {path}")
    if args.matched_manifest is not None and not args.matched_manifest.is_file():
        raise FileNotFoundError(args.matched_manifest)
    if args.baseline_tolerance < 0 or args.bootstrap_replicates <= 0:
        raise ValueError("baseline-tolerance must be non-negative and bootstrap-replicates positive")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_ground(record: dict[str, Any]) -> bool:
    return "drone" not in str(record.get("mono_filename", "")).lower()


def load_dataset(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or len(payload) != 4197:
        raise ValueError(f"Expected official 4,197-record unseen_test list: {path}")
    if sum(isinstance(row, dict) and is_ground(row) for row in payload) != 2180:
        raise ValueError("Official unseen_test Ground count is not 2,180")
    return payload


def load_layerwise(path: Path) -> dict[int, dict[str, Any]]:
    required = {
        "index", "layer", "hit8", "gt_rank", "runtime_det_iou", "runtime_mask_iou",
    }
    by_index: dict[int, dict[str, dict[str, str]]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Layerwise CSV missing columns: {sorted(missing)}")
        for row in reader:
            index = int(row["index"])
            by_index[index][row["layer"]] = row

    result: dict[int, dict[str, Any]] = {}
    for index, layers in by_index.items():
        stage11 = layers.get("pi3_stage_11_spatial")
        final = layers.get("pi3_final_spatial")
        if stage11 is None or final is None:
            raise ValueError(f"Index {index} lacks stage11/final spatial records")
        det_values = {float(row["runtime_det_iou"]) for row in layers.values()}
        mask_values = {float(row["runtime_mask_iou"]) for row in layers.values()}
        if len(det_values) != 1 or len(mask_values) != 1:
            raise ValueError(f"Runtime baseline metric drift across layers at index {index}")
        hit11, hit_final = int(stage11["hit8"]), int(final["hit8"])
        rank11, rank_final = int(stage11["gt_rank"]), int(final["gt_rank"])
        result[index] = {
            "d8": hit11 == 1 and hit_final == 0,
            "rank_worsened": rank_final > rank11,
            "stage11_hit8": hit11,
            "final_hit8": hit_final,
            "stage11_gt_rank": rank11,
            "final_gt_rank": rank_final,
            "saved_final_det_iou": next(iter(det_values)),
            "saved_final_mask_iou": next(iter(mask_values)),
        }
    if len(result) != 2180:
        raise ValueError(f"Expected 2,180 Ground indices in layerwise CSV, got {len(result)}")
    if sum(row["d8"] for row in result.values()) != 116:
        raise ValueError("Expected exactly 116 D8 samples")
    if sum(row["rank_worsened"] for row in result.values()) != 335:
        raise ValueError("Expected exactly 335 rank-worsened samples")
    return result


def load_matched(path: Path | None, dataset: list[dict[str, Any]]) -> dict[int, str]:
    if path is None:
        return {}
    labels: dict[int, str] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"index", "cohort", "mono_filename", "sat_filename", "split", "prompt_type"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Matched manifest missing columns: {sorted(missing)}")
        for row in reader:
            if row["split"] != "unseen_test" or row["prompt_type"] != "point":
                raise ValueError("Matched manifest protocol mismatch")
            if row["cohort"] not in {"ground_severe", "ground_success"}:
                continue
            index = int(row["index"])
            record = dataset[index]
            sat = record.get("sat_filename") or record.get("sate_filename")
            if row["mono_filename"] != record.get("mono_filename") or row["sat_filename"] != sat:
                raise ValueError(f"Matched manifest provenance mismatch at index {index}")
            labels[index] = row["cohort"]
    return labels


def stable_order(indices: list[int], dataset: list[dict[str, Any]], seed: int, tag: str) -> list[int]:
    def key(index: int) -> tuple[str, int]:
        name = str(dataset[index].get("mono_filename", ""))
        value = hashlib.sha256(f"{seed}|{tag}|{index}|{name}".encode()).hexdigest()
        return value, index
    return sorted(indices, key=key)


def select_indices(
    layerwise: dict[int, dict[str, Any]],
    dataset: list[dict[str, Any]],
    smoke_samples: int,
    seed: int,
) -> tuple[list[int], str]:
    all_indices = sorted(layerwise)
    if smoke_samples == 0:
        return all_indices, "full_ground_2180"
    d8 = stable_order([i for i in all_indices if layerwise[i]["d8"]], dataset, seed, "d8")
    rank_only = stable_order(
        [i for i in all_indices if layerwise[i]["rank_worsened"] and not layerwise[i]["d8"]],
        dataset,
        seed,
        "rank_worsened_non_d8",
    )
    stable = stable_order(
        [i for i in all_indices if not layerwise[i]["rank_worsened"]], dataset, seed, "non_destructive"
    )
    d8_count = max(1, smoke_samples // 4)
    rank_count = max(1, smoke_samples // 4)
    selected = d8[:d8_count] + rank_only[:rank_count] + stable[: smoke_samples - d8_count - rank_count]
    if len(selected) != smoke_samples or not any(layerwise[i]["d8"] for i in selected):
        raise RuntimeError("Unable to create deterministic mixed smoke cohort")
    return sorted(selected), f"smoke_mixed_{smoke_samples}"


def finite_tensor(value: Any, torch_module) -> bool:
    return value is not None and torch_module.is_tensor(value) and bool(torch_module.isfinite(value).all())


def validate_prediction_state(state: dict[str, Any], batch_size: int, image_size: int, torch_module) -> dict[str, Any]:
    required = ("pred_boxes", "bbox_scores", "mask_pred", "position", "rotation_matrix")
    missing = [name for name in required if name not in state]
    if missing:
        raise RuntimeError(f"Prediction state missing keys: {missing}")
    if state["pred_boxes"].ndim != 3 or state["pred_boxes"].shape[0] != batch_size or state["pred_boxes"].shape[-1] != 4:
        raise RuntimeError(f"Invalid pred_boxes shape: {tuple(state['pred_boxes'].shape)}")
    queries = state["pred_boxes"].shape[1]
    expected = {
        "bbox_scores": (batch_size, queries),
        "mask_pred": (batch_size, queries, image_size, image_size),
        "position": (batch_size, 2),
        "rotation_matrix": (batch_size, 3, 3),
    }
    for name, shape in expected.items():
        if tuple(state[name].shape) != shape:
            raise RuntimeError(f"Invalid {name} shape: expected {shape}, got {tuple(state[name].shape)}")
    if not all(finite_tensor(state[name], torch_module) for name in required):
        raise RuntimeError("NaN/Inf or non-tensor prediction state")
    return {name: list(state[name].shape) for name in required}


def state_metrics(
    state: dict[str, Any],
    batch: dict[str, Any],
    image_size: int,
    helpers: dict[str, Any],
    torch_module,
    np_module,
) -> dict[str, float | int | None]:
    boxes = state["pred_boxes"]
    masks = state["mask_pred"]
    if boxes.shape[1] > 1:
        query = int(state["bbox_scores"][0].argmax().item())
    else:
        query = 0
    pred_box = helpers["sanitize_bbox_xyxy"](
        helpers["bbox_cxcywh_norm_to_xyxy_abs"](boxes[0, query], image_size), image_size
    )
    gt_box = helpers["clip_bbox_xyxy"](batch["gt_bbox_xyxy"][0].numpy().astype(np_module.float32), image_size)
    det_iou = helpers["bbox_iou_np"](pred_box, gt_box)
    pred_mask = (masks[0, query].detach().cpu().numpy() > 0.5).astype(np_module.uint8)
    gt_mask = (batch["gt_mask"][0].numpy() > 0).astype(np_module.uint8)
    mask_iou = helpers["SegMetrics"].iou(pred_mask, gt_mask)

    rotation_error = None
    if bool(batch["has_rotation"][0]):
        pred_rotation = state["rotation_matrix"][0].detach().cpu().numpy().astype(np_module.float32)
        gt_rotation = batch["gt_rotation_matrix"][0].numpy().astype(np_module.float32)
        rotation_error = helpers["geodesic_rotation_error_deg_np"](pred_rotation, gt_rotation)
    position_error = None
    if bool(batch["has_pose"][0]):
        pred_position = state["position"][0].detach().cpu().numpy().astype(np_module.float32)
        gt_position = batch["gt_position"][0].numpy().astype(np_module.float32)
        position_error = float(np_module.linalg.norm(pred_position - gt_position) * image_size)
    return {
        "det_iou": float(det_iou),
        "mask_iou": float(mask_iou),
        "pos_err_px": position_error,
        "rotation_error_deg": rotation_error,
        "severe": int(det_iou == 0.0 and mask_iou == 0.0),
    }


def same_metrics(left: dict[str, Any], right: dict[str, Any], tolerance: float) -> bool:
    for name in METRIC_NAMES:
        a, b = left[name], right[name]
        if a is None or b is None:
            if a is not b:
                return False
        elif abs(float(a) - float(b)) > tolerance:
            return False
    return True


def aggregate(rows: list[dict[str, Any]], state_name: str, np_module) -> dict[str, Any]:
    if not rows:
        return {"count": 0}
    det = np_module.asarray([row[f"{state_name}_det_iou"] for row in rows], dtype=np_module.float64)
    mask = np_module.asarray([row[f"{state_name}_mask_iou"] for row in rows], dtype=np_module.float64)
    severe = np_module.asarray([row[f"{state_name}_severe"] for row in rows], dtype=np_module.float64)
    result = {
        "count": len(rows),
        "det_miou": float(det.mean()),
        "mask_miou": float(mask.mean()),
        "det_acc50": float((det >= 0.50).mean()),
        "det_acc75": float((det >= 0.75).mean()),
        "severe_count": int(severe.sum()),
        "severe_rate": float(severe.mean()),
    }
    for metric in ("pos_err_px", "rotation_error_deg"):
        values = [row[f"{state_name}_{metric}"] for row in rows if row[f"{state_name}_{metric}"] is not None]
        result[f"mean_{metric}"] = float(np_module.mean(values)) if values else None
    baseline_severe = [row for row in rows if row["baseline_final_severe"] == 1]
    result["baseline_severe_count"] = len(baseline_severe)
    result["severe_recovery_count"] = sum(row[f"{state_name}_severe"] == 0 for row in baseline_severe)
    result["severe_recovery_rate"] = (
        result["severe_recovery_count"] / len(baseline_severe) if baseline_severe else None
    )
    return result


def paired_bootstrap(
    rows: list[dict[str, Any]],
    state_name: str,
    metric: str,
    replicates: int,
    seed: int,
    np_module,
) -> dict[str, float] | None:
    baseline_values, intervention_values = [], []
    for row in rows:
        baseline = row[f"baseline_final_{metric}"]
        intervention = row[f"{state_name}_{metric}"]
        if baseline is not None and intervention is not None:
            baseline_values.append(float(baseline))
            intervention_values.append(float(intervention))
    if not baseline_values:
        return None
    delta = np_module.asarray(intervention_values) - np_module.asarray(baseline_values)
    rng = np_module.random.default_rng(seed)
    estimates = np_module.empty(replicates, dtype=np_module.float64)
    for replicate in range(replicates):
        indices = rng.integers(0, len(delta), size=len(delta))
        estimates[replicate] = delta[indices].mean()
    low, high = np_module.quantile(estimates, [0.025, 0.975])
    return {"mean_delta": float(delta.mean()), "ci95_low": float(low), "ci95_high": float(high)}


def main() -> int:
    args = parse_args()
    if args.print_plan:
        print(PLAN)
        return 0
    require_paths(args)
    dataset_records = load_dataset(args.dataset_json.resolve())
    layerwise = load_layerwise(args.layerwise_csv.resolve())
    if any(not is_ground(dataset_records[index]) for index in layerwise):
        raise RuntimeError("Layerwise CSV includes a non-Ground sample")
    matched = load_matched(args.matched_manifest, dataset_records)
    selected_indices, selection_mode = select_indices(
        layerwise, dataset_records, args.smoke_samples, args.smoke_seed
    )

    import numpy as np
    import torch

    sys.path.insert(0, str(args.gageo_root.resolve()))
    from evaluate_cmaloc import (  # type: ignore
        EvalDataset,
        SegMetrics,
        bbox_cxcywh_norm_to_xyxy_abs,
        bbox_iou_np,
        build_model_from_cfg,
        clip_bbox_xyxy,
        collate_eval,
        extract_state_dict,
        geodesic_rotation_error_deg_np,
        load_cfg_with_env,
        remap_legacy_mask_head_keys,
        resolve_checkpoint,
        sanitize_bbox_xyxy,
    )

    helpers = {
        "SegMetrics": SegMetrics,
        "bbox_cxcywh_norm_to_xyxy_abs": bbox_cxcywh_norm_to_xyxy_abs,
        "bbox_iou_np": bbox_iou_np,
        "clip_bbox_xyxy": clip_bbox_xyxy,
        "geodesic_rotation_error_deg_np": geodesic_rotation_error_deg_np,
        "sanitize_bbox_xyxy": sanitize_bbox_xyxy,
    }
    device = torch.device(args.device)
    cfg = load_cfg_with_env(str(args.config.resolve()))
    if bool(cfg.get("model", {}).get("use_late_spatial_pr_mha", False)):
        raise RuntimeError("Oracle test requires released baseline with PR-MHA disabled")
    model = build_model_from_cfg(cfg, device)
    checkpoint_file = resolve_checkpoint(args.checkpoint.resolve())
    state = torch.load(str(checkpoint_file), map_location="cpu")
    state_dict = extract_state_dict(state)
    state_dict, _ = remap_legacy_mask_head_keys(state_dict)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing or unexpected:
        raise RuntimeError(f"Checkpoint mismatch: missing={missing[:20]} unexpected={unexpected[:20]}")
    model.eval()
    for parameter in model.parameters():
        parameter.requires_grad_(False)
    if sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad) != 0:
        raise RuntimeError("Baseline is not fully frozen")

    image_size = int(cfg["data"].get("img_size", 518))
    official_dataset = EvalDataset(dataset_records, image_root=str(args.image_root.resolve()), img_size=image_size)
    rows: list[dict[str, Any]] = []
    shape_audit = None
    with torch.inference_mode():
        for source_index in selected_indices:
            record = dataset_records[source_index]
            batch = collate_eval([official_dataset[source_index]])
            if int(batch["index"][0]) != source_index:
                raise RuntimeError(f"Dataset index mismatch at {source_index}")
            front = batch["front_view"].to(device)
            satellite = batch["sat_view"].to(device)
            mono_point = batch["mono_point"].to(device)
            points = (mono_point.unsqueeze(1), torch.ones(1, 1, device=device))
            outputs = model(front_view=front, satellite_view=satellite, points=points)
            intermediate = outputs.get("intermediate_preds", {})
            stage11 = intermediate.get(11, intermediate.get("11"))
            if not isinstance(stage11, dict):
                raise RuntimeError("Released model did not expose intermediate_preds[11]")
            final = {name: outputs[name] for name in ("pred_boxes", "bbox_scores", "mask_pred", "position", "rotation_matrix")}
            stage_shapes = validate_prediction_state(stage11, 1, image_size, torch)
            final_shapes = validate_prediction_state(final, 1, image_size, torch)
            if shape_audit is None:
                shape_audit = {"stage11": stage_shapes, "final": final_shapes}

            stage11_metrics = state_metrics(stage11, batch, image_size, helpers, torch, np)
            final_metrics = state_metrics(final, batch, image_size, helpers, torch, np)
            labels = layerwise[source_index]
            if abs(final_metrics["det_iou"] - labels["saved_final_det_iou"]) > args.baseline_tolerance:
                raise RuntimeError(f"Final detection IoU provenance mismatch at index {source_index}")
            if abs(final_metrics["mask_iou"] - labels["saved_final_mask_iou"]) > args.baseline_tolerance:
                raise RuntimeError(f"Final mask IoU provenance mismatch at index {source_index}")

            joint11 = 0.5 * stage11_metrics["det_iou"] + 0.5 * stage11_metrics["mask_iou"]
            joint_final = 0.5 * final_metrics["det_iou"] + 0.5 * final_metrics["mask_iou"]
            coherent_name = "stage11" if joint11 > joint_final else "final"
            coherent = stage11_metrics if coherent_name == "stage11" else final_metrics
            d8_name = "stage11" if labels["d8"] else "final"
            d8_selective = stage11_metrics if labels["d8"] else final_metrics
            rank_name = "stage11" if labels["rank_worsened"] else "final"
            rank_selective = stage11_metrics if labels["rank_worsened"] else final_metrics
            if d8_name == "final" and not same_metrics(d8_selective, final_metrics, 0.0):
                raise RuntimeError(f"D8-selective changed an unintervened sample at {source_index}")
            if rank_name == "final" and not same_metrics(rank_selective, final_metrics, 0.0):
                raise RuntimeError(f"Rank-selective changed an unintervened sample at {source_index}")

            states = {
                "baseline_final": final_metrics,
                "stage11_early_exit": stage11_metrics,
                "coherent_oracle": coherent,
                "d8_selective": d8_selective,
                "rank_worsened_selective": rank_selective,
            }
            row: dict[str, Any] = {
                "index": source_index,
                "city": record.get("city", ""),
                "mono_filename": record.get("mono_filename", ""),
                "sat_filename": record.get("sat_filename") or record.get("sate_filename", ""),
                "d8": int(labels["d8"]),
                "rank_worsened": int(labels["rank_worsened"]),
                "stage11_hit8": labels["stage11_hit8"],
                "final_hit8": labels["final_hit8"],
                "stage11_gt_rank": labels["stage11_gt_rank"],
                "final_gt_rank": labels["final_gt_rank"],
                "matched_cohort": matched.get(source_index, ""),
                "coherent_selected_state": coherent_name,
                "d8_selective_state": d8_name,
                "rank_worsened_selective_state": rank_name,
            }
            for state_name, metrics in states.items():
                for metric_name, value in metrics.items():
                    row[f"{state_name}_{metric_name}"] = value
            rows.append(row)

    if not rows or shape_audit is None:
        raise RuntimeError("No samples evaluated")
    if args.smoke_samples == 0 and len(rows) != 2180:
        raise RuntimeError(f"Formal protocol requires 2,180 rows, got {len(rows)}")

    groups = {
        "evaluated": rows,
        "d8": [row for row in rows if row["d8"] == 1],
        "rank_worsened": [row for row in rows if row["rank_worsened"] == 1],
        "matched_ground_severe": [row for row in rows if row["matched_cohort"] == "ground_severe"],
        "matched_ground_success": [row for row in rows if row["matched_cohort"] == "ground_success"],
    }
    summary_groups: dict[str, Any] = {}
    for group_name, group_rows in groups.items():
        summary_groups[group_name] = {}
        for state_name in STATE_NAMES:
            state_summary = aggregate(group_rows, state_name, np)
            if state_name != "baseline_final" and group_rows:
                state_summary["paired_delta_ci95"] = {
                    metric: paired_bootstrap(
                        group_rows,
                        state_name,
                        metric,
                        args.bootstrap_replicates,
                        args.smoke_seed + offset,
                        np,
                    )
                    for offset, metric in enumerate(("det_iou", "mask_iou", "severe"))
                }
            summary_groups[group_name][state_name] = state_summary

    args.output_dir.mkdir(parents=True, exist_ok=True)
    per_sample_path = args.output_dir / "oracle_intervention_per_sample.csv"
    with per_sample_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "status": "oracle_controlled_intervention_no_training",
        "selection_mode": selection_mode,
        "sample_count": len(rows),
        "d8_count": sum(row["d8"] for row in rows),
        "rank_worsened_count": sum(row["rank_worsened"] for row in rows),
        "prompt_type": args.prompt_type,
        "view_subset": args.view_subset,
        "pr_mha_enabled": False,
        "trainable_parameter_count": 0,
        "checkpoint": str(checkpoint_file),
        "checkpoint_sha256": sha256_file(checkpoint_file),
        "config": str(args.config.resolve()),
        "config_sha256": sha256_file(args.config.resolve()),
        "dataset_json": str(args.dataset_json.resolve()),
        "dataset_json_sha256": sha256_file(args.dataset_json.resolve()),
        "layerwise_csv": str(args.layerwise_csv.resolve()),
        "layerwise_csv_sha256": sha256_file(args.layerwise_csv.resolve()),
        "matched_manifest": str(args.matched_manifest.resolve()) if args.matched_manifest else None,
        "matched_manifest_sha256": sha256_file(args.matched_manifest.resolve()) if args.matched_manifest else None,
        "stage11_source": "released intermediate_preds[11] deep-supervision task outputs",
        "illegal_cross_head_splice_used": False,
        "coherent_oracle_rule": "choose one complete state by max 0.5*det_iou + 0.5*mask_iou; ties choose final",
        "unintervened_identity_check": "exact metric-object reuse and zero-tolerance equality",
        "baseline_tolerance": args.baseline_tolerance,
        "shape_audit": shape_audit,
        "all_finite": True,
        "groups": summary_groups,
        "per_sample_csv": str(per_sample_path),
    }
    summary_path = args.output_dir / "oracle_intervention_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Evaluated {len(rows)} Ground samples ({selection_mode})")
    print(f"D8={summary['d8_count']}, rank_worsened={summary['rank_worsened_count']}")
    print(f"Wrote {per_sample_path}")
    print(f"Wrote {summary_path}")
    print("ORACLE_INTERVENTION_SMOKE: PASS" if args.smoke_samples else "ORACLE_INTERVENTION_FULL: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
