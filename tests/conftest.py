"""Shared pytest fixtures: tiny synthetic arrays so unit tests never need real MRC files."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tomoprint.heightmap import map_to_height
from tomoprint.params import GeometryParams

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CAPSID_MRC = DATA_DIR / "capsid_trim.mrc"


@pytest.fixture
def synthetic_volume() -> np.ndarray:
    """A small (Z, Y, X) = (8, 16, 24) volume with a low-value blob in the central slices."""
    rng = np.random.default_rng(0)
    vol = rng.normal(0.0, 0.01, size=(8, 16, 24)).astype(np.float32)
    vol[3:5, 6:10, 10:16] -= 0.2  # dense "feature" at low values
    return vol


@pytest.fixture
def synthetic_mrc(tmp_path: Path, synthetic_volume: np.ndarray) -> Path:
    """Write the synthetic volume to a real .mrc so the CLI can be exercised without sample data."""
    import mrcfile

    path = tmp_path / "synthetic.mrc"
    with mrcfile.new(path, overwrite=True) as mrc:
        mrc.set_data(synthetic_volume)
        mrc.voxel_size = 8.0
    return path


@pytest.fixture
def synthetic_heightmap():
    """A 5x7 gaussian bump mapped to physical mm (relief 4 mm, base 2 mm, footprint 20 mm)."""
    h, w = 5, 7
    yy, xx = np.mgrid[0:h, 0:w]
    z01 = np.exp(-(((yy - 2) / 1.5) ** 2 + ((xx - 3) / 1.5) ** 2)).astype(np.float32)
    geo = GeometryParams(footprint_mm=20.0, relief_depth_mm=4.0, base_thickness_mm=2.0)
    return map_to_height(z01, geo, voxel_size_a=8.0)


@pytest.fixture
def flat_heightmap():
    """A flat (zero-relief) plate -> an exact rectangular box for analytic volume checks."""
    z01 = np.zeros((6, 9), dtype=np.float32)
    geo = GeometryParams(footprint_mm=10.0, relief_depth_mm=5.0, base_thickness_mm=2.0)
    return map_to_height(z01, geo, voxel_size_a=8.0)
