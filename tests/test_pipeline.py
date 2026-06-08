"""Tests for pipeline orchestration and helpers."""

import pytest

from tomoprint.params import FilterParams, GeometryParams, MeshParams, ReduceParams
from tomoprint.pipeline import (
    compute_heightmap_2d,
    run_pipeline,
    suggest_bin_factor,
    suggest_export_bin,
)


def test_compute_heightmap_2d_range(synthetic_volume):
    hm = compute_heightmap_2d(synthetic_volume, ReduceParams(), FilterParams())
    assert hm.ndim == 2
    assert hm.min() >= 0.0 and hm.max() <= 1.0


def test_run_pipeline_is_watertight(synthetic_volume):
    mesh, diag = run_pipeline(
        synthetic_volume, 8.0, ReduceParams(), FilterParams(), GeometryParams(), MeshParams()
    )
    assert diag["watertight"] is True
    assert diag["n_faces"] > 0
    assert mesh.volume > 0


def test_progress_is_monotonic(synthetic_volume):
    seen: list[float] = []
    run_pipeline(
        synthetic_volume, 8.0, ReduceParams(), FilterParams(), GeometryParams(), MeshParams(),
        lambda msg, frac: seen.append(frac),
    )
    assert seen == sorted(seen)
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen[-1] == pytest.approx(1.0)


def test_suggest_bin_factors():
    assert suggest_bin_factor((200, 100)) == 1
    assert suggest_bin_factor((601, 427), max_dim=256) == 3
    assert suggest_export_bin((601, 427)) == 2
    assert suggest_export_bin((121, 201)) == 1
