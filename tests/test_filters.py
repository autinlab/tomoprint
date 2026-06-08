"""Tests for heightmap conditioning filters."""

import numpy as np

from tomoprint.filters import (
    apply_invert,
    downsample_heightmap,
    gaussian_smooth,
    normalize_contrast,
)


def test_gaussian_sigma_zero_is_identity():
    a = np.random.default_rng(1).normal(size=(10, 12)).astype(np.float32)
    assert gaussian_smooth(a, 0) is a


def test_gaussian_reduces_variance():
    a = np.random.default_rng(1).normal(size=(64, 64)).astype(np.float32)
    assert gaussian_smooth(a, 2.0).var() < a.var()


def test_downsample_halves_shape_and_is_block_mean():
    a = np.arange(64, dtype=np.float32).reshape(8, 8)
    out = downsample_heightmap(a, 2)
    assert out.shape == (4, 4)
    assert out[0, 0] == np.mean([a[0, 0], a[0, 1], a[1, 0], a[1, 1]])


def test_downsample_bin_one_is_identity():
    a = np.zeros((5, 5), dtype=np.float32)
    assert downsample_heightmap(a, 1) is a


def test_normalize_contrast_range():
    a = np.linspace(-5, 5, 100).reshape(10, 10).astype(np.float32)
    out = normalize_contrast(a, 0, 100)
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert out.min() == 0.0 and out.max() == 1.0


def test_normalize_flat_input_is_zeros():
    a = np.full((4, 4), 3.0, dtype=np.float32)
    np.testing.assert_array_equal(normalize_contrast(a, 1, 99), np.zeros((4, 4), np.float32))


def test_invert_is_involution():
    a = np.linspace(0, 1, 16).reshape(4, 4).astype(np.float32)
    np.testing.assert_allclose(apply_invert(apply_invert(a, True), True), a, atol=1e-6)
    np.testing.assert_allclose(apply_invert(a, True), 1.0 - a, atol=1e-6)
    assert apply_invert(a, False) is a
