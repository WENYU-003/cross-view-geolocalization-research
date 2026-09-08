#!/usr/bin/env python3
"""Verify that candidate-provenance logging leaves full-pipeline outputs unchanged."""

from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np


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


def load_pickle(path: Path) -> dict:
    with path.open("rb") as handle:
        value = pickle.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict in {path}, got {type(value)}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-pkl", required=True, type=Path)
    parser.add_argument("--logged-pkl", required=True, type=Path)
    args = parser.parse_args()

    baseline = load_pickle(args.baseline_pkl)
    logged = load_pickle(args.logged_pkl)

    assert baseline["best_index"] == logged["best_index"], "best_index changed"
    assert baseline["pred_error"] == logged["pred_error"], "final pred_error changed"
    assert np.array_equal(
        np.asarray(baseline["inliers"]), np.asarray(logged["inliers"])
    ), "candidate inlier counts changed"

    provenance_dir = args.logged_pkl.parent / "candidate_provenance"
    query_result = json.loads((provenance_dir / "query_result.json").read_text())
    slots = sorted(provenance_dir.glob("slot_*"))
    assert len(slots) == 5, f"Expected 5 candidate records, found {len(slots)}"
    assert query_result["num_processed_candidates"] == 5
    assert query_result["best_index"] == logged["best_index"]
    assert query_result["final_pred_error_m"] == logged["pred_error"]
    assert query_result["inlier_counts"] == [int(value) for value in logged["inliers"]]

    for slot_index, slot_dir in enumerate(slots):
        result = json.loads((slot_dir / "result.json").read_text())
        assert result["candidate_slot"] == slot_index
        assert result["retrieval_rank"] == slot_index + 1
        assert result["ir_order_gallery_block_index"] == int(
            np.asarray(logged["IR_order"]).reshape(-1)[slot_index]
        )
        assert result["inlier_count"] == int(logged["inliers"][slot_index])
        assert result["location_error_m"] == logged["location_error_list"][slot_index]

        with np.load(slot_dir / "matches_and_pnp_inputs.npz", allow_pickle=False) as arrays:
            assert set(arrays.files) == REQUIRED_ARRAYS
            for name in arrays.files:
                if arrays[name].dtype.kind in "fc":
                    assert np.isfinite(arrays[name]).all(), f"{slot_dir.name}/{name} has NaN/Inf"

            valid = np.asarray(arrays["valid"], dtype=bool)
            assert len(arrays["uav_pts_match"]) == len(valid)
            assert len(arrays["ref_pts_match"]) == len(valid)
            assert len(arrays["uav_pts_original"]) == len(valid)
            assert len(arrays["ref_pts_patch"]) == len(valid)
            assert len(arrays["local_x"]) == len(valid)
            assert len(arrays["local_y"]) == len(valid)
            assert len(arrays["dsm_z"]) == len(valid)
            assert len(arrays["pnp_input_2d"]) == int(valid.sum())
            assert len(arrays["pnp_input_3d"]) == int(valid.sum())
            assert len(arrays["pnp_object_points"]) == int(valid.sum())

            inlier_indices = np.asarray(arrays["inlier_indices"]).reshape(-1)
            assert len(inlier_indices) == result["inlier_count"]
            assert np.all(inlier_indices >= 0)
            assert np.all(inlier_indices < len(arrays["pnp_input_2d"]))

    print(
        json.dumps(
            {
                "status": "PASS",
                "sample_id": logged.get("sample_id"),
                "candidate_records": len(slots),
                "best_index": logged["best_index"],
                "final_pred_error_m": logged["pred_error"],
                "inlier_counts": [int(value) for value in logged["inliers"]],
                "all_numeric_arrays_finite": True,
            }
        )
    )


if __name__ == "__main__":
    main()
