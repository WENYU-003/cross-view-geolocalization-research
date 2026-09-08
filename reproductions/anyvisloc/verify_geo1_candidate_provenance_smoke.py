#!/usr/bin/env python3
"""Verify candidate-provenance integrity without assuming deterministic PnP runs."""

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


def sample_id(record: dict, path: Path) -> str:
    value = record.get("sample_id")
    if value is not None:
        return str(value)
    stem = path.stem
    return stem[len("VG_data_"):] if stem.startswith("VG_data_") else stem


def assert_equal_value(actual, expected, message: str) -> None:
    if actual is None or expected is None:
        assert actual is expected, message
    else:
        assert actual == expected, message


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-pkl", required=True, type=Path)
    parser.add_argument("--logged-pkl", required=True, type=Path)
    args = parser.parse_args()

    baseline = load_pickle(args.baseline_pkl)
    logged = load_pickle(args.logged_pkl)

    baseline_sample_id = sample_id(baseline, args.baseline_pkl)
    logged_sample_id = sample_id(logged, args.logged_pkl)
    assert baseline_sample_id == logged_sample_id, "baseline/logged sample id differs"

    baseline_ir_order = np.asarray(baseline["IR_order"]).reshape(-1)
    logged_ir_order = np.asarray(logged["IR_order"]).reshape(-1)
    assert len(baseline_ir_order) >= 5 and len(logged_ir_order) >= 5
    assert np.array_equal(
        baseline_ir_order[:5], logged_ir_order[:5]
    ), "baseline/logged IR_order top5 differs"

    disabled_provenance_dir = args.baseline_pkl.parent / "candidate_provenance"
    assert not disabled_provenance_dir.exists(), (
        "logging-disabled control unexpectedly contains candidate_provenance"
    )

    provenance_dir = args.logged_pkl.parent / "candidate_provenance"
    query_result = json.loads((provenance_dir / "query_result.json").read_text())
    slots = sorted(provenance_dir.glob("slot_*"))
    assert len(slots) == 5, f"Expected 5 candidate records, found {len(slots)}"
    assert [slot.name for slot in slots] == [f"slot_{index:02d}" for index in range(5)]
    assert query_result["num_processed_candidates"] == 5
    assert str(query_result["sample_id"]) == logged_sample_id
    assert query_result["best_index"] == logged["best_index"]
    assert_equal_value(
        query_result["final_pred_error_m"], logged["pred_error"],
        "query_result/logged pred_error differs",
    )
    assert query_result["inlier_counts"] == [int(value) for value in logged["inliers"]]
    assert query_result["location_error_list"] == logged["location_error_list"]
    assert query_result["pnp_success"] == bool(logged["pnp_success"])

    logged_inliers = [int(value) for value in logged["inliers"]]
    assert len(logged_inliers) == 5
    assert len(logged["XYZ_list"]) == 5
    assert len(logged["location_error_list"]) == 5
    assert len(logged["row_starts"]) >= 5 and len(logged["col_starts"]) >= 5

    best_index = logged["best_index"]
    selected = query_result["selected_candidate"]
    if best_index is None:
        assert selected is None
    else:
        best_index = int(best_index)
        assert 0 <= best_index < 5
        assert best_index == int(np.argmax(np.asarray(logged_inliers)))
        assert_equal_value(
            logged["pred_error"], logged["location_error_list"][best_index],
            "logged pred_error does not match selected candidate",
        )
        assert selected["candidate_slot"] == best_index
        assert selected["retrieval_rank"] == best_index + 1
        assert selected["ir_order_gallery_block_index"] == int(logged_ir_order[best_index])
        assert selected["inlier_count"] == int(logged["inliers"][best_index])
        assert_equal_value(
            selected["location_error_m"], logged["location_error_list"][best_index],
            "selected/logged location error differs",
        )

    for slot_index, slot_dir in enumerate(slots):
        result = json.loads((slot_dir / "result.json").read_text())
        assert str(result["sample_id"]) == logged_sample_id
        assert result["candidate_slot"] == slot_index
        assert result["retrieval_rank"] == slot_index + 1
        assert result["ir_order_gallery_block_index"] == int(logged_ir_order[slot_index])
        assert result["row_start"] == int(logged["row_starts"][slot_index])
        assert result["col_start"] == int(logged["col_starts"][slot_index])
        assert result["patch_h"] == int(logged["patch_h"])
        assert result["patch_w"] == int(logged["patch_w"])
        assert result["inlier_count"] == int(logged["inliers"][slot_index])
        assert_equal_value(
            result["location_error_m"], logged["location_error_list"][slot_index],
            f"{slot_dir.name} result/logged location error differs",
        )

        pose = logged["XYZ_list"][slot_index]
        assert_equal_value(result["pred_x"], pose.get("X"), f"{slot_dir.name} pred_x differs")
        assert_equal_value(result["pred_y"], pose.get("Y"), f"{slot_dir.name} pred_y differs")
        assert_equal_value(result["pred_z"], pose.get("Z"), f"{slot_dir.name} pred_z differs")
        expected_pnp_success = (
            pose.get("X") is not None
            and pose.get("Y") is not None
            and int(logged["inliers"][slot_index]) > 0
        )
        assert result["pnp_success"] == expected_pnp_success

        npz_path = slot_dir / "matches_and_pnp_inputs.npz"
        assert Path(result["artifact"]).name == npz_path.name
        with np.load(npz_path, allow_pickle=False) as arrays:
            assert set(arrays.files) == REQUIRED_ARRAYS
            for name in arrays.files:
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
            assert result["num_matches"] == len(arrays["ref_pts_match"])
            assert result["num_pnp_input"] == int(valid.sum())
            assert np.array_equal(
                arrays["pnp_input_3d"][:, [0, 2]],
                arrays["pnp_object_points"][:, [0, 2]],
            )
            assert np.array_equal(
                -arrays["pnp_input_3d"][:, 1], arrays["pnp_object_points"][:, 1]
            )

            inlier_indices = np.asarray(arrays["inlier_indices"]).reshape(-1)
            assert len(inlier_indices) == result["inlier_count"]
            assert np.all(inlier_indices >= 0)
            assert np.all(inlier_indices < len(arrays["pnp_input_2d"]))

    print(
        json.dumps(
            {
                "status": "PASS",
                "sample_id": logged_sample_id,
                "ir_order_top5": [int(value) for value in logged_ir_order[:5]],
                "candidate_records": len(slots),
                "baseline_best_index": baseline.get("best_index"),
                "logged_best_index": logged.get("best_index"),
                "baseline_pred_error_m": baseline.get("pred_error"),
                "logged_pred_error_m": logged.get("pred_error"),
                "all_numeric_arrays_finite": True,
                "cross_run_numeric_equality_required": False,
            }
        )
    )


if __name__ == "__main__":
    main()
