"""Tests for the heightmap crop (bbox slicing, shape masks, mm outline, contrast masking)."""

import numpy as np
import pytest

from tomoprint import crop
from tomoprint.exceptions import ValidationError
from tomoprint.filters import normalize_contrast
from tomoprint.params import CropParams


def test_disabled_crop_is_noop():
    hm = np.arange(50, dtype=np.float32).reshape(5, 10)
    assert crop.crop_heightmap(hm, CropParams(enabled=False)) is hm


def test_rect_crop_slices_to_bbox():
    hm = np.zeros((100, 80), dtype=np.float32)
    p = CropParams(enabled=True, shape="rect", cx=0.5, cy=0.5, width=0.6, height=0.4)
    out = crop.crop_heightmap(hm, p)
    assert out.shape == (40, 48)  # 0.4*100, 0.6*80


def test_rect_crop_has_no_mask():
    p = CropParams(enabled=True, shape="rect")
    assert crop.shape_mask(p, 20, 20) is None
    assert crop.outline_polygon_mm(p, (20, 20), 1.0, 1.0) is None


def test_crop_bbox_clamped_to_unit_square():
    p = CropParams(enabled=True, shape="rect", cx=0.9, cy=0.1, width=0.5, height=0.5)
    x0, y0, x1, y1 = crop.crop_bbox_norm(p)
    assert 0.0 <= x0 < x1 <= 1.0
    assert 0.0 <= y0 < y1 <= 1.0
    assert x1 == pytest.approx(1.0)  # right edge clamped


def test_ellipse_mask_fraction_near_pi_over_4():
    p = CropParams(enabled=True, shape="ellipse")
    mask = crop.shape_mask(p, 200, 200)
    assert mask.mean() == pytest.approx(np.pi / 4, abs=0.02)


def test_ellipse_outline_area_matches_formula():
    p = CropParams(enabled=True, shape="ellipse")
    poly = crop.outline_polygon_mm(p, (41, 61), 1.0, 1.0)  # ex=60, ey=40 => a=30, b=20
    assert poly.is_valid
    assert poly.area == pytest.approx(np.pi * 30 * 20, rel=0.01)


def test_polygon_crop_mask_and_outline():
    poly_pts = ((0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75))  # a square
    p = CropParams(enabled=True, shape="polygon", polygon=poly_pts)
    out = crop.crop_heightmap(np.zeros((100, 100), np.float32), p)
    assert out.shape == (50, 50)
    mask = crop.shape_mask(p, *out.shape)
    assert mask.mean() == pytest.approx(1.0, abs=0.05)  # square fills its own bbox
    outline = crop.outline_polygon_mm(p, out.shape, 1.0, 1.0)
    assert outline.is_valid and outline.area > 0


def test_normalize_contrast_mask_uses_in_shape_percentiles():
    hm = np.zeros((10, 10), dtype=np.float32)
    hm[:, :5] = np.linspace(0, 1, 50).reshape(10, 5)  # signal on the left half
    hm[:, 5:] = 1000.0  # outliers we want to ignore
    mask = np.zeros((10, 10), dtype=bool)
    mask[:, :5] = True
    out = normalize_contrast(hm, 0, 100, mask=mask)
    # masked region spans its full range; without the mask the 1000s would dominate
    assert out[:, :5].max() == pytest.approx(1.0)
    assert normalize_contrast(hm, 0, 100)[:, :5].max() < 0.01


def test_invalid_polygon_too_few_points():
    with pytest.raises(ValidationError):
        CropParams(enabled=True, shape="polygon", polygon=((0.1, 0.1), (0.9, 0.9)))


def test_invalid_size_out_of_range():
    with pytest.raises(ValidationError):
        CropParams(width=1.5)
