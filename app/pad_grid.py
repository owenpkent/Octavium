from typing import List
from PySide6.QtWidgets import (
    QWidget, QPushButton, QGridLayout, QSizePolicy, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QSlider
)
from PySide6.QtCore import Qt, QSize, QTimer, QEvent
from PySide6.QtGui import QColor
from .models import Layout, RowDef, KeyDef
from .midi_io import MidiOut
from .keyboard_widget import RangeSlider


def create_pad_grid_layout(rows: int = 4, cols: int = 4, start_note: int = 36) -> Layout:
    """Create a simple rows x cols pad grid layout.
    Defaults to 4x4 starting at MIDI note 36 (C1, General MIDI Kick)."""
    keys_rows: List[RowDef] = []
    note = int(start_note)
    for _ in range(rows):
        row_keys: List[KeyDef] = []
        for _ in range(cols):
            row_keys.append(KeyDef(label="", note=note, width=1.0, height=1.0, velocity=110, channel=9))
            note += 1
        keys_rows.append(RowDef(keys=row_keys))
    # Flip vertical order so higher notes are at the top row and lower at the bottom
    keys_rows = list(reversed(keys_rows))
    return Layout(
        name=f"Pad Grid {rows}x{cols}",
        rows=keys_rows,
        columns=cols,
        gap=6,
        base_octave=0,
        allow_poly=True,
        quantize_scale="chromatic",
    )


class PadGridWidget(QWidget):
    """A drum pad/grid widget with fixed layout and keyboard-like controls."""
    def __init__(self, layout_model: Layout, midi_out: MidiOut, title: str = "", scale: float = 1.0):
        super().__init__()
        self.layout_model = layout_model
        self.midi = midi_out
        self.port_name: str = ""
        self.midi_channel: int = 9  # default to channel 10 (drums) 0-based
        self.octave_offset: int = 0
        self.sustain: bool = False
        self.latch: bool = False
        self.vel_random: bool = True
        self.vel_low: int = 80
        self.vel_high: int = 110
        try:
            self.ui_scale = float(scale) if float(scale) > 0 else 1.0
        except Exception:
            self.ui_scale = 1.0
        self.setWindowTitle(title or layout_model.name)
        # Fixed-size central widget behavior
        try:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(int(8 * self.ui_scale))

        # Header controls (two rows to avoid crowding)
        header_box = QVBoxLayout()
        # Add small vertical margins to avoid button clipping
        header_box.setContentsMargins(int(6 * self.ui_scale), int(4 * self.ui_scale), int(6 * self.ui_scale), int(10 * self.ui_scale))
        header_box.setSpacing(int(16 * self.ui_scale))
        # keep a reference for sizeHint calculations
        self.header_box = header_box

        row1 = QHBoxLayout()
        row1.setContentsMargins(0, 0, 0, 0)
        row1.setSpacing(int(10 * self.ui_scale))
        try:
            row1.setAlignment(Qt.AlignCenter)
        except Exception:
            pass
        self.header_row1 = row1
        self.oct_label = QLabel("Octave")
        self.oct_minus = QPushButton("-")
        self.oct_plus = QPushButton("+")
        for b in (self.oct_minus, self.oct_plus):
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedSize(int(24 * self.ui_scale), int(22 * self.ui_scale))
        self.oct_minus.clicked.connect(lambda: self._change_octave(-1))
        self.oct_plus.clicked.connect(lambda: self._change_octave(+1))

        self.sustain_btn = QPushButton("Sustain: Off")
        self.sustain_btn.setCheckable(True)
        self.sustain_btn.clicked.connect(self._toggle_sustain)
        self.latch_btn = QPushButton("Latch: Off")
        self.latch_btn.setCheckable(True)
        self.latch_btn.clicked.connect(self._toggle_latch)
        # All Notes Off
        self.all_off_btn = QPushButton("All Notes Off")
        self.all_off_btn.clicked.connect(self._all_notes_off_clicked)
        for b in (self.sustain_btn, self.latch_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(int(28 * self.ui_scale))
        try:
            self.all_off_btn.setCursor(Qt.PointingHandCursor)
            self.all_off_btn.setFixedHeight(int(28 * self.ui_scale))
            # Allow wider text without clipping similar to keyboard widget
            self.sustain_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.latch_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            self.all_off_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            s = max(0.5, float(getattr(self, 'ui_scale', 1.0)))
            self.sustain_btn.setMinimumWidth(int(100 * s))
            self.latch_btn.setMinimumWidth(int(88 * s))
            self.all_off_btn.setMinimumWidth(int(120 * s))
            # Apply keyboard-style button QSS (blue when checked)
            kb_qss_toggle = (
                "QPushButton {\n"
                "  padding: 1px 4px;\n"
                "  min-height: 0px;\n"
                "  border-radius: 3px;\n"
                "  border: 1px solid #888;\n"
                "  background-color: #f3f3f3;\n"
                "  color: #222;\n"
                "}\n"
                "QPushButton:checked {\n"
                "  background-color: #3498db;\n"
                "  color: white;\n"
                "  border: 1px solid #2980b9;\n"
                "}\n"
                "QPushButton:hover { background-color: #e9e9e9; }\n"
                "QPushButton:pressed { background-color: #dcdcdc; }\n"
                "QPushButton:checked:hover { background-color: #2f8ccc; }\n"
                "QPushButton:checked:pressed { background-color: #2a7fb8; }\n"
            )
            kb_qss_plain = (
                "QPushButton {\n"
                "  padding: 1px 4px;\n"
                "  min-height: 0px;\n"
                "  border-radius: 3px;\n"
                "  border: 1px solid #888;\n"
                "  background-color: #fafafa;\n"
                "  color: #222;\n"
                "}\n"
                "QPushButton:hover { background-color: #f0f0f0; }\n"
                "QPushButton:pressed { background-color: #e5e5e5; }\n"
            )
            self.sustain_btn.setStyleSheet(kb_qss_toggle)
            self.latch_btn.setStyleSheet(kb_qss_toggle)
            self.all_off_btn.setStyleSheet(kb_qss_plain)
            # Keep base stylesheet so we can flash/revert on click
            self._all_off_btn_base_qss = str(self.all_off_btn.styleSheet())
        except Exception:
            pass
        self.vel_random_chk = QCheckBox("Randomized Velocity")
        self.vel_random_chk.setChecked(True)
        # Single velocity slider (when randomization is off)
        self.vel_slider = QSlider(Qt.Horizontal)
        self.vel_slider.setRange(1, 127)
        self.vel_slider.setValue(100)
        # Range slider (when randomization is on)
        self.vel_range = RangeSlider(1, 127, low=self.vel_low, high=self.vel_high, parent=self)
        # Start with randomization enabled: show range, hide single slider
        try:
            same_h = int(20 * self.ui_scale)
            self.vel_slider.setFixedHeight(same_h)
            self.vel_range.setFixedHeight(same_h)
            self.vel_slider.setMinimumWidth(int(140 * self.ui_scale))
            self.vel_range.setMinimumWidth(int(140 * self.ui_scale))
            self.vel_slider.setMaximumWidth(int(220 * self.ui_scale))
            self.vel_range.setMaximumWidth(int(220 * self.ui_scale))
            self.vel_slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.vel_range.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            # Apply unified slider styling (copied from KeyboardWidget) so single slider
            # keeps the same perceived thickness as the RangeSlider groove/handle.
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
        except Exception:
            pass
        # Connect toggle to show/hide sliders and set state flag
        self.vel_random_chk.toggled.connect(self._toggle_vel_random)
        # Initialize visibility to current checkbox state
        self._toggle_vel_random(self.vel_random_chk.isChecked())

        # Row 1: Velocity controls + Octave controls, centered
        row1.addWidget(self.vel_random_chk)
        row1.addSpacing(int(8 * self.ui_scale))
        row1.addWidget(self.vel_slider)
        row1.addWidget(self.vel_range)
        row1.addSpacing(int(12 * self.ui_scale))
        row1.addWidget(self.oct_minus)
        row1.addWidget(self.oct_label)
        row1.addWidget(self.oct_plus)

        # Row 2: Octave (left), Sustain/Latch (right)
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(int(10 * self.ui_scale))
        try:
            row2.setAlignment(Qt.AlignCenter)
        except Exception:
            pass
        self.header_row2 = row2
        # Row 2: Centered buttons
        row2.addWidget(self.sustain_btn)
        row2.addWidget(self.latch_btn)
        row2.addWidget(self.all_off_btn)

        header_box.addLayout(row1)
        header_box.addLayout(row2)
        # Wrap header in a QWidget to ensure height is honored
        self.header_widget = QWidget()
        # Let header grow to fit contents to avoid clipping
        self.header_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.header_widget.setLayout(header_box)
        root.addWidget(self.header_widget)
        # Do not allow the header to compress below its natural size
        try:
            buffer = int(24 * self.ui_scale)
            min_h = int(self.header_widget.sizeHint().height()) + buffer
            self.header_widget.setMinimumHeight(min_h)
            self.header_widget.setMaximumHeight(min_h)
        except Exception:
            pass
        # Extra breathing space between header and grid
        root.addSpacing(int(20 * self.ui_scale))

        # Pad grid
        self.buttons: dict[tuple[int, int], QPushButton] = {}
        grid_wrap = QWidget()
        grid_wrap.setObjectName("padPanel")
        grid_wrap.setStyleSheet(
            """
            QWidget#padPanel { background: #181a1f; border: 1px solid #2a2f35; border-radius: 6px; }
            """
        )
        grid_layout = QGridLayout(grid_wrap)
        gap = int(14 * self.ui_scale)
        # Use the same value for all margins so first/last gaps match inter-gaps
        grid_layout.setContentsMargins(gap, gap, gap, gap)
        # Ensure identical vertical and horizontal spacing
        grid_layout.setSpacing(gap)
        try:
            grid_layout.setHorizontalSpacing(gap)
            grid_layout.setVerticalSpacing(gap)
        except Exception:
            pass
        # Center the overall grid so edge gaps are symmetric, while internal spacing stays exact
        try:
            grid_layout.setAlignment(Qt.AlignCenter)
        except Exception:
            pass
        btn_size = int(96 * self.ui_scale)  # bigger pads
        # Ensure each grid cell is exactly the button size and does not stretch
        try:
            total_rows = len(layout_model.rows)
            total_cols = max((len(r.keys) for r in layout_model.rows), default=0)
            for rr in range(total_rows):
                grid_layout.setRowMinimumHeight(rr, btn_size)
                grid_layout.setRowStretch(rr, 0)
            for cc in range(total_cols):
                grid_layout.setColumnMinimumWidth(cc, btn_size)
                grid_layout.setColumnStretch(cc, 0)
        except Exception:
            pass
        # Map buttons to keys for drag handling
        self._btn_key: dict[QPushButton, KeyDef] = {}
        for r, row in enumerate(layout_model.rows):
            for c, key in enumerate(row.keys):
                btn = QPushButton("")
                btn.setCheckable(True)
                btn.setFixedSize(btn_size, btn_size)
                btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                btn.setStyleSheet(
                    """
                    QPushButton { background: #2b2f36; color: #ddd; border: 2px solid #3b4148; border-radius: 10px; }
                    /* Keep hover border same as normal to avoid blue outline lingering on drag */
                    QPushButton:hover { border: 2px solid #3b4148; }
                    QPushButton:checked { background: #2f82e6; color: white; border: 2px solid #2a6fc2; }
                    """
                )
                # Avoid focus outline artifacts when dragging across pads
                try:
                    btn.setFocusPolicy(Qt.NoFocus)
                except Exception:
                    pass
                # Annotate with base note so we can resolve latched visuals later
                try:
                    btn._base_note = int(getattr(key, 'note', -1))  # type: ignore[attr-defined]
                except Exception:
                    btn._base_note = -1  # type: ignore[attr-defined]
                # Enable drag-over triggering
                try:
                    btn.setMouseTracking(True)
                    btn.installEventFilter(self)
                except Exception:
                    pass
                self._btn_key[btn] = key
                btn.pressed.connect(lambda k=key, b=btn: self._on_pad_down(k, b))
                btn.released.connect(lambda k=key, b=btn: self._on_pad_up(k, b))
                # Do not pass per-widget alignment; keep cells tight to button size
                grid_layout.addWidget(btn, r, c)
                self.buttons[(r, c)] = btn
        # Prevent grid from expanding; set an exact fixed size based on buttons and spacing
        try:
            width_cols = max((len(r.keys) for r in layout_model.rows), default=0)
            height_rows = len(layout_model.rows)
            exact_w = width_cols * btn_size + max(0, width_cols - 1) * gap + 2 * gap
            exact_h = height_rows * btn_size + max(0, height_rows - 1) * gap + 2 * gap
            # Add 1px border on each side so content doesn't clip
            exact_w += 2
            exact_h += 2
            grid_wrap.setFixedSize(int(exact_w), int(exact_h))
            grid_wrap.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            try:
                grid_wrap.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            except Exception:
                pass
        # Save grid_wrap for drag handling and enable tracking
        self.grid_wrap = grid_wrap
        try:
            self.grid_wrap.setMouseTracking(True)
            self.grid_wrap.installEventFilter(self)
        except Exception:
            pass
        # Center the grid panel in the root layout as well
        try:
            root.addWidget(grid_wrap, 0, Qt.AlignCenter)
        except Exception:
            root.addWidget(grid_wrap)

        # Track active notes for sustain/latch
        self._active: set[tuple[int, int]] = set()  # (note, channel)
        self._latched: set[int] = set()  # notes toggled on
        # Drag state
        self.dragging: bool = False
        self.last_drag_button: QPushButton | None = None
        self.setLayout(root)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        # Compute the full content size so the main window can fit the header + grid without clipping
        try:
            rows = len(self.layout_model.rows)
            cols = max((len(r.keys) for r in self.layout_model.rows), default=4)
        except Exception:
            rows, cols = 4, 4
        pad = int(96 * self.ui_scale)
        gap = int(14 * self.ui_scale)
        side = gap  # match grid_layout contents margins
        # Header height: use the locked minimum to avoid clipping
        try:
            header_min = int(self.header_widget.minimumHeight())
        except Exception:
            header_min = 0
        try:
            header_buffer = int(16 * self.ui_scale)
            base_h = int(self.header_widget.sizeHint().height()) + header_buffer + int(12 * self.ui_scale)
        except Exception:
            base_h = int(112 * self.ui_scale)
        header_h = max(int(header_min), int(base_h))
        # Grid panel size (includes equal margins and +2 for 1px border on each edge)
        panel_w = cols * pad + (cols - 1) * gap + 2 * side + 2
        panel_h = rows * pad + (rows - 1) * gap + 2 * side + 2
        # Explicit spacing added between header and grid in __init__
        try:
            grid_spacing = int(20 * self.ui_scale)
        except Exception:
            grid_spacing = 20
        # Compute a conservative minimum width required by the header controls
        try:
            spacing = int(10 * self.ui_scale)
            slider_w = max(self.vel_slider.maximumWidth(), self.vel_range.maximumWidth())
            r1 = (
                self.vel_random_chk.sizeHint().width()
                + spacing
                + slider_w
                + spacing
                + self.oct_minus.sizeHint().width()
                + spacing
                + self.oct_label.sizeHint().width()
                + spacing
                + self.oct_plus.sizeHint().width()
            )
            r2 = (
                self.sustain_btn.sizeHint().width()
                + spacing
                + self.latch_btn.sizeHint().width()
                + spacing
                + self.all_off_btn.sizeHint().width()
            )
            header_min_w = max(r1, r2) + 12  # root margin buffer
        except Exception:
            header_min_w = 0
        content_w = max(panel_w + 12, int(header_min_w))
        h = panel_h + header_h + grid_spacing + 12
        return QSize(int(content_w), int(h))

    def set_channel(self, channel_1_based: int):
        self.midi_channel = max(1, min(16, int(channel_1_based))) - 1

    def _on_pad_down(self, key: KeyDef, btn: QPushButton):
        # When user presses, start dragging across pads and grab mouse
        self.dragging = True
        self.last_drag_button = btn
        try:
            if hasattr(self, 'grid_wrap') and self.grid_wrap is not None:
                self.grid_wrap.grabMouse()
        except Exception:
            pass
        vel = self._choose_velocity(default=int(getattr(key, 'velocity', 110)))
        ch = self.midi_channel
        note = int(key.note) + 12 * self.octave_offset
        # Latch toggle: if already latched, pressing again turns it off immediately
        if self.latch and note in self._latched:
            try:
                self.midi.note_off(note, ch)
            except Exception:
                pass
            self._latched.discard(note)
            self._active.discard((note, ch))
            try:
                btn.setChecked(False)
            except Exception:
                pass
            return
        try:
            self.midi.note_on(note, vel, ch)
        except Exception:
            pass
        try:
            btn.setChecked(True)
        except Exception:
            pass
        self._active.add((note, ch))
        if self.latch:
            self._latched.add(note)

    def _on_pad_up(self, key: KeyDef, btn: QPushButton):
        ch = self.midi_channel
        note = int(key.note) + 12 * self.octave_offset
        if self.latch and note in self._latched:
            # Keep sounding when latched; maintain visual down state.
            # Use a 0ms singleShot to override Qt's post-release toggle order.
            try:
                QTimer.singleShot(0, lambda b=btn: b.setChecked(True))
            except Exception:
                try:
                    btn.setChecked(True)
                except Exception:
                    pass
            return
        if self.sustain:
            # Defer note_off until sustain released
            self._active.add((note, ch))
        else:
            try:
                self.midi.note_off(note, ch)
            except Exception:
                pass
            try:
                self._active.discard((note, ch))
            except Exception:
                pass
        try:
            btn.setChecked(False)
        except Exception:
            pass
        # Stop dragging if mouse released on this button
        self.dragging = False
        self.last_drag_button = None
        try:
            if hasattr(self, 'grid_wrap') and self.grid_wrap is not None:
                self.grid_wrap.releaseMouse()
        except Exception:
            pass

    def set_midi_out(self, midi: MidiOut, port_name: str = ""):
        """Update MIDI out and remember a human-friendly port name."""
        try:
            self.midi = midi
        except Exception:
            pass
        try:
            self.port_name = str(port_name)
        except Exception:
            self.port_name = ""

    # ---- Helpers / controls ----
    def _change_octave(self, delta: int):
        self.octave_offset = max(-4, min(4, int(self.octave_offset) + int(delta)))
        # Keep the label static; do not append the numeric offset
        try:
            self.oct_label.setText("Octave")
        except Exception:
            pass

    def _toggle_sustain(self):
        self.sustain = bool(self.sustain_btn.isChecked())
        self.sustain_btn.setText("Sustain: On" if self.sustain else "Sustain: Off")
        if not self.sustain:
            # On sustain release, send note_off for all non-latched notes
            to_release = [nc for nc in list(self._active) if nc[0] not in self._latched]
            for note, ch in to_release:
                try:
                    self.midi.note_off(note, ch)
                except Exception:
                    pass
                self._active.discard((note, ch))

    def _toggle_latch(self):
        new_state = bool(self.latch_btn.isChecked())
        self.latch_btn.setText("Latch: On" if new_state else "Latch: Off")
        if not new_state:
            # Turning latch off: send note_off for latched notes and clear visuals
            previously_latched = list(self._latched)
            for note in previously_latched:
                try:
                    self.midi.note_off(note, self.midi_channel)
                except Exception:
                    pass
            self._latched.clear()
            # Uncheck buttons that corresponded to the previously latched notes
            try:
                for b in self.buttons.values():
                    base = int(getattr(b, '_base_note', -9999))
                    resolved = base + 12 * int(self.octave_offset)
                    if resolved in previously_latched:
                        b.setChecked(False)
            except Exception:
                pass
        self.latch = new_state

    # ---- Event filter to support click-drag across pads ----
    def eventFilter(self, obj, event):  # type: ignore[override]
        try:
            # Per-button events: only used to flag start/stop of dragging; note triggering handled by signals
            if isinstance(obj, QPushButton) and obj in self._btn_key:
                et = event.type()
                if et == QEvent.MouseButtonPress:
                    # Start drag; let QPushButton.pressed signal trigger note_on
                    self.dragging = True
                    self.last_drag_button = obj
                    return False
                if et == QEvent.Enter:
                    # Hover into a pad while dragging: switch active
                    if self.dragging:
                        if obj is self.last_drag_button:
                            return False
                        # Release previous (if any) appropriately
                        prev = self.last_drag_button
                        if prev is not None:
                            try:
                                pk = self._btn_key.get(prev)
                                if pk is not None:
                                    self._on_pad_up(pk, prev)
                                    # Force-clear any pressed/focus visuals to avoid lingering outline
                                    try:
                                        prev.setChecked(False)
                                        prev.setDown(False)
                                        prev.clearFocus()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                        # Press new pad
                        key = self._btn_key.get(obj)
                        if key is not None:
                            self._on_pad_down(key, obj)
                    return False
                if et == QEvent.MouseMove:
                    # Ignore per-button mouse move; we handle on grid container
                    return False
                if et == QEvent.MouseButtonRelease:
                    # Stop drag; let QPushButton.released signal handle note_off
                    self.dragging = False
                    self.last_drag_button = None
                    try:
                        if hasattr(self, 'grid_wrap') and self.grid_wrap is not None:
                            self.grid_wrap.releaseMouse()
                    except Exception:
                        pass
                    return False
            # Grid container events: handle drag transitions here for reliability
            if obj is getattr(self, 'grid_wrap', None):
                et = event.type()
                if et == QEvent.MouseMove and self.dragging:
                    try:
                        w = self.grid_wrap.childAt(event.pos())
                    except Exception:
                        w = None
                    if isinstance(w, QPushButton) and w in self._btn_key and w is not self.last_drag_button:
                        # Transition from previous to new button
                        prev = self.last_drag_button
                        if prev is not None:
                            try:
                                pk = self._btn_key.get(prev)
                                if pk is not None:
                                    self._on_pad_up(pk, prev)
                            except Exception:
                                pass
                        try:
                            nk = self._btn_key.get(w)
                            if nk is not None:
                                self._on_pad_down(nk, w)
                        except Exception:
                            pass
                        self.last_drag_button = w
                    return False
                if et == QEvent.MouseButtonRelease and self.dragging:
                    # Release current and end drag
                    cur = self.last_drag_button
                    if cur is not None:
                        try:
                            ck = self._btn_key.get(cur)
                            if ck is not None:
                                self._on_pad_up(ck, cur)
                        except Exception:
                            pass
                    self.dragging = False
                    self.last_drag_button = None
                    try:
                        self.grid_wrap.releaseMouse()
                    except Exception:
                        pass
                    return False
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _toggle_vel_random(self, checked: bool):
        # Update flag and toggle which slider is visible
        self.vel_random = bool(checked)
        try:
            self.vel_slider.setVisible(not self.vel_random)
            self.vel_range.setVisible(self.vel_random)
            # Recompute header minimum height to avoid clipping
            if hasattr(self, 'header_widget') and self.header_widget is not None:
                buffer = int(24 * self.ui_scale)
                min_h = int(self.header_widget.sizeHint().height()) + buffer
                self.header_widget.setMinimumHeight(min_h)
                self.header_widget.setMaximumHeight(min_h)
        except Exception:
            pass

    def _all_notes_off(self):
        """Send note_off for all active or latched notes and clear state."""
        try:
            # Turn off active notes
            for note, ch in list(self._active):
                try:
                    self.midi.note_off(note, ch)
                except Exception:
                    pass
            # Turn off latched notes (ensure off on current channel)
            for note in list(self._latched):
                try:
                    self.midi.note_off(note, self.midi_channel)
                except Exception:
                    pass
            self._active.clear()
            self._latched.clear()
            # Visually release all buttons
            try:
                for btn in self.buttons.values():
                    btn.setChecked(False)
            except Exception:
                pass
        except Exception:
            pass

    def _all_notes_off_clicked(self):
        """UI handler: flash All Notes Off button blue, then perform note-off."""
        try:
            self._flash_all_off_button()
        except Exception:
            pass
        self._all_notes_off()

    def _flash_all_off_button(self, duration_ms: int = 150):
        """Temporarily set All Notes Off button to blue to indicate action, then revert."""
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

    def _choose_velocity(self, default: int = 100) -> int:
        # If not randomizing, use the single slider value (fallback to default if missing)
        try:
            if not self.vel_random:
                return int(max(1, min(127, int(self.vel_slider.value()))))
        except Exception:
            pass
        # Randomized: choose within range slider
        import random
        try:
            lo, hi = self.vel_range.values()
            lo, hi = int(lo), int(hi)
        except Exception:
            lo, hi = int(self.vel_low), int(self.vel_high)
        if lo > hi:
            lo, hi = hi, lo
        return int(max(1, min(127, random.randint(lo, hi))))
