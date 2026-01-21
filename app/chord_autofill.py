"""
Chord Autofill Module for Octavium Chord Monitor.

Provides:
- AutofillDialog: Select key, mode/emotion, and preview chords before filling the grid
- ChordEditDialog: Interactive mini-keyboard to edit individual chord cards
- Diatonic chord generation based on key and mode selection
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFrame, QGridLayout, QWidget, QSizePolicy, QButtonGroup, QRadioButton,
    QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QFont
from typing import List, Optional, Dict, Tuple, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .midi_io import MidiOut

# Note names
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_TO_INDEX = {note: i for i, note in enumerate(NOTES)}

# Alternative note names with flats
NOTES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


@dataclass
class ScaleMode:
    """Represents a musical scale/mode with its intervals and emotional character."""
    name: str
    intervals: List[int]  # Semitones from root
    chord_qualities: List[str]  # Chord quality for each scale degree
    emotion: str  # Emotional character/mood
    category: str  # Category for grouping (Major modes, Minor modes, etc.)


# Scale/Mode definitions with emotional descriptions
SCALE_MODES: Dict[str, ScaleMode] = {
    # Major modes
    "Major (Ionian)": ScaleMode(
        name="Major (Ionian)",
        intervals=[0, 2, 4, 5, 7, 9, 11],
        chord_qualities=["Major", "Minor", "Minor", "Major", "Major", "Minor", "Diminished"],
        emotion="Happy, Bright, Uplifting",
        category="Major Modes"
    ),
    "Lydian": ScaleMode(
        name="Lydian",
        intervals=[0, 2, 4, 6, 7, 9, 11],
        chord_qualities=["Major", "Major", "Minor", "Diminished", "Major", "Minor", "Minor"],
        emotion="Dreamy, Ethereal, Magical",
        category="Major Modes"
    ),
    "Mixolydian": ScaleMode(
        name="Mixolydian",
        intervals=[0, 2, 4, 5, 7, 9, 10],
        chord_qualities=["Major", "Minor", "Diminished", "Major", "Minor", "Minor", "Major"],
        emotion="Bluesy, Relaxed, Rock",
        category="Major Modes"
    ),
    
    # Minor modes
    "Natural Minor (Aeolian)": ScaleMode(
        name="Natural Minor (Aeolian)",
        intervals=[0, 2, 3, 5, 7, 8, 10],
        chord_qualities=["Minor", "Diminished", "Major", "Minor", "Minor", "Major", "Major"],
        emotion="Sad, Melancholic, Reflective",
        category="Minor Modes"
    ),
    "Dorian": ScaleMode(
        name="Dorian",
        intervals=[0, 2, 3, 5, 7, 9, 10],
        chord_qualities=["Minor", "Minor", "Major", "Major", "Minor", "Diminished", "Major"],
        emotion="Jazzy, Sophisticated, Chill",
        category="Minor Modes"
    ),
    "Phrygian": ScaleMode(
        name="Phrygian",
        intervals=[0, 1, 3, 5, 7, 8, 10],
        chord_qualities=["Minor", "Major", "Major", "Minor", "Diminished", "Major", "Minor"],
        emotion="Spanish, Dark, Exotic",
        category="Minor Modes"
    ),
    "Locrian": ScaleMode(
        name="Locrian",
        intervals=[0, 1, 3, 5, 6, 8, 10],
        chord_qualities=["Diminished", "Major", "Minor", "Minor", "Major", "Major", "Minor"],
        emotion="Unstable, Tense, Dissonant",
        category="Minor Modes"
    ),
    
    # Other scales
    "Harmonic Minor": ScaleMode(
        name="Harmonic Minor",
        intervals=[0, 2, 3, 5, 7, 8, 11],
        chord_qualities=["Minor", "Diminished", "Augmented", "Minor", "Major", "Major", "Diminished"],
        emotion="Classical, Dramatic, Middle Eastern",
        category="Other Scales"
    ),
    "Melodic Minor": ScaleMode(
        name="Melodic Minor",
        intervals=[0, 2, 3, 5, 7, 9, 11],
        chord_qualities=["Minor", "Minor", "Augmented", "Major", "Major", "Diminished", "Diminished"],
        emotion="Jazz, Smooth, Complex",
        category="Other Scales"
    ),
    "Pentatonic Major": ScaleMode(
        name="Pentatonic Major",
        intervals=[0, 2, 4, 7, 9],
        chord_qualities=["Major", "Minor", "Minor", "Major", "Minor"],
        emotion="Folk, Simple, Universal",
        category="Pentatonic"
    ),
    "Pentatonic Minor": ScaleMode(
        name="Pentatonic Minor",
        intervals=[0, 3, 5, 7, 10],
        chord_qualities=["Minor", "Major", "Minor", "Minor", "Major"],
        emotion="Blues, Rock, Soulful",
        category="Pentatonic"
    ),
    "Blues": ScaleMode(
        name="Blues",
        intervals=[0, 3, 5, 6, 7, 10],
        chord_qualities=["Minor", "Major", "Diminished", "Diminished", "Minor", "Major"],
        emotion="Bluesy, Gritty, Expressive",
        category="Other Scales"
    ),
}

# Emotion-based presets for quick selection
EMOTION_PRESETS: Dict[str, Tuple[str, str]] = {
    "Happy": ("C", "Major (Ionian)"),
    "Sad": ("A", "Natural Minor (Aeolian)"),
    "Dreamy": ("G", "Lydian"),
    "Dark": ("E", "Phrygian"),
    "Jazzy": ("D", "Dorian"),
    "Bluesy": ("A", "Blues"),
    "Epic": ("D", "Harmonic Minor"),
    "Chill": ("F", "Mixolydian"),
    "Mysterious": ("B", "Locrian"),
    "Smooth": ("C", "Melodic Minor"),
}


def get_chord_notes(root: int, chord_type: str, octave: int = 4) -> List[int]:
    """Generate MIDI notes for a chord given root and type."""
    base = (octave * 12) + (root % 12)
    
    intervals = {
        "Major": [0, 4, 7],
        "Minor": [0, 3, 7],
        "Diminished": [0, 3, 6],
        "Augmented": [0, 4, 8],
        "Dim": [0, 3, 6],
        "Aug": [0, 4, 8],
    }
    
    chord_intervals = intervals.get(chord_type, [0, 4, 7])
    return [base + i for i in chord_intervals]


def generate_diatonic_chords(root_note: int, mode: ScaleMode, octave: int = 4) -> List[Tuple[int, str, List[int]]]:
    """
    Generate diatonic chords for a given key and mode.
    
    Returns list of (root_note, chord_type, midi_notes) tuples.
    """
    chords = []
    for i, interval in enumerate(mode.intervals):
        chord_root = (root_note + interval) % 12
        chord_type = mode.chord_qualities[i] if i < len(mode.chord_qualities) else "Major"
        midi_notes = get_chord_notes(chord_root, chord_type, octave)
        chords.append((chord_root, chord_type, midi_notes))
    return chords


class MiniKeyWidget(QWidget):
    """A minimal piano keyboard widget for chord selection/editing."""
    
    note_clicked = Signal(int)  # Emits MIDI note number
    notes_changed = Signal(list)  # Emits list of selected notes
    
    def __init__(self, octaves: int = 2, start_octave: int = 4, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.octaves = octaves
        self.start_octave = start_octave
        self.selected_notes: List[int] = []
        self._key_rects: Dict[int, Tuple[int, int, int, int]] = {}  # note -> (x, y, w, h)
        self._white_key_width = 24
        self._white_key_height = 80
        self._black_key_width = 16
        self._black_key_height = 50
        
        # Calculate total width
        white_keys_per_octave = 7
        total_white_keys = white_keys_per_octave * octaves
        total_width = total_white_keys * self._white_key_width + 2
        
        self.setFixedSize(total_width, self._white_key_height + 4)
        self.setMouseTracking(True)
        self._hovered_note: Optional[int] = None
        self._build_key_rects()
    
    def _build_key_rects(self) -> None:
        """Pre-calculate key rectangles for hit testing and drawing."""
        self._key_rects.clear()
        
        # White keys pattern: C, D, E, F, G, A, B
        white_notes = [0, 2, 4, 5, 7, 9, 11]  # Semitones from C
        # Black keys pattern: C#, D#, F#, G#, A#
        black_notes = [1, 3, 6, 8, 10]
        
        x = 1
        for octave in range(self.octaves):
            base_note = (self.start_octave + octave) * 12
            
            # White keys
            for i, semitone in enumerate(white_notes):
                note = base_note + semitone
                self._key_rects[note] = (x, 1, self._white_key_width - 1, self._white_key_height)
                x += self._white_key_width
        
        # Black keys (drawn over white keys)
        x = 1
        for octave in range(self.octaves):
            base_note = (self.start_octave + octave) * 12
            
            for i, semitone in enumerate(white_notes[:-1]):  # No black key after B
                if semitone + 1 in black_notes:
                    note = base_note + semitone + 1
                    bx = x + self._white_key_width - self._black_key_width // 2
                    self._key_rects[note] = (bx, 1, self._black_key_width, self._black_key_height)
                x += self._white_key_width
            x = 1 + (octave + 1) * 7 * self._white_key_width
    
    def set_selected_notes(self, notes: List[int]) -> None:
        """Set the currently selected/highlighted notes."""
        self.selected_notes = list(notes)
        self.update()
    
    def toggle_note(self, note: int) -> None:
        """Toggle a note's selection state."""
        if note in self.selected_notes:
            self.selected_notes.remove(note)
        else:
            self.selected_notes.append(note)
            self.selected_notes.sort()
        self.notes_changed.emit(self.selected_notes)
        self.update()
    
    def clear_selection(self) -> None:
        """Clear all selected notes."""
        self.selected_notes.clear()
        self.notes_changed.emit(self.selected_notes)
        self.update()
    
    def paintEvent(self, event) -> None:
        """Draw the mini keyboard."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw white keys first
        white_notes = [0, 2, 4, 5, 7, 9, 11]
        for octave in range(self.octaves):
            base_note = (self.start_octave + octave) * 12
            for semitone in white_notes:
                note = base_note + semitone
                if note in self._key_rects:
                    x, y, w, h = self._key_rects[note]
                    
                    # Determine color
                    if note in self.selected_notes:
                        color = QColor("#2f82e6")  # Blue for selected
                    elif note == self._hovered_note:
                        color = QColor("#e0e0e0")  # Light gray for hover
                    else:
                        color = QColor("#ffffff")  # White
                    
                    painter.fillRect(x, y, w, h, color)
                    painter.setPen(QColor("#666666"))
                    painter.drawRect(x, y, w, h)
        
        # Draw black keys on top
        black_notes = [1, 3, 6, 8, 10]
        for octave in range(self.octaves):
            base_note = (self.start_octave + octave) * 12
            for semitone in black_notes:
                note = base_note + semitone
                if note in self._key_rects:
                    x, y, w, h = self._key_rects[note]
                    
                    # Determine color
                    if note in self.selected_notes:
                        color = QColor("#1a5fb4")  # Darker blue for selected
                    elif note == self._hovered_note:
                        color = QColor("#444444")  # Dark gray for hover
                    else:
                        color = QColor("#222222")  # Black
                    
                    painter.fillRect(x, y, w, h, color)
                    painter.setPen(QColor("#000000"))
                    painter.drawRect(x, y, w, h)
    
    def _note_at_pos(self, x: int, y: int) -> Optional[int]:
        """Find which note is at the given position."""
        # Check black keys first (they're on top)
        black_notes = [1, 3, 6, 8, 10]
        for octave in range(self.octaves):
            base_note = (self.start_octave + octave) * 12
            for semitone in black_notes:
                note = base_note + semitone
                if note in self._key_rects:
                    kx, ky, kw, kh = self._key_rects[note]
                    if kx <= x <= kx + kw and ky <= y <= ky + kh:
                        return note
        
        # Then check white keys
        white_notes = [0, 2, 4, 5, 7, 9, 11]
        for octave in range(self.octaves):
            base_note = (self.start_octave + octave) * 12
            for semitone in white_notes:
                note = base_note + semitone
                if note in self._key_rects:
                    kx, ky, kw, kh = self._key_rects[note]
                    if kx <= x <= kx + kw and ky <= y <= ky + kh:
                        return note
        
        return None
    
    def mousePressEvent(self, event) -> None:
        """Handle mouse click to toggle note selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            note = self._note_at_pos(int(event.position().x()), int(event.position().y()))
            if note is not None:
                self.toggle_note(note)
                self.note_clicked.emit(note)
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for hover effect."""
        note = self._note_at_pos(int(event.position().x()), int(event.position().y()))
        if note != self._hovered_note:
            self._hovered_note = note
            self.update()
    
    def leaveEvent(self, event) -> None:
        """Clear hover when mouse leaves."""
        self._hovered_note = None
        self.update()


class ChordPreviewWidget(QFrame):
    """Widget to preview a single chord with its name and notes."""
    
    def __init__(self, root: int, chord_type: str, notes: List[int], degree: str = "", parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.root = root
        self.chord_type = chord_type
        self.notes = notes
        self.degree = degree
        
        self.setFixedSize(70, 60)
        self.setStyleSheet("""
            ChordPreviewWidget {
                background: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 6px;
            }
            ChordPreviewWidget:hover {
                border: 2px solid #2f82e6;
                background: #3a3f46;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)
        
        # Degree label (I, ii, iii, etc.)
        if degree:
            degree_label = QLabel(degree)
            degree_label.setStyleSheet("color: #888; font-size: 9px;")
            degree_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(degree_label)
        
        # Chord name
        name_label = QLabel(f"{NOTES[root % 12]}")
        name_label.setStyleSheet("color: #fff; font-size: 14px; font-weight: bold;")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(name_label)
        
        # Chord type
        type_label = QLabel(chord_type[:3] if len(chord_type) > 3 else chord_type)
        type_label.setStyleSheet("color: #aaa; font-size: 10px;")
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(type_label)


class AutofillDialog(QDialog):
    """Dialog for autofilling the chord monitor with diatonic chords."""
    
    def __init__(self, midi_out: 'MidiOut', midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.midi = midi_out
        self.midi_channel = midi_channel
        self._preview_notes: List[int] = []
        
        self.setWindowTitle("Autofill Chord Monitor")
        self.setMinimumSize(500, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2127;
            }
            QLabel {
                color: #fff;
            }
            QGroupBox {
                color: #fff;
                border: 1px solid #3b4148;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Autofill Chord Monitor")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        layout.addWidget(title)
        
        # Key selection section
        key_group = QGroupBox("Select Key")
        key_layout = QHBoxLayout(key_group)
        
        key_label = QLabel("Root Note:")
        key_layout.addWidget(key_label)
        
        self.key_combo = QComboBox()
        self.key_combo.addItems(NOTES)
        self.key_combo.setCurrentText("C")
        self.key_combo.setStyleSheet(self._combo_style())
        self.key_combo.currentTextChanged.connect(self._update_preview)
        key_layout.addWidget(self.key_combo)
        
        key_layout.addStretch()
        layout.addWidget(key_group)
        
        # Mode/Scale selection with emotion hints
        mode_group = QGroupBox("Select Mode / Scale")
        mode_layout = QVBoxLayout(mode_group)
        
        self.mode_combo = QComboBox()
        # Group modes by category
        current_category = ""
        for mode_name, mode_data in SCALE_MODES.items():
            if mode_data.category != current_category:
                if current_category:
                    self.mode_combo.insertSeparator(self.mode_combo.count())
                current_category = mode_data.category
            self.mode_combo.addItem(f"{mode_name} - {mode_data.emotion}", mode_name)
        self.mode_combo.setStyleSheet(self._combo_style())
        self.mode_combo.currentIndexChanged.connect(self._update_preview)
        mode_layout.addWidget(self.mode_combo)
        
        layout.addWidget(mode_group)
        
        # Quick emotion presets
        emotion_group = QGroupBox("Quick Emotion Presets")
        emotion_layout = QGridLayout(emotion_group)
        emotion_layout.setSpacing(8)
        
        emotions = list(EMOTION_PRESETS.keys())
        for i, emotion in enumerate(emotions):
            btn = QPushButton(emotion)
            btn.setStyleSheet(self._button_style())
            btn.clicked.connect(lambda checked, e=emotion: self._apply_emotion_preset(e))
            emotion_layout.addWidget(btn, i // 5, i % 5)
        
        layout.addWidget(emotion_group)
        
        # Chord preview section
        preview_group = QGroupBox("Preview Chords")
        preview_layout = QVBoxLayout(preview_group)
        
        # Mini keyboard for visual reference
        self.mini_keyboard = MiniKeyWidget(octaves=2, start_octave=4, parent=self)
        preview_layout.addWidget(self.mini_keyboard, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Chord preview grid
        self.chord_preview_layout = QHBoxLayout()
        self.chord_preview_layout.setSpacing(8)
        preview_layout.addLayout(self.chord_preview_layout)
        
        layout.addWidget(preview_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        preview_btn = QPushButton("Preview All")
        preview_btn.setStyleSheet(self._button_style())
        preview_btn.clicked.connect(self._preview_all_chords)
        button_layout.addWidget(preview_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._button_style())
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        fill_btn = QPushButton("Fill Grid")
        fill_btn.setStyleSheet(self._button_style(primary=True))
        fill_btn.clicked.connect(self.accept)
        button_layout.addWidget(fill_btn)
        
        layout.addLayout(button_layout)
        
        # Initial preview
        self._update_preview()
    
    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 6px;
                padding: 8px 12px;
                color: #fff;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 2px solid #2f82e6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                selection-background-color: #2f82e6;
                color: #fff;
            }
        """
    
    def _button_style(self, primary: bool = False) -> str:
        if primary:
            return """
                QPushButton {
                    background-color: #2f82e6;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    color: #fff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4a9fff;
                }
                QPushButton:pressed {
                    background-color: #2a6fc2;
                }
            """
        return """
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 6px;
                padding: 8px 16px;
                color: #fff;
            }
            QPushButton:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
            }
            QPushButton:pressed {
                background-color: #2b2f36;
            }
        """
    
    def _apply_emotion_preset(self, emotion: str) -> None:
        """Apply an emotion preset to key and mode selection."""
        if emotion in EMOTION_PRESETS:
            key, mode = EMOTION_PRESETS[emotion]
            self.key_combo.setCurrentText(key)
            # Find and select the mode in combo box
            for i in range(self.mode_combo.count()):
                if self.mode_combo.itemData(i) == mode:
                    self.mode_combo.setCurrentIndex(i)
                    break
    
    def _update_preview(self) -> None:
        """Update the chord preview based on current selections."""
        # Clear existing previews
        while self.chord_preview_layout.count():
            item = self.chord_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Get current selections
        root_note = NOTE_TO_INDEX.get(self.key_combo.currentText(), 0)
        mode_name = self.mode_combo.currentData()
        if mode_name and mode_name in SCALE_MODES:
            mode = SCALE_MODES[mode_name]
            chords = generate_diatonic_chords(root_note, mode, octave=4)
            
            # Roman numeral degrees
            degrees = ["I", "ii", "iii", "IV", "V", "vi", "vii°"]
            if "Minor" in mode_name or mode_name in ["Dorian", "Phrygian", "Locrian"]:
                degrees = ["i", "ii°", "III", "iv", "v", "VI", "VII"]
            
            # Create preview widgets
            all_notes = []
            for i, (chord_root, chord_type, notes) in enumerate(chords):
                degree = degrees[i] if i < len(degrees) else ""
                preview = ChordPreviewWidget(chord_root, chord_type, notes, degree, self)
                self.chord_preview_layout.addWidget(preview)
                all_notes.extend(notes)
            
            # Update mini keyboard to show scale notes
            scale_notes = [(root_note + interval) % 12 + 48 for interval in mode.intervals]  # Octave 4
            scale_notes.extend([(root_note + interval) % 12 + 60 for interval in mode.intervals])  # Octave 5
            self.mini_keyboard.set_selected_notes(scale_notes)
    
    def _preview_all_chords(self) -> None:
        """Play a quick preview of all chords in sequence."""
        root_note = NOTE_TO_INDEX.get(self.key_combo.currentText(), 0)
        mode_name = self.mode_combo.currentData()
        if mode_name and mode_name in SCALE_MODES:
            mode = SCALE_MODES[mode_name]
            chords = generate_diatonic_chords(root_note, mode, octave=4)
            
            def play_chord(index: int) -> None:
                if index >= len(chords):
                    return
                # Stop previous notes
                for note in self._preview_notes:
                    self.midi.note_off(note, self.midi_channel)
                
                # Play new chord
                _, _, notes = chords[index]
                self._preview_notes = notes
                for note in notes:
                    self.midi.note_on(note, 80, self.midi_channel)
                
                # Schedule next chord
                QTimer.singleShot(400, lambda: play_chord(index + 1))
            
            play_chord(0)
            
            # Stop after all chords
            QTimer.singleShot(400 * (len(chords) + 1), self._stop_preview)
    
    def _stop_preview(self) -> None:
        """Stop any playing preview notes."""
        for note in self._preview_notes:
            self.midi.note_off(note, self.midi_channel)
        self._preview_notes = []
    
    def get_chords(self) -> List[Tuple[int, str, List[int]]]:
        """Get the list of chords to fill the grid with."""
        root_note = NOTE_TO_INDEX.get(self.key_combo.currentText(), 0)
        mode_name = self.mode_combo.currentData()
        if mode_name and mode_name in SCALE_MODES:
            mode = SCALE_MODES[mode_name]
            return generate_diatonic_chords(root_note, mode, octave=4)
        return []
    
    def closeEvent(self, event) -> None:
        """Stop any playing notes when dialog closes."""
        self._stop_preview()
        super().closeEvent(event)


class ChordEditDialog(QDialog):
    """Dialog for editing a chord using an interactive keyboard."""
    
    def __init__(self, root_note: int, chord_type: str, actual_notes: List[int],
                 midi_out: 'MidiOut', midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.midi = midi_out
        self.midi_channel = midi_channel
        self.original_root = root_note
        self.original_type = chord_type
        self.original_notes = actual_notes.copy() if actual_notes else []
        self._playing_notes: List[int] = []
        
        self.setWindowTitle("Edit Chord")
        self.setMinimumSize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e2127;
            }
            QLabel {
                color: #fff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("Edit Chord")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        layout.addWidget(title)
        
        # Current chord display
        current_label = QLabel(f"Current: {NOTES[root_note % 12]} {chord_type}")
        current_label.setStyleSheet("font-size: 14px; color: #aaa;")
        layout.addWidget(current_label)
        
        # Instructions
        instructions = QLabel("Click keys to select notes for your chord. Right-click to clear.")
        instructions.setStyleSheet("font-size: 11px; color: #888;")
        layout.addWidget(instructions)
        
        # Mini keyboard for editing
        self.keyboard = MiniKeyWidget(octaves=2, start_octave=4, parent=self)
        if actual_notes:
            self.keyboard.set_selected_notes(actual_notes)
        self.keyboard.notes_changed.connect(self._on_notes_changed)
        layout.addWidget(self.keyboard, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Selected notes display
        self.notes_label = QLabel(self._format_notes(actual_notes))
        self.notes_label.setStyleSheet("font-size: 12px; color: #2f82e6;")
        self.notes_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.notes_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(self._button_style())
        clear_btn.clicked.connect(self._clear_selection)
        button_layout.addWidget(clear_btn)
        
        preview_btn = QPushButton("Preview")
        preview_btn.setStyleSheet(self._button_style())
        preview_btn.clicked.connect(self._preview_chord)
        button_layout.addWidget(preview_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(self._button_style())
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save")
        save_btn.setStyleSheet(self._button_style(primary=True))
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def _button_style(self, primary: bool = False) -> str:
        if primary:
            return """
                QPushButton {
                    background-color: #2f82e6;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    color: #fff;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4a9fff;
                }
            """
        return """
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 6px;
                padding: 8px 16px;
                color: #fff;
            }
            QPushButton:hover {
                border: 2px solid #2f82e6;
            }
        """
    
    def _format_notes(self, notes: List[int]) -> str:
        """Format note list for display."""
        if not notes:
            return "No notes selected"
        note_names = [f"{NOTES[n % 12]}{n // 12}" for n in sorted(notes)]
        return " - ".join(note_names)
    
    def _on_notes_changed(self, notes: List[int]) -> None:
        """Handle note selection changes."""
        self.notes_label.setText(self._format_notes(notes))
    
    def _clear_selection(self) -> None:
        """Clear all selected notes."""
        self.keyboard.clear_selection()
    
    def _preview_chord(self) -> None:
        """Play the current chord selection."""
        # Stop any currently playing notes
        self._stop_playing()
        
        # Play selected notes
        notes = self.keyboard.selected_notes
        for note in notes:
            self.midi.note_on(note, 80, self.midi_channel)
            self._playing_notes.append(note)
        
        # Stop after delay
        QTimer.singleShot(800, self._stop_playing)
    
    def _stop_playing(self) -> None:
        """Stop any playing notes."""
        for note in self._playing_notes:
            self.midi.note_off(note, self.midi_channel)
        self._playing_notes = []
    
    def get_notes(self) -> List[int]:
        """Get the selected notes."""
        return sorted(self.keyboard.selected_notes)
    
    def closeEvent(self, event) -> None:
        """Stop any playing notes when dialog closes."""
        self._stop_playing()
        super().closeEvent(event)
    
    def contextMenuEvent(self, event) -> None:
        """Right-click to clear selection."""
        self._clear_selection()
