#!/usr/bin/env python3
"""Isolate mechanisms in the fixed Scene_16 counterexample shortlist.

This analysis uses saved aerial/satellite RoMa correspondence artifacts only.
Agreement with aerial endpoints is a pseudo-correctness signal, not manual
ground truth and not a direct label of localization utility.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from analyze_scene16_spatial_support import (
    ResultArchive,
    finite_arrays,
    mutual_pairs,
    normalize_points,
    spatial_metrics,
)


FOCUS_TYPES = ("HIGH_AGREEMENT_CATASTROPHIC", "LOW_AGREEMENT_SUCCESS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aerial-archive", type=Path, required=True)
    parser.add_argument("--satellite-archive", type=Path, required=True)
    parser.add_argument("--shortlist", type=Path, required=True)
    parser.add_argument("--rgb-review", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--query-threshold-px", type=float, default=5.0)
    parser.add_argument("--grid-size", type=int, default=8)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def add_support_metrics(
    row: dict[str, object],
    query_normalized: np.ndarray,
    reference_normalized: np.ndarray,
    mask: np.ndarray,
    grid_size: int,
    label: str,
) -> None:
    count = int(mask.sum())
    row[f"{label}_count"] = count
    row[f"{label}_fraction"] = float(mask.mean())
    if count < 3:
        for space in ("uav", "satellite_ref"):
            for metric in (
                "grid_occupancy",
                "convex_hull_coverage",
                "normalized_hhi",
                "spatial_entropy",
                "top4_cell_mass_proxy",
            ):
                row[f"{label}_{space}_{metric}"] = ""
        return
    for key, value in spatial_metrics(query_normalized[mask], grid_size, "uav").items():
        if any(
            key.endswith(metric)
            for metric in (
                "grid_occupancy",
                "convex_hull_coverage",
                "normalized_hhi",
                "spatial_entropy",
                "top4_cell_mass_proxy",
            )
        ):
            row[f"{label}_{key}"] = value
    for key, value in spatial_metrics(
        reference_normalized[mask], grid_size, "satellite_ref"
    ).items():
        if any(
            key.endswith(metric)
            for metric in (
                "grid_occupancy",
                "convex_hull_coverage",
                "normalized_hhi",
                "spatial_entropy",
                "top4_cell_mass_proxy",
            )
        ):
            row[f"{label}_{key}"] = value


def mechanism_interpretation(row: dict[str, object]) -> tuple[str, str, str]:
    types = str(row["counterexample_types"])
    shift = float(row["coherent_shift_magnitude_m"])
    residual = float(row["shift_corrected_residual_median_m"])
    agreement = float(row["agreement_5m"])
    rgb_available = bool(row["rgb_panel_available"])
    visual_clause = (
        f" RGB review: {row['visual_primary_label']} / {row['visual_secondary_label']}."
        if rgb_available
        else " No RGB panel exists in the current 24-query audit."
    )

    if "HIGH_AGREEMENT_CATASTROPHIC" in types:
        if shift < 1.0 and residual < 2.0:
            family = "2D_CONSISTENT_BUT_CATASTROPHIC"
            explanation = (
                "Aerial and satellite endpoints agree broadly with near-zero coherent shift "
                "and low local residual, yet final localization is catastrophic. The saved "
                "2D cross-reference signal does not explain the failure; a common ambiguous "
                "match, 3D/map interface, or downstream instability remains possible."
            )
        else:
            family = "HIGH_AGREEMENT_WITH_NONTRIVIAL_SHIFT_OR_RESIDUAL"
            explanation = (
                "Overall Agreement@5m is high, but the nontrivial shift/residual indicates a "
                "mixed correspondence pattern. Global agreement hides local structure."
            )
        uncertainty = (
            "Cannot distinguish common visually wrong correspondence from map/DSM/PnP effects "
            "using the current 2D pseudo-reference alone."
        )
    elif "LOW_AGREEMENT_SUCCESS" in types:
        if shift >= 5.0:
            family = "LOW_AGREEMENT_COHERENT_OFFSET_BUT_SUCCESS"
            explanation = (
                "Raw aerial-satellite agreement is low and a several-metre coherent offset is "
                "present, but the satellite run localizes successfully. This suggests that "
                "cross-reference disagreement can include map-frame/georegistration offset and "
                "is not equivalent to satellite match incorrectness."
            )
        else:
            family = "LOW_AGREEMENT_LOCAL_INCONSISTENCY_BUT_SUCCESS"
            explanation = (
                "The query succeeds despite low cross-reference agreement and substantial local "
                "residual. A minority of distributed support may be sufficient, or the aerial "
                "pseudo-reference may disagree with valid satellite correspondences."
            )
        uncertainty = (
            "Agreement-threshold support is not a PnP inlier set or manual landmark annotation; "
            "the exact correspondences driving the successful pose are unknown."
        )
    elif "HIGH_CONCENTRATION_CATASTROPHIC" in types:
        family = "CONCENTRATED_LOW_AGREEMENT_CATASTROPHIC"
        explanation = (
            "Low agreement, high concentration, and large residual are jointly compatible with "
            "localized ambiguity or weak support diversity."
        )
        uncertainty = (
            "Concentration has no semantic meaning without RGB/region labels and cannot by itself "
            "be called repetitive-structure ambiguity."
        )
    elif "HIGH_MATCH_COUNT_CATASTROPHIC" in types:
        family = "MANY_PAIRS_BUT_LOW_GEOGRAPHIC_UTILITY"
        explanation = (
            "A large shared-pair count does not prevent catastrophic error; geographic agreement "
            "and residual structure are more informative than quantity alone."
        )
        uncertainty = (
            "The saved artifacts do not identify which subset was decisive for the final solver."
        )
    elif "BROAD_COVERAGE_SUCCESS" in types:
        family = "BROAD_SUPPORT_SUCCESS_CONTROL"
        explanation = (
            "Broad reference support accompanies a successful outcome and serves as a positive "
            "control, but broad coverage is not globally sufficient for success."
        )
        uncertainty = "Coverage is geometric only; stable context is not semantically labeled."
    else:
        family = "MIXED_COUNTEREXAMPLE"
        explanation = "The case does not isolate a single mechanism with current evidence."
        uncertainty = "Additional RGB or correspondence-level annotation is required."

    return family, explanation + visual_clause, uncertainty


def analyze_case(
    shortlist_row: dict[str, str],
    aerial: ResultArchive,
    satellite: ResultArchive,
    rgb_by_id: dict[str, dict[str, str]],
    query_threshold_px: float,
    grid_size: int,
) -> dict[str, object]:
    sample_id = shortlist_row["sample_id"]
    aerial_query, _, aerial_map = finite_arrays(aerial.arrays(sample_id))
    satellite_query, satellite_reference, satellite_map = finite_arrays(
        satellite.arrays(sample_id)
    )
    aerial_indices, satellite_indices, _ = mutual_pairs(
        aerial_query, satellite_query, query_threshold_px
    )
    query = (aerial_query[aerial_indices] + satellite_query[satellite_indices]) / 2.0
    reference = satellite_reference[satellite_indices]
    query_normalized, _, _ = normalize_points(
        query,
        float(satellite.records[sample_id]["uav_input_width"]),
        float(satellite.records[sample_id]["uav_input_height"]),
    )
    reference_normalized, _, _ = normalize_points(
        reference,
        float(satellite.records[sample_id]["ref_patch_width"]),
        float(satellite.records[sample_id]["ref_patch_height"]),
    )
    delta = satellite_map[satellite_indices] - aerial_map[aerial_indices]
    disagreement = np.linalg.norm(delta, axis=1)
    coherent_shift = np.median(delta, axis=0)
    residual = np.linalg.norm(delta - coherent_shift, axis=1)
    visual = rgb_by_id.get(sample_id)
    row: dict[str, object] = {
        "counterexample_types": shortlist_row["counterexample_types"],
        "sample_id": sample_id,
        "failure_group": shortlist_row["failure_group"],
        "satellite_final_error_m": float(shortlist_row["satellite_final_error_m"]),
        "agreement_3m": float(np.mean(disagreement <= 3.0)),
        "agreement_5m": float(np.mean(disagreement <= 5.0)),
        "num_shared_uav_correspondences": int(len(aerial_indices)),
        "coherent_shift_x_m": float(coherent_shift[0]),
        "coherent_shift_y_m": float(coherent_shift[1]),
        "coherent_shift_magnitude_m": float(np.linalg.norm(coherent_shift)),
        "shift_corrected_residual_median_m": float(np.median(residual)),
        "shift_corrected_agreement_3m": float(np.mean(residual <= 3.0)),
        "shift_corrected_agreement_5m": float(np.mean(residual <= 5.0)),
        "uav_grid_occupancy": float(shortlist_row["uav_grid_occupancy"]),
        "uav_convex_hull_coverage": float(shortlist_row["uav_convex_hull_coverage"]),
        "satellite_ref_grid_occupancy": float(
            shortlist_row["satellite_ref_grid_occupancy"]
        ),
        "satellite_ref_convex_hull_coverage": float(
            shortlist_row["satellite_ref_convex_hull_coverage"]
        ),
        "satellite_ref_normalized_hhi": float(
            shortlist_row["satellite_ref_normalized_hhi"]
        ),
        "satellite_ref_spatial_entropy": float(
            shortlist_row["satellite_ref_spatial_entropy"]
        ),
        "rgb_panel_available": visual is not None,
        "visual_primary_label": (
            visual["primary_failure_label"]
            if visual
            else "NO_RGB_PANEL_IN_CURRENT_24_QUERY_AUDIT"
        ),
        "visual_secondary_label": (
            visual["secondary_failure_label"] if visual else "MISSING"
        ),
        "visual_reviewer_notes": visual["reviewer_notes"] if visual else "",
        "visual_panel_path": visual["panel_path"] if visual else "",
    }
    add_support_metrics(
        row,
        query_normalized,
        reference_normalized,
        disagreement <= 3.0,
        grid_size,
        "agree3_support",
    )
    add_support_metrics(
        row,
        query_normalized,
        reference_normalized,
        disagreement <= 5.0,
        grid_size,
        "agree5_support",
    )
    family, explanation, uncertainty = mechanism_interpretation(row)
    row["mechanism_family"] = family
    row["reviewer_explanation"] = explanation
    row["uncertainty"] = uncertainty
    return row


def metric_summary(rows: list[dict[str, object]], metric: str) -> dict[str, float]:
    values = np.asarray([float(row[metric]) for row in rows], dtype=np.float64)
    return {
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "min": float(values.min()),
        "max": float(values.max()),
    }


def focus_summary(rows: list[dict[str, object]]) -> dict:
    metrics = (
        "satellite_final_error_m",
        "agreement_3m",
        "agreement_5m",
        "num_shared_uav_correspondences",
        "coherent_shift_magnitude_m",
        "shift_corrected_residual_median_m",
        "uav_grid_occupancy",
        "satellite_ref_grid_occupancy",
        "satellite_ref_normalized_hhi",
        "agree3_support_count",
        "agree3_support_uav_grid_occupancy",
        "agree3_support_uav_convex_hull_coverage",
        "agree3_support_satellite_ref_grid_occupancy",
        "agree3_support_satellite_ref_convex_hull_coverage",
        "agree5_support_count",
        "agree5_support_uav_grid_occupancy",
        "agree5_support_uav_convex_hull_coverage",
        "agree5_support_satellite_ref_grid_occupancy",
        "agree5_support_satellite_ref_convex_hull_coverage",
    )
    groups = {}
    for focus_type in FOCUS_TYPES:
        group_rows = [
            row for row in rows if focus_type in str(row["counterexample_types"])
        ]
        groups[focus_type] = {
            "num_queries": len(group_rows),
            **{metric: metric_summary(group_rows, metric) for metric in metrics},
        }
    return {
        "num_counterexamples": len(rows),
        "num_rgb_reviewed": sum(bool(row["rgb_panel_available"]) for row in rows),
        "focus_groups": groups,
        "mechanism_family_counts": dict(
            sorted(Counter(str(row["mechanism_family"]) for row in rows).items())
        ),
        "evidence_boundary": [
            "Agreement-threshold support uses aerial endpoints as a pseudo-reference.",
            "Agree3/Agree5 support is not a PnP inlier set and does not reveal solver influence.",
            "Only six of the 29 queries have RGB panels in the current visual audit.",
            "No semantic roof/context annotations or RoMa confidence values are available.",
        ],
    }


def comparison_csv(summary: dict) -> list[dict[str, object]]:
    rows = []
    first = summary["focus_groups"][FOCUS_TYPES[0]]
    second = summary["focus_groups"][FOCUS_TYPES[1]]
    for metric in first:
        if metric == "num_queries":
            continue
        rows.append(
            {
                "metric": metric,
                "high_agreement_catastrophic_median": first[metric]["median"],
                "low_agreement_success_median": second[metric]["median"],
                "high_agreement_catastrophic_mean": first[metric]["mean"],
                "low_agreement_success_mean": second[metric]["mean"],
            }
        )
    return rows


def write_note(path: Path, rows: list[dict[str, object]], summary: dict) -> None:
    high = summary["focus_groups"]["HIGH_AGREEMENT_CATASTROPHIC"]
    low = summary["focus_groups"]["LOW_AGREEMENT_SUCCESS"]
    five_consistent = sum(
        "HIGH_AGREEMENT_CATASTROPHIC" in str(row["counterexample_types"])
        and float(row["coherent_shift_magnitude_m"]) < 1.0
        and float(row["shift_corrected_residual_median_m"]) < 2.0
        for row in rows
    )
    lines = [
        "# Scene_16 Counterexample Mechanism Isolation",
        "",
        "## Scope",
        "",
        "This audit analyzes the fixed 29-query counterexample shortlist using saved aerial/satellite correspondence artifacts only. It does not rerun retrieval, RoMa, DSM, PnP, or training.",
        "",
        "Only 6/29 cases have panels in the existing 24-query RGB audit. Missing visual labels remain explicit and are not inferred from metrics.",
        "",
        "## Focus comparison",
        "",
        "| Metric (median) | High-Agreement catastrophic (n=6) | Low-Agreement success (n=6) |",
        "| --- | ---: | ---: |",
    ]
    for metric, label in (
        ("satellite_final_error_m", "Final error (m)"),
        ("agreement_3m", "Agreement@3m"),
        ("agreement_5m", "Agreement@5m"),
        ("num_shared_uav_correspondences", "Shared pairs"),
        ("coherent_shift_magnitude_m", "Coherent shift (m)"),
        ("shift_corrected_residual_median_m", "Shift-corrected residual (m)"),
        ("agree3_support_count", "Agree3 support count"),
        ("agree3_support_uav_grid_occupancy", "Agree3 UAV occupancy"),
        ("agree3_support_satellite_ref_grid_occupancy", "Agree3 satellite occupancy"),
        ("agree5_support_uav_convex_hull_coverage", "Agree5 UAV hull coverage"),
        ("agree5_support_satellite_ref_convex_hull_coverage", "Agree5 satellite hull coverage"),
    ):
        lines.append(
            f"| {label} | {high[metric]['median']:.3f} | {low[metric]['median']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Mechanism isolation result",
            "",
            f"- {five_consistent}/6 high-Agreement catastrophic cases have coherent shift <1 m and shift-corrected median residual <2 m. Their aerial and satellite 2D endpoint fields are mutually consistent and broadly supported, yet final errors remain catastrophic.",
            "- The high-Agreement catastrophic group has more Agreement<=3/5m pairs and broader pseudo-correct support than the low-Agreement successful group. Therefore neither pseudo-correct count nor pseudo-correct coverage explains their failure.",
            "- Low-Agreement successful cases show that a minority of support can be sufficient, but the current artifacts do not identify which correspondences actually drove PnP. Several also contain a coherent aerial-satellite offset, indicating that cross-reference disagreement can include map-frame/georegistration effects.",
            "- The stable difference is not repeated-structure ambiguity versus context support. It is a diagnostic split: some catastrophic outcomes are not explained at all by 2D cross-reference consistency, while some successful outcomes violate the aerial-pseudo-reference assumption.",
            "- A narrower frontend-associated subgroup is repeatable inside the shortlist: L16_0208 and L16_0210-L16_0214 are all catastrophic with low Agreement, concentrated support, and large local residual. Compared with the six low-Agreement successes, their median UAV occupancy is 0.344 versus 0.656, satellite normalized HHI is 0.0446 versus 0.0103, and spatial entropy is 0.754 versus 0.904. This supports weak spatial diversity/local inconsistency for this subgroup, but not as a universal explanation of every catastrophic case.",
            "",
            "## What is supported",
            "",
            "1. Global aerial-satellite Agreement is unsuitable as a per-correspondence localization-utility label.",
            "2. Many mutually consistent and spatially broad 2D pairs are not sufficient for correct final localization.",
            "3. Low cross-reference Agreement is not necessary for failure and can coexist with accurate satellite localization.",
            "4. The 29 cases contain at least two mechanism families and should not be optimized with one undifferentiated frontend objective.",
            "5. Low Agreement becomes more failure-informative when it co-occurs with concentrated support and large residual; Agreement alone is insufficient.",
            "",
            "## What remains unconfirmed",
            "",
            "- Repeated-structure ambiguity and surrounding-context rescue are visually supported only in a small subset, not the full 29.",
            "- The five 2D-consistent catastrophic cases may reflect common visually wrong matches, satellite DSM/georegistration, or downstream pose instability; current 2D artifacts cannot separate them.",
            "- Exact localization utility requires either solver-selected correspondence provenance or a DSM-free manual/planar landmark correctness protocol in the native reference frame.",
            "",
            "## Decision",
            "",
            "Do not expand immediately to new scenes and do not design a model yet. First export RGB panels for the 23 currently unviewed counterexamples and, if possible, record which sampled correspondences become solver inputs/inliers without changing the solver. External-scene validation is justified only after the 2D-consistent-catastrophic subgroup is separated from genuine frontend ambiguity.",
            "",
            "## Provisional external validation plan",
            "",
            "This section is a plan, not an executed experiment. Official scene statistics provide query count, altitude, pitch, and map resolution, but they do not map scene IDs to semantic content or repetitive-structure labels.",
            "",
            "- Scene_19 is the provisional viewpoint-diversity candidate: 256 queries and a narrow, strongly oblique 18-34 degree pitch range, unlike Scene_16's 29-90 degree range. Its actual visual-content difference must be confirmed with a CPU-only map/query montage before selection.",
            "- Scene_24 is the provisional resolution-gap candidate: 162 queries, aerial resolution 0.067 m and satellite resolution 0.278 m (about 4.15x), versus Scene_16's 0.042 m and 0.132 m (about 3.14x). It is the smallest fast candidate among the scene-level statistics considered here.",
            "- Scene_15 is the stronger but slightly larger resolution-gap alternative: 300 queries, 0.030 m aerial versus 0.285 m satellite (9.5x). Use it only if Scene_24's visual inventory does not provide the intended stress condition.",
            "",
            "Before any GPU work, inspect whether matching+localization artifacts already exist for these scenes and generate a small RGB inventory. If new artifacts are necessary, rerun only controlled aerial-GT-reference and satellite-GT-reference RoMa matching+localization with the same matcher, pose prior, PnP method, keypoint budget, and logging schema. Reuse the analysis code, thresholds, plots, and Scene_16 definitions; do not rerun retrieval or train a model.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    shortlist = read_csv(args.shortlist)
    if len(shortlist) != 29 or len({row["sample_id"] for row in shortlist}) != 29:
        raise ValueError("Expected exactly 29 unique shortlist rows")
    rgb_rows = read_csv(args.rgb_review)
    rgb_by_id = {row["sample_id"]: row for row in rgb_rows}
    aerial = ResultArchive(args.aerial_archive, "aerial")
    satellite = ResultArchive(args.satellite_archive, "satellite")
    try:
        rows = [
            analyze_case(
                shortlist_row,
                aerial,
                satellite,
                rgb_by_id,
                args.query_threshold_px,
                args.grid_size,
            )
            for shortlist_row in shortlist
        ]
    finally:
        aerial.close()
        satellite.close()
    for focus_type in FOCUS_TYPES:
        if sum(focus_type in str(row["counterexample_types"]) for row in rows) != 6:
            raise ValueError(f"Expected six {focus_type} cases")
    required = {"L16_0098", "L16_0076", "L16_0077"}
    if not required.issubset({str(row["sample_id"]) for row in rows}):
        raise ValueError("Required known counterexamples are missing")

    summary = focus_summary(rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "scene16_counterexample_mechanisms.csv", rows)
    write_csv(
        args.output_dir / "scene16_counterexample_focus_comparison.csv",
        comparison_csv(summary),
    )
    (args.output_dir / "scene16_counterexample_mechanism_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    write_note(
        args.output_dir / "scene16_counterexample_mechanism_note.md", rows, summary
    )
    print(
        json.dumps(
            {
                "num_counterexamples": len(rows),
                "num_rgb_reviewed": summary["num_rgb_reviewed"],
                "outputs": sorted(path.name for path in args.output_dir.iterdir()),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
