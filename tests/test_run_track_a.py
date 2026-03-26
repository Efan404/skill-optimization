"""Tests for the dedicated ORQA Track A runner."""

from src.run_track_a import TRACK_A_CONDITIONS, build_track_a_metadata


def test_track_a_condition_order():
    """Track A should evaluate only baseline, scaffold, v1, A1, and A2."""
    assert TRACK_A_CONDITIONS == [
        "baseline",
        "generic_scaffold",
        "v1_curated",
        "v1_component_minimal",
        "v1_component_enriched",
    ]


def test_track_a_conditions_exclude_phase1_generation_and_optimization():
    """Track A should not run v0 self-generation or v2 optimization."""
    assert "v0_self_generated" not in TRACK_A_CONDITIONS
    assert "v2_optimized" not in TRACK_A_CONDITIONS


def test_build_track_a_metadata_uses_track_a_conditions():
    """Metadata should record the exact Track A condition set."""
    metadata = build_track_a_metadata(
        run_id="track_a_test",
        model_name="step_2_mini",
        git_commit="abc123",
        data_digest="sha256:test",
        split_counts={"seed": 5, "dev": 25, "test": 20},
        dataset_label="ORQA subset",
    )
    assert metadata["conditions_run"] == TRACK_A_CONDITIONS
    assert metadata["model"] == "step_2_mini"
    assert metadata["run_id"] == "track_a_test"
