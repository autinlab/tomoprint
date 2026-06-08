"""A labelled slider paired with a (double) spin box, kept in sync. Used by ~all controls."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets


class LabeledSlider(QtWidgets.QWidget):
    """A horizontal slider + spin box that always agree. Emits ``valueChanged(float)``.

    Set ``decimals > 0`` for a floating-point control (the slider works on scaled integer ticks).
    """

    valueChanged = QtCore.Signal(float)

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        step: float = 1.0,
        decimals: int = 0,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._decimals = decimals
        self._scale = 10**decimals
        self._block = False

        self.label = QtWidgets.QLabel(label)
        self.label.setMinimumWidth(64)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(round(minimum * self._scale), round(maximum * self._scale))
        self.slider.setSingleStep(max(1, round(step * self._scale)))

        if decimals > 0:
            self.spin: QtWidgets.QAbstractSpinBox = QtWidgets.QDoubleSpinBox()
            self.spin.setDecimals(decimals)
        else:
            self.spin = QtWidgets.QSpinBox()
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.spin.setFixedWidth(72)

        self.set_value(value)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

        self.slider.valueChanged.connect(self._on_slider)
        self.spin.valueChanged.connect(self._on_spin)

    def value(self) -> float:
        return float(self.spin.value())

    def set_value(self, value: float) -> None:
        self._block = True
        self.slider.setValue(round(value * self._scale))
        self.spin.setValue(value if self._decimals else int(round(value)))
        self._block = False

    def set_maximum(self, maximum: float) -> None:
        self.slider.setMaximum(round(maximum * self._scale))
        self.spin.setMaximum(maximum)

    def _on_slider(self, ival: int) -> None:
        if self._block:
            return
        self._block = True
        val = ival / self._scale
        self.spin.setValue(val if self._decimals else int(round(val)))
        self._block = False
        self.valueChanged.emit(float(val))

    def _on_spin(self, val: float) -> None:
        if self._block:
            return
        self._block = True
        self.slider.setValue(round(float(val) * self._scale))
        self._block = False
        self.valueChanged.emit(float(val))
