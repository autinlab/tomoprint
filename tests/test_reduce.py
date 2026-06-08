"""Tests for 3D->2D reduction."""

import numpy as np

from tomoprint.params import ReduceParams
from tomoprint.reduce import reduce_to_heightmap, resolve_slice_index


def test_resolve_slice_index():
    assert resolve_slice_index(101, -1) == 50  # negative -> middle
    assert resolve_slice_index(10, 3) == 3
    assert resolve_slice_index(10, 999) == 9  # clamped to last


def test_slice_mode_returns_exact_slice(synthetic_volume):
    hm = reduce_to_heightmap(synthetic_volume, ReduceParams(mode="slice", index=4, axis=0))
    np.testing.assert_array_equal(hm, synthetic_volume[4])
    assert hm.shape == synthetic_volume.shape[1:]


def test_slab_mean_zero_thickness_equals_slice(synthetic_volume):
    p = ReduceParams(mode="slab_mean", index=4, half_thickness=0, axis=0)
    hm = reduce_to_heightmap(synthetic_volume, p)
    np.testing.assert_allclose(hm, synthetic_volume[4], rtol=1e-6)


def test_projections_match_numpy(synthetic_volume):
    center, n = 4, 2
    lo, hi = center - n, center + n
    slab = synthetic_volume[lo : hi + 1]
    for mode, ref in (("min", slab.min(0)), ("mean", slab.mean(0)), ("max", slab.max(0))):
        p = ReduceParams(mode=mode, index=center, half_thickness=n, axis=0)
        np.testing.assert_allclose(reduce_to_heightmap(synthetic_volume, p), ref, rtol=1e-6)


def test_slab_clamps_to_bounds(synthetic_volume):
    # half_thickness larger than the volume should clamp, not error
    p = ReduceParams(mode="mean", index=0, half_thickness=100, axis=0)
    hm = reduce_to_heightmap(synthetic_volume, p)
    np.testing.assert_allclose(hm, synthetic_volume.mean(0), rtol=1e-6)
