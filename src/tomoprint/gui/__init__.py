"""Desktop GUI for tomoprint (PySide6 + embedded pyvista 3D viewport).

The GUI is a thin frontend: it only calls the pure pipeline in :mod:`tomoprint.pipeline` and
never duplicates algorithm logic. Launch with the ``tomoprint-gui`` console script or
``python -m tomoprint.gui.app``.
"""
