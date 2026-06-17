"""Tests for jigsaw piece partitioning and the 3D piece cut."""

import pytest

from tomoprint import jigsaw
from tomoprint.exceptions import ValidationError
from tomoprint.mesh import build_relief_mesh, verify_watertight
from tomoprint.params import JigsawParams


@pytest.fixture
def rect_outline():
    from shapely.geometry import box

    return box(0.0, 0.0, 200.0, 150.0)


def test_piece_count_matches_grid(rect_outline):
    polys = jigsaw.piece_polygons(rect_outline, JigsawParams(enabled=True, cols=4, rows=3, seed=0))
    assert len(polys) == 12


def test_pieces_tile_outline_within_kerf(rect_outline):
    p = JigsawParams(enabled=True, cols=4, rows=3, seed=1, kerf_mm=0.0)
    polys = jigsaw.piece_polygons(rect_outline, p)
    total = sum(poly.area for poly in polys)
    assert total == pytest.approx(rect_outline.area, rel=1e-6)  # exact tiling, no kerf


def test_kerf_shrinks_total_area(rect_outline):
    no_kerf = JigsawParams(enabled=True, seed=2, kerf_mm=0.0)
    with_kerf = JigsawParams(enabled=True, seed=2, kerf_mm=0.6)
    base = sum(p.area for p in jigsaw.piece_polygons(rect_outline, no_kerf))
    kerfed = sum(p.area for p in jigsaw.piece_polygons(rect_outline, with_kerf))
    assert kerfed < base


def test_all_pieces_are_valid_simple_polygons(rect_outline):
    polys = jigsaw.piece_polygons(rect_outline, JigsawParams(enabled=True, cols=5, rows=4, seed=3))
    assert all(poly.is_valid and poly.geom_type == "Polygon" for poly in polys)


def test_single_column_and_row(rect_outline):
    polys = jigsaw.piece_polygons(rect_outline, JigsawParams(enabled=True, cols=1, rows=1))
    assert len(polys) == 1


def test_invalid_params():
    with pytest.raises(ValidationError):
        JigsawParams(cols=0)
    with pytest.raises(ValidationError):
        JigsawParams(tab_size=0.8)


def test_cut_pieces_are_watertight(synthetic_heightmap):
    mesh = build_relief_mesh(synthetic_heightmap)
    from shapely.geometry import box

    (minx, miny), (maxx, maxy) = mesh.bounds[0][:2], mesh.bounds[1][:2]
    outline = box(minx, miny, maxx, maxy)
    polys = jigsaw.piece_polygons(outline, JigsawParams(enabled=True, cols=2, rows=2, seed=0))
    z_hi = float(mesh.vertices[:, 2].max())
    pieces = jigsaw.cut_mesh_into_pieces(mesh, polys, 0.0, z_hi)
    assert len(pieces) >= 4
    assert all(verify_watertight(p)["watertight"] for p in pieces)
    # total volume close to the uncut plate (minus the kerf gaps)
    assert sum(p.volume for p in pieces) == pytest.approx(mesh.volume, rel=0.1)
