"""Offscreen smoke test for the GUI controller: threaded rebuild + signals end to end."""

import os
import time

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6 import QtWidgets  # noqa: E402

from tomoprint.gui.controller import Controller  # noqa: E402
from tomoprint.gui.settings import ReliefSettings  # noqa: E402

pytestmark = [pytest.mark.gui, pytest.mark.slow]


def _spin(app, predicate, timeout=20.0):
    deadline = time.time() + timeout
    while not predicate() and time.time() < deadline:
        app.processEvents()
        time.sleep(0.01)


def test_controller_build_and_export(synthetic_volume, tmp_path):
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    controller = Controller()
    state: dict = {}
    controller.meshReady.connect(lambda p: state.__setitem__("payload", p))
    controller.heightmapReady.connect(lambda hm: state.__setitem__("hm", hm))
    controller.errorOccurred.connect(lambda m: state.__setitem__("error", m))
    controller.exportFinished.connect(lambda d: state.__setitem__("export", d))

    controller.set_volume(synthetic_volume, 8.0, "synthetic.mrc", ReliefSettings())
    _spin(app, lambda: "payload" in state or "error" in state)

    assert "error" not in state, state.get("error")
    assert "hm" in state and state["hm"].ndim == 2
    payload = state["payload"]
    assert payload.diagnostics["watertight"] is True

    out = tmp_path / "out.stl"
    controller.export(str(out), "stl")
    _spin(app, lambda: "export" in state or "error" in state)
    assert "error" not in state, state.get("error")
    assert out.exists()
    assert state["export"]["watertight"] is True
