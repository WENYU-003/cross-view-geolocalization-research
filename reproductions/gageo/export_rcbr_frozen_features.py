#!/usr/bin/env python3
"""Export leakage-controlled frozen features for the RCBR premise probe.

This diagnostic runs the released GAGeo baseline with Point Prompt only.  The
predictor features use pair-stage 4/11 tensors and the input point; GT masks
and final tensors are used only to create separately named supervision/audit
columns.  It does not train a probe, RCBR, or any GAGeo parameter.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import sys
from pathlib import Path
from typing import Any


EXPECTED_COUNTS = {"train": 95_681, "val": 12_166, "unseen_test": 2_180}
METADATA_NAMES = {
    "train": "train_all.json",
    "val": "val_all.json",
    "unseen_test": "unseen_test.json",
}
FEATURE_COLUMNS = (
    "feature_point11_entropy_norm",
    "feature_point11_top1_top2_gap",
    "feature_point11_top1_top8_gap",
    "feature_point11_top8_mass",
    "feature_point11_peak_zscore",
    "feature_point11_top8_spatial_dispersion",
    "feature_point_task11_js_divergence",
    "feature_point_task11_top8_overlap",
    "feature_point_task11_peak_distance_norm",
    "feature_point4_11_js_divergence",
    "feature_point4_11_top8_overlap",
    "feature_point4_11_peak_distance_norm",
    "feature_prompt_local_global_cosine_11",
    "feature_prompt_local_feature_norm_11",
    "feature_reference_feature_norm_mean_11",
)


PLAN = """RCBR frozen feature export

Inputs:
  --gageo-root     official GAGeo checkout
  --config         released baseline evaluation config (PR-MHA disabled)
  --checkpoint     released full GAGeo checkpoint
  --image-root     CMA-Loc image root
  --metadata-root  official directory containing train_all.json, val_all.json,
                   and unseen_test.json
  --split           train, val, or unseen_test

Predictor provenance:
  Point Prompt + pair-stage 4/11 only; no GT mask pooling and no stage 12--17
  or final information. GT and final spatial tensors are used only for
  label_d8 and namespaced label_/audit_ fields.

Train preprocessing:
  Official CrossViewDataset with crop_sat=True. The official random crop is
  made reproducible per sample with deterministic_crop_seed + metadata index.
Val/unseen_test preprocessing:
  Official CrossViewDataset with crop_sat=False and crop_sate images.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-plan", action="store_true")
    parser.add_argument("--gageo-root", type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--metadata-root", type=Path)
    parser.add_argument("--split", choices=tuple(METADATA_NAMES))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--num-workers", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.07)
    parser.add_argument("--point-sigma-patches", type=float, default=1.0)
    parser.add_argument("--deterministic-crop-seed", type=int, default=42)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--shard-id", type=int, default=0)
    parser.add_argument("--max-samples", type=int, default=0, help="Smoke tests only; 0 exports the full shard")
    return parser.parse_args()


def require_args(args: argparse.Namespace) -> None:
    names = ("gageo_root", "config", "checkpoint", "image_root", "metadata_root", "split", "output_dir")
    missing = [name for name in names if getattr(args, name) is None]
    if missing:
        raise SystemExit("Missing arguments: " + ", ".join("--" + x.replace("_", "-") for x in missing))
    for name in ("gageo_root", "config", "checkpoint", "image_root", "metadata_root"):
        if not getattr(args, name).exists():
            raise FileNotFoundError(f"{name} does not exist: {getattr(args, name)}")
    if args.batch_size <= 0 or args.num_workers < 0:
        raise ValueError("batch-size must be positive and num-workers non-negative")
    if args.temperature <= 0 or args.point_sigma_patches <= 0:
        raise ValueError("temperature and point-sigma-patches must be positive")
    if args.num_shards <= 0 or not 0 <= args.shard_id < args.num_shards:
        raise ValueError("Require num-shards > 0 and 0 <= shard-id < num-shards")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_ground(record: dict[str, Any]) -> bool:
    """Match official CrossViewDataset Ground filtering exactly."""
    return "drone" not in str(record.get("mono_filename", "")).lower()


def load_split(path: Path, split: str) -> tuple[list[dict[str, Any]], list[int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise TypeError(f"Official metadata must be a list, got {type(payload).__name__}: {path}")
    indices = [index for index, record in enumerate(payload) if isinstance(record, dict) and is_ground(record)]
    expected = EXPECTED_COUNTS[split]
    if len(indices) != expected:
        raise RuntimeError(f"Expected {expected} Ground {split} samples, found {len(indices)} in {path}")
    return payload, indices


def output_names(args: argparse.Namespace) -> tuple[str, str]:
    if args.num_shards == 1:
        return "rcbr_frozen_features.csv", "rcbr_export_summary.json"
    suffix = f"shard_{args.shard_id:03d}_of_{args.num_shards:03d}"
    return f"rcbr_frozen_features.{suffix}.csv", f"rcbr_export_summary.{suffix}.json"


def main() -> int:
    args = parse_args()
    if args.print_plan:
        print(PLAN)
        return 0
    require_args(args)

    metadata_path = (args.metadata_root / METADATA_NAMES[args.split]).resolve()
    if not metadata_path.is_file():
        raise FileNotFoundError(metadata_path)
    all_records, ground_source_indices = load_split(metadata_path, args.split)
    selected_positions = list(range(args.shard_id, len(ground_source_indices), args.num_shards))
    if args.max_samples > 0:
        selected_positions = selected_positions[: args.max_samples]
    selected_source_indices = [ground_source_indices[position] for position in selected_positions]
    if not selected_source_indices:
        raise RuntimeError("Shard/sample selection is empty")

    import numpy as np
    import torch
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, Dataset

    sys.path.insert(0, str(args.gageo_root.resolve()))
    from datasets.cmaloc import CrossViewDataset, collate_fn  # type: ignore
    from evaluate_cmaloc import (  # type: ignore
        build_model_from_cfg,
        extract_state_dict,
        load_cfg_with_env,
        remap_legacy_mask_head_keys,
        resolve_checkpoint,
    )

    class SelectedGroundDataset(Dataset):
        def __init__(self, base, positions, source_indices, crop_seed):
            self.base = base
            self.positions = positions
            self.source_indices = source_indices
            self.crop_seed = crop_seed

        def __len__(self):
            return len(self.positions)

        def __getitem__(self, item_index):
            ground_position = self.positions[item_index]
            source_index = self.source_indices[item_index]
            state = random.getstate()
            try:
                random.seed(self.crop_seed + source_index)
                sample = self.base[ground_position]
            finally:
                random.setstate(state)
            return {"sample": sample, "source_index": source_index, "ground_position": ground_position}

    def selected_collate(items):
        batch = collate_fn([item["sample"] for item in items])
        batch["source_indices"] = [int(item["source_index"]) for item in items]
        batch["ground_positions"] = [int(item["ground_position"]) for item in items]
        return batch

    device = torch.device(args.device)
    cfg = load_cfg_with_env(str(args.config.resolve()))
    if bool(cfg.get("model", {}).get("use_late_spatial_pr_mha", False)):
        raise RuntimeError("RCBR premise export requires model.use_late_spatial_pr_mha=false")
    img_size = int(cfg["data"].get("img_size", 518))
    patch_size = int(cfg["model"].get("patch_size", 14))
    grid = img_size // patch_size
    crop_sat = args.split == "train"

    official_dataset = CrossViewDataset(
        json_path=str(metadata_path),
        data_root=str(args.image_root.resolve()),
        mono_size=img_size,
        crop_sat=crop_sat,
        crop_size=img_size,
        view_subset="ground_to_satellite",
    )
    if len(official_dataset) != EXPECTED_COUNTS[args.split]:
        raise RuntimeError("Official CrossViewDataset filtering disagrees with metadata audit")
    dataset = SelectedGroundDataset(
        official_dataset,
        selected_positions,
        selected_source_indices,
        args.deterministic_crop_seed,
    )
    loader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.num_workers,
        collate_fn=selected_collate,
        pin_memory=device.type == "cuda",
    )

    model = build_model_from_cfg(cfg, device)
    checkpoint_file = resolve_checkpoint(args.checkpoint.resolve())
    state = torch.load(str(checkpoint_file), map_location="cpu")
    state_dict = extract_state_dict(state)
    state_dict, _ = remap_legacy_mask_head_keys(state_dict)
    missing, unexpected = model.load_state_dict(state_dict, strict=False)
    if missing or unexpected:
        raise RuntimeError(f"Checkpoint mismatch: missing={missing[:20]} unexpected={unexpected[:20]}")
    model.eval()
    if any(parameter.requires_grad for parameter in model.parameters()):
        for parameter in model.parameters():
            parameter.requires_grad_(False)

    supervision_layers = list(model.backbone.supervision_layers)
    if supervision_layers != [4, 11, 17]:
        raise RuntimeError(f"Expected Pi3 pair-stage hooks [4, 11, 17], got {supervision_layers}")

    captures: dict[str, Any] = {}

    def backbone_hook(_module, _inputs, output):
        captures["backbone"] = output

    hook_handle = model.backbone.register_forward_hook(backbone_hook)

    def patch_region(mask):
        return F.adaptive_max_pool2d(mask.float(), (grid, grid)).flatten(1) > 0

    def masked_pool(features, region):
        weights = region.to(features.dtype)
        return (features * weights.unsqueeze(-1)).sum(1) / weights.sum(1, keepdim=True).clamp_min(1.0)

    def point_pool(features, points):
        batch_size = features.shape[0]
        coords = torch.arange(grid, device=features.device, dtype=torch.float32) + 0.5
        yy, xx = torch.meshgrid(coords, coords, indexing="ij")
        px = points[:, 0].float() * grid / img_size
        py = points[:, 1].float() * grid / img_size
        dist2 = (xx.unsqueeze(0) - px[:, None, None]).square() + (yy.unsqueeze(0) - py[:, None, None]).square()
        weights = torch.exp(-0.5 * dist2 / (args.point_sigma_patches ** 2)).reshape(batch_size, -1)
        weights = weights / weights.sum(1, keepdim=True).clamp_min(1e-12)
        return (features.float() * weights.unsqueeze(-1)).sum(1)

    def score_map(query, reference):
        return torch.einsum("bc,bnc->bn", F.normalize(query.float(), dim=-1), F.normalize(reference.float(), dim=-1))

    def probabilities(scores):
        return torch.softmax(scores / args.temperature, dim=1)

    def js_divergence(p, q):
        eps = 1e-12
        midpoint = 0.5 * (p + q)
        return 0.5 * (
            (p * ((p + eps).log() - (midpoint + eps).log())).sum(1)
            + (q * ((q + eps).log() - (midpoint + eps).log())).sum(1)
        )

    def topk_indices(scores, k=8):
        return torch.topk(scores, k=min(k, scores.shape[1]), dim=1).indices

    def topk_overlap(a, b):
        return (a.unsqueeze(2) == b.unsqueeze(1)).any(2).float().sum(1) / a.shape[1]

    def normalized_peak_distance(a_scores, b_scores):
        a = a_scores.argmax(1)
        b = b_scores.argmax(1)
        ax, ay = a % grid, torch.div(a, grid, rounding_mode="floor")
        bx, by = b % grid, torch.div(b, grid, rounding_mode="floor")
        diagonal = math.sqrt(2.0) * max(grid - 1, 1)
        return torch.sqrt((ax - bx).float().square() + (ay - by).float().square()) / diagonal

    def topk_dispersion(scores, k=8):
        indices = topk_indices(scores, k)
        selected = torch.gather(probabilities(scores), 1, indices)
        weights = selected / selected.sum(1, keepdim=True).clamp_min(1e-12)
        x = (indices % grid).float()
        y = torch.div(indices, grid, rounding_mode="floor").float()
        cx = (weights * x).sum(1, keepdim=True)
        cy = (weights * y).sum(1, keepdim=True)
        radius = torch.sqrt((x - cx).square() + (y - cy).square())
        diagonal = math.sqrt(2.0) * max(grid - 1, 1)
        return (weights * radius).sum(1) / diagonal

    def oracle_rank_hit8(query, reference, gt_region):
        scores = score_map(query, reference)
        masked = scores.masked_fill(~gt_region, -torch.inf)
        best_gt = masked.max(1).values
        rank = (scores > best_gt.unsqueeze(1)).sum(1) + 1
        return rank, rank <= 8

    rows: list[dict[str, Any]] = []
    with torch.inference_mode():
        for batch in loader:
            front = batch["front_view"].to(device, non_blocking=True)
            satellite = batch["satellite_view"].to(device, non_blocking=True)
            points_xy = batch["mono_point"].to(device, non_blocking=True)
            point_prompt = (points_xy.unsqueeze(1), torch.ones(points_xy.shape[0], 1, device=device))
            captures.clear()
            model(front_view=front, satellite_view=satellite, points=point_prompt)
            backbone = captures.get("backbone")
            if not isinstance(backbone, dict):
                raise RuntimeError("Backbone hook did not capture a dictionary output")
            stage4 = backbone["intermediate"][4]
            stage11 = backbone["intermediate"][11]
            front4 = stage4.get("front_patches")
            front11 = stage11.get("front_patches")
            if front4 is None or front11 is None:
                raise RuntimeError("Pair-stage 4/11 front_patches are required")
            sat4 = stage4["sate_patches"]
            sat11 = stage11["sate_patches"]

            point_query4 = point_pool(front4, points_xy)
            point_query11 = point_pool(front11, points_xy)
            point_scores4 = score_map(point_query4, sat4)
            point_scores11 = score_map(point_query11, sat11)
            task_scores11 = score_map(stage11["learnable"][:, 0], sat11)
            point_prob4 = probabilities(point_scores4)
            point_prob11 = probabilities(point_scores11)
            task_prob11 = probabilities(task_scores11)
            sorted11 = torch.sort(point_scores11, dim=1, descending=True).values
            top8_idx11 = topk_indices(point_scores11)

            entropy = -(point_prob11 * point_prob11.clamp_min(1e-12).log()).sum(1) / math.log(point_prob11.shape[1])
            score_std = point_scores11.std(1, unbiased=False).clamp_min(1e-12)
            point_mean = point_scores11.mean(1)
            global_query11 = front11.float().mean(1)

            feature_tensors = {
                "feature_point11_entropy_norm": entropy,
                "feature_point11_top1_top2_gap": sorted11[:, 0] - sorted11[:, 1],
                "feature_point11_top1_top8_gap": sorted11[:, 0] - sorted11[:, 7],
                "feature_point11_top8_mass": torch.gather(point_prob11, 1, top8_idx11).sum(1),
                "feature_point11_peak_zscore": (sorted11[:, 0] - point_mean) / score_std,
                "feature_point11_top8_spatial_dispersion": topk_dispersion(point_scores11),
                "feature_point_task11_js_divergence": js_divergence(point_prob11, task_prob11),
                "feature_point_task11_top8_overlap": topk_overlap(top8_idx11, topk_indices(task_scores11)),
                "feature_point_task11_peak_distance_norm": normalized_peak_distance(point_scores11, task_scores11),
                "feature_point4_11_js_divergence": js_divergence(point_prob4, point_prob11),
                "feature_point4_11_top8_overlap": topk_overlap(topk_indices(point_scores4), top8_idx11),
                "feature_point4_11_peak_distance_norm": normalized_peak_distance(point_scores4, point_scores11),
                "feature_prompt_local_global_cosine_11": F.cosine_similarity(point_query11.float(), global_query11, dim=1),
                "feature_prompt_local_feature_norm_11": point_query11.float().norm(dim=1),
                "feature_reference_feature_norm_mean_11": sat11.float().norm(dim=2).mean(1),
            }
            if tuple(feature_tensors) != FEATURE_COLUMNS:
                raise RuntimeError("Feature schema/order drift")
            feature_matrix = torch.stack([feature_tensors[name] for name in FEATURE_COLUMNS], dim=1)
            if not bool(torch.isfinite(feature_matrix).all()):
                raise RuntimeError("Non-finite frozen predictor feature detected")

            mono_gt_region = patch_region(batch["mono_mask"].to(device, non_blocking=True))
            sat_gt_region = patch_region(batch["sat_mask"].to(device, non_blocking=True))
            if not bool(mono_gt_region.any(1).all()) or not bool(sat_gt_region.any(1).all()):
                raise RuntimeError("Invalid GT patch region while constructing supervision labels")
            oracle_query11 = masked_pool(front11, mono_gt_region)
            oracle_query_final = masked_pool(backbone["front_features"], mono_gt_region)
            rank11, hit11 = oracle_rank_hit8(oracle_query11, sat11, sat_gt_region)
            rank_final, hit_final = oracle_rank_hit8(
                oracle_query_final, backbone["sate_features"], sat_gt_region
            )
            label_d8 = hit11 & ~hit_final

            for batch_index, source_index in enumerate(batch["source_indices"]):
                original = all_records[source_index]
                mono_filename = batch["mono_filenames"][batch_index]
                sat_filename = batch["sat_filenames"][batch_index]
                expected_sat = original.get("sat_filename") or original.get("sate_filename")
                if mono_filename != original.get("mono_filename") or sat_filename != expected_sat:
                    raise RuntimeError(f"Dataset provenance mismatch at source index {source_index}")
                row: dict[str, Any] = {
                    "split": args.split,
                    "source_index": source_index,
                    "ground_position": batch["ground_positions"][batch_index],
                    "city": original.get("city", ""),
                    "mono_filename": mono_filename,
                    "sat_filename": sat_filename,
                    "prompt_type": "point",
                    "crop_offset_x": float(batch["crop_offset"][batch_index, 0]),
                    "crop_offset_y": float(batch["crop_offset"][batch_index, 1]),
                }
                row.update({
                    name: float(feature_tensors[name][batch_index].cpu()) for name in FEATURE_COLUMNS
                })
                row.update({
                    "label_stage11_hit8": int(hit11[batch_index].cpu()),
                    "label_final_hit8": int(hit_final[batch_index].cpu()),
                    "label_d8": int(label_d8[batch_index].cpu()),
                    "audit_stage11_gt_rank": int(rank11[batch_index].cpu()),
                    "audit_final_gt_rank": int(rank_final[batch_index].cpu()),
                })
                rows.append(row)

    hook_handle.remove()
    if len(rows) != len(selected_source_indices):
        raise RuntimeError(f"Expected {len(selected_source_indices)} rows, collected {len(rows)}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_name, summary_name = output_names(args)
    csv_path = args.output_dir / csv_name
    summary_path = args.output_dir / summary_name
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    d8_count = sum(int(row["label_d8"]) for row in rows)
    if (
        args.split == "unseen_test"
        and args.num_shards == 1
        and args.max_samples == 0
        and d8_count != 116
    ):
        raise RuntimeError(
            f"Unseen-test D8 provenance mismatch: expected 116/2180, got {d8_count}/{len(rows)}"
        )
    summary = {
        "status": "frozen_feature_export_only_probe_not_run",
        "split": args.split,
        "official_ground_count": EXPECTED_COUNTS[args.split],
        "exported_sample_count": len(rows),
        "d8_count": d8_count,
        "d8_prevalence": d8_count / len(rows),
        "checkpoint": str(checkpoint_file),
        "checkpoint_sha256": sha256_file(checkpoint_file),
        "config": str(args.config.resolve()),
        "config_sha256": sha256_file(args.config.resolve()),
        "metadata": str(metadata_path),
        "metadata_sha256": sha256_file(metadata_path),
        "image_root": str(args.image_root.resolve()),
        "prompt_type": "point",
        "view_subset": "ground_to_satellite",
        "pr_mha_enabled": False,
        "model_trainable_parameter_count": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "predictor_max_stage": 11,
        "feature_columns": list(FEATURE_COLUMNS),
        "feature_count": len(FEATURE_COLUMNS),
        "predictor_uses_gt": False,
        "label_definition": "stage11 oracle-spatial H@8=1 and final oracle-spatial H@8=0",
        "gt_and_final_usage": "label_/audit_ columns only",
        "temperature": args.temperature,
        "point_sigma_patches": args.point_sigma_patches,
        "deterministic_crop_seed": args.deterministic_crop_seed if crop_sat else None,
        "crop_mode": "official deterministic random raw-satellite crop" if crop_sat else "official fixed crop_sate",
        "supervision_pair_stages": supervision_layers,
        "num_shards": args.num_shards,
        "shard_id": args.shard_id,
        "max_samples": args.max_samples,
        "csv": str(csv_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} frozen feature rows to {csv_path}")
    print(f"D8: {d8_count}/{len(rows)} = {d8_count / len(rows):.6f}")
    print("RCBR_FROZEN_FEATURE_EXPORT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
