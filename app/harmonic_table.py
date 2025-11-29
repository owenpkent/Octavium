from typing import Tuple
from types import SimpleNamespace
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, QLabel, QSlider, QCheckBox, QApplication
from PySide6.QtCore import Qt, QSize, QPoint, QEvent, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush

from .midi_io import MidiOut
# Try to reuse the RangeSlider from keyboard_widget; if unavailable (e.g., during
# import ordering), fall back to a minimal local implementation so the widget
# still loads and the view can switch correctly.
try:
    from .keyboard_widget import RangeSlider  # type: ignore
except Exception:
    class RangeSlider(QWidget):  # type: ignore
        def __init__(self, minimum=1, maximum=127, low=64, high=100, parent=None):
            super().__init__(parent)
            self._min = int(minimum)
            self._max = int(maximum)
            self._low = int(low)
            self._high = int(high)
            self.setFixedHeight(22)
        def setRange(self, minimum: int, maximum: int):
            self._min = int(minimum); self._max = int(maximum)
        def setValues(self, low: int, high: int):
            self._low, self._high = int(low), int(high)
        def values(self):
            return int(self._low), int(self._high)
try:
    from .keyboard_widget import DragReferenceSlider  # type: ignore
except Exception:
    class DragReferenceSlider(QSlider):  # type: ignore
        def __init__(self, orientation=Qt.Vertical, parent=None):
            super().__init__(orientation, parent)
            # Fallback behaves like a normal vertical slider
            self.setOrientation(orientation)
import random


class HexButton(QPushButton):
    """Custom painted hexagonal button in the app's blue theme with octave-based colors."""
    
    # Octave color palette - distinct colors per octave for visual clarity
    # Format: (fill_color, border_color)
    OCTAVE_COLORS = [
        ('#1a1a2e', '#2d2d4a'),  # -1: Deep navy
        ('#1e2a3a', '#2f4562'),  # 0: Dark slate blue
        ('#1a2f2f', '#2d4a4a'),  # 1: Dark teal
        ('#1f2d1f', '#334a33'),  # 2: Dark forest
        ('#2a2a1e', '#454530'),  # 3: Dark olive
        ('#2d2424', '#4a3838'),  # 4: Dark burgundy (middle C area)
        ('#2d1f2d', '#4a334a'),  # 5: Dark plum
        ('#1f1f2d', '#33334a'),  # 6: Dark indigo
        ('#1a2a2a', '#2d4545'),  # 7: Dark cyan
        ('#2a1f1a', '#45332d'),  # 8: Dark brown
        ('#1f2a1f', '#334533'),  # 9: Dark sage
    ]
    
    def __init__(self, label: str, size_px: int, parent=None, note: int = 60):
        super().__init__(label, parent)
        # Non-latching (momentary) behavior by default
        self.setCheckable(False)
        # Visual latch flag managed by owner widget
        self._latched: bool = False
        self._active: bool = False  # For duplicate note highlighting
        self._note: int = note  # Store the MIDI note for octave coloring
        self._size = int(size_px)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        # Remove native styling; we paint everything
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        # Flat-top hex proper aspect ratio: H = sqrt(3)/2 * W
        self._height = int(self._size * 0.8660254)
        self.setFixedSize(self._size, self._height)

    # Forward drag moves to owner so we can glide notes
    def mouseMoveEvent(self, ev):  # type: ignore[override]
        try:
            if ev.buttons() & Qt.LeftButton:
                owner = getattr(self, "_owner", None)
                if owner is not None:
                    try:
                        gp = ev.globalPosition().toPoint()
                    except Exception:
                        try:
                            gp = ev.globalPos()
                        except Exception:
                            gp = None
                    if gp is not None:
                        try:
                            owner._drag_update_from_global(gp)
                        except Exception:
                            pass
        except Exception:
            pass
        return super().mouseMoveEvent(ev)

    

    def _hex_path(self) -> QPainterPath:
        # Use the actual widget width/height so the path matches the visual size
        W = float(self.width())
        H = float(self.height())
        # Flat-top hex exact vertices using full widget rect (no extra margin)
        m = 0.0
        w = W - 2 * m
        h = H - 2 * m
        x0 = m
        x1 = m + 0.25 * w
        x2 = m + 0.75 * w
        x3 = m + w
        y0 = m
        y1 = m + 0.5 * h
        y2 = m + h
        pts = [
            QPoint(int(x3), int(y1)),  # right
            QPoint(int(x2), int(y2)),  # bottom-right
            QPoint(int(x1), int(y2)),  # bottom-left
            QPoint(int(x0), int(y1)),  # left
            QPoint(int(x1), int(y0)),  # top-left
            QPoint(int(x2), int(y0)),  # top-right
        ]
        
        path = QPainterPath()
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        path.closeSubpath()
        return path

    def _get_octave_colors(self) -> tuple[str, str]:
        """Get fill and border colors based on the note's octave."""
        try:
            octave = (self._note // 12) - 1  # MIDI octave (-1 to 9)
            idx = max(0, min(len(self.OCTAVE_COLORS) - 1, octave + 1))
            return self.OCTAVE_COLORS[idx]
        except Exception:
            return ('#1b1f24', '#3b4148')
    
    def paintEvent(self, ev):  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = self._hex_path()
        
        # Background: show active style when pressed, latched, or duplicate-highlighted
        is_active = self.isDown() or getattr(self, "_latched", False) or getattr(self, "_active", False)
        
        if is_active:
            fill = QColor('#2f82e6')
            text = QColor('white')
            border = QColor('#61b3ff')
        else:
            # Use octave-based coloring for inactive state
            fill_hex, border_hex = self._get_octave_colors()
            fill = QColor(fill_hex)
            text = QColor('#cfe7ff')
            border = QColor(border_hex)
        
        p.fillPath(path, QBrush(fill))
        pen = QPen(border)
        pen.setWidth(2 if is_active else 1)
        p.setPen(pen)
        p.drawPath(path)
        
        # Label with dynamic font sizing relative to hex width
        p.setPen(text)
        try:
            f = p.font()
            # Roughly 20-24% of hex width looks balanced
            fs = max(8.0, float(self._size) * 0.22)
            f.setPointSizeF(fs)
            p.setFont(f)
        except Exception:
            pass
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()

    # Allow dynamic resizing of the hex without recreating the button
    def set_pixel_size(self, size_px: int):
        try:
            size_px = int(size_px)
            if size_px <= 0:
                return
            self._size = size_px
            self._height = int(self._size * 0.8660254)
            self.setFixedSize(self._size, self._height)
            self.update()
        except Exception:
            pass


class HarmonicTableWidget(QWidget):
    """Isomorphic Harmonic Table layout with a hex-style staggered grid of buttons.

    Mapping used here (flat-top, odd-q offset):
    - Up (same column): +7 semitones (perfect fifth)
    - Upper-right: +4 semitones (major third)
    - Upper-left:  +3 semitones (minor third)
    Horizontal neighbors are parity-dependent and may shift by -3/+?; the three listed
    musical adjacencies are guaranteed regardless of column parity.

    We render a rectangular footprint using a flat-top hex grid with odd-q offset
    (columns are vertically offset by half a hex). This produces a tidy rectangle
    while preserving isomorphic harmonic adjacency.
    """
    def __init__(self, midi_out: MidiOut, scale: float = 1.0,
                 rows: int = 9, cols: int = 18,
                 base_note: int = 24,  # C1 starting octave for a lower overall range
                 # Interval mapping (flat-top, odd-q offset):
                 # We construct a parity-aware column term so visual neighbors are:
                 #   - Up (visually above, even columns) .......... +7 (perfect fifth)
                 #   - Upper-right (UR) ........................... +4 (major third)
                 #   - Upper-left  (UL) ........................... +3 (minor third)
                 # This matches the provided diagram and keeps lower notes at the bottom.
                 # step_y defines the vertical row increment (default 7). step_x is unused in
                 # the parity mapping but kept for API parity.
                 step_x: int = 1, step_y: int = 7):
        super().__init__()
        self.midi: MidiOut = midi_out
        self.port_name: str = ""
        try:
            self.ui_scale = float(scale) if float(scale) > 0 else 1.0
        except Exception:
            self.ui_scale = 1.0
        self.midi_channel: int = 0
        self.rows = int(rows)
        self.cols = int(cols)
        self.base_note = int(base_note)
        self.step_x = int(step_x)
        self.step_y = int(step_y)
        self.layout_model = SimpleNamespace(name="Harmonic Table", columns=self.cols)
        self.setWindowTitle("Harmonic Table")
        try:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(int(10 * self.ui_scale), int(8 * self.ui_scale), int(10 * self.ui_scale), int(10 * self.ui_scale))
        root.setSpacing(int(8 * self.ui_scale))

        # --- Header controls (Sustain, Latch, All Notes Off, Velocity) ---
        self.sustain: bool = False
        self.latch: bool = False
        self._active_notes: set[int] = set()
        self._latched_notes: set[int] = set()
        self._sustained_notes: set[int] = set()

        # Header controls inside a container widget so we can measure its sizeHint accurately
        controls_widget = QWidget(self)
        header = QHBoxLayout(controls_widget)
        controls_widget.setLayout(header)
        header.setContentsMargins(0, 0, 0, 0)
        try:
            header.setSpacing(max(4, int(8 * self.ui_scale)))
        except Exception:
            header.setSpacing(8)

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

        # Velocity controls: single slider and randomized range (lowered by 20% to match keyboard)
        self.vel_label = QLabel("Velocity")
        self.vel_slider = QSlider(Qt.Horizontal)
        self.vel_slider.setMinimum(1)
        self.vel_slider.setMaximum(127)
        self.vel_slider.setValue(80)
        self.vel_random_chk = QCheckBox("Randomize")
        self.vel_random_chk.setChecked(True)
        self.vel_range = RangeSlider(1, 127, low=64, high=88, parent=self)
        # Toggle behavior like the piano header
        try:
            self.vel_random_chk.toggled.connect(lambda checked: self._toggle_vel_random(checked))
            # Ensure initial visibility matches checked state
            self._toggle_vel_random(self.vel_random_chk.isChecked())
        except Exception:
            pass

        header.addWidget(self.sustain_btn)
        header.addWidget(self.latch_btn)
        header.addWidget(self.all_off_btn)
        header.addStretch()
        header.addWidget(self.vel_label)
        header.addWidget(self.vel_slider)
        header.addWidget(self.vel_random_chk)
        header.addWidget(self.vel_range)
        # Keep a reference for sizing and external usage
        self.controls_widget = controls_widget
        root.addWidget(controls_widget)

        # Apply unified slider styling (matching keyboard) and sizes
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
                f"QSlider::groove:horizontal {{ height: {gh}px; background: #3a3f46; border: 1px solid #2a2f35; border-radius: 3px; }}"
                "QSlider::sub-page:horizontal { background: #61b3ff; border: 1px solid #2f82e6; border-radius: 3px; }"
                "QSlider::add-page:horizontal { background: transparent; }"
                f"QSlider::handle:horizontal {{ width: {hw}px; height: {hh}px; background: #eaeaea; border: 1px solid #5a5f66; border-radius: 3px; margin: -{m}px 0; }}"
                f"QSlider::groove:vertical {{ width: {vmw}px; background: #3a3f46; border: 1px solid #2a2f35; border-radius: 3px; }}"
                "QSlider::sub-page:vertical { background: transparent; }"
                "QSlider::add-page:vertical { background: #61b3ff; border: 1px solid #2f82e6; border-radius: 3px; }"
                f"QSlider::handle:vertical {{ height: {vhh}px; width: {vhw}px; background: #eaeaea; border: 1px solid #5a5f66; border-radius: 3px; margin: 0 -{m}px; }}"
                "border: 1px solid #444; border-radius: 3px;"
            )
            self._slider_qss = slider_qss
            self.vel_slider.setStyleSheet(slider_qss)
            # Dedicated thicker style for vertical wheels (wider groove/handle for easier grabbing)
            vmw2 = int(24 * s)   # groove width
            vhw2 = int(26 * s)   # handle width
            vhh2 = int(28 * s)   # handle height
            m2 = int(6 * s)
            self._wheel_qss = (
                f"QSlider::groove:vertical {{ width: {vmw2}px; background: #3a3f46; border: 1px solid #2a2f35; border-radius: 4px; }}"
                "QSlider::sub-page:vertical { background: transparent; }"
                "QSlider::add-page:vertical { background: #61b3ff; border: 1px solid #2f82e6; border-radius: 4px; }"
                f"QSlider::handle:vertical {{ height: {vhh2}px; width: {vhw2}px; background: #eaeaea; border: 1px solid #5a5f66; border-radius: 4px; margin: 0 -{m2}px; }}"
            )
            # Widths/heights similar to piano
            base_w = int(200 * s)
            self._base_slider_width = base_w
            self.vel_slider.setFixedWidth(base_w)
            self.vel_range.setFixedWidth(base_w)
            self.vel_slider.setFixedHeight(int(16 * s))
            self.vel_range.setFixedHeight(int(20 * s))
            self.vel_slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.vel_range.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.vel_label.setStyleSheet(f"font-size: {max(9, int(11 * s))}px; color: #ddd;")
        except Exception:
            pass

        

        # Absolute-positioned honeycomb using axial coordinates (flat-top)
        self.buttons: list[list[QPushButton]] = []
        self.notes: list[list[int | None]] = []
        self._recompute_grid()

        grid = QWidget(self)
        grid.setObjectName("harmonic_grid")
        grid.setMouseTracking(True)
        # --- Left-side wheels panel (Mod/Pitch) ---
        self.show_mod_wheel = False
        self.show_pitch_wheel = False
        self.left_panel = QWidget(self)
        try:
            # Expand vertically to match the grid height; keep width fixed
            self.left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        except Exception:
            pass
        lp_layout = QVBoxLayout()
        lp_layout.setContentsMargins(6, 2, 6, 2)
        lp_layout.setSpacing(8)
        # Build columns stacked vertically to keep panel narrow
        self.mod_slider = DragReferenceSlider(Qt.Vertical)
        try:
            self.mod_slider.setMinimum(0)
            self.mod_slider.setMaximum(127)
            self.mod_slider.setValue(0)
            self.mod_slider.setTickPosition(QSlider.NoTicks)
            self.mod_slider.valueChanged.connect(lambda v: self._send_mod_cc(v))
            # 4x wider
            self.mod_slider.setFixedWidth(int(28 * 4 * self.ui_scale))
            # Expand vertically to use full available height
            self.mod_slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            try:
                # Apply thicker wheel style
                self.mod_slider.setStyleSheet(getattr(self, '_wheel_qss', self._slider_qss))
            except Exception:
                pass
        except Exception:
            pass
        self.mod_lbl = QLabel("Mod")
        try:
            self.mod_lbl.setAlignment(Qt.AlignHCenter)
            self.mod_lbl.setStyleSheet(f"font-size: {max(8, int(9 * self.ui_scale))}px; color: #ddd;")
        except Exception:
            pass
        mod_col = QVBoxLayout()
        mod_col.setContentsMargins(0, 0, 0, 0)
        mod_col.setSpacing(4)
        mod_col.addWidget(self.mod_slider, 1)
        mod_col.addWidget(self.mod_lbl, 0)

        self.pitch_slider = DragReferenceSlider(Qt.Vertical)
        try:
            self.pitch_slider.setMinimum(-8192)
            self.pitch_slider.setMaximum(8191)
            self.pitch_slider.setValue(0)
            self.pitch_slider.setTickPosition(QSlider.NoTicks)
            self.pitch_slider.valueChanged.connect(lambda v: self._send_pitch_bend(v))
            # 4x wider
            self.pitch_slider.setFixedWidth(int(28 * 4 * self.ui_scale))
            # Expand vertically to use full available height
            self.pitch_slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
            try:
                # Apply thicker wheel style
                self.pitch_slider.setStyleSheet(getattr(self, '_wheel_qss', self._slider_qss))
            except Exception:
                pass
        except Exception:
            pass
        # Inertial return-to-center for pitch wheel
        self._pitch_anim = None
        try:
            self.pitch_slider.sliderReleased.connect(self._animate_pitch_to_center)
            self.pitch_slider.sliderPressed.connect(self._stop_pitch_anim)
        except Exception:
            pass
        self.pitch_lbl = QLabel("Pitch")
        try:
            self.pitch_lbl.setAlignment(Qt.AlignHCenter)
            self.pitch_lbl.setStyleSheet(f"font-size: {max(8, int(9 * self.ui_scale))}px; color: #ddd;")
        except Exception:
            pass
        pitch_col = QVBoxLayout()
        pitch_col.setContentsMargins(0, 0, 0, 0)
        pitch_col.setSpacing(4)
        pitch_col.addWidget(self.pitch_slider, 1)
        pitch_col.addWidget(self.pitch_lbl, 0)

        # Wrap columns into a horizontal row inside the panel
        wheels_row = QHBoxLayout()
        wheels_row.setContentsMargins(0, 0, 0, 0)
        wheels_row.setSpacing(12)
        wheels_row.addLayout(mod_col, 1)
        wheels_row.addLayout(pitch_col, 1)
        self._mod_col = mod_col
        self._pitch_col = pitch_col
        lp_layout.addLayout(wheels_row)
        self.left_panel.setLayout(lp_layout)
        self.left_panel.setVisible(False)

        # Keys row: left panel + grid
        keys_row = QHBoxLayout()
        try:
            s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
            keys_row.setSpacing(max(4, int(8 * s)))
            self._keys_row_spacing = int(keys_row.spacing())
        except Exception:
            keys_row.setSpacing(8)
            self._keys_row_spacing = 8
        keys_row.setContentsMargins(0, 0, 0, 0)
        keys_row.addWidget(self.left_panel)
        keys_row.addWidget(grid, 1)
        root.addLayout(keys_row)

        # Geometry: flat-top hexes with odd-q vertical offset (rectangular footprint)
        # Compute size and auto-fit to screen if necessary by scaling hex width.
        import math
        base_size_px = int(60 * self.ui_scale)  # hex width = 2 * radius
        # Remember the unscaled base so we always scale from a stable reference
        self._base_hex_size_px = int(base_size_px)
        # Dynamic margin: ensure at least half a hex so children are never placed at negative coords
        def compute_grid_wh(size_px: int) -> tuple[int, int, int, int, int]:
            s = size_px / 2.0
            H = int(round(math.sqrt(3.0) * s))
            max_q = self.cols - 1
            max_r = self.rows - 1
            cx_max = s * 1.5 * max_q
            cy_max = H * max_r + (H / 2 if self.cols > 1 else 0)
            # Margin must be >= half the hex width to avoid clipping at left/top
            margin_dyn = max(int(12 * self.ui_scale), int(math.ceil(size_px / 2.0)))
            # Width needs full size on right plus half-size on left => cx_max + size_px (+ margin both sides)
            grid_w = int(math.ceil(cx_max + size_px)) + margin_dyn * 2
            # Height needs full H on bottom plus half H on top
            grid_h = int(math.ceil(cy_max + H)) + margin_dyn * 2
            return grid_w, grid_h, H, size_px, margin_dyn

        # Start at base hex size and let MainWindow resize the window to fit
        grid_w, grid_h, H, size_px, margin = compute_grid_wh(base_size_px)
        self._hex_size_px = int(size_px)
        grid.setFixedSize(grid_w, grid_h)

        # Drag state for click-and-drag playing
        self.drag_active: bool = False
        self._drag_current: tuple[int, int] | None = None
        self._grid = grid
        self._mouse_grabbed: bool = False
        try:
            self._grid.installEventFilter(self)
        except Exception:
            pass
        # Cache for resize-to-fit to avoid thrashing
        self._last_fit_key: tuple[int, int, int, int, int] | None = None

        # Build a map of note -> list of buttons for duplicate highlighting
        self._note_to_buttons: dict[int, list[HexButton]] = {}
        # Track right-click latched notes separately
        self._right_click_latched: set[int] = set()
        
        for r in range(self.rows):
            row_btns: list[QPushButton] = []
            row_notes: list[int] = []
            for q in range(self.cols):
                note = self.notes[r][q]
                row_notes.append(note)
                label = self._note_name(note) if (note is not None and 0 <= note <= 127) else ""
                b = HexButton(label, self._hex_size_px, grid, note=note if note is not None else 60)
                # centers (flat-top, odd-q offset rectangle)
                s = self._hex_size_px / 2.0
                cx = s * 1.5 * q
                cy = H * r + (H / 2 if (q % 2) == 1 else 0)
                # top-left position
                x = int(round(cx - self._hex_size_px / 2.0)) + margin
                y = int(round(cy - H / 2.0)) + margin
                b.move(x, y)
                # Store coordinates on the button for quick lookup during drag
                try:
                    setattr(b, "_rq", (r, q))
                except Exception:
                    pass
                # Ensure we receive move events while pressed, and also for hover polish
                try:
                    b.setMouseTracking(True)
                    b.installEventFilter(self)
                    setattr(b, "_owner", self)
                except Exception:
                    pass
                if note is not None and 0 <= note <= 127:
                    # Route to handlers that support drag glide
                    b.pressed.connect(lambda r=r, q=q: self._handle_press(r, q))
                    b.released.connect(lambda r=r, q=q: self._handle_release(r, q))
                    b.setEnabled(True)
                    # Add to note->buttons map for duplicate highlighting
                    if note not in self._note_to_buttons:
                        self._note_to_buttons[note] = []
                    self._note_to_buttons[note].append(b)
                else:
                    b.setEnabled(False)
                row_btns.append(b)
            self.buttons.append(row_btns)
            self.notes.append(row_notes)
        self.setLayout(root)

    def showEvent(self, ev):  # type: ignore[override]
        super().showEvent(ev)
        # No dynamic rescale here; initial size is computed once based on screen.
        return

    def resizeEvent(self, ev):  # type: ignore[override]
        super().resizeEvent(ev)
        # Keep size; no auto-rescale on resize.
        return

    def _rescale_to_window_fit(self):
        # Disabled: initial sizing now handled in __init__ based on screen.
        return

    def sizeHint(self) -> QSize:  # type: ignore[override]
        try:
            size_px = int(getattr(self, '_hex_size_px', int(60 * self.ui_scale)))
            s = size_px / 2.0
            import math
            H = int(round(math.sqrt(3.0) * s))
            max_q = self.cols - 1
            max_r = self.rows - 1
            cx_max = s * 1.5 * max_q
            cy_max = H * max_r + (H / 2 if self.cols > 1 else 0)
            # Use the same dynamic margin and extents as grid construction
            margin = max(int(12 * self.ui_scale), int(math.ceil(size_px / 2.0)))
            grid_w = int(math.ceil(cx_max + size_px)) + margin * 2
            # Compare with header width, include root side margins
            try:
                header_w = int(self.controls_widget.sizeHint().width())
            except Exception:
                header_w = 0
            try:
                m_left, m_top, m_right, m_bottom = self.layout().contentsMargins().getCoords()  # type: ignore[attr-defined]
                root_lr = abs(m_left) + abs(m_right)
            except Exception:
                root_lr = int(20 * self.ui_scale)
            # Include left panel when visible
            try:
                left_w = int(self.left_panel.sizeHint().width()) if self.left_panel.isVisible() else 0
            except Exception:
                left_w = 0
            try:
                gap = int(getattr(self, '_keys_row_spacing', 8)) if self.left_panel.isVisible() else 0
            except Exception:
                gap = 0
            content_w = grid_w + left_w + gap
            # Very small safety buffer to avoid right-edge clipping from DPI/titlebar rounding
            w = max(content_w, header_w + root_lr) + 2
            # Include header height and root spacing in the size hint so the window sizes correctly
            try:
                header_h = int(self.controls_widget.sizeHint().height())
            except Exception:
                header_h = int(40 * self.ui_scale)
            try:
                root_spacing = int(self.layout().spacing()) if self.layout() is not None else 6
            except Exception:
                root_spacing = 6
            # Very small safety buffer on height to avoid bottom clipping
            h = int(math.ceil(cy_max + H)) + margin * 2 + header_h + root_spacing + 4
            return QSize(w, h)
        except Exception:
            return QSize(900, 420)

    # --- Wheels visibility and MIDI ---
    def _update_left_panel_visibility(self):
        try:
            any_wheels = bool(self.show_mod_wheel or self.show_pitch_wheel)
            self.left_panel.setVisible(any_wheels)
            # Toggle sub-columns individually
            try:
                for w in (self.mod_slider, self.mod_lbl):
                    w.setVisible(bool(self.show_mod_wheel))
            except Exception:
                pass
            try:
                for w in (self.pitch_slider, self.pitch_lbl):
                    w.setVisible(bool(self.show_pitch_wheel))
            except Exception:
                pass
            # Recompute size
            self.left_panel.updateGeometry()
            self.updateGeometry()
        except Exception:
            pass

    def set_show_mod_wheel(self, checked: bool):
        self.show_mod_wheel = bool(checked)
        self._update_left_panel_visibility()

    def set_show_pitch_wheel(self, checked: bool):
        self.show_pitch_wheel = bool(checked)
        self._update_left_panel_visibility()

    def _send_mod_cc(self, value: int):
        try:
            self.midi.cc(1, int(value), self.midi_channel)
        except Exception:
            pass

    def _send_pitch_bend(self, value: int):
        try:
            self.midi.pitch_bend(int(value), self.midi_channel)
        except Exception:
            pass

    def _animate_pitch_to_center(self):
        try:
            # Stop any running animation
            self._stop_pitch_anim()
            anim = QPropertyAnimation(self.pitch_slider, b"value", self)
            anim.setDuration(350)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            try:
                anim.setStartValue(int(self.pitch_slider.value()))
            except Exception:
                pass
            anim.setEndValue(0)
            # Keep a reference so it isn't garbage-collected
            self._pitch_anim = anim
            anim.start()
        except Exception:
            pass

    def _stop_pitch_anim(self):
        try:
            if self._pitch_anim is not None:
                self._pitch_anim.stop()
                self._pitch_anim = None
        except Exception:
            self._pitch_anim = None

    # Mapping helpers
    def _recompute_grid(self):
        # Map notes using a parity-aware affine mapping on visual rows/cols.
        # Base is placed at bottom-left cell (row = rows-1, col = 0)
        # Orientation: LOWER notes at the BOTTOM. Moving upward increases pitch.
        # Neighbor intervals (independent of column parity):
        #   Up (even cols) = +7, UR = +4, UL = +3.
        rows, cols = self.rows, self.cols
        notes: list[list[int | None]] = [[None for _ in range(cols)] for __ in range(rows)]
        if rows == 0 or cols == 0:
            self.notes = notes
            return
        base = int(self.base_note)
        step_r = int(self.step_y)  # per one visual row upward (perfect fifth)
        last_row = rows - 1
        for r in range(rows):
            for q in range(cols):
                # Visual mapping: parity-aware column term ensures consistent diagonals
                # col_term = 0.5*q - 3.5*(q%2) which is always an integer:
                #   = floor(q/2) - 3 if q odd, else floor(q/2)
                if (q % 2) == 1:
                    col_term = (q // 2) - 3
                else:
                    col_term = (q // 2)
                dr = last_row - r  # rows above the bottom
                n = base + col_term + step_r * dr
                notes[r][q] = n
        self.notes = notes

    @staticmethod
    def _note_name(n: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        if n < 0:
            n = 0
        if n > 127:
            n = 127
        # Use octave numbering one lower than the default (middle C = C3 if MIDI 60)
        octave = (n // 12) - 2
        return f"{names[n % 12]}{octave}"

    # --- Controls logic (velocity, sustain, latch, panic) ---
    def _compute_velocity(self) -> int:
        try:
            if self.vel_random_chk.isChecked():
                low, high = self.vel_range.values()
                if low > high:
                    low, high = high, low
                return int(max(1, min(127, random.randint(int(low), int(high)))))
            return int(max(1, min(127, self.vel_slider.value())))
        except Exception:
            return 100

    def _send_note_on(self, note: int):
        v = self._compute_velocity()
        try:
            self.midi.note_on(int(note), v, self.midi_channel)
            self._active_notes.add(int(note))
        except Exception:
            pass
        # Highlight all duplicate buttons for this note
        self._set_note_active(note, True)

    def _send_note_off(self, note: int):
        try:
            self.midi.note_off(int(note), self.midi_channel)
        except Exception:
            pass
        self._active_notes.discard(int(note))
        self._sustained_notes.discard(int(note))
        self._latched_notes.discard(int(note))
        # Unhighlight all duplicate buttons for this note (unless right-click latched)
        if note not in self._right_click_latched:
            self._set_note_active(note, False)
    
    def _set_note_active(self, note: int, active: bool):
        """Set the _active flag on all buttons for a given note (for duplicate highlighting)."""
        try:
            buttons = self._note_to_buttons.get(note, [])
            for btn in buttons:
                btn._active = active
                btn.update()
        except Exception:
            pass
    
    def _handle_right_click(self, r: int, c: int):
        """Handle right-click on a hex as a latch toggle (independent of global latch mode)."""
        try:
            note = int(self.notes[r][c])
        except Exception:
            return
        
        btn = self.buttons[r][c]
        
        if note in self._right_click_latched:
            # Note is already latched - turn it off
            self._send_note_off(note)
            self._right_click_latched.discard(note)
            self._set_note_active(note, False)
            try:
                btn._latched = False
                btn.update()
            except Exception:
                pass
        else:
            # Note is not latched - turn it on and latch it
            self._send_note_on(note)
            self._right_click_latched.add(note)
            self._set_note_active(note, True)
            try:
                btn._latched = True
                btn.update()
            except Exception:
                pass

    def toggle_sustain(self):
        try:
            self.sustain = bool(self.sustain_btn.isChecked())
            self.sustain_btn.setText("Sustain: On" if self.sustain else "Sustain: Off")
        except Exception:
            self.sustain = False
        # If turning sustain off, release any notes that were sustained (not held)
        if not self.sustain and getattr(self, "_sustained_notes", None):
            for n in list(self._sustained_notes):
                self._send_note_off(n)
            self._sustained_notes.clear()

    def toggle_latch(self):
        try:
            self.latch = bool(self.latch_btn.isChecked())
            self.latch_btn.setText("Latch: On" if self.latch else "Latch: Off")
        except Exception:
            self.latch = False

    def all_notes_off_clicked(self):
        # Flash button like the piano keyboard, then perform note-offs
        try:
            self._flash_all_off_button()
        except Exception:
            pass
        self._perform_all_notes_off()

    def _perform_all_notes_off(self):
        # Send All Sound Off + All Notes Off + explicit note_offs for tracked and full range
        try:
            # CC120: All Sound Off, CC123: All Notes Off
            self.midi.cc(120, 0, self.midi_channel)
            self.midi.cc(123, 0, self.midi_channel)
        except Exception:
            pass
        notes_to_stop = set()
        try:
            notes_to_stop |= set(self._active_notes)
            notes_to_stop |= set(self._sustained_notes)
            notes_to_stop |= set(self._latched_notes)
            notes_to_stop |= set(self._right_click_latched)
        except Exception:
            pass
        for n in list(notes_to_stop):
            try:
                self.midi.note_off(int(n), self.midi_channel)
            except Exception:
                pass
        # Belt-and-suspenders: stop all 0..127
        try:
            for n in range(128):
                self.midi.note_off(n, self.midi_channel)
        except Exception:
            pass
        self._active_notes.clear()
        self._sustained_notes.clear()
        self._latched_notes.clear()
        self._right_click_latched.clear()
        # Clear visuals and drag state
        try:
            for row in self.buttons:
                for btn in row:
                    try:
                        btn._latched = False
                        btn._active = False
                    except Exception:
                        pass
                    btn.setDown(False)
                    btn.update()
        except Exception:
            pass
        self.drag_active = False
        self._drag_current = None
        if getattr(self, '_mouse_grabbed', False):
            try:
                self._grid.releaseMouse()
            except Exception:
                pass
            self._mouse_grabbed = False

    def _flash_all_off_button(self, duration_ms: int = 150):
        btn = getattr(self, 'all_off_btn', None)
        if not isinstance(btn, QPushButton):
            return
        try:
            base_qss = getattr(self, '_all_off_btn_base_qss', str(btn.styleSheet()))
        except Exception:
            base_qss = ""
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
        try:
            QTimer.singleShot(max(50, int(duration_ms)), lambda b=btn, q=base_qss: b.setStyleSheet(q))
        except Exception:
            try:
                btn.setStyleSheet(base_qss)
            except Exception:
                pass

    # --- Drag helpers ---
    def _set_button_active(self, coords: tuple[int, int] | None, active: bool):
        if coords is None:
            return
        r, c = coords
        try:
            btn = self.buttons[r][c]
        except Exception:
            return
        try:
            btn.setDown(bool(active))
            btn.update()
        except Exception:
            pass
        self._on_btn(r, c, active)

    def _handle_press(self, r: int, c: int):
        # Latch mode: toggle note on press and do not engage drag
        if self.latch:
            try:
                note = int(self.notes[r][c])
            except Exception:
                return
            btn = self.buttons[r][c]
            if note in self._latched_notes:
                self._send_note_off(note)
                self._latched_notes.discard(note)
                try:
                    btn._latched = False
                    btn.setDown(False)
                    btn.update()
                except Exception:
                    pass
            else:
                self._send_note_on(note)
                self._latched_notes.add(note)
                try:
                    btn._latched = True
                    btn.setDown(True)
                    btn.update()
                except Exception:
                    pass
            # Ensure drag state is off in latch
            if self.drag_active and self._mouse_grabbed:
                try:
                    self._grid.releaseMouse()
                except Exception:
                    pass
                self._mouse_grabbed = False
            self.drag_active = False
            self._drag_current = None
            return
        # Momentary mode: start a drag and activate the pressed button
        self.drag_active = True
        if not self._mouse_grabbed:
            try:
                self._grid.grabMouse()
                self._mouse_grabbed = True
            except Exception:
                self._mouse_grabbed = False
        new_coords = (r, c)
        if self._drag_current != new_coords:
            if self._drag_current is not None:
                self._set_button_active(self._drag_current, False)
            self._drag_current = new_coords
            self._set_button_active(new_coords, True)

    def _handle_release(self, r: int, c: int):
        # On mouse release, deactivate whichever button is currently active
        if self.drag_active:
            if self._drag_current is not None:
                self._set_button_active(self._drag_current, False)
                self._drag_current = None
        self.drag_active = False
        if self._mouse_grabbed:
            try:
                self._grid.releaseMouse()
            except Exception:
                pass
            self._mouse_grabbed = False

    # Called by buttons to continue a drag when mouse moves
    def _drag_update_from_global(self, gpt):
        if not self.drag_active:
            return
        try:
            local = self._grid.mapFromGlobal(gpt)
        except Exception:
            return
        child = self._grid.childAt(local)
        new_coords = None
        if isinstance(child, QPushButton) and child.isEnabled():
            new_coords = getattr(child, "_rq", None)
        if new_coords is not None and new_coords != self._drag_current:
            if self._drag_current is not None:
                self._set_button_active(self._drag_current, False)
            self._drag_current = new_coords
            self._set_button_active(new_coords, True)

    # Velocity toggle behavior (match piano): show range when randomized, otherwise single slider
    def _toggle_vel_random(self, checked: bool):
        try:
            self.vel_range.setVisible(bool(checked))
            self.vel_slider.setVisible(not bool(checked))
        except Exception:
            pass

    def eventFilter(self, obj, ev):  # type: ignore[override]
        # Handle events originating from the grid or any child button
        if obj is getattr(self, "_grid", None) or isinstance(obj, QPushButton):
            et = ev.type()
            
            # Handle right-click for latch toggle
            if et == QEvent.MouseButtonPress and isinstance(obj, QPushButton):
                try:
                    if ev.button() == Qt.RightButton:
                        coords = getattr(obj, "_rq", None)
                        if coords is not None:
                            self._handle_right_click(coords[0], coords[1])
                            return True  # consume the event
                except Exception:
                    pass
            
            if et == QEvent.MouseMove and self.drag_active:
                # Resolve cursor position in grid coordinates regardless of source
                try:
                    gpt = ev.globalPosition().toPoint()
                except Exception:
                    try:
                        gpt = ev.globalPos()
                    except Exception:
                        gpt = None
                new_coords = None
                if gpt is not None:
                    local = self._grid.mapFromGlobal(gpt)
                    child = self._grid.childAt(local)
                    if isinstance(child, QPushButton) and child.isEnabled():
                        new_coords = getattr(child, "_rq", None)
                # If we moved to a different valid cell, switch notes. If over a gap, keep current.
                if new_coords is not None and new_coords != self._drag_current:
                    if self._drag_current is not None:
                        self._set_button_active(self._drag_current, False)
                    self._drag_current = new_coords
                    self._set_button_active(new_coords, True)
                return False
            if et == QEvent.MouseButtonRelease and self.drag_active:
                if self._drag_current is not None:
                    self._set_button_active(self._drag_current, False)
                    self._drag_current = None
                self.drag_active = False
                if self._mouse_grabbed:
                    try:
                        self._grid.releaseMouse()
                    except Exception:
                        pass
                    self._mouse_grabbed = False
                return False
        return super().eventFilter(obj, ev)

    # MIDI handlers
    def _on_btn(self, r: int, c: int, pressed: bool):
        try:
            note = int(self.notes[r][c])
        except Exception:
            return
        if pressed:
            # In latch mode, presses are handled in _handle_press
            if not self.latch:
                self._send_note_on(note)
        else:
            if not self.latch:
                if self.sustain:
                    # Keep sounding; mark as sustained
                    if note in self._active_notes:
                        self._sustained_notes.add(note)
                else:
                    self._send_note_off(note)

    # External API parity
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

    # Config
    def get_mapping(self) -> Tuple[int, int, int]:
        return int(self.base_note), int(self.step_x), int(self.step_y)

    def set_mapping(self, base_note: int, step_x: int, step_y: int):
        try:
            self.base_note = int(base_note)
            self.step_x = int(step_x)
            self.step_y = int(step_y)
            # Recompute labels/notes
            self._recompute_grid()
            for r in range(self.rows):
                for c in range(self.cols):
                    n = self.notes[r][c]
                    try:
                        if n is not None and 0 <= n <= 127:
                            self.buttons[r][c].setText(self._note_name(int(n)))
                            self.buttons[r][c].setEnabled(True)
                        else:
                            self.buttons[r][c].setText("")
                            self.buttons[r][c].setEnabled(False)
                    except Exception:
                        pass
        except Exception:
            pass
