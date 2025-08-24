from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QApplication, QSizePolicy
from PySide6.QtCore import Qt, QSize, QEvent
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

class KeyboardWidget(QWidget):
    def __init__(self, layout_model: Layout, midi_out: MidiOut, title: str = "", show_header: bool = True, compact_controls: bool = True):
        super().__init__()
        self.layout_model = layout_model
        self.midi = midi_out
        self.port_name: str | None = None
        self.midi_channel: int = 0  # 0-15, shown as 1-16
        self.octave_offset = 0
        self.sustain = False
        self.latch = False
        self.visual_hold_on_sustain = True  # whether sustained notes keep visual down state
        self.vel_curve = "linear"
        self.active_notes: set[tuple[int,int]] = set()
        # Polyphony control
        self.polyphony_enabled: bool = False
        self.polyphony_max: int = 8
        self._voice_order: list[tuple[int,int,int]] = []  # (note, ch, base_note)
        self.dragging = False
        self.last_drag_key = None
        self.last_drag_button: QPushButton | None = None
        self.key_buttons = {}  # Map from note to button
        self.setWindowTitle(title or layout_model.name)
        self.setMouseTracking(True)  # Enable mouse tracking for drag
        # Capture mouse moves globally so we see events while a button has the grab
        QApplication.instance().installEventFilter(self)
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
        header.setSpacing(1)
        self.oct_label = QLabel("Octave: 0")
        
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
                background-color: #2ecc71; /* green */
                color: white;
                border: 1px solid #27ae60;
            }
            QPushButton:hover { background-color: #e9e9e9; }
            QPushButton:pressed { background-color: #dcdcdc; }
            QPushButton:checked:hover { background-color: #29c267; }
            QPushButton:checked:pressed { background-color: #25b75f; }
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
        
        self.vel_label = QLabel("Vel curve: linear")
        self.vel_slider = QSlider(Qt.Horizontal)
        self.vel_slider.setMinimum(20)
        self.vel_slider.setMaximum(127)
        self.vel_slider.setValue(100)
        # Keep header small so small keyboards can shrink
        try:
            self.vel_slider.setFixedWidth(160)
            self.vel_slider.setFixedHeight(12)
            self.vel_slider.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.oct_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.vel_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.sustain_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.latch_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.all_off_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.sustain_btn.setFixedHeight(18)
            self.latch_btn.setFixedHeight(18)
            self.all_off_btn.setFixedHeight(18)
            self.oct_label.setFixedHeight(16)
            self.vel_label.setFixedHeight(16)
            self.oct_label.setStyleSheet("font-size: 9px;")
            self.vel_label.setStyleSheet("font-size: 9px;")
        except Exception:
            pass
        
        header.addWidget(self.oct_label)
        header.addWidget(self.vel_label)
        header.addStretch()
        header.addWidget(self.sustain_btn)
        header.addWidget(self.latch_btn)
        header.addWidget(self.all_off_btn)
        header.addWidget(self.vel_slider)
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
                self.sustain_btn.setFixedHeight(22)
                self.latch_btn.setFixedHeight(22)
                self.all_off_btn.setFixedHeight(22)
                self.sustain_btn.setMinimumWidth(90)
                self.latch_btn.setMinimumWidth(70)
                self.all_off_btn.setMinimumWidth(110)
                # Increase padding and font size for readability
                self.sustain_btn.setStyleSheet(self.sustain_btn.styleSheet() + "\nQPushButton { padding: 4px 8px; font-size: 11px; }")
                self.latch_btn.setStyleSheet(self.latch_btn.styleSheet() + "\nQPushButton { padding: 4px 8px; font-size: 11px; }")
                self.all_off_btn.setStyleSheet(self.all_off_btn.styleSheet() + "\nQPushButton { padding: 4px 8px; font-size: 11px; }")
            except Exception:
                pass
            controls.addWidget(self.sustain_btn)
            controls.addWidget(self.latch_btn)
            controls.addWidget(self.all_off_btn)
            controls.addStretch()
            root.addWidget(controls_widget)

        # Create a container widget for absolute positioning
        piano_container = QWidget()
        piano_container.setFixedHeight(100)  # Exactly white key height
        try:
            # Do not allow horizontal expansion; keep width exactly to keys
            piano_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass
        piano_container.setMouseTracking(True)  # Enable mouse tracking on container
        self.piano_container = piano_container  # Store reference for mouse events
        
        # Create white keys first (they go in the background)
        white_keys = self.layout_model.rows[0].keys
        x_pos = 0
        
        for white_key in white_keys:
            if white_key.note >= 0:  # Skip spacer keys
                btn = QPushButton("", piano_container)
                btn.setGeometry(x_pos, 0, int(44 * white_key.width), 100)  # Align to top
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {white_key.color or 'white'};
                        border: 1px solid #ccc;
                        border-radius: 0px;
                    }}
                    QPushButton:pressed, QPushButton[held="true"] {{
                        background-color: #e0e0e0;
                    }}
                """)
                btn.pressed.connect(lambda k=white_key: self.on_key_press(k))
                btn.released.connect(lambda k=white_key: self.on_key_release(k))
                
                # Store button geometry for mouse detection
                btn.key_note = white_key.note
                
                # Store button reference keyed by base note (independent of octave)
                self.key_buttons[white_key.note] = btn
            
            x_pos += int(44 * white_key.width)
        
        # Create black keys (they overlay the white keys) - direct approach
        if len(self.layout_model.rows) > 1:
            # Calculate white key positions
            white_key_positions = []
            temp_x = 0
            for white_key in white_keys:
                if white_key.note >= 0:
                    white_key_positions.append((temp_x, white_key.note))
                temp_x += int(44 * white_key.width)
            
            # Create black keys directly based on white key notes
            for i, (white_x, white_note) in enumerate(white_key_positions):
                note_in_octave = white_note % 12
                
                # Black keys come after C, D, F, G, A (notes 0, 2, 5, 7, 9)
                if note_in_octave in [0, 2, 5, 7, 9]:
                    # Calculate the black key note (semitone above the white key)
                    black_note = white_note + 1
                    
                    # Position black key between this white key and the next
                    black_x = white_x + 32  # Center between keys
                    
                    btn = QPushButton("", piano_container)
                    btn.setGeometry(black_x, 0, 28, 65)  # Align to top
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: black;
                            border: 1px solid #333;
                            border-radius: 0px;
                        }
                        QPushButton:pressed, QPushButton[held="true"] {
                            background-color: #333;
                        }
                    """)
                    
                    # Create a KeyDef for the black key with correct note
                    black_key_def = KeyDef(
                        label="",
                        note=black_note,
                        color="black",
                        width=0.7,
                        height=1.0,
                        velocity=100,
                        channel=0
                    )
                    
                    btn.pressed.connect(lambda k=black_key_def: self.on_key_press(k))
                    btn.released.connect(lambda k=black_key_def: self.on_key_release(k))
                    btn.raise_()  # Bring black keys to front
                    
                    # Store button geometry for mouse detection
                    btn.key_note = black_note
                    
                    # Store button reference keyed by base note (independent of octave)
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
            root.addWidget(piano_container, 0, Qt.AlignLeft)
        except Exception:
            root.addWidget(piano_container)

    def effective_note(self, base_note: int) -> int:
        n = base_note + 12 * (self.layout_model.base_octave + self.octave_offset)
        n = max(0, min(127, n))
        n = quantize(n, self.layout_model.quantize_scale or "chromatic", self.layout_model.custom_scale)
        return n

    # --- Sizing helpers ---
    def sizeHint(self) -> QSize:  # type: ignore[override]
        try:
            width = int(self.piano_container.width())
        except Exception:
            width = 800
        if getattr(self, "_show_header", True):
            # header(~20-24) + keys(100)
            return QSize(width, 124)
        elif getattr(self, "_compact_controls", True):
            # compact controls (~18) + keys(100)
            return QSize(width, 118)
        else:
            # keys only
            return QSize(width, 100)

    # --- Visual helpers ---
    def _apply_btn_visual(self, btn: QPushButton | None, down: bool, held: bool):
        if btn is None:
            return
        try:
            btn.setDown(down)
            btn.setProperty('held', 'true' if held else 'false')
            st = btn.style()
            if st is not None:
                st.unpolish(btn)
                st.polish(btn)
            btn.update()
        except Exception:
            pass

    def _apply_note_visual(self, note: int, down: bool, held: bool):
        try:
            btn = self.key_buttons.get(note)
        except Exception:
            btn = None
        self._apply_btn_visual(btn, down, held)

    def minimumSizeHint(self) -> QSize:  # type: ignore[override]
        try:
            width = int(self.piano_container.width())
        except Exception:
            width = 400
        if getattr(self, "_show_header", True):
            return QSize(width, 118)
        elif getattr(self, "_compact_controls", True):
            return QSize(width, 118)
        else:
            return QSize(width, 100)

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
        vel = velocity_curve(int(self.vel_slider.value() * (key.velocity / 127)), self.vel_curve)
        self.midi.note_on(note, vel, ch)
        self.active_notes.add((note, ch))
        self._voice_order.append((note, ch, base_note))
        # Ensure the corresponding key button shows as pressed (by base note)
        self._apply_note_visual(base_note, True, False)
        
        # Set dragging state (disabled while latch is on)
        if not getattr(self, 'latch', False):
            self.dragging = True
            self.last_drag_key = key
            # Track and visually press the originating button
            sender = self.sender()
            if isinstance(sender, QPushButton):
                self.last_drag_button = sender
                self.last_drag_button.setDown(True)

    def on_key_release(self, key: KeyDef):
        base_note = key.note
        note = self.effective_note(base_note)
        # In latch mode, do not send note-off on release; keep it held until toggled by another press
        if getattr(self, 'latch', False):
            # Keep visual down in latch mode
            self._apply_note_visual(base_note, True, True)
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
        else:
            # Sustaining: optionally keep or clear visual based on preference
            if not getattr(self, 'visual_hold_on_sustain', True):
                self._apply_note_visual(base_note, False, False)
            else:
                # Qt auto-releases the button visually on mouse release; re-press it
                self._apply_note_visual(base_note, True, True)
        # Do NOT clear dragging here. We only stop dragging on actual mouse button
        # release handled by eventFilter/mouseReleaseEvent so that drag can traverse
        # across multiple keys smoothly.

    def eventFilter(self, obj, event):
        """Global event filter to handle drag across child buttons reliably."""
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
                if isinstance(widget_under, QPushButton) and hasattr(widget_under, 'key_note'):
                    current_note = self.effective_note(widget_under.key_note)
                    if not self.last_drag_key or current_note != self.effective_note(self.last_drag_key.note):
                        # Stop previous
                        if self.last_drag_key and not self.sustain and not getattr(self, 'latch', False):
                            prev_note = self.effective_note(self.last_drag_key.note)
                            ch = self.midi_channel
                            self.midi.note_off(prev_note, ch)
                            self.active_notes.discard((prev_note, ch))
                        # Update previous button visual
                        if self.last_drag_button is not None and self.last_drag_button is not widget_under:
                            if not (self.sustain and getattr(self, 'visual_hold_on_sustain', True)) and not getattr(self, 'latch', False):
                                self._apply_btn_visual(self.last_drag_button, False, False)
                        # Start new
                        current_key = KeyDef(
                            label="",
                            note=widget_under.key_note,
                            color="black" if current_note % 12 in [1, 3, 6, 8, 10] else "white",
                            width=1.0,
                            height=1.0,
                            velocity=100,
                            channel=0,
                        )
                        vel = velocity_curve(int(self.vel_slider.value() * (current_key.velocity / 127)), self.vel_curve)
                        ch = self.midi_channel
                        if not getattr(self, 'latch', False):
                            self.midi.note_on(current_note, vel, ch)
                            self.active_notes.add((current_note, ch))
                        self.last_drag_key = current_key
                        # Update current button visual and reference
                        widget_under.setDown(True)
                        self.last_drag_button = widget_under
                else:
                    # Not over any key: release previous note and clear visual, keep dragging
                    if self.last_drag_key and not self.sustain and not getattr(self, 'latch', False):
                        prev_note = self.effective_note(self.last_drag_key.note)
                        ch = self.midi_channel
                        self.midi.note_off(prev_note, ch)
                        self.active_notes.discard((prev_note, ch))
                    if self.last_drag_button is not None:
                        if not (self.sustain and getattr(self, 'visual_hold_on_sustain', True)) and not getattr(self, 'latch', False):
                            self._apply_btn_visual(self.last_drag_button, False, False)
                    self.last_drag_key = None
                    self.last_drag_button = None
                return False
            # Ensure release anywhere stops dragging and releases note
            if event.type() == QEvent.MouseButtonRelease:
                self.dragging = False
                if self.last_drag_key and not self.sustain and not getattr(self, 'latch', False):
                    note = self.effective_note(self.last_drag_key.note)
                    ch = self.midi_channel
                    self.midi.note_off(note, ch)
                    self.active_notes.discard((note, ch))
                # Clear visuals unless sustain visual hold or latch
                if self.last_drag_button is not None:
                    if not (self.sustain and getattr(self, 'visual_hold_on_sustain', True)) and not getattr(self, 'latch', False):
                        self._apply_btn_visual(self.last_drag_button, False, False)
                self.last_drag_key = None
                self.last_drag_button = None
                return False
        return super().eventFilter(obj, event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        if self.dragging:
            self.dragging = False
            if self.last_drag_key and not self.sustain and not getattr(self, 'latch', False):
                note = self.effective_note(self.last_drag_key.note)
                ch = self.midi_channel
                self.midi.note_off(note, ch)
                self.active_notes.discard((note, ch))
            # Clear visuals
            if self.last_drag_button is not None:
                if not (self.sustain and getattr(self, 'visual_hold_on_sustain', True)) and not getattr(self, 'latch', False):
                    self._apply_btn_visual(self.last_drag_button, False, False)
            self.last_drag_key = None
            self.last_drag_button = None

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
            # When turning sustain off, ensure no stuck notes or visuals
            self.all_notes_off_clicked()

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
            # When turning latch OFF, release everything immediately
            self.all_notes_off_clicked()

    def toggle_latch(self):
        self.set_latch(self.latch_btn.isChecked())

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key_Z:
            self.octave_offset -= 1
            self.oct_label.setText(f"Octave: {self.octave_offset}")
        elif k == Qt.Key_X:
            self.octave_offset += 1
            self.oct_label.setText(f"Octave: {self.octave_offset}")
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
        # Stop any currently sounding notes before switching
        self.all_notes_off_clicked()
        self.midi = midi_out
        if port_name is not None:
            self.port_name = port_name
        self.update_window_title()

    def update_window_title(self):
        base = self.layout_model.name
        port_suffix = f" -> {self.port_name}" if self.port_name else ""
        ch_suffix = f" [Ch {self.midi_channel + 1}]"
        self.setWindowTitle(f"{base}{port_suffix}{ch_suffix}")

    def all_notes_off_clicked(self):
        """Clear all active notes, pressed visuals, and any drag state."""
        self.all_notes_off()
        if self.last_drag_button is not None:
            self.last_drag_button.setDown(False)
        self.last_drag_button = None
        self.last_drag_key = None
        self.dragging = False

    def set_channel(self, channel_1_based: int):
        """Set MIDI channel (1-16). Sends All Notes Off and updates title."""
        channel_1_based = max(1, min(16, channel_1_based))
        if self.midi_channel == channel_1_based - 1:
            return
        self.all_notes_off_clicked()
        self.midi_channel = channel_1_based - 1
        self.update_window_title()
