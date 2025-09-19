from typing import Tuple
from types import SimpleNamespace
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QSize, QPointF, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

from .midi_io import MidiOut


class XYFaderWidget(QWidget):
    """Draggable XY pad that sends two MIDI CC values (X and Y) on the current channel.

    - Blue color scheme to match app
    - Optional Lock X / Lock Y buttons and Reset
    - Provides get/set for CC numbers and XY values to preserve across zoom
    """
    def __init__(self, midi_out: MidiOut, scale: float = 1.0, cc_x: int = 1, cc_y: int = 74):
        super().__init__()
        self.midi: MidiOut = midi_out
        self.port_name: str = ""
        try:
            self.ui_scale = float(scale) if float(scale) > 0 else 1.0
        except Exception:
            self.ui_scale = 1.0
        self.midi_channel: int = 0  # 0-based
        # CC assignments
        self.cc_x: int = int(max(0, min(127, cc_x)))
        self.cc_y: int = int(max(0, min(127, cc_y)))
        # current values 0..127 (center at 64)
        self.val_x: int = 64
        self.val_y: int = 64
        # locks
        self.lock_x = False
        self.lock_y = False
        # layout_model shim for title/size computations
        self.layout_model = SimpleNamespace(name="XY Fader", columns=10)
        self.setWindowTitle("XY Fader")
        try:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(int(10 * self.ui_scale), int(8 * self.ui_scale), int(10 * self.ui_scale), int(10 * self.ui_scale))
        root.setSpacing(int(10 * self.ui_scale))

        # Pad area widget (we paint directly on self for simplicity)
        # Header controls under pad
        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(int(16 * self.ui_scale))
        controls.addStretch()
        self.lock_x_btn = QPushButton("Lock X")
        self.lock_y_btn = QPushButton("Lock Y")
        self.reset_btn = QPushButton("RESET")
        for b in (self.lock_x_btn, self.lock_y_btn, self.reset_btn):
            b.setCursor(Qt.PointingHandCursor)
            try:
                b.setFixedHeight(int(28 * self.ui_scale))
            except Exception:
                pass
        try:
            toggle_qss = (
                "QPushButton { padding: 2px 8px; min-height: 0px; border-radius: 4px;\n"
                "  border: 1px solid #2f82e6; background-color: #1b1f24; color: #ddd; }\n"
                "QPushButton:hover { border: 1px solid #61b3ff; }\n"
                "QPushButton:checked { background-color: #2f82e6; color: white; }"
            )
            plain_qss = (
                "QPushButton { padding: 2px 8px; min-height: 0px; border-radius: 4px;\n"
                "  border: 1px solid #2f82e6; background-color: #1b1f24; color: #ddd; }\n"
                "QPushButton:hover { border: 1px solid #61b3ff; }\n"
            )
            self.lock_x_btn.setCheckable(True)
            self.lock_y_btn.setCheckable(True)
            self.lock_x_btn.setStyleSheet(toggle_qss)
            self.lock_y_btn.setStyleSheet(toggle_qss)
            self.reset_btn.setStyleSheet(plain_qss)
        except Exception:
            pass
        self.lock_x_btn.toggled.connect(lambda c: self._set_lock('x', c))
        self.lock_y_btn.toggled.connect(lambda c: self._set_lock('y', c))
        self.reset_btn.clicked.connect(self._reset_center)
        controls.addWidget(self.lock_x_btn)
        controls.addWidget(self.reset_btn)
        controls.addWidget(self.lock_y_btn)
        controls.addStretch()

        # Add a spacer where the pad will be; we paint in paintEvent at full area except bottom controls
        # We'll just keep the controls in the root and rely on sizeHint
        root.addStretch(1)
        root.addLayout(controls)

        self.setLayout(root)
        self.setMouseTracking(True)
        self._dragging = False
        self._press_pos: QPointF | None = None
        self._press_val_x: int | None = None
        self._press_val_y: int | None = None

    # ---- Painting ----
    def sizeHint(self) -> QSize:  # type: ignore[override]
        try:
            pad_side = int(420 * self.ui_scale)
            controls_h = int(48 * self.ui_scale)
            return QSize(pad_side + int(24 * self.ui_scale), pad_side + controls_h + int(24 * self.ui_scale))
        except Exception:
            return QSize(460, 480)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        return self.sizeHint()

    def _pad_rect(self) -> QRectF:
        # Compute square area for pad within widget rect, leaving space for controls at bottom
        w = self.width()
        h = self.height()
        try:
            controls_h = int(64 * self.ui_scale)
        except Exception:
            controls_h = 64
        side = min(w - 20, h - controls_h - 20)
        side = max(100, side)
        x = (w - side) / 2
        y = 10
        return QRectF(x, y, side, side)

    def paintEvent(self, _):  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Background
        p.fillRect(self.rect(), QColor('#0f1115'))
        # Pad
        pad = self._pad_rect()
        # Panel background
        p.setBrush(QColor('#181a1f'))
        p.setPen(QColor('#2a2f35'))
        p.drawRoundedRect(pad, 8, 8)
        # Grid lines (subtle)
        grid_pen = QPen(QColor('#2a2f35'))
        grid_pen.setWidth(1)
        p.setPen(grid_pen)
        steps = 10
        for i in range(1, steps):
            # vertical
            x = pad.left() + pad.width() * (i / steps)
            p.drawLine(int(x), int(pad.top()), int(x), int(pad.bottom()))
            # horizontal
            y = pad.top() + pad.height() * (i / steps)
            p.drawLine(int(pad.left()), int(y), int(pad.right()), int(y))
        # Cursor
        cx, cy = self._value_to_pos(self.val_x, self.val_y, pad)
        knob = QRectF(cx - 10, cy - 10, 20, 20)
        p.setBrush(QColor('#61b3ff'))
        p.setPen(QColor('#2f82e6'))
        p.drawRoundedRect(knob, 4, 4)
        p.end()

    # ---- Helpers ----
    def _pos_to_value(self, pt: QPointF, pad: QRectF) -> Tuple[int, int]:
        # map position within pad to 0..127 (x increases right, y increases up)
        fx = (pt.x() - pad.left()) / max(1.0, pad.width())
        fy = (pt.y() - pad.top()) / max(1.0, pad.height())
        fx = min(1.0, max(0.0, fx))
        fy = min(1.0, max(0.0, fy))
        vx = int(round(fx * 127))
        vy = int(round((1.0 - fy) * 127))
        return vx, vy

    def _value_to_pos(self, vx: int, vy: int, pad: QRectF) -> Tuple[float, float]:
        fx = min(1.0, max(0.0, vx / 127.0))
        fy = min(1.0, max(0.0, 1.0 - (vy / 127.0)))
        x = pad.left() + fx * pad.width()
        y = pad.top() + fy * pad.height()
        return x, y

    def mousePressEvent(self, ev):  # type: ignore[override]
        if ev.button() != Qt.LeftButton:
            return super().mousePressEvent(ev)
        self._dragging = True
        # Store reference point and current values; do not move yet
        self._press_pos = ev.position()
        self._press_val_x = int(self.val_x)
        self._press_val_y = int(self.val_y)

    def mouseMoveEvent(self, ev):  # type: ignore[override]
        if not self._dragging:
            return super().mouseMoveEvent(ev)
        # Relative drag from the press point -> value deltas across full pad span
        if self._press_pos is None or self._press_val_x is None or self._press_val_y is None:
            return super().mouseMoveEvent(ev)
        pad = self._pad_rect()
        # Compute deltas as fraction of pad
        dx = (ev.position().x() - self._press_pos.x()) / max(1.0, pad.width())
        dy = (ev.position().y() - self._press_pos.y()) / max(1.0, pad.height())
        dvx = int(round(dx * 127))
        dvy = int(round(-dy * 127))  # up increases value
        new_x = int(self._press_val_x) + dvx
        new_y = int(self._press_val_y) + dvy
        new_x = max(0, min(127, new_x))
        new_y = max(0, min(127, new_y))
        changed = False
        if not self.lock_x and new_x != self.val_x:
            self.val_x = new_x
            try:
                self.midi.cc(int(self.cc_x), int(self.val_x), self.midi_channel)
            except Exception:
                pass
            changed = True
        if not self.lock_y and new_y != self.val_y:
            self.val_y = new_y
            try:
                self.midi.cc(int(self.cc_y), int(self.val_y), self.midi_channel)
            except Exception:
                pass
            changed = True
        if changed:
            self.update()

    def mouseReleaseEvent(self, ev):  # type: ignore[override]
        if self._dragging:
            self._dragging = False
            self._press_pos = None
            self._press_val_x = None
            self._press_val_y = None
        return super().mouseReleaseEvent(ev)

    def _update_from_point(self, pt: QPointF):
        pad = self._pad_rect()
        vx, vy = self._pos_to_value(pt, pad)
        if not self.lock_x:
            self.val_x = vx
            try:
                self.midi.cc(int(self.cc_x), int(self.val_x), self.midi_channel)
            except Exception:
                pass
        if not self.lock_y:
            self.val_y = vy
            try:
                self.midi.cc(int(self.cc_y), int(self.val_y), self.midi_channel)
            except Exception:
                pass
        self.update()

    def _set_lock(self, axis: str, checked: bool):
        if axis == 'x':
            self.lock_x = bool(checked)
        elif axis == 'y':
            self.lock_y = bool(checked)

    def _reset_center(self):
        self.val_x = 64
        self.val_y = 64
        try:
            self.midi.cc(int(self.cc_x), int(self.val_x), self.midi_channel)
            self.midi.cc(int(self.cc_y), int(self.val_y), self.midi_channel)
        except Exception:
            pass
        self.update()

    # --- External API parity ---
    def set_channel(self, channel_1_based: int):
        try:
            self.midi_channel = max(1, min(16, int(channel_1_based))) - 1
        except Exception:
            self.midi_channel = 0

    def set_midi_out(self, midi: MidiOut, port_name: str = ""):
        try:
            self.midi = midi
        except Exception:
            pass
        try:
            self.port_name = str(port_name)
        except Exception:
            self.port_name = ""

    # CC config
    def get_cc_numbers(self) -> Tuple[int, int]:
        return int(self.cc_x), int(self.cc_y)

    def set_cc_numbers(self, ccx: int, ccy: int):
        try:
            self.cc_x = int(max(0, min(127, ccx)))
            self.cc_y = int(max(0, min(127, ccy)))
        except Exception:
            pass

    # Values
    def get_values(self) -> Tuple[int, int]:
        return int(self.val_x), int(self.val_y)

    def set_values(self, vx: int, vy: int, emit: bool = False):
        try:
            self.val_x = int(max(0, min(127, vx)))
            self.val_y = int(max(0, min(127, vy)))
            if emit:
                try:
                    self.midi.cc(int(self.cc_x), int(self.val_x), self.midi_channel)
                    self.midi.cc(int(self.cc_y), int(self.val_y), self.midi_channel)
                except Exception:
                    pass
            self.update()
        except Exception:
            pass
