"""The critical watertight/manifold gate for the relief solid."""

import numpy as np
import pytest

from tomoprint.exceptions import ValidationError
from tomoprint.mesh import build_relief_mesh, decimate_mesh, repair_mesh, verify_watertight
from tomoprint.params import GeometryParams


def test_relief_solid_is_watertight(synthetic_heightmap):
    mesh = build_relief_mesh(synthetic_heightmap)
    diag = verify_watertight(mesh)
    assert diag["watertight"] is True
    assert diag["winding_consistent"] is True
    assert diag["euler_number"] == 2  # genus-0 closed solid
    assert diag["volume_mm3"] > 0  # outward normals

    h, w = synthetic_heightmap.z.shape
    expected = 4 * (h - 1) * (w - 1) + 4 * (h + w - 2)
    assert diag["n_faces"] == expected
    assert diag["n_vertices"] == 2 * h * w


def test_height_range(synthetic_heightmap):
    mesh = build_relief_mesh(synthetic_heightmap)
    z = mesh.vertices[:, 2]
    assert z.min() == pytest.approx(0.0)  # flat bottom
    assert z.max() == pytest.approx(6.0, abs=1e-4)  # base(2) + relief(4) * peak(1)


def test_flat_plate_volume_is_exact(flat_heightmap):
    mesh = build_relief_mesh(flat_heightmap)
    ext_x, ext_y = flat_heightmap.extent_mm
    expected = ext_x * ext_y * flat_heightmap.base_thickness_mm
    assert mesh.volume == pytest.approx(expected, rel=1e-4)


def test_watertight_after_decimate(synthetic_heightmap):
    mesh = build_relief_mesh(synthetic_heightmap)
    small = decimate_mesh(mesh, fraction=0.5, target_faces=None)
    small = repair_mesh(small)
    diag = verify_watertight(small)
    assert diag["watertight"] is True
    assert diag["winding_consistent"] is True


def test_base_zero_rejected():
    with pytest.raises(ValidationError):
        GeometryParams(base_thickness_mm=0.0)


def test_inverted_heightmap_mirrors_relief():
    z01 = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
    geo = GeometryParams(footprint_mm=10, relief_depth_mm=4, base_thickness_mm=2)
    from tomoprint.filters import apply_invert
    from tomoprint.heightmap import map_to_height

    normal = build_relief_mesh(map_to_height(z01, geo, 8.0))
    inverted = build_relief_mesh(map_to_height(apply_invert(z01, True), geo, 8.0))
    # peak of one is the valley of the other; total z-range identical
    assert normal.vertices[:, 2].max() == pytest.approx(inverted.vertices[:, 2].max())
