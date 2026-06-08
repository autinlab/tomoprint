"""Tests for the GUI settings <-> core params bridge and JSON presets (no Qt needed)."""

import pytest

from tomoprint.gui.settings import ReliefSettings


def test_settings_to_params_defaults():
    s = ReliefSettings()
    assert s.reduce_params().mode == "slice"
    assert s.filter_params().bin_factor == 1
    assert s.geometry_params().footprint_mm == 200.0
    assert s.mesh_params().decimate_fraction is None  # 0% reduction => no decimation


def test_decimate_percent_maps_to_fraction():
    s = ReliefSettings(decimate_percent=60.0)
    assert s.mesh_params().decimate_fraction == pytest.approx(0.4)


def test_preset_json_roundtrip(tmp_path):
    s = ReliefSettings(mode="min", index=42, relief_depth_mm=8.0, invert=True, source_path="x.mrc")
    path = tmp_path / "preset.json"
    s.to_json(path)
    loaded = ReliefSettings.from_json(path)
    assert loaded.mode == "min"
    assert loaded.index == 42
    assert loaded.relief_depth_mm == 8.0
    assert loaded.invert is True
    assert loaded.source_path == "x.mrc"


def test_from_json_ignores_unknown_keys(tmp_path):
    path = tmp_path / "p.json"
    path.write_text('{"schema_version": 1, "mode": "max", "bogus_key": 123}')
    loaded = ReliefSettings.from_json(path)
    assert loaded.mode == "max"
