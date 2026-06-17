"""Tests for the GUI's VTK-free worker compute functions (no event loop needed)."""

import numpy as np
import pytest

pytest.importorskip("PySide6")

from tomoprint.gui.workers import build_mesh_payload, export_to_file  # noqa: E402
from tomoprint.params import (  # noqa: E402
    CropParams,
    GeometryParams,
    JigsawParams,
    MeshParams,
)

pytestmark = pytest.mark.gui


def _hm():
    yy, xx = np.mgrid[0:40, 0:60]
    return np.exp(-(((yy - 20) / 8) ** 2 + ((xx - 30) / 8) ** 2)).astype(np.float32)


def test_build_payload_is_watertight():
    payload = build_mesh_payload(_hm(), GeometryParams(), MeshParams(), 8.0)
    assert payload.diagnostics["watertight"] is True
    assert payload.points.shape[1] == 3
    assert payload.faces.shape[1] == 3
    assert payload.scalars.shape[0] == payload.points.shape[0]
    assert payload.preview is False


def test_preview_cap_reduces_resolution():
    big = np.zeros((600, 400), dtype=np.float32)
    full = build_mesh_payload(big, GeometryParams(), MeshParams(), 8.0)
    prev = build_mesh_payload(big, GeometryParams(), MeshParams(), 8.0, preview_cap=200)
    assert prev.preview is True
    assert prev.points.shape[0] < full.points.shape[0]


def test_export_writes_watertight_file(tmp_path):
    out = tmp_path / "relief.stl"
    diag = export_to_file(_hm(), GeometryParams(), MeshParams(), 8.0, str(out), "stl")
    assert out.exists() and out.stat().st_size > 0
    assert diag["watertight"] is True
    assert diag["path"] == str(out)


def test_export_jigsaw_writes_multi_body_file(tmp_path):
    out = tmp_path / "puzzle.stl"
    diag = export_to_file(
        _hm(), GeometryParams(), MeshParams(), 8.0, str(out), "stl",
        crop=CropParams(enabled=True, shape="ellipse"),
        jigsaw=JigsawParams(enabled=True, cols=3, rows=2, seed=0),
    )
    assert out.exists() and out.stat().st_size > 0
    assert diag["watertight"] is True
    assert diag["n_pieces"] == 6
