"""Application entry point for the tomoprint desktop GUI (``tomoprint-gui``)."""

from __future__ import annotations

import sys


def main() -> None:
    """Configure the surface format / high-DPI policy, then launch the main window."""
    from PySide6 import QtCore, QtGui, QtWidgets

    # Must be set BEFORE the QApplication is created.
    QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    fmt = QtGui.QSurfaceFormat()
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    QtGui.QSurfaceFormat.setDefaultFormat(fmt)

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    app.setApplicationName("tomoprint")
    app.setApplicationDisplayName("tomoprint")

    from tomoprint.gui.main_window import MainWindow

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
