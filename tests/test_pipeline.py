"""Tests for pipeline orchestration and helpers."""

import pytest

from tomoprint.params import (
    CropParams,
    FilterParams,
    GeometryParams,
    JigsawParams,
    MeshParams,
    ReduceParams,
)
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
        progress=lambda msg, frac: seen.append(frac),
    )
    assert seen == sorted(seen)
    assert all(0.0 <= f <= 1.0 for f in seen)
    assert seen[-1] == pytest.approx(1.0)


def test_crop_changes_heightmap_shape(synthetic_volume):
    full = compute_heightmap_2d(synthetic_volume, ReduceParams(), FilterParams())
    cropped = compute_heightmap_2d(
        synthetic_volume,
        ReduceParams(),
        FilterParams(),
        CropParams(enabled=True, shape="rect", width=0.5, height=0.5),
    )
    assert cropped.shape[0] < full.shape[0] and cropped.shape[1] < full.shape[1]


@pytest.mark.slow
def test_ellipse_crop_yields_watertight_shaped_plate(synthetic_volume):
    mesh, diag = run_pipeline(
        synthetic_volume, 8.0, ReduceParams(mode="mean"), FilterParams(),
        GeometryParams(footprint_mm=100), MeshParams(),
        crop_p=CropParams(enabled=True, shape="ellipse", width=0.8, height=0.6),
    )
    assert diag["watertight"] is True
    assert mesh.body_count == 1
    assert mesh.volume > 0


@pytest.mark.slow
def test_jigsaw_yields_multi_body_watertight_mesh(synthetic_volume):
    mesh, diag = run_pipeline(
        synthetic_volume, 8.0, ReduceParams(mode="mean"), FilterParams(),
        GeometryParams(footprint_mm=100), MeshParams(),
        jigsaw_p=JigsawParams(enabled=True, cols=3, rows=2, seed=0),
    )
    assert diag["watertight"] is True
    assert diag["n_pieces"] == 6
    assert mesh.body_count == 6


def test_suggest_bin_factors():
    assert suggest_bin_factor((200, 100)) == 1
    assert suggest_bin_factor((601, 427), max_dim=256) == 3
    assert suggest_export_bin((601, 427)) == 2
    assert suggest_export_bin((121, 201)) == 1
