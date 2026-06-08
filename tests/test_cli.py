"""Tests for the typer CLI."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from tomoprint.cli import app

runner = CliRunner()
CAPSID_MRC = Path(__file__).resolve().parent.parent / "data" / "capsid_trim.mrc"


def test_cli_synthetic_roundtrip(tmp_path, synthetic_mrc):
    import trimesh

    out = tmp_path / "out.stl"
    result = runner.invoke(app, [str(synthetic_mrc), str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
    assert trimesh.load(out).is_watertight


def test_cli_rejects_bad_mode(tmp_path, synthetic_mrc):
    out = tmp_path / "out.stl"
    result = runner.invoke(app, [str(synthetic_mrc), str(out), "--mode", "bogus"])
    assert result.exit_code != 0


@pytest.mark.slow
@pytest.mark.needs_data
@pytest.mark.skipif(not CAPSID_MRC.exists(), reason="capsid_trim.mrc not present")
def test_cli_capsid_end_to_end(tmp_path):
    import trimesh

    out = tmp_path / "capsid.stl"
    result = runner.invoke(app, [str(CAPSID_MRC), str(out), "--report"])
    assert result.exit_code == 0, result.output
    mesh = trimesh.load(out)
    assert mesh.is_watertight
    ext = mesh.bounds[1] - mesh.bounds[0]
    assert max(ext[0], ext[1]) == pytest.approx(200.0, rel=0.02)  # footprint longest side
    assert ext[2] == pytest.approx(8.0, rel=0.05)  # base 2 mm + relief 6 mm
