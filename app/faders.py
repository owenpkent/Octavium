from typing import List
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider, QSizePolicy
)
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor

from .midi_io import MidiOut
from types import SimpleNamespace
from .keyboard_widget import DragReferenceSlider


class FadersWidget(QWidget):
    """A simple 4-channel faders surface with per-channel CC sliders and bottom buttons.

    - 4 vertical faders mapped to MIDI CC by default: [1, 7, 74, 10]
    - Live sends CC on value change on the current channel
    - 4 bottom buttons send Note On/Off (C4..D#4) as momentary triggers
    - Has a compact header with an "All Notes Off" safety button
    - Scales with the same ui_scale convention as other widgets
    """
    def __init__(self, midi_out: MidiOut, scale: float = 1.0, cc_numbers: List[int] | None = None):
        super().__init__()
        self.midi: MidiOut = midi_out
        self.port_name: str = ""
        try:
            self.ui_scale = float(scale) if float(scale) > 0 else 1.0
        except Exception:
            self.ui_scale = 1.0
        self.midi_channel: int = 0  # 0-based like KeyboardWidget
        # Default to 8 commonly used CCs
        self.cc_numbers: List[int] = list(cc_numbers) if cc_numbers else [1, 7, 74, 10, 71, 73, 11, 91]
        # current fader values cached
        self._values: List[int] = [0, 0, 0, 0]
        # Provide a minimal layout_model for compatibility with existing code
        # name for title, columns for potential width fallbacks
        self.layout_model = SimpleNamespace(name="Faders", columns=8)
        self.setWindowTitle("Faders")
        try:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(int(10 * self.ui_scale), int(8 * self.ui_scale), int(10 * self.ui_scale), int(10 * self.ui_scale))
        root.setSpacing(int(10 * self.ui_scale))

        # Header row (kept minimal—no title text per request)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(int(10 * self.ui_scale))
        # No title label; just keep a small top margin via the root margins
        header.addStretch()
        root.addLayout(header)

        # Main faders row
        faders_row = QHBoxLayout()
        faders_row.setContentsMargins(0, 0, 0, 0)
        faders_row.setSpacing(int(18 * self.ui_scale))

        self.sliders: List[QSlider] = []
        # No value labels

        # Build 8 columns: [slider]
        for i in range(8):
            col = QVBoxLayout()
            col.setContentsMargins(0, 0, 0, 0)
            col.setSpacing(int(8 * self.ui_scale))

            # Reference-drag slider (no jump to click)
            vslider = DragReferenceSlider(Qt.Vertical)
            vslider.setRange(0, 127)
            vslider.setValue(64)
            try:
                # Make faders thick and tall
                vslider.setFixedWidth(int(44 * self.ui_scale))
                vslider.setMinimumHeight(int(300 * self.ui_scale))
                # Blue scheme, thick groove
                s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
                vmw = int(16 * s)  # groove width
                vhh = int(16 * s)  # handle height
                vhw = int(28 * s)  # handle width
                m = int(8 * s)
                slider_qss = (
                    f"QSlider::groove:vertical {{ width: {vmw}px; background: #3a3f46; border: 1px solid #2a2f35; border-radius: 6px; }}"
                    "QSlider::sub-page:vertical { background: transparent; }"
                    "QSlider::add-page:vertical { background: #61b3ff; border: 1px solid #2f82e6; border-radius: 6px; }"
                    f"QSlider::handle:vertical {{ height: {vhh}px; width: {vhw}px; background: #eaeaea; border: 1px solid #5a5f66; border-radius: 6px; margin: 0 -{m}px; }}"
                    "border: 1px solid #444; border-radius: 6px;"
                )
                vslider.setStyleSheet(slider_qss)
                vslider.setToolTip(f"CC {self.cc_numbers[i] if i < len(self.cc_numbers) else 0}")
            except Exception:
                pass
            vslider.valueChanged.connect(lambda v, idx=i: self._on_slider(idx, v))
            col.addWidget(vslider, 1, Qt.AlignHCenter)
            faders_row.addLayout(col)

            self.sliders.append(vslider)

        root.addLayout(faders_row)

        self.setLayout(root)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        try:
            pad = int(18 * self.ui_scale)
            slider_height = int(300 * self.ui_scale)
            col_w = int(72 * self.ui_scale)  # dominated by slider width
            total_w = 8 * col_w + 7 * pad + int(24 * self.ui_scale)
            total_h = int(24 * self.ui_scale) + slider_height + int(24 * self.ui_scale)
            return QSize(total_w, total_h)
        except Exception:
            return QSize(900, 480)

    # --- External API parity with other widgets ---
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

    # --- Handlers ---
    def _on_slider(self, idx: int, value: int):
        value = max(0, min(127, int(value)))
        try:
            self._values[idx] = value
        except Exception:
            pass
        try:
            cc = int(self.cc_numbers[idx]) if idx < len(self.cc_numbers) else 7
            self.midi.cc(cc, value, self.midi_channel)
        except Exception:
            pass

    # --- CC assignment API ---
    def get_cc_numbers(self) -> List[int]:
        return list(self.cc_numbers)

    def set_cc_numbers(self, nums: List[int]):
        try:
            cleaned = [max(0, min(127, int(n))) for n in nums][:8]
            # pad to 8 if shorter
            while len(cleaned) < 8:
                cleaned.append(0)
            self.cc_numbers = cleaned
            # update tooltips
            try:
                for i, s in enumerate(self.sliders):
                    s.setToolTip(f"CC {self.cc_numbers[i]}")
            except Exception:
                pass
        except Exception:
            pass

    # Removed bottom note buttons and All Notes Off to keep the surface minimal

    # --- Values API (for preserving on zoom/switch) ---
    def get_values(self) -> List[int]:
        try:
            return [max(0, min(127, int(v))) for v in self._values[:8]]
        except Exception:
            return [64] * 8

    def set_values(self, values: List[int], emit: bool = False):
        """Set slider positions. If emit is False, do not send CC while applying."""
        try:
            vals = [max(0, min(127, int(v))) for v in values][:8]
            while len(vals) < 8:
                vals.append(64)
            self._values = list(vals)
            for i, s in enumerate(self.sliders):
                try:
                    if not emit:
                        s.blockSignals(True)
                    s.setValue(int(vals[i]))
                finally:
                    if not emit:
                        s.blockSignals(False)
        except Exception:
            pass
