"""Tests for the 0..1 -> physical-mm mapping."""

import numpy as np
import pytest

from tomoprint.exceptions import ValidationError
from tomoprint.heightmap import map_to_height
from tomoprint.params import GeometryParams


def test_height_range_and_base():
    z01 = np.linspace(0, 1, 12).reshape(3, 4).astype(np.float32)
    geo = GeometryParams(footprint_mm=100, relief_depth_mm=6, base_thickness_mm=2)
    hm = map_to_height(z01, geo, voxel_size_a=8.0)
    assert hm.z.min() == pytest.approx(2.0)  # base where z01 == 0
    assert hm.z.max() == pytest.approx(8.0)  # base + relief where z01 == 1


def test_longest_side_equals_footprint_and_square_pixels():
    z01 = np.zeros((5, 9), dtype=np.float32)  # W=9 is the longest side
    geo = GeometryParams(footprint_mm=200, relief_depth_mm=6, base_thickness_mm=2)
    hm = map_to_height(z01, geo, voxel_size_a=8.0)
    ext_x, ext_y = hm.extent_mm
    assert ext_x == pytest.approx(200.0)  # longest side scaled exactly to footprint
    assert hm.dx_mm == pytest.approx(hm.dy_mm)  # isotropic source -> square pixels
    assert ext_y < ext_x


def test_too_small_raises():
    geo = GeometryParams()
    with pytest.raises(ValidationError):
        map_to_height(np.zeros((1, 5), dtype=np.float32), geo, 8.0)
