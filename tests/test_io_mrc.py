"""Tests for MRC loading and mesh export."""

from pathlib import Path

import numpy as np
import pytest

from tomoprint.exceptions import ValidationError
from tomoprint.io_mrc import load_volume, write_mesh
from tomoprint.mesh import build_relief_mesh

CAPSID_MRC = Path(__file__).resolve().parent.parent / "data" / "capsid_trim.mrc"


def test_load_promotes_2d(tmp_path):
    import mrcfile

    path = tmp_path / "img.mrc"
    with mrcfile.new(path, overwrite=True) as mrc:
        mrc.set_data(np.zeros((10, 12), dtype=np.float32))
        mrc.voxel_size = 4.0
    vol, voxel = load_volume(path)
    assert vol.shape == (1, 10, 12)
    assert vol.dtype == np.float32
    assert voxel == pytest.approx(4.0)


def test_load_missing_file_raises():
    with pytest.raises(ValidationError):
        load_volume("/no/such/file.mrc")


@pytest.mark.parametrize("ext", ["stl", "obj", "ply"])
def test_write_mesh_roundtrip(tmp_path, synthetic_heightmap, ext):
    import trimesh

    mesh = build_relief_mesh(synthetic_heightmap)
    out = tmp_path / f"mesh.{ext}"
    write_mesh(mesh, out)
    assert out.exists() and out.stat().st_size > 0
    reloaded = trimesh.load(out)
    assert len(reloaded.faces) > 0


def test_write_mesh_bad_format_raises(tmp_path, synthetic_heightmap):
    mesh = build_relief_mesh(synthetic_heightmap)
    with pytest.raises(ValidationError):
        write_mesh(mesh, tmp_path / "mesh.xyz")


@pytest.mark.needs_data
@pytest.mark.skipif(not CAPSID_MRC.exists(), reason="capsid_trim.mrc not present")
def test_load_capsid_header():
    vol, voxel = load_volume(CAPSID_MRC)
    assert vol.shape == (101, 121, 201)  # (Z, Y, X)
    assert vol.dtype == np.float32
    assert voxel == pytest.approx(8.0, abs=0.1)
