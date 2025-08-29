from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QApplication, QSizePolicy, QCheckBox
from PySide6.QtCore import Qt, QSize, QEvent, QPropertyAnimation, QEasingCurve, QRectF, QTimer
from PySide6.QtGui import QPainter, QColor
import random
from .models import Layout, KeyDef
from .midi_io import MidiOut
from .scale import quantize

def velocity_curve(v_in: int, curve: str) -> int:
    v = max(1, min(127, v_in))
    if curve == "soft":
        return int((v / 127) ** 0.7 * 127)
    if curve == "hard":
        return int((v / 127) ** 1.5 * 127)
    return v

class ClickAnywhereSlider(QSlider):
    """QSlider that lets you click anywhere on the groove to jump and drag from that point."""
    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            # Map click position to value range immediately
            if self.orientation() == Qt.Vertical:
                h = max(1, self.height())
                # Invert because top is max
                frac = 1.0 - min(1.0, max(0.0, event.position().y() / h))
            else:
                w = max(1, self.width())
                frac = min(1.0, max(0.0, event.position().x() / w))
            vmin, vmax = self.minimum(), self.maximum()
            new_val = int(round(vmin + frac * (vmax - vmin)))
            try:
                self.setSliderDown(True)
            except Exception:
                pass
            self.setValue(new_val)
        # Continue with default handling to start drag
        super().mousePressEvent(event)


class DragReferenceSlider(QSlider):
    """Slider that does not jump to click. Clicking sets a reference; dragging adjusts value relatively.
    Works for both orientations, used here for vertical Mod/Pitch wheels.
    """
    def __init__(self, orientation=Qt.Vertical, parent=None):
        super().__init__(orientation, parent)
        self._drag_active = False
        self._press_pos = None
        self._press_value = None

    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        self._drag_active = True
        self._press_pos = event.position()
        try:
            self._press_value = int(self.value())
        except Exception:
            self._press_value = 0
        try:
            self.setSliderDown(True)
        except Exception:
            pass

    def mouseMoveEvent(self, event):  # type: ignore[override]
        if not self._drag_active or self._press_pos is None or self._press_value is None:
            return super().mouseMoveEvent(event)
        rng = max(1, int(self.maximum()) - int(self.minimum()))
        # Determine pixel span
        if self.orientation() == Qt.Vertical:
            span = max(1.0, self.height() - 8.0)
            delta_px = self._press_pos.y() - event.position().y()  # up increases value
        else:
            span = max(1.0, self.width() - 8.0)
            delta_px = event.position().x() - self._press_pos.x()
        # Map pixels to value delta; 1 full span = full range
        dv = int(round((delta_px / span) * rng))
        new_val = int(self._press_value) + dv
        new_val = max(int(self.minimum()), min(int(self.maximum()), new_val))
        self.setValue(new_val)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        if self._drag_active:
            self._drag_active = False
            self._press_pos = None
            self._press_value = None
            try:
                self.setSliderDown(False)
            except Exception:
                pass
        return super().mouseReleaseEvent(event)

class RangeSlider(QWidget):
    """Minimal horizontal range slider with two handles (low/high). Values are ints.
    - Click-and-drag a handle to resize the range.
    - Click-and-drag inside the highlighted range to move the whole range.
    - Clicking elsewhere does nothing (no jump)."""
    def __init__(self, minimum=1, maximum=127, low=64, high=100, parent=None):
        super().__init__(parent)
        self._min = int(minimum)
        self._max = int(maximum)
        self._low = int(max(self._min, min(low, maximum)))
        self._high = int(max(self._min, min(high, maximum)))
        if self._low > self._high:
            self._low, self._high = self._high, self._low
        self._dragging = None  # 'low' | 'high' | 'range' | None
        self._press_v = None
        self._init_low = None
        self._init_high = None
        self.setMinimumHeight(22)
        self.setMouseTracking(True)

    def setRange(self, minimum: int, maximum: int):
        self._min = int(minimum)
        self._max = int(maximum)
        self._low = max(self._min, min(self._low, self._max))
        self._high = max(self._min, min(self._high, self._max))
        self.update()

    def setValues(self, low: int, high: int):
        low, high = int(low), int(high)
        if low > high:
            low, high = high, low
        self._low = max(self._min, min(low, self._max))
        self._high = max(self._min, min(high, self._max))
        self.update()

    def values(self):
        return int(self._low), int(self._high)

    def _pos_to_value(self, x: float) -> int:
        w = max(1, self.width() - 10)
        frac = min(1.0, max(0.0, (x - 5) / w))
        return int(round(self._min + frac * (self._max - self._min)))

    def _value_to_pos(self, v: int) -> float:
        rng = max(1, self._max - self._min)
        frac = (int(v) - self._min) / rng
        return 5 + frac * (self.width() - 10)

    def paintEvent(self, _):  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # Groove (thicker)
        groove_h = 8
        groove = QRectF(5, self.height() / 2 - groove_h/2, max(1, self.width() - 10), groove_h)
        p.setBrush(QColor('#3a3f46'))
        p.setPen(QColor('#2a2f35'))
        p.drawRoundedRect(groove, 3, 3)
        # Range selection
        x1 = self._value_to_pos(self._low)
        x2 = self._value_to_pos(self._high)
        sel = QRectF(min(x1, x2), groove.top(), max(2.0, abs(x2 - x1)), groove_h)
        p.setBrush(QColor('#61b3ff'))
        p.setPen(QColor('#2f82e6'))
        p.drawRoundedRect(sel, 3, 3)
        # Handles
        handle_w, handle_h = 12, 20
        for xv in (x1, x2):
            handle = QRectF(xv - handle_w/2, self.height() / 2 - handle_h/2, handle_w, handle_h)
            p.setBrush(QColor('#eaeaea'))
            p.setPen(QColor('#5a5f66'))
            p.drawRoundedRect(handle, 3, 3)
        p.end()

    def _handle_rects(self):
        """Return (low_rect, high_rect) in widget coordinates."""
        handle_w, handle_h = 12, 20
        x1 = self._value_to_pos(self._low)
        x2 = self._value_to_pos(self._high)
        low_r = QRectF(x1 - handle_w/2, self.height() / 2 - handle_h/2, handle_w, handle_h)
        high_r = QRectF(x2 - handle_w/2, self.height() / 2 - handle_h/2, handle_w, handle_h)
        return low_r, high_r

    def mousePressEvent(self, ev):  # type: ignore[override]
        if ev.button() != Qt.LeftButton:
            return super().mousePressEvent(ev)
        posx = ev.position().x()
        v = self._pos_to_value(posx)
        low_r, high_r = self._handle_rects()
        # If click is on a handle: start resizing that edge without snapping
        if low_r.adjusted(-3, -3, 3, 3).contains(ev.position()):
            self._dragging = 'low'
            self._press_v = v
        elif high_r.adjusted(-3, -3, 3, 3).contains(ev.position()):
            self._dragging = 'high'
            self._press_v = v
        else:
            # If click is inside the selected range: drag the whole range
            x1 = self._value_to_pos(self._low)
            x2 = self._value_to_pos(self._high)
            sel_left, sel_right = min(x1, x2), max(x1, x2)
            if sel_left <= posx <= sel_right:
                self._dragging = 'range'
                self._press_v = v
                self._init_low, self._init_high = self._low, self._high
            else:
                self._dragging = None
        self.update()

    def mouseMoveEvent(self, ev):  # type: ignore[override]
        if self._dragging is None:
            return super().mouseMoveEvent(ev)
        v = self._pos_to_value(ev.position().x())
        if self._dragging == 'low':
            self._low = max(self._min, min(v, self._high))
        elif self._dragging == 'high':
            self._high = min(self._max, max(v, self._low))
        elif self._dragging == 'range' and self._press_v is not None and self._init_low is not None and self._init_high is not None:
            width = self._init_high - self._init_low
            delta = v - self._press_v
            new_low = self._init_low + delta
            new_high = new_low + width
            # Clamp to bounds while preserving width
            if new_low < self._min:
                new_low = self._min
                new_high = new_low + width
            if new_high > self._max:
                new_high = self._max
                new_low = new_high - width
            self._low, self._high = int(new_low), int(new_high)
        self.update()

    def mouseReleaseEvent(self, ev):  # type: ignore[override]
        self._dragging = None
        self._press_v = None
        self._init_low = None
        self._init_high = None
        return super().mouseReleaseEvent(ev)

class KeyboardWidget(QWidget):
    def __init__(self, layout_model: Layout, midi_out: MidiOut, title: str = "", show_header: bool = True, compact_controls: bool = True, scale: float = 1.0):
        super().__init__()
        self.layout_model = layout_model
        self.midi = midi_out
        self.port_name: str | None = None
        self.midi_channel: int = 0  # 0-15, shown as 1-16
        self.octave_offset = 0
        self.sustain = False
        self.latch = False
        self.visual_hold_on_sustain = False  # whether sustained notes keep visual down state
        self.vel_curve = "linear"
        self.active_notes: set[tuple[int,int]] = set()
        # Polyphony control
        self.polyphony_enabled: bool = False
        self.polyphony_max: int = 8
        self._voice_order: list[tuple[int,int,int]] = []  # (note, ch, base_note)
        self.dragging = False
        self.last_drag_key = None
        self.last_drag_button: QPushButton | None = None
        self._last_drag_note_base: int | None = None  # Track last dragged raw base note (key pitch class)
        self.key_buttons = {}  # Map from note to button
        self.setWindowTitle(title or layout_model.name)
        # UI scale factor (zoom). Used for key geometry and certain panel widths.
        try:
            self.ui_scale = float(scale) if float(scale) > 0 else 1.0
        except Exception:
            self.ui_scale = 1.0
        self.setMouseTracking(True)  # Enable mouse tracking for drag
        # Event filter will be installed on the piano container after it is created
        root = QVBoxLayout(self)
        # Do not allow vertical expansion; we'll size exactly to header + keys
        try:
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        except Exception:
            pass
        # Eliminate extra gaps around keyboard
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._show_header = show_header
        self._compact_controls = compact_controls
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        try:
            s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
            header.setSpacing(max(1, int(2 * s)))
        except Exception:
            header.setSpacing(1)
        self.oct_label = QLabel("Octave")
        # Octave +/- buttons
        self.oct_minus_btn = QPushButton("-")
        self.oct_plus_btn = QPushButton("+")
        for b in (self.oct_minus_btn, self.oct_plus_btn):
            b.setCursor(Qt.PointingHandCursor)
            try:
                b.setFixedWidth(int(20 * self.ui_scale))
                b.setFixedHeight(int(18 * self.ui_scale))
            except Exception:
                pass
            # Styling will be applied uniformly later via _apply_header_button_styles()
        self.oct_minus_btn.clicked.connect(lambda: self.change_octave(-1))
        self.oct_plus_btn.clicked.connect(lambda: self.change_octave(+1))
        
        # Add sustain toggle button (clearly styled) and All Notes Off button
        self.sustain_btn = QPushButton("Sustain: Off")
        self.sustain_btn.setCheckable(True)
        self.sustain_btn.clicked.connect(self.toggle_sustain)
        self.sustain_btn.setCursor(Qt.PointingHandCursor)
        self.sustain_btn.setStyleSheet(
            """
            QPushButton {
                padding: 1px 4px;
                min-height: 0px;
                border-radius: 3px;
                border: 1px solid #888;
                background-color: #f3f3f3;
                color: #222;
            }
            QPushButton:checked {
                background-color: #3498db; /* blue to match Latch */
                color: white;
                border: 1px solid #2980b9;
            }
            QPushButton:hover { background-color: #e9e9e9; }
            QPushButton:pressed { background-color: #dcdcdc; }
            QPushButton:checked:hover { background-color: #2f8ccc; }
            QPushButton:checked:pressed { background-color: #2a7fb8; }
            """
        )
        # Latch button (toggle)
        self.latch_btn = QPushButton("Latch: Off")
        self.latch_btn.setCheckable(True)
        self.latch_btn.clicked.connect(self.toggle_latch)
        self.latch_btn.setCursor(Qt.PointingHandCursor)
        self.latch_btn.setStyleSheet(
            """
            QPushButton {
                padding: 1px 4px;
                min-height: 0px;
                border-radius: 3px;
                border: 1px solid #888;
                background-color: #f3f3f3;
                color: #222;
            }
            QPushButton:checked {
                background-color: #3498db; /* blue */
                color: white;
                border: 1px solid #2980b9;
            }
            QPushButton:hover { background-color: #e9e9e9; }
            QPushButton:pressed { background-color: #dcdcdc; }
            QPushButton:checked:hover { background-color: #2f8ccc; }
            QPushButton:checked:pressed { background-color: #2a7fb8; }
            """
        )
        self.all_off_btn = QPushButton("All Notes Off")
        self.all_off_btn.setCursor(Qt.PointingHandCursor)
        self.all_off_btn.clicked.connect(self.all_notes_off_clicked)
        self.all_off_btn.setStyleSheet(
            """
            QPushButton {
                padding: 1px 4px;
                min-height: 0px;
                border-radius: 3px;
                border: 1px solid #888;
                background-color: #fafafa;
                color: #222;
            }
            QPushButton:hover { background-color: #f0f0f0; }
            QPushButton:pressed { background-color: #e5e5e5; }
            """
        )
        # Store base stylesheet for flash/revert behavior
        try:
            self._all_off_btn_base_qss = str(self.all_off_btn.styleSheet())
        except Exception:
            self._all_off_btn_base_qss = ""
        
        self.vel_label = QLabel("Vel curve: linear")
        # Velocity controls: single slider and randomized range
        self.vel_random_chk = QCheckBox("Randomized Velocity")
        self.vel_random_chk.setToolTip("Randomize velocity within a range")
        # Style checkbox to use the same blue as sliders, scaled by ui_scale
        try:
            s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
            ind = int(14 * s)
            sp = int(4 * s)
            rad = max(2, int(3 * s))
            font_px = max(9, int(11 * s))
            self.vel_random_chk.setStyleSheet(
                f"QCheckBox {{ color: #ddd; spacing: {sp}px; font-size: {font_px}px; }}"
                "QCheckBox::indicator {"
                f"  width: {ind}px; height: {ind}px;"
                "  border: 1px solid #2a2f35;"
                "  background: #2b2f36;"
                f"  border-radius: {rad}px;"
                "}"
                "QCheckBox::indicator:hover { border: 1px solid #61b3ff; }"
                "QCheckBox::indicator:checked {"
                "  background: #61b3ff;"
                "  border: 1px solid #2f82e6;"
                "}"
            )
        except Exception:
            pass
        self.vel_slider = QSlider(Qt.Horizontal)  # single value slider
        self.vel_slider.setMinimum(1)
        self.vel_slider.setMaximum(127)
        self.vel_slider.setValue(100)
        self.vel_range = RangeSlider(1, 127, low=80, high=110, parent=self)
        self.vel_range.setVisible(False)
        self.vel_random_chk.toggled.connect(self._toggle_vel_random)
        # Default to randomized velocity enabled
        try:
            self.vel_random_chk.setChecked(True)
            # Ensure UI elements reflect the default state even if signal doesn't fire
            self._toggle_vel_random(True)
        except Exception:
            pass
        # Keep header small so small keyboards can shrink (but scale with ui_scale)
        try:
            self.vel_slider.setFixedWidth(int(200 * self.ui_scale))
            self.vel_range.setFixedWidth(int(200 * self.ui_scale))
            self.vel_slider.setFixedHeight(int(16 * self.ui_scale))
            self.vel_range.setFixedHeight(int(20 * self.ui_scale))
            self.vel_slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.vel_range.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.oct_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.vel_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # Allow buttons to grow horizontally to avoid text clipping
            self.sustain_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.latch_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.all_off_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.sustain_btn.setFixedHeight(int(18 * self.ui_scale))
            self.latch_btn.setFixedHeight(int(18 * self.ui_scale))
            self.all_off_btn.setFixedHeight(int(18 * self.ui_scale))
            self.oct_label.setFixedHeight(int(16 * self.ui_scale))
            self.vel_label.setFixedHeight(int(16 * self.ui_scale))
        except Exception:
            pass
        # Apply unified slider styling to match RangeSlider look when visible
        try:
            s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
            gh = int(8 * s)
            hw = int(12 * s)
            hh = int(20 * s)
            vmw = int(8 * s)
            vhh = int(12 * s)
            vhw = int(20 * s)
            m = int(6 * s)
            slider_qss = (
                f"QSlider::groove:horizontal {{"
                f"  height: {gh}px;"
                "  background: #3a3f46;"
                "  border: 1px solid #2a2f35;"
                "  border-radius: 3px;"
                "}"
                "QSlider::sub-page:horizontal {"
                "  background: #61b3ff;"
                "  border: 1px solid #2f82e6;"
                "  border-radius: 3px;"
                "}"
                "QSlider::add-page:horizontal {"
                "  background: transparent;"
                "}"
                f"QSlider::handle:horizontal {{"
                f"  width: {hw}px;"
                f"  height: {hh}px;"
                "  background: #eaeaea;"
                "  border: 1px solid #5a5f66;"
                "  border-radius: 3px;"
                f"  margin: -{m}px 0; /* extend handle vertically to overlap groove */"
                "}"
                f"QSlider::groove:vertical {{"
                f"  width: {vmw}px;"
                "  background: #3a3f46;"
                "  border: 1px solid #2a2f35;"
                "  border-radius: 3px;"
                "}"
                "QSlider::sub-page:vertical {"
                "  background: transparent;"
                "}"
                "QSlider::add-page:vertical {"
                "  background: #61b3ff;"
                "  border: 1px solid #2f82e6;"
                "  border-radius: 3px;"
                "}"
                f"QSlider::handle:vertical {{"
                f"  height: {vhh}px;"
                f"  width: {vhw}px;"
                "  background: #eaeaea;"
                "  border: 1px solid #5a5f66;"
                "  border-radius: 3px;"
                f"  margin: 0 -{m}px; /* extend handle horizontally to overlap groove */"
                "}"
                "border: 1px solid #444; border-radius: 3px;"
            )
            self._slider_qss = slider_qss
            self.vel_slider.setStyleSheet(slider_qss)
            try:
                fs = max(8, int(9 * self.ui_scale))
            except Exception:
                fs = 9
            self.vel_label.setStyleSheet(f"font-size: {fs}px;")
        except Exception:
            pass
        
        # Ensure header buttons/labels have adequate size at higher zoom
        try:
            s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
            # Minimum widths to avoid text clipping (bumped again for 200%)
            self.sustain_btn.setMinimumWidth(int(120 * s))
            self.latch_btn.setMinimumWidth(int(100 * s))
            self.all_off_btn.setMinimumWidth(int(160 * s))
            # Octave label font size
            self.oct_label.setStyleSheet(f"font-size: {max(9, int(11 * s))}px; color: #ddd;")
            # Octave +/- buttons sized
            self.oct_minus_btn.setFixedHeight(int(18 * s))
            self.oct_plus_btn.setFixedHeight(int(18 * s))
            self.oct_minus_btn.setFixedWidth(int(24 * s))
            self.oct_plus_btn.setFixedWidth(int(24 * s))
        except Exception:
            pass
        header.addWidget(self.oct_minus_btn)
        header.addWidget(self.oct_label)
        header.addWidget(self.oct_plus_btn)
        header.addWidget(self.vel_label)
        header.addWidget(self.vel_random_chk)
        header.addWidget(self.vel_slider)
        header.addWidget(self.vel_range)
        header.addWidget(self.sustain_btn)
        header.addWidget(self.latch_btn)
        header.addWidget(self.all_off_btn)
        header.addStretch()
        # Keep original per-button styles (defined when buttons are created)
        if self._show_header:
            root.addLayout(header)
        elif self._compact_controls:
            # Add a compact controls bar (centered) with Sustain + All Notes Off
            controls_widget = QWidget()
            try:
                controls_widget.setFixedHeight(26)
                controls_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            except Exception:
                pass
            self.controls_widget = controls_widget
            controls = QHBoxLayout(controls_widget)
            controls.setContentsMargins(0, 0, 0, 0)
            controls.setSpacing(6)
            controls.addStretch()
            # Enlarge buttons a bit so text isn't clipped
            try:
                self.sustain_btn.setFixedHeight(int(22 * self.ui_scale))
                self.latch_btn.setFixedHeight(int(22 * self.ui_scale))
                self.all_off_btn.setFixedHeight(int(22 * self.ui_scale))
                self.sustain_btn.setMinimumWidth(int(90 * self.ui_scale))
                self.latch_btn.setMinimumWidth(int(70 * self.ui_scale))
                self.all_off_btn.setMinimumWidth(int(110 * self.ui_scale))
                # Keep original per-button styles
                # Slightly larger octave buttons in compact bar
                self.oct_minus_btn.setFixedHeight(int(22 * self.ui_scale))
                self.oct_plus_btn.setFixedHeight(int(22 * self.ui_scale))
                self.oct_minus_btn.setFixedWidth(int(24 * self.ui_scale))
                self.oct_plus_btn.setFixedWidth(int(24 * self.ui_scale))
            except Exception:
                pass
            controls.addWidget(self.oct_minus_btn)
            controls.addWidget(self.oct_label)
            controls.addWidget(self.oct_plus_btn)
            controls.addWidget(self.sustain_btn)
            controls.addWidget(self.latch_btn)
            controls.addWidget(self.all_off_btn)
            controls.addWidget(self.vel_random_chk)
            controls.addWidget(self.vel_slider)
            controls.addWidget(self.vel_range)
            controls.addStretch()
            root.addWidget(controls_widget)

        # Small vertical gap between controls and keys
        try:
            root.addSpacing(8)
        except Exception:
            pass

        # --- Left-side wheels panel (Mod/Pitch) ---
        # Create once; visibility controlled by flags
        self.show_mod_wheel = False
        self.show_pitch_wheel = False
        self.left_panel = QWidget()
        try:
            # Start with single-wheel width; will grow if both wheels are shown
            self.left_panel.setFixedWidth(int(44 * self.ui_scale))
            self.left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass
        # Horizontal layout to place Mod and Pitch next to each other
        lp_layout = QHBoxLayout(self.left_panel)
        lp_layout.setContentsMargins(6, 2, 6, 2)
        lp_layout.setSpacing(12)
        # Pitch wheel (center detent)
        self.pitch_slider = DragReferenceSlider(Qt.Vertical)
        self.pitch_slider.setMinimum(-8192)
        self.pitch_slider.setMaximum(8191)
        self.pitch_slider.setValue(0)
        self.pitch_slider.setTickPosition(QSlider.NoTicks)
        self.pitch_slider.valueChanged.connect(lambda v: self._send_pitch_bend(v))
        # Smooth auto-return to center on release
        self._pitch_anim = None
        try:
            self.pitch_slider.sliderReleased.connect(self._animate_pitch_to_center)
            self.pitch_slider.sliderPressed.connect(self._stop_pitch_anim)
        except Exception:
            pass
        # Mod wheel (CC1)
        self.mod_slider = DragReferenceSlider(Qt.Vertical)
        self.mod_slider.setMinimum(0)
        self.mod_slider.setMaximum(127)
        self.mod_slider.setValue(0)
        self.mod_slider.setTickPosition(QSlider.NoTicks)
        self.mod_slider.valueChanged.connect(lambda v: self._send_mod_cc(v))
        try:
            for s in (self.pitch_slider, self.mod_slider):
                s.setFixedWidth(int(28 * self.ui_scale))
                s.setStyleSheet(slider_qss)
        except Exception:
            pass
        # Labels
        self.mod_lbl = QLabel("Mod")
        self.pitch_lbl = QLabel("Pitch")
        try:
            fs_lbl = max(8, int(9 * self.ui_scale))
            for lbl in (self.mod_lbl, self.pitch_lbl):
                lbl.setAlignment(Qt.AlignHCenter)
                lbl.setStyleSheet(f"font-size: {fs_lbl}px; color: #ddd;")
        except Exception:
            pass
        # Build two vertical columns: Mod column and Pitch column
        mod_col = QVBoxLayout()
        mod_col.setContentsMargins(0, 0, 0, 0)
        mod_col.setSpacing(4)
        mod_col.addWidget(self.mod_slider, 1)
        mod_col.addWidget(self.mod_lbl, 0)
        pitch_col = QVBoxLayout()
        pitch_col.setContentsMargins(0, 0, 0, 0)
        pitch_col.setSpacing(4)
        pitch_col.addWidget(self.pitch_slider, 1)
        pitch_col.addWidget(self.pitch_lbl, 0)
        lp_layout.addLayout(mod_col, 1)
        lp_layout.addLayout(pitch_col, 1)
        self.left_panel.setVisible(False)

        # --- Row containing optional left panel and piano ---
        keys_row = QHBoxLayout()
        keys_row.setContentsMargins(0, 0, 0, 0)
        keys_row.setSpacing(4)
        keys_row.addWidget(self.left_panel)

        # Create a container widget for absolute positioning
        piano_container = QWidget()
        # Match or exceed white key height (134 * scale) to avoid bottom clipping at higher zoom
        piano_container.setFixedHeight(int(140 * self.ui_scale))
        # Dark instrument panel background under keys
        piano_container.setStyleSheet(
            """
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1b1b1b, stop:0.5 #202020, stop:1 #1b1b1b);
            }
            """
        )
        try:
            # Do not allow horizontal expansion; keep width exactly to keys
            piano_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass
        piano_container.setMouseTracking(True)  # Enable mouse tracking on container
        self.piano_container = piano_container  # Store reference for mouse events
        # Scope the event filter to the piano container only (lower overhead than app-wide)
        try:
            self.piano_container.installEventFilter(self)
        except Exception:
            pass
        
        # Create white keys first (they go in the background)
        white_keys = self.layout_model.rows[0].keys
        x_pos = 0
        white_positions: list[tuple[int, int]] = []  # (white_note, x)

        for white_key in white_keys:
            w = int(44 * self.ui_scale * white_key.width)
            if white_key.note >= 0:  # Skip spacer keys
                btn = QPushButton("", piano_container)
                # Use full width for reliable click/drag; separators are visual via borders
                btn.setGeometry(x_pos, 0, w, int(134 * self.ui_scale))
                try:
                    btn.setAttribute(Qt.WA_StyledBackground, True)
                except Exception:
                    pass
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #ffffff, stop:0.25 #fbfbfb, stop:0.55 #f3f3f3, stop:1 #e7e7e7);
                        border-top: 1px solid #d8d8d8;
                        border-left: 1px solid #dadada;
                        border-right: 1px solid #cfcfcf; /* slightly darker right edge */
                        border-bottom: 2px solid #bbbbbb; /* subtle bottom lip */
                        border-radius: 0px;
                    }}
                    /* Put hover BEFORE held so held wins when both apply */
                    QPushButton:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #ffffff, stop:0.5 #f9f9f9, stop:1 #f0f0f0);
                    }}
                    QPushButton[active="true"] {{
                        /* Fill entire key with activation blue */
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #6bb8ff, stop:1 #2f82e6);
                        border-top: 1px solid #2f82e6;
                        border-left: 1px solid #2f82e6;
                        border-right: 1px solid #2f82e6;
                        border-bottom: 2px solid #1b64c7;
                    }}
                    QPushButton[held=\"true\"] {{
                        /* Slightly different blue for held to differentiate subtly */
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #5fb1ff, stop:1 #2b7ade);
                        border-top: 1px solid #2f82e6;
                        border-left: 1px solid #2f82e6;
                        border-right: 1px solid #2f82e6;
                        border-bottom: 2px solid #1b64c7;
                    }}
                    /* Keep held look even when hovered */
                    QPushButton[held=\"true\"]:hover {{
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #5fb1ff, stop:1 #2b7ade);
                        border-top: 1px solid #2f82e6;
                        border-left: 1px solid #2f82e6;
                        border-right: 1px solid #2f82e6;
                        border-bottom: 2px solid #1b64c7;
                    }}
                """)
                btn.pressed.connect(lambda k=white_key: self.on_key_press(k))
                btn.released.connect(lambda k=white_key: self.on_key_release(k))
                btn.key_note = white_key.note
                self.key_buttons[white_key.note] = btn
                white_positions.append((white_key.note, x_pos))
            # advance by full width (no -1; gaps are visual only)
            x_pos += w

        # Create black keys (in front), positioned between specific whites
        for white_note, white_x in white_positions:
            note_in_octave = white_note % 12
            if note_in_octave in [0, 2, 5, 7, 9]:
                black_note = white_note + 1
                black_x = white_x + int(32 * self.ui_scale)  # centered between adjacent whites
                btn = QPushButton("", piano_container)
                btn.setGeometry(black_x, 0, int(28 * self.ui_scale), int(68 * self.ui_scale))
                try:
                    btn.setAttribute(Qt.WA_StyledBackground, True)
                except Exception:
                    pass
                btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #3a3a3a, stop:0.12 #2a2a2a, stop:0.5 #121212, stop:1 #050505);
                        border-top: 1px solid #3a3a3a;
                        border-left: 1px solid #222;
                        border-right: 1px solid #222;
                        border-bottom: 2px solid #0b0b0b;
                        border-radius: 3px;
                    }
                    /* Put hover BEFORE held so held wins when both apply */
                    QPushButton:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #3b3b3b, stop:0.5 #191919, stop:1 #060606);
                    }
                    QPushButton[active="true"] {
                        /* Fill entire key with activation blue */
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #4aa3ff, stop:1 #2f82e6);
                        border-top: 1px solid #2f82e6;
                        border-left: 1px solid #2f82e6;
                        border-right: 1px solid #2f82e6;
                        border-bottom: 2px solid #0a0a0a;
                    }
                    QPushButton[held="true"] {
                        /* Slightly darker blue for held */
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #3f9cff, stop:1 #2b7ade);
                        border-top: 1px solid #2f82e6;
                        border-left: 1px solid #2f82e6;
                        border-right: 1px solid #2f82e6;
                        border-bottom: 2px solid #0b0b0b;
                    }
                    /* Keep held look even when hovered */
                    QPushButton[held="true"]:hover {
                        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #3f9cff, stop:1 #2b7ade);
                        border-top: 1px solid #2f82e6;
                        border-left: 1px solid #2f82e6;
                        border-right: 1px solid #2f82e6;
                        border-bottom: 2px solid #0b0b0b;
                    }
                """)
                # Signals use KeyDef with the black note
                black_key_def = KeyDef(
                    label="",
                    note=black_note,
                    color="black",
                    width=0.7,
                    height=1.0,
                    velocity=100,
                    channel=0,
                )
                btn.pressed.connect(lambda k=black_key_def: self.on_key_press(k))
                btn.released.connect(lambda k=black_key_def: self.on_key_release(k))
                btn.raise_()
                btn.key_note = black_note
                self.key_buttons[black_note] = btn
        
        # If the highest key is black, remove it so the keyboard doesn't end with a black key
        try:
            if self.key_buttons:
                max_note = max(self.key_buttons.keys())
                if max_note % 12 in [1, 3, 6, 8, 10]:
                    btn = self.key_buttons.pop(max_note)
                    try:
                        btn.hide()
                        btn.deleteLater()
                    except Exception:
                        pass
        except Exception:
            pass

        # Set the container width to the exact right edge of remaining keys (no padding)
        try:
            if self.key_buttons:
                max_edge = 0
                for btn in self.key_buttons.values():
                    g = btn.geometry()
                    edge = g.x() + g.width()  # precise right edge (exclusive)
                    if edge > max_edge:
                        max_edge = edge
                piano_container.setFixedWidth(max_edge)
            else:
                piano_container.setFixedWidth(x_pos)
        except Exception:
            piano_container.setFixedWidth(x_pos)
        # Ensure minimum width matches the actual key area (no extra padding)
        try:
            exact_w = int(self.piano_container.width())
            # Include left panel width if visible
            if self.left_panel.isVisible():
                try:
                    exact_w += int(self.left_panel.width()) + 4
                except Exception:
                    exact_w += 48
            self.setMinimumWidth(exact_w)
            self.setMaximumWidth(exact_w)
            self.setFixedWidth(exact_w)
            # Match compact controls width to piano to avoid pushing layout wider
            if hasattr(self, 'controls_widget') and self.controls_widget is not None:
                try:
                    self.controls_widget.setFixedWidth(exact_w)
                    self.controls_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                except Exception:
                    pass
        except Exception:
            pass
        # Prefer fixed sizing so QMainWindow can shrink exactly to fit
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        # Align piano container to the left to avoid right-side blank expansion
        try:
            keys_row.addWidget(piano_container, 0, Qt.AlignLeft)
        except Exception:
            keys_row.addWidget(piano_container)
        # Add the row to root
        root.addLayout(keys_row)

    def effective_note(self, base_note: int) -> int:
        """Return the effective MIDI note after octave offset."""
        return int(base_note + 12 * (self.layout_model.base_octave + self.octave_offset))

    def change_octave(self, delta: int):
        # Clamp to a reasonable range to avoid running off MIDI limits
        delta = int(delta)
        new_off = max(-5, min(5, self.octave_offset + delta))
        if new_off != self.octave_offset:
            self.octave_offset = new_off
            self._update_oct_label()

    # --- Left panel (Mod/Pitch wheels) visibility & sizing ---
    def _update_left_panel_width(self):
        """Adjust left panel width based on which wheels are visible and current ui_scale."""
        try:
            s = float(getattr(self, 'ui_scale', 1.0))
        except Exception:
            s = 1.0
        show_mod = bool(getattr(self, 'show_mod_wheel', False))
        show_pitch = bool(getattr(self, 'show_pitch_wheel', False))
        count = (1 if show_mod else 0) + (1 if show_pitch else 0)
        any_visible = count > 0
        # Toggle individual widgets
        try:
            if hasattr(self, 'mod_slider'):
                self.mod_slider.setVisible(show_mod)
            if hasattr(self, 'mod_lbl'):
                self.mod_lbl.setVisible(show_mod)
            if hasattr(self, 'pitch_slider'):
                self.pitch_slider.setVisible(show_pitch)
            if hasattr(self, 'pitch_lbl'):
                self.pitch_lbl.setVisible(show_pitch)
        except Exception:
            pass
        # Update panel visibility and width
        try:
            self.left_panel.setVisible(any_visible)
        except Exception:
            pass
        try:
            base_single = 44
            base_double = 80
            target = 0
            if count == 1:
                target = int(base_single * s)
            elif count >= 2:
                target = int(base_double * s)
            self.left_panel.setFixedWidth(max(0, target))
            self.left_panel.updateGeometry()
        except Exception:
            pass
        # Nudge layout sizing
        try:
            self.updateGeometry()
            self.adjustSize()
        except Exception:
            pass

    def set_show_mod_wheel(self, show: bool):
        self.show_mod_wheel = bool(show)
        self._update_left_panel_width()

    def set_show_pitch_wheel(self, show: bool):
        self.show_pitch_wheel = bool(show)
        self._update_left_panel_width()

    # --- Sizing helpers ---
    def sizeHint(self) -> QSize:  # type: ignore[override]
        try:
            width = int(self.piano_container.width())
        except Exception:
            width = 800
        keys_h = int(134 * getattr(self, 'ui_scale', 1.0))
        # Add vertical extras for header/controls when present
        if getattr(self, "_show_header", True):
            header_h = 24  # approximate header row height
            gap = 8  # spacer added between header and keys
            return QSize(width, keys_h + header_h + gap)
        elif getattr(self, "_compact_controls", True):
            try:
                controls_h = int(self.controls_widget.height())
            except Exception:
                controls_h = 26
            gap = 8  # spacing between controls and keys
            return QSize(width, keys_h + controls_h + gap)
        else:
            # keys only
            return QSize(width, keys_h)

    # --- Visual helpers ---
    def _apply_btn_visual(self, btn: QPushButton | None, down: bool, held: bool):
        if btn is None:
            return
        try:
            # Only touch properties when they actually change to avoid heavy restyles
            # Use dynamic properties for visuals instead of the built-in :pressed state.
            # 1) Active (pressed) state via [active="true"]
            prev_active = btn.property('active')
            new_active = 'true' if down else 'false'
            # Do NOT sync Qt's internal pressed state for keys; rely solely on dynamic properties
            if prev_active != new_active:
                btn.setProperty('active', new_active)
                st = btn.style()
                if st is not None:
                    st.unpolish(btn)
                    st.polish(btn)

            # 2) Held dynamic property (used by stylesheet selector [held="true"]) 
            prev_held = btn.property('held')
            new_held = 'true' if held else 'false'
            if prev_held != new_held:
                btn.setProperty('held', new_held)
                st = btn.style()
                if st is not None:
                    st.unpolish(btn)
                    st.polish(btn)

            # Request a paint; avoid synchronous repaint to keep UI responsive
            btn.update()
        except Exception:
            pass

    def _apply_note_visual(self, note: int, down: bool, held: bool):
        try:
            btn = self.key_buttons.get(note)
        except Exception:
            btn = None
        self._apply_btn_visual(btn, down, held)

    def _sync_visuals_if_needed(self):
        """When neither sustain nor latch is enabled, ensure no stray 'held' visuals remain
        for keys that aren't in active_notes. This helps avoid 'stuck' pressed looks after
        complex drags.
        """
        if getattr(self, 'sustain', False) or getattr(self, 'latch', False):
            return
        ch = self.midi_channel
        try:
            active = set(self.active_notes)
        except Exception:
            active = set()
        for base_note, btn in self.key_buttons.items():
            eff = self.effective_note(base_note)
            if (eff, ch) not in active:
                self._apply_btn_visual(btn, False, False)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        try:
            width = int(self.piano_container.width())
        except Exception:
            width = 400
        keys_h = int(134 * getattr(self, 'ui_scale', 1.0))
        if getattr(self, "_show_header", True):
            header_h = 24
            gap = 8
            return QSize(width, keys_h + header_h + gap)
        elif getattr(self, "_compact_controls", True):
            try:
                controls_h = int(self.controls_widget.height())
            except Exception:
                controls_h = 26
            gap = 8
            return QSize(width, keys_h + controls_h + gap)
        else:
            return QSize(width, keys_h)

    def on_key_press(self, key: KeyDef):
        base_note = key.note
        note = self.effective_note(base_note)
        ch = self.midi_channel
        # Latch mode: pressing a sounding note turns it off; otherwise turns it on and keeps it on
        if getattr(self, 'latch', False):
            if (note, ch) in self.active_notes:
                # Turn it off
                try:
                    self.midi.note_off(note, ch)
                except Exception:
                    pass
                self.active_notes.discard((note, ch))
                # Remove from voice order if present
                try:
                    for i, (n, c, b) in enumerate(list(self._voice_order)):
                        if n == note and c == ch:
                            self._voice_order.pop(i)
                            break
                except Exception:
                    pass
                self._apply_note_visual(base_note, False, False)
                return
            # Otherwise, ensure polyphony limit before latching this note
            if getattr(self, 'polyphony_enabled', False):
                try:
                    current_voices = len(self.active_notes)
                except Exception:
                    current_voices = 0
                if current_voices >= max(1, int(getattr(self, 'polyphony_max', 8))):
                    if self._voice_order:
                        old_note, old_ch, old_base = self._voice_order.pop(0)
                        try:
                            self.midi.note_off(old_note, old_ch)
                        except Exception:
                            pass
                        self.active_notes.discard((old_note, old_ch))
                        self._apply_note_visual(old_base, False, False)
        
        # Enforce polyphony limit: steal oldest if necessary
        if getattr(self, 'polyphony_enabled', False):
            try:
                current_voices = len(self.active_notes)
            except Exception:
                current_voices = 0
            if current_voices >= max(1, int(getattr(self, 'polyphony_max', 8))):
                # Steal the oldest voice
                if self._voice_order:
                    old_note, old_ch, old_base = self._voice_order.pop(0)
                    try:
                        self.midi.note_off(old_note, old_ch)
                    except Exception:
                        pass
                    self.active_notes.discard((old_note, old_ch))
                    # Clear its visual regardless of sustain
                    self._apply_note_visual(old_base, False, False)
        vel = self._compute_velocity(int(key.velocity))
        self.midi.note_on(note, vel, ch)
        self.active_notes.add((note, ch))
        self._voice_order.append((note, ch, base_note))
        # Ensure the corresponding key button shows as pressed (by base note)
        self._apply_note_visual(base_note, True, False)
        
        # Set dragging state only when neither latch nor sustain is active
        if not getattr(self, 'latch', False) and not getattr(self, 'sustain', False):
            self.dragging = True
            self.last_drag_key = key
            self._last_drag_note_base = key.note
            # Track and visually press the originating button
            sender = self.sender()
            if isinstance(sender, QPushButton):
                self.last_drag_button = sender
                self._apply_btn_visual(self.last_drag_button, True, False)
                # From the outset of a drag, ensure only this button is active
                self._clear_other_actives(self.last_drag_button)
            # Capture the mouse so we keep receiving move/release events even if cursor leaves
            try:
                self.piano_container.grabMouse()
            except Exception:
                pass

    def on_key_release(self, key: KeyDef):
        base_note = key.note
        note = self.effective_note(base_note)
        # In latch mode, reflect the actual latched state on release
        if getattr(self, 'latch', False):
            ch = self.midi_channel
            if (note, ch) in self.active_notes:
                # Still latched: keep held visual
                self._apply_note_visual(base_note, True, True)
            else:
                # Was toggled off on press: clear visual
                self._apply_note_visual(base_note, False, False)
            return
        if not self.sustain:
            ch = self.midi_channel
            self.midi.note_off(note, ch)
            self.active_notes.discard((note, ch))
            # Remove from voice order if present
            try:
                for i, (n, c, b) in enumerate(list(self._voice_order)):
                    if n == note and c == ch:
                        self._voice_order.pop(i)
                        break
            except Exception:
                pass
            # Clear visual when not sustaining
            self._apply_note_visual(base_note, False, False)
            # Also ensure no other strays
            self._sync_visuals_if_needed()
        else:
            # Sustaining: always clear visual on release; audio remains sustained
            self._apply_note_visual(base_note, False, False)
            # Also ensure no other key remains visually active due to sustain
            self._clear_other_actives(None)
            # Reinforce after event processing: clear all key visuals
            try:
                def _clear_all_keys():
                    try:
                        for b in self.key_buttons.values():
                            self._apply_btn_visual(b, False, False)
                    except Exception:
                        pass
                QTimer.singleShot(0, _clear_all_keys)
            except Exception:
                pass
        # Extra safety: explicitly clear the actual sender button's visual
        try:
            sender_btn = self.sender()
            if isinstance(sender_btn, QPushButton):
                self._apply_btn_visual(sender_btn, False, False)
                # Reinforce after event processing in case of ordering/race
                try:
                    QTimer.singleShot(0, lambda b=sender_btn: self._apply_btn_visual(b, False, False))
                except Exception:
                    pass
        except Exception:
            pass
        # Ensure drag state is stopped on a normal click release (not just via eventFilter)
        if not getattr(self, 'latch', False):
            self.dragging = False
            self.last_drag_key = None
            self._last_drag_note_base = None
            # Clear any lingering reference button so drag logic can't re-press it on move
            if self.last_drag_button is not None:
                self.last_drag_button = None
        # Do NOT clear dragging here. We only stop dragging on actual mouse button
        # release handled by eventFilter/mouseReleaseEvent so that drag can traverse
        # across multiple keys smoothly.

    def eventFilter(self, obj, event):
        """Global event filter to handle drag across child buttons reliably."""
        # Even when not dragging: if sustain is on, ensure a click release clears visuals
        if event.type() == QEvent.MouseButtonRelease and getattr(self, 'sustain', False):
            try:
                if isinstance(obj, QPushButton) and hasattr(obj, 'key_note'):
                    self._apply_btn_visual(obj, False, False)
                    self._clear_other_actives(None)
                    # Reinforce after event loop
                    QTimer.singleShot(0, lambda b=obj: self._apply_btn_visual(b, False, False))
            except Exception:
                pass
        if self.dragging:
            # Handle mouse move while dragging
            if event.type() == QEvent.MouseMove:
                if getattr(self, 'latch', False):
                    return False  # ignore drag changes while in latch mode
                # Map global position to the piano container and find the child under cursor
                try:
                    # Qt6: globalPosition() returns QPointF
                    gp = event.globalPosition().toPoint()
                except AttributeError:
                    gp = event.globalPos()
                container_pos = self.piano_container.mapFromGlobal(gp)
                widget_under = self.piano_container.childAt(container_pos)
                # If we're no longer over the previously pressed button, clear its pressed visual immediately
                if self.last_drag_button is not None and widget_under is not self.last_drag_button:
                    self._apply_btn_visual(self.last_drag_button, False, False)
                # Only suppress switching if the cursor is still within the original button
                # AND there isn't a different key under the cursor. This allows switching to
                # Only keep the last key visually down if the cursor is directly over that same button
                if isinstance(widget_under, QPushButton) and widget_under is self.last_drag_button:
                    self._apply_btn_visual(self.last_drag_button, True, False)
                    # Ensure no other keys remain visually active
                    self._clear_other_actives(self.last_drag_button)
                    return False
                if isinstance(widget_under, QPushButton) and hasattr(widget_under, 'key_note'):
                    base = widget_under.key_note
                    current_note = self.effective_note(base)
                    prev_eff = self.effective_note(self._last_drag_note_base) if self._last_drag_note_base is not None else None
                    if prev_eff is None or current_note != prev_eff:
                        # Stop previous
                        if self._last_drag_note_base is not None and not self.sustain and not getattr(self, 'latch', False):
                            prev_note = prev_eff  # already computed
                            ch = self.midi_channel
                            self.midi.note_off(prev_note, ch)
                            self.active_notes.discard((prev_note, ch))
                        # Update previous button visual (always clear during drag)
                        if self.last_drag_button is not None and self.last_drag_button is not widget_under:
                            self._apply_btn_visual(self.last_drag_button, False, False)
                        # Start new
                        vel = self._compute_velocity(100)
                        ch = self.midi_channel
                        if not getattr(self, 'latch', False):
                            self.midi.note_on(current_note, vel, ch)
                            self.active_notes.add((current_note, ch))
                        # Update current button visual and references
                        self._apply_btn_visual(widget_under, True, False)
                        self.last_drag_button = widget_under
                        self._last_drag_note_base = base
                        self.last_drag_key = None  # no heavy KeyDef allocation
                        # Ensure no other keys remain visually active
                        self._clear_other_actives(self.last_drag_button)
                else:
                    # Not over any key: release previous note and clear visual, keep dragging
                    if self._last_drag_note_base is not None and not self.sustain and not getattr(self, 'latch', False):
                        prev_note = self.effective_note(self._last_drag_note_base)
                        ch = self.midi_channel
                        self.midi.note_off(prev_note, ch)
                        self.active_notes.discard((prev_note, ch))
                    if self.last_drag_button is not None:
                        # Always clear visual during drag when not over any key
                        self._apply_btn_visual(self.last_drag_button, False, False)
                    self._last_drag_note_base = None
                    self.last_drag_key = None
                    self.last_drag_button = None
                    # Ensure no keys remain visually active when off any key
                    self._clear_other_actives(None)
                return False
            # Ensure release anywhere stops dragging and releases note
            if event.type() == QEvent.MouseButtonRelease:
                self.dragging = False
                if self._last_drag_note_base is not None and not self.sustain and not getattr(self, 'latch', False):
                    note = self.effective_note(self._last_drag_note_base)
                    ch = self.midi_channel
                    self.midi.note_off(note, ch)
                    self.active_notes.discard((note, ch))
                # On drag-release: only latch keeps visuals held; sustain clears visuals
                if self.last_drag_button is not None:
                    if getattr(self, 'latch', False):
                        self._apply_btn_visual(self.last_drag_button, True, True)
                    else:
                        self._apply_btn_visual(self.last_drag_button, False, False)
                        # Reinforce after event processing to avoid any transient re-activation
                        try:
                            btn_ref = self.last_drag_button
                            QTimer.singleShot(0, lambda b=btn_ref: self._apply_btn_visual(b, False, False))
                        except Exception:
                            pass
                self._last_drag_note_base = None
                self.last_drag_key = None
                self.last_drag_button = None
                # Normalize visuals in case of missed transitions
                self._sync_visuals_if_needed()
                # Release mouse capture
                try:
                    self.piano_container.releaseMouse()
                except Exception:
                    pass
                return False
        return super().eventFilter(obj, event)

    # ---- Velocity helpers ----
    def _toggle_vel_random(self, checked: bool):
        """Switch between fixed velocity slider and range slider."""
        random_mode = bool(checked)
        try:
            self.vel_slider.setVisible(not random_mode)
            self.vel_range.setVisible(random_mode)
        except Exception:
            pass

    def _compute_velocity(self, base: int) -> int:
        """Compute outgoing velocity from UI.
        base is the key's default velocity (e.g., KeyDef.velocity or 100 during drag).
        """
        if getattr(self, 'vel_random_chk', None) and self.vel_random_chk.isChecked():
            low, high = self.vel_range.values()
            raw = random.randint(min(low, high), max(low, high))
        else:
            raw = int(self.vel_slider.value())
        # Apply per-key scaling then curve
        scaled = int(raw * (base / 127))
        return max(1, min(127, velocity_curve(scaled, self.vel_curve)))

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        if self.dragging:
            self.dragging = False
            if self._last_drag_note_base is not None and not self.sustain and not getattr(self, 'latch', False):
                note = self.effective_note(self._last_drag_note_base)
                ch = self.midi_channel
                self.midi.note_off(note, ch)
                self.active_notes.discard((note, ch))
            # Clear visuals
            if self.last_drag_button is not None:
                if not getattr(self, 'latch', False):
                    # Always clear visuals on release; sustain should not keep visuals held
                    self._apply_btn_visual(self.last_drag_button, False, False)
            self._last_drag_note_base = None
            self.last_drag_key = None
            self.last_drag_button = None
            self._sync_visuals_if_needed()
            try:
                self.piano_container.releaseMouse()
            except Exception:
                pass

    def set_sustain(self, checked: bool):
        """Set sustain state and synchronize UI/notes."""
        self.sustain = bool(checked)
        try:
            self.sustain_btn.blockSignals(True)
            self.sustain_btn.setChecked(self.sustain)
            self.sustain_btn.setText(f"Sustain: {'On' if self.sustain else 'Off'}")
        finally:
            try:
                self.sustain_btn.blockSignals(False)
            except Exception:
                pass
        if not self.sustain:
            # When turning sustain off, ensure no stuck notes or visuals (no flash)
            self._perform_all_notes_off()

    def toggle_sustain(self):
        """Toggle sustain invoked from the header button; sync via set_sustain."""
        self.set_sustain(self.sustain_btn.isChecked())

    def set_latch(self, checked: bool):
        """Enable/disable latch mode and sync UI."""
        prev = getattr(self, 'latch', False)
        self.latch = bool(checked)
        try:
            self.latch_btn.blockSignals(True)
            self.latch_btn.setChecked(self.latch)
            self.latch_btn.setText(f"Latch: {'On' if self.latch else 'Off'}")
        finally:
            try:
                self.latch_btn.blockSignals(False)
            except Exception:
                pass
        if prev and not self.latch:
            # When turning latch OFF, release everything immediately (no flash)
            self._perform_all_notes_off()

    def toggle_latch(self):
        self.set_latch(self.latch_btn.isChecked())

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key_Z:
            self.change_octave(-1)
        elif k == Qt.Key_X:
            self.change_octave(+1)
        elif k == Qt.Key_1:
            self.vel_curve = "linear"; self.vel_label.setText("Vel curve: linear")
        elif k == Qt.Key_2:
            self.vel_curve = "soft"; self.vel_label.setText("Vel curve: soft")
        elif k == Qt.Key_3:
            self.vel_curve = "hard"; self.vel_label.setText("Vel curve: hard")
        elif k == Qt.Key_Q:
            q = self.layout_model.quantize_scale or "chromatic"
            self.layout_model.quantize_scale = "chromatic" if q != "chromatic" else "major"
        elif k == Qt.Key_Escape:
            self.all_notes_off()

    def all_notes_off(self):
        for note, ch in list(self.active_notes):
            self.midi.note_off(note, ch)
        self.active_notes.clear()
        self._voice_order.clear()
        # Clear all pressed visuals
        try:
            for btn in self.key_buttons.values():
                self._apply_btn_visual(btn, False, False)
        except Exception:
            pass

    def _clear_other_actives(self, except_btn: QPushButton | None):
        """Ensure only except_btn (if any) is visually active. Clear all others."""
        try:
            for b in self.key_buttons.values():
                if b is except_btn:
                    # Ensure it stays active
                    if b.property('active') != 'true':
                        self._apply_btn_visual(b, True, False)
                    continue
                # Unconditionally clear both active and held for all others
                self._apply_btn_visual(b, False, False)
        except Exception:
            pass

    # ---- Polyphony setters ----
    def set_polyphony_enabled(self, enabled: bool):
        self.polyphony_enabled = bool(enabled)
        if not self.polyphony_enabled:
            # Unlimited: no action needed; existing voices persist
            return

    def set_polyphony_max(self, maximum: int):
        self.polyphony_max = max(1, min(8, int(maximum)))
        if not self.polyphony_enabled:
            return
        # If over the limit right now, steal oldest until compliant
        try:
            while len(self.active_notes) > self.polyphony_max and self._voice_order:
                old_note, old_ch, old_base = self._voice_order.pop(0)
                try:
                    self.midi.note_off(old_note, old_ch)
                except Exception:
                    pass
                self.active_notes.discard((old_note, old_ch))
                self._apply_note_visual(old_base, False, False)
        except Exception:
            pass

    # ---- MIDI and title helpers ----
    def set_midi_out(self, midi_out: MidiOut, port_name: str | None = None):
        """Swap the MIDI output device for this keyboard and update title."""
        # Stop any currently sounding notes before switching (no flash)
        self._perform_all_notes_off()
        self.midi = midi_out
        if port_name is not None:
            self.port_name = port_name
        self.update_window_title()

    def update_window_title(self):
        # Use the layout's computed name (already reflects total key count correctly)
        base = getattr(self.layout_model, 'name', 'Keyboard')
        port_suffix = f" -> {self.port_name}" if self.port_name else ""
        ch_suffix = f" [Ch {self.midi_channel + 1}]"
        self.setWindowTitle(f"{base}{port_suffix}{ch_suffix}")

    def all_notes_off_clicked(self):
        """UI handler: flash blue, then clear all active notes and visuals."""
        try:
            self._flash_all_off_button()
        except Exception:
            pass
        self._perform_all_notes_off()

    def _perform_all_notes_off(self):
        """Clear all active notes, pressed visuals, and any drag state (no flash)."""
        self.all_notes_off()
        if self.last_drag_button is not None:
            self._apply_btn_visual(self.last_drag_button, False, False)
        self.last_drag_button = None
        self.last_drag_key = None
        self._last_drag_note_base = None
        self.dragging = False
        try:
            self.piano_container.releaseMouse()
        except Exception:
            pass

    def _flash_all_off_button(self, duration_ms: int = 150):
        """Temporarily set All Notes Off button to blue to indicate action, then revert."""
        btn = getattr(self, 'all_off_btn', None)
        if not isinstance(btn, QPushButton):
            return
        try:
            base_qss = getattr(self, '_all_off_btn_base_qss', str(btn.styleSheet()))
        except Exception:
            base_qss = ""
        # Blue flash style matching Sustain/Latch blue
        flash_qss = (
            "QPushButton {"
            "  padding: 1px 4px;"
            "  min-height: 0px;"
            "  border-radius: 3px;"
            "  color: white;"
            "  background-color: #3498db;"
            "  border: 1px solid #2980b9;"
            "}"
            "QPushButton:hover { background-color: #2f8ccc; }"
            "QPushButton:pressed { background-color: #2a7fb8; }"
        )
        try:
            btn.setStyleSheet(flash_qss)
        except Exception:
            return
        # Revert after delay
        try:
            QTimer.singleShot(max(50, int(duration_ms)), lambda b=btn, q=base_qss: b.setStyleSheet(q))
        except Exception:
            # Fallback: immediate revert if timer unavailable
            try:
                btn.setStyleSheet(base_qss)
            except Exception:
                pass

    def set_channel(self, channel_1_based: int):
        """Set MIDI channel (1-16). Sends All Notes Off and updates title."""
        channel_1_based = max(1, min(16, channel_1_based))
        if self.midi_channel == channel_1_based - 1:
            return
        self._perform_all_notes_off()
        self.midi_channel = channel_1_based - 1
        self.update_window_title()

    # ---- Mod wheel / Pitch bend helpers ----
    def _send_mod_cc(self, value: int):
        """Send Modulation (CC1) on current channel."""
        try:
            v = max(0, min(127, int(value)))
        except Exception:
            v = 0
        try:
            self.midi.cc(1, v, self.midi_channel)
        except Exception:
            pass

    def _send_pitch_bend(self, value: int):
        """Send pitch bend value in [-8192, 8191] on current channel."""
        try:
            self.midi.pitch_bend(int(value), self.midi_channel)
        except Exception:
            pass

    def _stop_pitch_anim(self):
        anim = getattr(self, '_pitch_anim', None)
        if anim is not None:
            try:
                anim.stop()
            except Exception:
                pass
        self._pitch_anim = None

    def _animate_pitch_to_center(self):
        """Smoothly animate pitch wheel back to center (0) on release."""
        try:
            self._stop_pitch_anim()
            anim = QPropertyAnimation(self.pitch_slider, b"value")
            anim.setDuration(160)
            anim.setStartValue(int(self.pitch_slider.value()))
            anim.setEndValue(0)
            try:
                anim.setEasingCurve(QEasingCurve.OutCubic)
            except Exception:
                pass
            # Keep a reference so GC doesn't kill the animation
            self._pitch_anim = anim
            def _clear_anim():
                self._pitch_anim = None
            try:
                anim.finished.connect(_clear_anim)
            except Exception:
                pass
            anim.start()
        except Exception:
            # If animation fails, snap to center
            try:
                self.pitch_slider.setValue(0)
            except Exception:
                pass
