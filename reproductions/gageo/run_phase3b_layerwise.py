#!/usr/bin/env python3
"""Run frozen-checkpoint GAGeo layer-wise correspondence diagnosis.

Run this script in the released GAGeo environment. It imports the official
evaluator/model, registers read-only forward hooks, and never trains or changes
the baseline. The oracle mono GT mask is used only to measure whether target
information is present at a layer; it is not supplied as the Point Prompt.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


PLAN = """Required inputs:
  --gageo-root       official GAGeo checkout
  --config           exact released evaluation config
  --checkpoint       released GAGeo checkpoint
  --image-root       CMA-Loc image root containing <city>/mono and <city>/crop_sate
  --manifest         phase3b/matched_control_manifest.csv

Dataset metadata is loaded exactly as official evaluate_cmaloc.py does: from
$JSON_ROOT/unseen_test.json, defaulting to <gageo-root>/data/json/unseen_test.json.
Use --dataset-json only to override that path with the real per-sample split
file. Aggregate outputs such as outputs/unseen_test_point.json are rejected.

Actual Pi3 checkpoints are read from model.backbone.supervision_layers. For the
released large model they are expected to be pair-stages 4, 11, and 17. Output
contains DINOv2, every available supervised Pi3 stage, final spatial features,
and final object-task token correspondence. No training is performed.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--gageo-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument(
        "--dataset-json",
        type=Path,
        default=None,
        help="Optional override for the real per-sample unseen_test.json; never pass aggregate metrics JSON.",
    )
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("phase3b_layerwise"))
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-per-cohort", type=int, default=0, help="0 means all manifest rows")
    parser.add_argument("--temperature", type=float, default=0.07)
    return parser.parse_args()


def require_paths(args: argparse.Namespace) -> None:
    required = ("gageo_root", "config", "checkpoint", "image_root", "manifest")
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        raise SystemExit("Missing arguments: " + ", ".join("--" + x.replace("_", "-") for x in missing))
    for name in required:
        path = getattr(args, name)
        if not path.exists():
            raise FileNotFoundError(f"{name} does not exist: {path}")
    if args.dataset_json is not None and not args.dataset_json.exists():
        raise FileNotFoundError(f"dataset_json does not exist: {args.dataset_json}")


def resolve_dataset_json(gageo_root: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.resolve()
    json_root = Path(os.environ.get("JSON_ROOT", gageo_root / "data" / "json")).expanduser()
    return (json_root / "unseen_test.json").resolve()


def load_dataset_records(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"Official unseen_test dataset metadata not found: {path}. "
            "Set JSON_ROOT or pass --dataset-json /path/to/unseen_test.json."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        top_keys = list(payload)[:8] if isinstance(payload, dict) else []
        raise ValueError(
            f"Dataset JSON must be the official per-sample unseen_test list, got "
            f"{type(payload).__name__} with top-level keys={top_keys}. "
            "Aggregate metrics JSON (for example outputs/unseen_test_point.json) is not a dataset."
        )
    if len(payload) != 4197:
        raise ValueError(f"Expected 4197 official unseen_test samples, found {len(payload)} in {path}")
    return payload


def validate_manifest_record(
    manifest_row: dict[str, str],
    dataset_records: list[dict[str, object]],
) -> tuple[int, dict[str, object]]:
    if manifest_row.get("split") != "unseen_test" or manifest_row.get("prompt_type") != "point":
        raise ValueError(
            f"Manifest row violates fixed protocol: split={manifest_row.get('split')!r}, "
            f"prompt_type={manifest_row.get('prompt_type')!r}"
        )
    sample_index = int(manifest_row["index"])
    if sample_index < 0 or sample_index >= len(dataset_records):
        raise IndexError(
            f"Manifest index={sample_index} is outside official dataset range [0, {len(dataset_records) - 1}]"
        )
    record = dataset_records[sample_index]
    if not isinstance(record, dict):
        raise TypeError(f"Official dataset record at index={sample_index} is not an object")
    dataset_mono = str(record.get("mono_filename", ""))
    dataset_sat = str(record.get("sat_filename") or record.get("sate_filename") or "")
    manifest_mono = manifest_row["mono_filename"]
    manifest_sat = manifest_row["sat_filename"]
    if dataset_mono != manifest_mono or dataset_sat != manifest_sat:
        raise RuntimeError(
            "Manifest→official-dataset mapping error at "
            f"index={sample_index}: mono manifest={manifest_mono!r}, dataset={dataset_mono!r}; "
            f"sat manifest={manifest_sat!r}, dataset={dataset_sat!r}. Refuse to continue."
        )
    for field in ("task_type", "size_category", "shape_category", "city"):
        dataset_value = record.get(field)
        if dataset_value is not None and str(dataset_value).lower() != manifest_row[field].lower():
            raise RuntimeError(
                f"Manifest→official-dataset metadata mismatch at index={sample_index}, field={field}: "
                f"manifest={manifest_row[field]!r}, dataset={dataset_value!r}. Refuse to continue."
            )
    return sample_index, record


def load_manifest(path: Path, max_per_cohort: int) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {
            "control_id", "cohort", "index", "task_type", "size_category", "shape_category",
            "city", "prompt_type", "split", "mono_filename", "sat_filename", "det_iou", "mask_iou",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Manifest missing required columns: {sorted(missing)}")
        rows = list(reader)
    if not rows:
        raise ValueError(f"Manifest contains no samples: {path}")
    if max_per_cohort <= 0:
        return rows
    counts: dict[str, int] = defaultdict(int)
    selected = []
    for row in rows:
        cohort = row["cohort"]
        if counts[cohort] < max_per_cohort:
            selected.append(row)
            counts[cohort] += 1
    return selected


def binary_auroc(positives: list[float], negatives: list[float]) -> float | None:
    if not positives or not negatives:
        return None
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            wins += float(positive > negative) + 0.5 * float(positive == negative)
    return wins / (len(positives) * len(negatives))


def binary_average_precision(positives: list[float], negatives: list[float]) -> float | None:
    if not positives:
        return None
    ranked = sorted([(x, 1) for x in positives] + [(x, 0) for x in negatives], reverse=True)
    true_seen = 0
    precision_sum = 0.0
    for rank, (_score, label) in enumerate(ranked, start=1):
        if label:
            true_seen += 1
            precision_sum += true_seen / rank
    return precision_sum / len(positives)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    if args.print_plan:
        print(PLAN)
        return 0
    require_paths(args)

    # Resolve and validate the official split before loading the 937M model.
    dataset_json = resolve_dataset_json(args.gageo_root.resolve(), args.dataset_json)
    dataset_records = load_dataset_records(dataset_json)
    manifest = load_manifest(args.manifest, args.max_per_cohort)
    for manifest_row in manifest:
        validate_manifest_record(manifest_row, dataset_records)

    import cv2
    import numpy as np
    import torch
    import torch.nn.functional as F

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
        load_cfg_with_env,
        remap_legacy_mask_head_keys,
        resolve_checkpoint,
        sanitize_bbox_xyxy,
    )

    device = torch.device(args.device)
    cfg = load_cfg_with_env(str(args.config.resolve()))
    model = build_model_from_cfg(cfg, device)
    checkpoint_file = resolve_checkpoint(args.checkpoint.resolve())
    state = torch.load(str(checkpoint_file), map_location="cpu")
    state_dict = extract_state_dict(state)
    state_dict, _ = remap_legacy_mask_head_keys(state_dict)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing or unexpected:
        raise RuntimeError(
            f"Checkpoint/model mismatch: missing={missing[:12]} unexpected={unexpected[:12]}"
        )
    model.eval()

    supervision_layers = list(model.backbone.supervision_layers)
    if not supervision_layers:
        raise RuntimeError("No Pi3 supervision layers exposed by checkpoint config")
    print(f"Using actual Pi3 pair-stage checkpoints: {supervision_layers}")

    captures: dict[str, object] = {}

    def encoder_hook(_module, _inputs, output):
        captures["dino"] = output

    def backbone_hook(_module, _inputs, output):
        captures["backbone"] = output

    encoder_handle = model.backbone.encoder.register_forward_hook(encoder_hook)
    backbone_handle = model.backbone.register_forward_hook(backbone_hook)

    img_size = int(cfg["data"].get("img_size", 518))
    grid = img_size // int(cfg["model"].get("patch_size", 14))
    dataset = EvalDataset(dataset_records, image_root=str(args.image_root), img_size=img_size)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    panel_dir = args.output_dir / "taxonomy_panels"
    panel_dir.mkdir(exist_ok=True)

    def patch_region(mask: torch.Tensor) -> torch.Tensor:
        return F.adaptive_max_pool2d(mask.float().unsqueeze(1), (grid, grid)).flatten(1) > 0

    def pooled(features: torch.Tensor, region: torch.Tensor) -> torch.Tensor:
        weights = region.to(features.dtype)
        return (features * weights.unsqueeze(-1)).sum(1) / weights.sum(1, keepdim=True).clamp_min(1.0)

    def layer_measure(
        query_vector: torch.Tensor,
        sat_features: torch.Tensor,
        front_features: torch.Tensor | None,
        query_region: torch.Tensor,
        gt_region: torch.Tensor,
    ) -> dict[str, float | int | None]:
        q = F.normalize(query_vector.float(), dim=-1)
        sat_n = F.normalize(sat_features.float(), dim=-1)
        scores = torch.einsum("bc,bnc->bn", q, sat_n)[0]
        gt = gt_region[0]
        if not bool(gt.any()) or bool(gt.all()):
            raise RuntimeError("Invalid satellite GT patch region")
        order = torch.argsort(scores, descending=True)
        gt_positions = torch.nonzero(gt[order], as_tuple=False).flatten()
        gt_rank = int(gt_positions.min().item()) + 1
        best_gt_idx = torch.where(gt, scores, torch.full_like(scores, -torch.inf)).argmax()
        best_wrong_idx = torch.where(~gt, scores, torch.full_like(scores, -torch.inf)).argmax()
        result: dict[str, float | int | None] = {
            "hit1": int(gt_rank <= 1),
            "hit4": int(gt_rank <= 4),
            "hit8": int(gt_rank <= 8),
            "gt_rank": gt_rank,
            "gt_vs_wrong_margin": float((scores[best_gt_idx] - scores[best_wrong_idx]).item()),
            "true_return_score": None,
            "wrong_return_score": None,
            "return_margin": None,
        }
        if front_features is not None:
            front_n = F.normalize(front_features.float(), dim=-1)[0]
            qmask = query_region[0]

            def return_mass(candidate_idx: torch.Tensor) -> torch.Tensor:
                logits = torch.mv(front_n, sat_n[0, candidate_idx]) / args.temperature
                probabilities = torch.softmax(logits, dim=0)
                return probabilities[qmask].sum()

            true_return = return_mass(best_gt_idx)
            wrong_return = return_mass(best_wrong_idx)
            result.update({
                "true_return_score": float(true_return.item()),
                "wrong_return_score": float(wrong_return.item()),
                "return_margin": float((true_return - wrong_return).item()),
            })
        return result

    def to_rgb(tensor: torch.Tensor) -> np.ndarray:
        return (tensor.detach().cpu().permute(1, 2, 0).numpy().clip(0, 1) * 255).astype(np.uint8)

    def overlay(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
        out = image.copy()
        selected = mask.astype(bool)
        out[selected] = (0.55 * out[selected] + 0.45 * np.asarray(color)).astype(np.uint8)
        return out

    records: list[dict[str, object]] = []
    audit_runtime: list[dict[str, object]] = []
    with torch.no_grad():
        for manifest_row in manifest:
            source_index, _dataset_record = validate_manifest_record(manifest_row, dataset_records)
            batch = collate_eval([dataset[source_index]])
            if int(batch["index"][0]) != source_index:
                raise RuntimeError(
                    f"Official EvalDataset returned index={batch['index'][0]} for requested index={source_index}"
                )
            front = batch["front_view"].to(device)
            sat = batch["sat_view"].to(device)
            mono_point = batch["mono_point"].to(device)
            points = (mono_point.unsqueeze(1), torch.ones(1, 1, device=device))
            captures.clear()
            outputs = model(front_view=front, satellite_view=sat, points=points)
            dino_raw = captures["dino"]
            dino = dino_raw["x_norm_patchtokens"] if isinstance(dino_raw, dict) else dino_raw
            dino = dino.reshape(1, 2, grid * grid, -1)
            backbone = captures["backbone"]

            query_region = patch_region(batch["mono_mask"].to(device))
            gt_region = patch_region(batch["gt_mask"].to(device))

            if outputs["pred_boxes"].shape[1] > 1:
                selected_query = int(outputs["bbox_scores"][0].argmax().item())
            else:
                selected_query = 0
            runtime_pred_box = sanitize_bbox_xyxy(
                bbox_cxcywh_norm_to_xyxy_abs(outputs["pred_boxes"][0, selected_query], img_size), img_size
            )
            runtime_gt_box = clip_bbox_xyxy(batch["gt_bbox_xyxy"][0].numpy(), img_size)
            runtime_det_iou = bbox_iou_np(runtime_pred_box, runtime_gt_box)
            runtime_pred_mask = (
                outputs["mask_pred"][0, selected_query].detach().cpu().numpy() > 0.5
            ).astype(np.uint8)
            runtime_gt_mask = batch["gt_mask"][0].numpy().astype(np.uint8)
            runtime_mask_iou = SegMetrics.iou(runtime_pred_mask, runtime_gt_mask)
            cohort = manifest_row["cohort"]
            if cohort == "ground_severe":
                cohort_consistent = runtime_det_iou == 0.0 and runtime_mask_iou == 0.0
            else:
                cohort_consistent = runtime_det_iou >= 0.5 and runtime_mask_iou >= 0.5
            if not cohort_consistent:
                raise RuntimeError(
                    f"Runtime output no longer matches cohort={cohort} at index={source_index}: "
                    f"det_iou={runtime_det_iou:.6f}, mask_iou={runtime_mask_iou:.6f}. "
                    "Check checkpoint/config/data identity before interpreting features."
                )
            layers: dict[str, tuple[torch.Tensor, torch.Tensor, torch.Tensor | None]] = {
                "dinov2": (pooled(dino[:, 1], query_region), dino[:, 0], dino[:, 1]),
            }
            for stage in supervision_layers:
                stage_data = backbone["intermediate"][stage]
                stage_sat = stage_data["sate_patches"]
                stage_front = stage_data.get("front_patches")
                if stage_front is not None:
                    layers[f"pi3_stage_{stage}_spatial"] = (
                        pooled(stage_front, query_region), stage_sat, stage_front
                    )
                layers[f"pi3_stage_{stage}_object_token"] = (
                    stage_data["learnable"][:, 0], stage_sat, stage_front
                )
            layers["pi3_final_spatial"] = (
                pooled(backbone["front_features"], query_region),
                backbone["sate_features"],
                backbone["front_features"],
            )
            layers["pi3_final_object_token"] = (
                backbone["learnable_out"][:, 0], backbone["sate_features"], backbone["front_features"]
            )

            for layer_name, (query_vector, sat_features, front_features) in layers.items():
                metrics = layer_measure(query_vector, sat_features, front_features, query_region, gt_region)
                records.append({
                    "control_id": manifest_row["control_id"],
                    "cohort": manifest_row["cohort"],
                    "index": source_index,
                    "size_category": manifest_row["size_category"],
                    "shape_category": manifest_row["shape_category"],
                    "layer": layer_name,
                    "saved_det_iou": manifest_row["det_iou"],
                    "saved_mask_iou": manifest_row["mask_iou"],
                    "runtime_det_iou": runtime_det_iou,
                    "runtime_mask_iou": runtime_mask_iou,
                    **metrics,
                })

            if manifest_row["cohort"] == "ground_severe":
                query_rgb, sat_rgb = to_rgb(front[0]), to_rgb(sat[0])
                point = tuple(int(x) for x in mono_point[0].detach().cpu().tolist())
                cv2.circle(query_rgb, point, 7, (255, 0, 255), 3)
                gt_panel = overlay(sat_rgb, runtime_gt_mask, (0, 255, 0))
                pred_panel = overlay(sat_rgb, runtime_pred_mask, (255, 0, 0))
                gt_box = runtime_gt_box.astype(int)
                pred_box = runtime_pred_box.astype(int)
                cv2.rectangle(gt_panel, tuple(gt_box[:2]), tuple(gt_box[2:]), (0, 255, 0), 3)
                cv2.rectangle(pred_panel, tuple(pred_box[:2]), tuple(pred_box[2:]), (255, 0, 0), 3)
                panel = np.concatenate([query_rgb, gt_panel, pred_panel], axis=1)
                panel_path = panel_dir / f"idx{source_index:05d}.jpg"
                cv2.imwrite(str(panel_path), cv2.cvtColor(panel, cv2.COLOR_RGB2BGR))
                audit_runtime.append({
                    **manifest_row,
                    "panel_path": str(panel_path),
                    "runtime_det_iou": runtime_det_iou,
                    "runtime_mask_iou": runtime_mask_iou,
                    "audit_label": "",
                    "audit_confidence": "",
                    "annotation_valid": "",
                    "notes": "",
                })

    encoder_handle.remove()
    backbone_handle.remove()

    fieldnames = list(records[0])
    with (args.output_dir / "layerwise_per_sample.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    with (args.output_dir / "taxonomy_runtime_audit.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit_runtime[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(audit_runtime)

    summary: dict[str, object] = {
        "checkpoint": str(checkpoint_file),
        "checkpoint_sha256": sha256_file(checkpoint_file),
        "config": str(args.config.resolve()),
        "config_sha256": sha256_file(args.config.resolve()),
        "dataset_json": str(dataset_json),
        "dataset_json_sha256": sha256_file(dataset_json),
        "supervision_pair_stages": supervision_layers,
        "query_representation": "oracle GT mono-mask pooled feature; model input remains Point Prompt",
        "sample_count": len(manifest),
        "groups": {},
    }
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[(str(record["cohort"]), str(record["layer"]))].append(record)
    for (cohort, layer), group in grouped.items():
        label = f"{cohort}/{layer}"
        return_rows = [r for r in group if r["return_margin"] is not None]
        true_returns = [float(r["true_return_score"]) for r in return_rows]
        wrong_returns = [float(r["wrong_return_score"]) for r in return_rows]
        summary["groups"][label] = {
            "count": len(group),
            "hit1": sum(int(r["hit1"]) for r in group) / len(group),
            "hit4": sum(int(r["hit4"]) for r in group) / len(group),
            "hit8": sum(int(r["hit8"]) for r in group) / len(group),
            "mean_gt_rank": sum(int(r["gt_rank"]) for r in group) / len(group),
            "mean_gt_vs_wrong_margin": sum(float(r["gt_vs_wrong_margin"]) for r in group) / len(group),
            "mean_return_margin": (
                sum(float(r["return_margin"]) for r in return_rows) / len(return_rows) if return_rows else None
            ),
            "return_auroc": binary_auroc(true_returns, wrong_returns),
            "return_auprc": binary_average_precision(true_returns, wrong_returns),
        }
    (args.output_dir / "layerwise_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(records)} layer records and {len(audit_runtime)} taxonomy panels to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
