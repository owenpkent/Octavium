"""Chord Selector Widget with drag-and-drop chord cards for replay functionality."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QComboBox, QFrame, QScrollArea, QMenu, QSizePolicy, QSlider, QCheckBox
)
from PySide6.QtCore import Qt, QMimeData, QPoint, QTimer, QRectF
from PySide6.QtGui import QDrag, QPainter, QColor, QFont
from typing import List, Tuple, Optional, Callable, Iterable, Dict, Set, FrozenSet, TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .keyboard_widget import RangeSlider
from dataclasses import dataclass
from collections import defaultdict
import random
from .midi_io import MidiOut

# Chord definitions: (root_note_offset, intervals)
# Intervals are relative to root, in semitones (0-11 for one octave, can extend beyond)
CHORD_DEFINITIONS = {
    # Basic Triads
    "Major": (0, [0, 4, 7]),
    "Minor": (0, [0, 3, 7]),
    "Diminished": (0, [0, 3, 6]),
    "Augmented": (0, [0, 4, 8]),
    "Sus2": (0, [0, 2, 7]),
    "Sus4": (0, [0, 5, 7]),
    
    # 6th Chords
    "Major 6th": (0, [0, 4, 7, 9]),
    "Minor 6th": (0, [0, 3, 7, 9]),
    "6/9": (0, [0, 4, 7, 9, 14]),
    
    # 7th Chords
    "Major 7th": (0, [0, 4, 7, 11]),
    "Minor 7th": (0, [0, 3, 7, 10]),
    "Dominant 7th": (0, [0, 4, 7, 10]),
    "Diminished 7th": (0, [0, 3, 6, 9]),
    "Half Diminished": (0, [0, 3, 6, 10]),
    "Augmented 7th": (0, [0, 4, 8, 10]),
    "Minor Major 7th": (0, [0, 3, 7, 11]),
    
    # Suspended 7th
    "Sus2 7th": (0, [0, 2, 7, 10]),
    "Sus4 7th": (0, [0, 5, 7, 10]),
    
    # Add Chords
    "Add9": (0, [0, 4, 7, 14]),
    "Minor Add9": (0, [0, 3, 7, 14]),
    "Add11": (0, [0, 4, 7, 17]),
    "Add13": (0, [0, 4, 7, 21]),
    
    # 9th Chords
    "Major 9th": (0, [0, 4, 7, 11, 14]),
    "Minor 9th": (0, [0, 3, 7, 10, 14]),
    "Dominant 9th": (0, [0, 4, 7, 10, 14]),
    "Diminished 9th": (0, [0, 3, 6, 9, 14]),
    "Minor Major 9th": (0, [0, 3, 7, 11, 14]),
    
    # 11th Chords
    "Major 11th": (0, [0, 4, 7, 11, 14, 17]),
    "Minor 11th": (0, [0, 3, 7, 10, 14, 17]),
    "Dominant 11th": (0, [0, 4, 7, 10, 14, 17]),
    
    # 13th Chords
    "Major 13th": (0, [0, 4, 7, 11, 14, 17, 21]),
    "Minor 13th": (0, [0, 3, 7, 10, 14, 17, 21]),
    "Dominant 13th": (0, [0, 4, 7, 10, 14, 17, 21]),
    
    # Altered Chords
    "7♭9": (0, [0, 4, 7, 10, 13]),  # Dominant 7 flat 9
    "7♯9": (0, [0, 4, 7, 10, 15]),  # Dominant 7 sharp 9
    "7♭5": (0, [0, 4, 6, 10]),       # Dominant 7 flat 5
    "7♯5": (0, [0, 4, 8, 10]),       # Dominant 7 sharp 5
    "7♭9♯9": (0, [0, 4, 7, 10, 13, 15]),  # 7 flat 9 sharp 9
    
    # Power Chords
    "Power": (0, [0, 7]),
    "Power 5th": (0, [0, 7]),
    
    # Extended Power Chords
    "Power +4": (0, [0, 7, 17]),    # Power chord with add11
    
    # 2-Note Intervals (Dyads)
    "Unison": (0, [0, 0]),          # Same note (octave)
    "Minor 2nd": (0, [0, 1]),
    "Major 2nd": (0, [0, 2]),
    "Minor 3rd": (0, [0, 3]),
    "Major 3rd": (0, [0, 4]),
    "Perfect 4th": (0, [0, 5]),
    "Tritone": (0, [0, 6]),
    "Perfect 5th": (0, [0, 7]),
    "Minor 6th": (0, [0, 8]),
    "Major 6th": (0, [0, 9]),
    "Minor 7th": (0, [0, 10]),
    "Major 7th": (0, [0, 11]),
    "Octave": (0, [0, 12]),
    
    # Jazz Chords
    "Major 7♯11": (0, [0, 4, 7, 11, 18]),  # Major 7 sharp 11 (lydian)
    "Minor 7♭5": (0, [0, 3, 6, 10]),       # Minor 7 flat 5
    
    # Quartal/Quintal Chords (stacked 4ths/5ths)
    "Quartal": (0, [0, 5, 10]),
    "Quintal": (0, [0, 7, 14]),
    
    # Cluster Chords
    "Cluster": (0, [0, 1, 2]),      # Very tight intervals
    "Cluster Minor": (0, [0, 1, 3]),
    
    # Open Chords (wider voicings)
    "Open Major": (0, [0, 4, 7, 12]),  # With octave
    "Open Minor": (0, [0, 3, 7, 12]),
}

NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# ---------- Improved Chord Detection ----------

NOTE_NAMES_SHARP = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
NOTE_NAMES_FLAT  = ["C","Db","D","Eb","E","F","Gb","G","Ab","A","Bb","B"]

def pc(n: int) -> int:
    """Get pitch class (0-11) from MIDI note."""
    return n % 12

def pcs(notes: Iterable[int]) -> FrozenSet[int]:
    """Reduce MIDI notes or pitch classes to a pitch-class set."""
    return frozenset(pc(n) for n in notes)

def transpose(pcs_set: FrozenSet[int], t: int) -> FrozenSet[int]:
    """Transpose a pitch class set by t semitones."""
    return frozenset(pc(n + t) for n in pcs_set)

def name_root(root_pc: int, prefer_flats=False) -> str:
    """Get root note name from pitch class."""
    names = NOTE_NAMES_FLAT if prefer_flats else NOTE_NAMES_SHARP
    return names[root_pc]

# Chord library, normalized to pitch classes
_RAW_CHORDS: Dict[str, List[int]] = {
    # Triads
    "Major": [0,4,7],
    "Minor": [0,3,7],
    "Diminished": [0,3,6],
    "Augmented": [0,4,8],
    "Sus2": [0,2,7],
    "Sus4": [0,5,7],
    # 6ths
    "Major 6th": [0,4,7,9],
    "Minor 6th": [0,3,7,9],
    "6/9": [0,4,7,2],  # 14 -> 2 (normalized)
    # 7ths
    "Major 7th": [0,4,7,11],
    "Minor 7th": [0,3,7,10],
    "Dominant 7th": [0,4,7,10],
    "Diminished 7th": [0,3,6,9],
    "Half Diminished": [0,3,6,10],     # m7b5
    "Minor Major 7th": [0,3,7,11],
    "Augmented 7th": [0,4,8,10],
    # Suspended 7ths
    "Sus2 7th": [0,2,7,10],
    "Sus4 7th": [0,5,7,10],
    # Add chords
    "Add9": [0,4,7,2],
    "Minor Add9": [0,3,7,2],
    "Add11": [0,4,7,5],
    "Add13": [0,4,7,9],
    # 9ths
    "Major 9th": [0,4,7,11,2],
    "Minor 9th": [0,3,7,10,2],
    "Dominant 9th": [0,4,7,10,2],
    "Diminished 9th": [0,3,6,9,2],
    "Minor Major 9th": [0,3,7,11,2],
    # 11ths
    "Major 11th": [0,4,7,11,2,5],
    "Minor 11th": [0,3,7,10,2,5],
    "Dominant 11th": [0,4,7,10,2,5],
    # 13ths
    "Major 13th": [0,4,7,11,2,5,9],
    "Minor 13th": [0,3,7,10,2,5,9],
    "Dominant 13th": [0,4,7,10,2,5,9],
    # Altered dominants
    "7♭9": [0,4,7,10,1],
    "7♯9": [0,4,7,10,3],
    "7♭5": [0,4,6,10],
    "7♯5": [0,4,8,10],
    "7♭9♯9": [0,4,7,10,1,3],
    # Power / dyads
    "Power": [0,7],
    "Quartal": [0,5,10],
    "Quintal": [0,7,2],
    "Cluster": [0,1,2],
    "Open Major": [0,4,7],
    "Open Minor": [0,3,7],
    # Intervals as named dyads
    "Perfect 5th": [0,7],
    "Perfect 4th": [0,5],
    "Tritone": [0,6],
    "Major 3rd": [0,4],
    "Minor 3rd": [0,3],
    "Major 2nd": [0,2],
    "Minor 2nd": [0,1],
    "Major 6th (dyad)": [0,9],
    "Minor 6th": [0,8],
    "Major 7th (dyad)": [0,11],
    "Minor 7th (dyad)": [0,10],
    "Octave": [0,0],  # Unison/octave
    "Unison": [0,0],
}

@dataclass(frozen=True)
class ChordTemplate:
    name: str
    pcs: FrozenSet[int]
    size: int

# Build normalized library
CHORD_TEMPLATES: List[ChordTemplate] = []
_seen: Set[FrozenSet[int]] = set()
for name, ivals in _RAW_CHORDS.items():
    s = frozenset(pc(i) for i in ivals)
    CHORD_TEMPLATES.append(ChordTemplate(name, s, len(s)))

@dataclass
class Match:
    name: str
    root: int
    score: float
    missing: Set[int]
    extras: Set[int]
    template_size: int

def score_match(chord_set: FrozenSet[int],
                templ_set: FrozenSet[int],
                allow_omit_third: bool = True,
                allow_omit_fifth: bool = True) -> Tuple[float, Set[int], Set[int]]:
    """
    Score how well a chord set matches a template.
    Positive for covered tones, small penalty for extras, small penalty for allowed omissions,
    larger penalty for missing essential tones.
    """
    covered = chord_set & templ_set
    missing = templ_set - chord_set
    extras = chord_set - templ_set

    # Essential tones: root (0) always essential; third and fifth can be optionally omitted
    essential_missing = set()
    optional_missing = set()
    for tone in missing:
        if tone == 0:
            essential_missing.add(tone)
        elif tone in {3,4} and allow_omit_third:
            optional_missing.add(tone)
        elif tone in {7,6,8} and allow_omit_fifth:
            optional_missing.add(tone)
        else:
            essential_missing.add(tone)

    score = (
        2.0 * len(covered)
        - 1.0 * len(extras)
        - 1.5 * len(essential_missing)
        - 0.25 * len(optional_missing)
    )
    return score, essential_missing | optional_missing, set(extras)

def detect_chords_improved(notes: Iterable[int],
                  prefer_flats: bool = False,
                  include_dyads: bool = False,
                  top_k: int = 5) -> List[Match]:
    """
    Improved chord detection with scoring system.
    Returns ranked matches with root and score.
    """
    input_set = pcs(notes)
    results: List[Match] = []
    
    for root in range(12):
        # Rotate so 'root' is treated as 0
        rel = frozenset(pc(n - root) for n in input_set)
        for templ in CHORD_TEMPLATES:
            if not include_dyads and templ.size < 3:
                continue
            sc, missing, extras = score_match(rel, templ.pcs)
            if sc > 0.0:
                results.append(Match(templ.name, root, sc, missing, extras, templ.size))
    
    # Sort by score, then prefer larger templates to reduce trivial matches
    results.sort(key=lambda m: (m.score, m.template_size), reverse=True)

    # Deduplicate by (name, root) keeping best score
    best: Dict[Tuple[str,int], Match] = {}
    for r in results:
        key = (r.name, r.root)
        if key not in best or r.score > best[key].score:
            best[key] = r
    
    ranked = list(best.values())
    ranked.sort(key=lambda m: (m.score, m.template_size), reverse=True)
    return ranked[:top_k]


def detect_chord(notes: list[int]) -> tuple[Optional[int], Optional[str]]:
    """Detect chord from a list of MIDI notes using improved algorithm.
    Returns (root_note_offset, chord_type) or (None, None) if no chord detected.
    Always returns something when notes are playing (handles 1 note, 2 notes, etc.)
    """
    if not notes:
        return (None, None)
    
    # Handle single note
    if len(notes) == 1:
        note = notes[0]
        root_pc = note % 12
        return (root_pc, "Note")
    
    # Convert to pitch classes
    pitch_classes = sorted(set(pc(n) for n in notes))
    
    # Handle case where all notes are the same pitch class (octaves)
    if len(pitch_classes) == 1:
        root_pc = pitch_classes[0]
        return (root_pc, "Octave")
    
    # Use improved detection algorithm
    try:
        matches = detect_chords_improved(notes, prefer_flats=False, include_dyads=True, top_k=1)
        if matches and len(matches) > 0:
            best = matches[0]
            return (best.root, best.name)
    except Exception:
        pass
    
    # Fallback: Handle 2-note intervals manually if improved algorithm didn't match
    if len(pitch_classes) == 2:
        interval = (pitch_classes[1] - pitch_classes[0]) % 12
        interval_map = {
            0: "Unison",
            1: "Minor 2nd",
            2: "Major 2nd",
            3: "Minor 3rd",
            4: "Major 3rd",
            5: "Perfect 4th",
            6: "Tritone",
            7: "Perfect 5th",
            8: "Minor 6th",
            9: "Major 6th",
            10: "Minor 7th",
            11: "Major 7th",
        }
        if interval in interval_map:
            return (pitch_classes[0], interval_map[interval])
        return (pitch_classes[0], f"Interval {interval}")
    
    # Final fallback: show interval pattern or note count
    if len(pitch_classes) >= 3:
        interval_names = []
        intervals = [(pitch_classes[i] - pitch_classes[0]) % 12 for i in range(1, len(pitch_classes))]
        interval_map = {1: "m2", 2: "M2", 3: "m3", 4: "M3", 5: "P4", 6: "TT", 
                       7: "P5", 8: "m6", 9: "M6", 10: "m7", 11: "M7"}
        for iv in intervals:
            if iv in interval_map:
                interval_names.append(interval_map[iv])
        
        if interval_names:
            return (pitch_classes[0], f"({''.join(interval_names)})")
        else:
            return (pitch_classes[0], f"{len(pitch_classes)} Notes")
    
    return (pitch_classes[0] if pitch_classes else 0, "Chord")


class ReplayCard(QFrame):
    """A clickable card in the replay area that plays a chord."""
    _slot_index: Optional[int]  # For grid tracking
    
    def __init__(self, root_note: int, chord_type: str, replay_area: 'ReplayArea', actual_notes: Optional[List[int]] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.root_note = root_note
        self.chord_type = chord_type
        self.actual_notes = actual_notes or []  # Store actual MIDI notes for exact replay
        self.replay_area = replay_area
        self._slot_index = None
        self._playing_notes: List[int] = []  # Track currently playing notes
        self._pending_timers: List[QTimer] = []  # Track pending delayed note timers
        self._should_play = False  # Flag to prevent delayed notes after release
        self.setFixedSize(120, 80)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setAcceptDrops(True)  # Allow drops on cards to replace them
        self.setStyleSheet("""
            ReplayCard {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 8px;
                padding: 8px;
            }
            ReplayCard:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Root note label
        root_label = QLabel(NOTES[root_note % 12])
        root_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        root_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(root_label)
        
        # Chord type label
        type_label = QLabel(chord_type)
        type_label.setStyleSheet("font-size: 12px; color: #aaa;")
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setWordWrap(True)
        layout.addWidget(type_label)
        
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def dragEnterEvent(self, event):  # type: ignore[override]
        """Accept drag events on the card."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
    
    def dragMoveEvent(self, event):  # type: ignore[override]
        """Handle drag move on the card."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
    
    def dropEvent(self, event):
        """Handle drop on the card - replace this card with the dropped chord."""
        if not event.mimeData().hasText():
            return
        
        data = event.mimeData().text()
        try:
            parts = data.split(":")
            root_note_str = parts[0]
            chord_type = parts[1]
            root_note = int(root_note_str)
            
            # Parse actual notes if present
            actual_notes = None
            if len(parts) >= 3 and parts[2]:
                try:
                    actual_notes = [int(n) for n in parts[2].split(",") if n.strip()]
                except (ValueError, AttributeError):
                    actual_notes = None
            
            # Update this card's data
            self.root_note = root_note
            self.chord_type = chord_type
            self.actual_notes = actual_notes or []
            
            # Update labels
            layout = self.layout()
            if layout:
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if isinstance(widget, QLabel):
                            if i == 0:  # Root note label
                                widget.setText(NOTES[root_note % 12])
                            else:  # Chord type label
                                widget.setText(chord_type)
            
            # If this card is in a grid (Chord Monitor), update grid tracking
            if hasattr(self, '_slot_index'):
                slot_idx = getattr(self, '_slot_index', None)
                if slot_idx is not None and hasattr(self.replay_area, 'grid_positions'):
                    # Update grid tracking
                    self.replay_area.grid_positions[slot_idx] = self
            
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        except Exception:
            pass
    
    def mousePressEvent(self, event):  # type: ignore[override]
        """Play chord when mouse button is pressed and hold it."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Stop any currently playing notes first
            self._stop_playing_notes()
            
            # Enable playback
            self._should_play = True
            
            # Determine which notes to play
            if self.actual_notes:
                notes_to_play = self.actual_notes
            else:
                # Generate notes from chord type
                if self.chord_type in CHORD_DEFINITIONS:
                    _, intervals = CHORD_DEFINITIONS[self.chord_type]
                    base_note = 60 + self.root_note
                    notes_to_play = [base_note + interval for interval in intervals]
                else:
                    notes_to_play = []
            
            # Play the notes and track them
            if notes_to_play:
                self._playing_notes = notes_to_play
                self._play_notes_sustained(notes_to_play)
    
    def mouseReleaseEvent(self, event):  # type: ignore[override]
        """Stop playing chord when mouse button is released."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Disable playback to prevent delayed notes
            self._should_play = False
            # Cancel any pending timers
            self._cancel_pending_timers()
            
            # Check if sustain is enabled
            sustain_enabled = False
            if hasattr(self.replay_area, 'sustain'):
                sustain_enabled = self.replay_area.sustain
            
            # Only stop notes if sustain is off
            if not sustain_enabled:
                self._stop_playing_notes()
    
    def _play_notes_sustained(self, notes: List[int]) -> None:
        """Play notes without auto-release (for hold functionality)."""
        # Get drift value and direction from parent window
        drift_ms = 0
        drift_direction = "Up"
        if hasattr(self.replay_area, '_parent_window') and self.replay_area._parent_window is not None:
            if hasattr(self.replay_area._parent_window, '_get_drift'):
                drift_ms = self.replay_area._parent_window._get_drift()
            if hasattr(self.replay_area._parent_window, '_get_drift_direction'):
                drift_direction = self.replay_area._parent_window._get_drift_direction()
        
        # Play notes with drift timing
        if drift_ms > 0 and len(notes) > 1:
            # Order notes based on drift direction
            ordered_notes = notes.copy()
            if drift_direction == "Down":
                ordered_notes.reverse()
            elif drift_direction == "Random":
                import random as rand
                rand.shuffle(ordered_notes)
            # "Up" uses the natural order
            
            # Spread notes over the drift time
            for i, note in enumerate(ordered_notes):
                # Calculate delay for this note (spread evenly across drift time)
                delay_ms = int((i / (len(ordered_notes) - 1)) * drift_ms) if len(ordered_notes) > 1 else 0
                
                # Schedule note with delay
                if delay_ms == 0:
                    # Play first note immediately
                    velocity = self._get_velocity_for_note()
                    self.replay_area.midi.note_on(note, velocity, self.replay_area.midi_channel)
                else:
                    # Schedule delayed notes and track the timer
                    timer = QTimer()
                    timer.setSingleShot(True)
                    timer.timeout.connect(lambda n=note: self._play_single_note(n))
                    timer.start(delay_ms)
                    self._pending_timers.append(timer)
        else:
            # No drift - play all notes immediately
            for note in notes:
                velocity = self._get_velocity_for_note()
                self.replay_area.midi.note_on(note, velocity, self.replay_area.midi_channel)
    
    def _get_velocity_for_note(self) -> int:
        """Get velocity for a single note."""
        velocity = 100
        if hasattr(self.replay_area, '_parent_window') and self.replay_area._parent_window is not None:
            if hasattr(self.replay_area._parent_window, '_get_velocity'):
                velocity = self.replay_area._parent_window._get_velocity()
        elif hasattr(self.replay_area, '_parent_widget') and self.replay_area._parent_widget is not None:
            if hasattr(self.replay_area._parent_widget, '_get_velocity'):
                velocity = self.replay_area._parent_widget._get_velocity()
        return velocity
    
    def _play_single_note(self, note: int) -> None:
        """Play a single note (used for delayed playback with drift)."""
        # Only play if we should still be playing (mouse still held)
        if not self._should_play:
            return
        velocity = self._get_velocity_for_note()
        self.replay_area.midi.note_on(note, velocity, self.replay_area.midi_channel)
    
    def _cancel_pending_timers(self) -> None:
        """Cancel all pending delayed note timers."""
        for timer in self._pending_timers:
            if timer.isActive():
                timer.stop()
        self._pending_timers = []
    
    def _stop_playing_notes(self) -> None:
        """Stop all currently playing notes."""
        for note in self._playing_notes:
            self.replay_area.midi.note_off(note, self.replay_area.midi_channel)
        self._playing_notes = []


class ChordCard(QFrame):
    """A draggable card representing a chord."""
    drag_start_position: QPoint
    
    def __init__(self, root_note: int, chord_type: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.root_note = root_note
        self.chord_type = chord_type
        self.drag_start_position = QPoint()
        self.setFixedSize(120, 80)
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            ChordCard {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 8px;
                padding: 8px;
            }
            ChordCard:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Root note label
        root_label = QLabel(NOTES[root_note % 12])
        root_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #fff;")
        root_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(root_label)
        
        # Chord type label
        type_label = QLabel(chord_type)
        type_label.setStyleSheet("font-size: 12px; color: #aaa;")
        type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        type_label.setWordWrap(True)
        layout.addWidget(type_label)
        
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mousePressEvent(self, event):  # type: ignore[override]
        """Start drag operation."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event):  # type: ignore[override]
        """Handle drag movement."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < 10:
            return
        
        drag = QDrag(self)
        mime_data = QMimeData()
        # Store chord data as text
        chord_data = f"{self.root_note}:{self.chord_type}"
        mime_data.setText(chord_data)
        drag.setMimeData(mime_data)
        
        # Create a pixmap for drag preview
        pixmap = self.grab()
        if pixmap:
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.pos())
        
        # Use CopyAction for cross-window drags (MoveAction doesn't work across windows)
        result = drag.exec_(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, event):  # type: ignore[override]
        """Reset cursor on release."""
        self.setCursor(Qt.CursorShape.OpenHandCursor)


class ReplayArea(QWidget):
    """Area where chord cards can be dropped and clicked to replay."""
    _layout: QHBoxLayout
    grid_positions: Dict[int, ReplayCard]  # For chord monitor compatibility
    _parent_widget: Optional['ChordSelectorWidget']  # For velocity access
    _parent_window: Optional[Any]  # For chord monitor window reference
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.midi = midi_out
        self.midi_channel = midi_channel
        self.cards: List[ReplayCard] = []
        self.grid_positions = {}
        self._parent_widget = None
        self._parent_window = None
        
        self.setAcceptDrops(True)
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            ReplayArea {
                background-color: #1e2127;
                border: 2px dashed #3b4148;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._layout = layout
        
        # Placeholder label
        self.placeholder = QLabel("Drag chord cards here to replay")
        self.placeholder.setStyleSheet("color: #666; font-style: italic;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.placeholder)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def dragEnterEvent(self, event):  # type: ignore[override]
        """Accept drag events."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

    def dragMoveEvent(self, event):  # type: ignore[override]
        """Handle drag move."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

    def dropEvent(self, event):  # type: ignore[override]
        """Handle dropped chord card."""
        if not event.mimeData().hasText():
            return
        
        data = event.mimeData().text()
        try:
            parts = data.split(":")
            root_note_str = parts[0]
            chord_type = parts[1]
            root_note = int(root_note_str)
            
            # Parse actual notes if present (format: "root:type:note1,note2,note3")
            actual_notes: Optional[List[int]] = None
            if len(parts) >= 3 and parts[2]:
                try:
                    actual_notes = [int(n) for n in parts[2].split(",") if n.strip()]
                except (ValueError, AttributeError):
                    actual_notes = None
            
            # Hide placeholder
            if self.placeholder.isVisible():
                self.placeholder.hide()
            
            # Create a new card in the replay area with actual notes
            card = ReplayCard(root_note, chord_type, self, actual_notes)
            self.cards.append(card)
            self._layout.addWidget(card)
            
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        except Exception:
            pass

    def _replay_chord(self, root_note: int, chord_type: str):
        """Play the chord when card is clicked."""
        self._play_chord(root_note, chord_type)
    
    def _play_exact_notes(self, notes: List[int]) -> None:
        """Play exact MIDI notes (preserves octave and voicing)."""
        if not notes:
            return
        
        # Get velocity from parent widget if available
        velocity = 100
        if self._parent_widget is not None:
            if hasattr(self._parent_widget, '_get_velocity'):
                velocity = self._parent_widget._get_velocity()
        
        # Play all notes
        for note in notes:
            self.midi.note_on(note, velocity, self.midi_channel)
        
        # Schedule note offs after a short duration (200ms)
        def release_notes() -> None:
            for note in notes:
                self.midi.note_off(note, self.midi_channel)
        
        QTimer.singleShot(200, release_notes)

    def _play_chord(self, root_note: int, chord_type: str) -> None:
        """Play a chord using MIDI."""
        if chord_type not in CHORD_DEFINITIONS:
            return
        
        _, intervals = CHORD_DEFINITIONS[chord_type]
        base_note = 60 + root_note  # C4 + root offset
        
        # Get velocity from parent widget if available
        velocity = 100
        if self._parent_widget is not None:
            if hasattr(self._parent_widget, '_get_velocity'):
                velocity = self._parent_widget._get_velocity()
        
        # Play all notes of the chord
        for interval in intervals:
            note = base_note + interval
            self.midi.note_on(note, velocity, self.midi_channel)
        
        # Schedule note offs after a short duration (200ms)
        def release_notes() -> None:
            for interval in intervals:
                note = base_note + interval
                self.midi.note_off(note, self.midi_channel)
        
        # Use QTimer for delayed release
        QTimer.singleShot(200, release_notes)

    def set_channel(self, channel: int) -> None:
        """Update MIDI channel."""
        self.midi_channel = channel


class ChordSelectorWidget(QWidget):
    """Main widget for chord selection and management."""
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Late import to avoid circular dependency
        from .keyboard_widget import RangeSlider  # noqa: F811
        self._RangeSlider = RangeSlider
        
        self.midi = midi_out
        self.midi_channel = midi_channel
        self.current_card: Optional[ChordCard] = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header
        header = QLabel("Chord Selector")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #fff;")
        layout.addWidget(header)
        
        # Chord selection controls
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        
        # Root note selector
        root_label = QLabel("Root:")
        root_label.setStyleSheet("color: #aaa;")
        controls_layout.addWidget(root_label)
        
        self.root_combo = QComboBox()
        for note in NOTES:
            self.root_combo.addItem(note)
        self.root_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2f36;
                border: 1px solid #3b4148;
                border-radius: 4px;
                padding: 4px 8px;
                color: #fff;
                min-width: 80px;
            }
            QComboBox:hover {
                border: 1px solid #2f82e6;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        controls_layout.addWidget(self.root_combo)
        
        # Chord type selector
        type_label = QLabel("Type:")
        type_label.setStyleSheet("color: #aaa;")
        controls_layout.addWidget(type_label)
        
        self.type_combo = QComboBox()
        for chord_type in CHORD_DEFINITIONS.keys():
            self.type_combo.addItem(chord_type)
        self.type_combo.setStyleSheet("""
            QComboBox {
                background-color: #2b2f36;
                border: 1px solid #3b4148;
                border-radius: 4px;
                padding: 4px 8px;
                color: #fff;
                min-width: 120px;
            }
            QComboBox:hover {
                border: 1px solid #2f82e6;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        controls_layout.addWidget(self.type_combo)
        
        # Select button
        self.select_button = QPushButton("Select Chord")
        self.select_button.setStyleSheet("""
            QPushButton {
                background-color: #2f82e6;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                color: white;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2a6fc2;
            }
            QPushButton:pressed {
                background-color: #1e5aa8;
            }
        """)
        self.select_button.clicked.connect(self._on_select_chord)
        controls_layout.addWidget(self.select_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Velocity controls
        velocity_layout = QHBoxLayout()
        velocity_layout.setSpacing(10)
        
        vel_label = QLabel("Velocity:")
        vel_label.setStyleSheet("color: #aaa;")
        velocity_layout.addWidget(vel_label)
        
        # Single velocity slider (when randomization is off)
        self.vel_slider = QSlider(Qt.Orientation.Horizontal)
        self.vel_slider.setMinimum(1)
        self.vel_slider.setMaximum(127)
        self.vel_slider.setValue(100)
        self.vel_slider.setFixedWidth(200)
        self.vel_slider.setFixedHeight(20)
        self.vel_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3b4148;
                height: 6px;
                background: #2b2f36;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2f82e6;
                border: 1px solid #2a6fc2;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #4a9fff;
            }
        """)
        velocity_layout.addWidget(self.vel_slider)
        
        # Range slider (when randomization is on)
        self.vel_range = self._RangeSlider(1, 127, low=80, high=110, parent=self)
        self.vel_range.setFixedWidth(200)
        self.vel_range.setMinimumHeight(22)
        self.vel_range.setFixedHeight(22)
        self.vel_range.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        velocity_layout.addWidget(self.vel_range)
        
        # Randomize checkbox
        self.vel_random_chk = QCheckBox("Randomize")
        self.vel_random_chk.setChecked(True)
        self.vel_random_chk.setStyleSheet("""
            QCheckBox {
                color: #aaa;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #3b4148;
                border-radius: 3px;
                background: #2b2f36;
            }
            QCheckBox::indicator:checked {
                background: #2f82e6;
                border: 2px solid #2a6fc2;
            }
        """)
        self.vel_random_chk.toggled.connect(self._toggle_vel_random)
        velocity_layout.addWidget(self.vel_random_chk)
        
        # Initialize visibility - make sure widgets are visible
        self.vel_slider.setVisible(False)  # Hide single slider initially (random is on)
        self.vel_range.setVisible(True)    # Show range slider
        # Make sure range slider has a minimum size and is properly displayed
        self.vel_range.show()
        self.vel_range.update()
        
        velocity_layout.addStretch()
        layout.addLayout(velocity_layout)
        
        # Debug: Ensure layout spacing is reasonable
        velocity_layout.setContentsMargins(0, 5, 0, 5)
        
        # Current chord display area
        current_label = QLabel("Current Chord:")
        current_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(current_label)
        
        self.current_area = QFrame()
        self.current_area.setFixedHeight(100)
        self.current_area.setStyleSheet("""
            QFrame {
                background-color: #1e2127;
                border: 2px solid #3b4148;
                border-radius: 8px;
            }
        """)
        current_layout = QVBoxLayout(self.current_area)
        current_layout.setContentsMargins(10, 10, 10, 10)
        current_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.current_placeholder = QLabel("No chord selected")
        self.current_placeholder.setStyleSheet("color: #666; font-style: italic;")
        self.current_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        current_layout.addWidget(self.current_placeholder)
        
        layout.addWidget(self.current_area)
        
        # Replay area
        replay_label = QLabel("Replay Area (drag chords here, click to replay):")
        replay_label.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(replay_label)
        
        self.replay_area = ReplayArea(midi_out, midi_channel, self)
        # Store reference to parent widget in replay area for velocity access
        self.replay_area._parent_widget = self
        layout.addWidget(self.replay_area)

    def _on_select_chord(self) -> None:
        """Handle chord selection."""
        root_index = self.root_combo.currentIndex()
        root_note = root_index % 12
        chord_type = self.type_combo.currentText()
        
        # Remove old current card
        if self.current_card is not None:
            self.current_card.deleteLater()
            self.current_card = None
        
        # Hide placeholder
        if self.current_placeholder.isVisible():
            self.current_placeholder.hide()
        
        # Create new current card
        current_layout = self.current_area.layout()
        self.current_card = ChordCard(root_note, chord_type, self.current_area)
        if current_layout and isinstance(current_layout, QVBoxLayout):
            current_layout.addWidget(self.current_card, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Play the chord
        self._play_chord(root_note, chord_type)

    def _play_chord(self, root_note: int, chord_type: str) -> None:
        """Play a chord using MIDI."""
        if chord_type not in CHORD_DEFINITIONS:
            return
        
        _, intervals = CHORD_DEFINITIONS[chord_type]
        base_note = 60 + root_note  # C4 + root offset
        
        # Get velocity from widget
        velocity = self._get_velocity()
        
        # Play all notes of the chord
        for interval in intervals:
            note = base_note + interval
            self.midi.note_on(note, velocity, self.midi_channel)
        
        # Schedule note offs after a short duration (500ms)
        def release_notes() -> None:
            for interval in intervals:
                note = base_note + interval
                self.midi.note_off(note, self.midi_channel)
        
        QTimer.singleShot(500, release_notes)

    def set_channel(self, channel: int) -> None:
        """Update MIDI channel."""
        self.midi_channel = channel
        self.replay_area.set_channel(channel)
    
    def _toggle_vel_random(self, checked: bool) -> None:
        """Switch between fixed velocity slider and range slider."""
        random_mode = bool(checked)
        try:
            self.vel_slider.setVisible(not random_mode)
            self.vel_range.setVisible(random_mode)
        except Exception:
            pass
    
    def _get_velocity(self) -> int:
        """Get velocity based on current settings (randomized or fixed)."""
        if self.vel_random_chk.isChecked():
            low, high = self.vel_range.values()
            return random.randint(min(low, high), max(low, high))
        else:
            return self.vel_slider.value()

