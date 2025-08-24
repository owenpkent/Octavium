from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QApplication
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
    def __init__(self, layout_model: Layout, midi_out: MidiOut, title: str = ""):
        super().__init__()
        self.layout_model = layout_model
        self.midi = midi_out
        self.octave_offset = 0
        self.sustain = False
        self.vel_curve = "linear"
        self.active_notes: set[tuple[int,int]] = set()
        self.dragging = False
        self.last_drag_key = None
        self.last_drag_button: QPushButton | None = None
        self.key_buttons = {}  # Map from note to button
        self.setWindowTitle(title or layout_model.name)
        self.setMouseTracking(True)  # Enable mouse tracking for drag
        # Capture mouse moves globally so we see events while a button has the grab
        QApplication.instance().installEventFilter(self)
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self.oct_label = QLabel("Octave: 0")
        
        # Add sustain toggle button (clearly styled) and All Notes Off button
        self.sustain_btn = QPushButton("Sustain: Off")
        self.sustain_btn.setCheckable(True)
        self.sustain_btn.clicked.connect(self.toggle_sustain)
        self.sustain_btn.setCursor(Qt.PointingHandCursor)
        self.sustain_btn.setStyleSheet(
            """
            QPushButton {
                padding: 6px 10px;
                border-radius: 4px;
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
        self.all_off_btn = QPushButton("All Notes Off")
        self.all_off_btn.setCursor(Qt.PointingHandCursor)
        self.all_off_btn.clicked.connect(self.all_notes_off_clicked)
        self.all_off_btn.setStyleSheet(
            """
            QPushButton {
                padding: 6px 10px;
                border-radius: 4px;
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
        
        header.addWidget(self.oct_label)
        header.addWidget(self.vel_label)
        header.addStretch()
        header.addWidget(self.sustain_btn)
        header.addWidget(self.all_off_btn)
        header.addWidget(self.vel_slider)
        root.addLayout(header)

        # Create a container widget for absolute positioning
        piano_container = QWidget()
        piano_container.setFixedHeight(120)  # Height for white keys + black keys
        piano_container.setMouseTracking(True)  # Enable mouse tracking on container
        self.piano_container = piano_container  # Store reference for mouse events
        
        # Create white keys first (they go in the background)
        white_keys = self.layout_model.rows[0].keys
        x_pos = 0
        
        for white_key in white_keys:
            if white_key.note >= 0:  # Skip spacer keys
                btn = QPushButton("", piano_container)
                btn.setGeometry(x_pos, 40, int(44 * white_key.width), 80)  # White key dimensions
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {white_key.color or 'white'};
                        border: 1px solid #ccc;
                        border-radius: 0px;
                    }}
                    QPushButton:pressed {{
                        background-color: #e0e0e0;
                    }}
                """)
                btn.pressed.connect(lambda k=white_key: self.on_key_press(k))
                btn.released.connect(lambda k=white_key: self.on_key_release(k))
                
                # Store button geometry for mouse detection
                btn.key_note = white_key.note
                
                # Store button reference for drag functionality
                effective_note = self.effective_note(white_key.note)
                self.key_buttons[effective_note] = btn
            
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
                    btn.setGeometry(black_x, 40, 28, 50)  # Black key dimensions
                    btn.setStyleSheet("""
                        QPushButton {
                            background-color: black;
                            border: 1px solid #333;
                            border-radius: 0px;
                        }
                        QPushButton:pressed {
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
                    
                    # Store button reference for drag functionality
                    effective_black_note = self.effective_note(black_note)
                    self.key_buttons[effective_black_note] = btn
        
        # Set the container width
        piano_container.setFixedWidth(x_pos)
        root.addWidget(piano_container)

        tips = QLabel("Shortcuts: Z/X octave down/up, 1/2/3 velocity curve, Q quantize toggle, Esc all notes off")
        tips.setStyleSheet("color: gray;")
        root.addWidget(tips)

    def effective_note(self, base_note: int) -> int:
        n = base_note + 12 * (self.layout_model.base_octave + self.octave_offset)
        n = max(0, min(127, n))
        n = quantize(n, self.layout_model.quantize_scale or "chromatic", self.layout_model.custom_scale)
        return n

    def on_key_press(self, key: KeyDef):
        note = self.effective_note(key.note)
        vel = velocity_curve(int(self.vel_slider.value() * (key.velocity / 127)), self.vel_curve)
        self.midi.note_on(note, vel, key.channel)
        self.active_notes.add((note, key.channel))
        
        # Set dragging state
        self.dragging = True
        self.last_drag_key = key
        # Track and visually press the originating button
        sender = self.sender()
        if isinstance(sender, QPushButton):
            self.last_drag_button = sender
            self.last_drag_button.setDown(True)

    def on_key_release(self, key: KeyDef):
        note = self.effective_note(key.note)
        if not self.sustain:
            self.midi.note_off(note, key.channel)
            self.active_notes.discard((note, key.channel))
        # Do NOT clear dragging here. We only stop dragging on actual mouse button
        # release handled by eventFilter/mouseReleaseEvent so that drag can traverse
        # across multiple keys smoothly.

    def eventFilter(self, obj, event):
        """Global event filter to handle drag across child buttons reliably."""
        if self.dragging:
            # Handle mouse move while dragging
            if event.type() == QEvent.MouseMove:
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
                        if self.last_drag_key and not self.sustain:
                            prev_note = self.effective_note(self.last_drag_key.note)
                            self.midi.note_off(prev_note, self.last_drag_key.channel)
                            self.active_notes.discard((prev_note, self.last_drag_key.channel))
                        # Update previous button visual
                        if self.last_drag_button is not None and self.last_drag_button is not widget_under:
                            self.last_drag_button.setDown(False)
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
                        self.midi.note_on(current_note, vel, current_key.channel)
                        self.active_notes.add((current_note, current_key.channel))
                        self.last_drag_key = current_key
                        # Update current button visual and reference
                        widget_under.setDown(True)
                        self.last_drag_button = widget_under
                else:
                    # Not over any key: release previous note and clear visual, keep dragging
                    if self.last_drag_key and not self.sustain:
                        prev_note = self.effective_note(self.last_drag_key.note)
                        self.midi.note_off(prev_note, self.last_drag_key.channel)
                        self.active_notes.discard((prev_note, self.last_drag_key.channel))
                    if self.last_drag_button is not None:
                        self.last_drag_button.setDown(False)
                    self.last_drag_key = None
                    self.last_drag_button = None
                return False
            # Ensure release anywhere stops dragging and releases note
            if event.type() == QEvent.MouseButtonRelease:
                self.dragging = False
                if self.last_drag_key and not self.sustain:
                    note = self.effective_note(self.last_drag_key.note)
                    self.midi.note_off(note, self.last_drag_key.channel)
                    self.active_notes.discard((note, self.last_drag_key.channel))
                # Clear visuals
                if self.last_drag_button is not None:
                    self.last_drag_button.setDown(False)
                self.last_drag_key = None
                self.last_drag_button = None
                return False
        return super().eventFilter(obj, event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop dragging"""
        if self.dragging:
            self.dragging = False
            if self.last_drag_key and not self.sustain:
                note = self.effective_note(self.last_drag_key.note)
                self.midi.note_off(note, self.last_drag_key.channel)
                self.active_notes.discard((note, self.last_drag_key.channel))
            # Clear visuals
            if self.last_drag_button is not None:
                self.last_drag_button.setDown(False)
            self.last_drag_key = None
            self.last_drag_button = None

    def toggle_sustain(self):
        """Toggle sustain on/off via button click (use button checked state)."""
        self.sustain = self.sustain_btn.isChecked()
        self.sustain_btn.setText(f"Sustain: {'On' if self.sustain else 'Off'}")
        if not self.sustain:
            # When turning sustain off, ensure no stuck notes or visuals
            self.all_notes_off_clicked()

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

    def all_notes_off_clicked(self):
        """Clear all active notes, pressed visuals, and any drag state."""
        self.all_notes_off()
        if self.last_drag_button is not None:
            self.last_drag_button.setDown(False)
        self.last_drag_button = None
        self.last_drag_key = None
        self.dragging = False
