"""
Chord Autofill Module for Octavium Chord Pad.

Provides:
- AutofillDialog: Select key, mode/emotion, and preview chords before filling the grid
- ChordEditDialog: Interactive mini-keyboard to edit individual chord cards
- Diatonic chord generation based on key and mode selection
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QFrame, QGridLayout, QWidget, QSizePolicy, QButtonGroup, QRadioButton,
    QGroupBox, QScrollArea, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QFont
from typing import List, Optional, Dict, Tuple, TYPE_CHECKING
from dataclasses import dataclass
import random

if TYPE_CHECKING:
    from .midi_io import MidiOut

from .midi_chord_loader import (
    load_chords_for_key, midi_library_available, MidiChord, CHORD_CATEGORIES,
)

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


# Extended interval lookup for varied chord generation
CHORD_INTERVALS: Dict[str, List[int]] = {
    # Triads (3 notes)
    "Major": [0, 4, 7],
    "Minor": [0, 3, 7],
    "Diminished": [0, 3, 6],
    "Augmented": [0, 4, 8],
    "Dim": [0, 3, 6],
    "Aug": [0, 4, 8],
    "Sus2": [0, 2, 7],
    "Sus4": [0, 5, 7],
    # 4-note chords
    "Major 7th": [0, 4, 7, 11],
    "Minor 7th": [0, 3, 7, 10],
    "Dominant 7th": [0, 4, 7, 10],
    "Diminished 7th": [0, 3, 6, 9],
    "Half Diminished": [0, 3, 6, 10],
    "Minor Major 7th": [0, 3, 7, 11],
    "Major 6th": [0, 4, 7, 9],
    "Minor 6th": [0, 3, 7, 9],
    "Add9": [0, 4, 7, 14],
    "Minor Add9": [0, 3, 7, 14],
    # 5-note chords
    "Major 9th": [0, 4, 7, 11, 14],
    "Minor 9th": [0, 3, 7, 10, 14],
    "Dominant 9th": [0, 4, 7, 10, 14],
    "6/9": [0, 4, 7, 9, 14],
}

# Which extended chord types are appropriate for each base quality
_EXTENDED_TYPES: Dict[str, List[str]] = {
    "Major": [
        "Major", "Major 7th", "Major 9th", "Add9", "Sus2", "Sus4",
        "Major 6th", "6/9", "Dominant 7th", "Dominant 9th",
    ],
    "Minor": [
        "Minor", "Minor 7th", "Minor 9th", "Minor Add9", "Minor 6th",
        "Minor Major 7th", "Sus2", "Sus4",
    ],
    "Diminished": [
        "Diminished", "Diminished 7th", "Half Diminished",
    ],
    "Augmented": [
        "Augmented", "Major 7th", "Dominant 7th",
    ],
}


def get_chord_notes(root: int, chord_type: str, octave: int = 4) -> List[int]:
    """Generate MIDI notes for a chord given root and type."""
    base = (octave * 12) + (root % 12)
    chord_intervals = CHORD_INTERVALS.get(chord_type, [0, 4, 7])
    return [base + i for i in chord_intervals]


def apply_inversion(notes: List[int], inversion: int) -> List[int]:
    """
    Apply an inversion to a list of MIDI notes.

    inversion 0 = root position (no change)
    inversion 1 = move lowest note up an octave
    inversion 2 = move two lowest notes up an octave
    inversion 3 = move three lowest notes up an octave (for 7th+ chords)
    """
    if inversion <= 0 or not notes:
        return list(notes)
    result = sorted(notes)
    inv = min(inversion, len(result) - 1)
    for i in range(inv):
        result[i] += 12
    result.sort()
    return result


def _pick_inversion(note_count: int, allowed_inversions: Optional[List[int]] = None) -> int:
    """Pick a random inversion from the allowed list, clamped to note_count - 1."""
    if allowed_inversions is None or len(allowed_inversions) == 0:
        return 0  # root position only
    valid = [inv for inv in allowed_inversions if inv < note_count]
    if not valid:
        return 0
    return random.choice(valid)


def _note_count_ok(chord_type: str, allowed_counts: Optional[List[int]]) -> bool:
    """Check if a chord type's note count is in the allowed set."""
    if allowed_counts is None:
        return True
    n = len(CHORD_INTERVALS.get(chord_type, [0, 4, 7]))
    return n in allowed_counts


# ---------------------------------------------------------------------------
# Chord family classification (for lock-influence weighting)
# ---------------------------------------------------------------------------
_CHORD_FAMILY: Dict[str, str] = {}
for _ct in ("Major", "Minor", "Diminished", "Augmented", "Dim", "Aug", "Sus2", "Sus4"):
    _CHORD_FAMILY[_ct] = "triad"
for _ct in ("Major 7th", "Minor 7th", "Dominant 7th", "Diminished 7th",
            "Half Diminished", "Minor Major 7th"):
    _CHORD_FAMILY[_ct] = "seventh"
for _ct in ("Major 6th", "Minor 6th"):
    _CHORD_FAMILY[_ct] = "sixth"
for _ct in ("Add9", "Minor Add9"):
    _CHORD_FAMILY[_ct] = "add"
for _ct in ("Major 9th", "Minor 9th", "Dominant 9th", "6/9"):
    _CHORD_FAMILY[_ct] = "extended"

# Related modes for modal interchange (parallel borrowing)
_PARALLEL_MODES: Dict[str, List[str]] = {
    "Major (Ionian)": ["Natural Minor (Aeolian)", "Dorian", "Mixolydian", "Lydian"],
    "Lydian": ["Major (Ionian)", "Mixolydian"],
    "Mixolydian": ["Major (Ionian)", "Dorian"],
    "Natural Minor (Aeolian)": ["Major (Ionian)", "Dorian", "Harmonic Minor"],
    "Dorian": ["Natural Minor (Aeolian)", "Mixolydian", "Major (Ionian)"],
    "Phrygian": ["Natural Minor (Aeolian)", "Harmonic Minor"],
    "Locrian": ["Phrygian", "Natural Minor (Aeolian)"],
    "Harmonic Minor": ["Natural Minor (Aeolian)", "Phrygian"],
    "Melodic Minor": ["Dorian", "Mixolydian", "Harmonic Minor"],
    "Blues": ["Mixolydian", "Dorian", "Pentatonic Minor"],
    "Pentatonic Major": ["Major (Ionian)", "Mixolydian"],
    "Pentatonic Minor": ["Natural Minor (Aeolian)", "Blues"],
}


# ---------------------------------------------------------------------------
# Weighted pool builder
# ---------------------------------------------------------------------------
def _build_weighted_pool(
    root_note: int,
    mode: ScaleMode,
    mode_name: str,
    octave: int,
    allowed_note_counts: Optional[List[int]],
    allowed_inversions: Optional[List[int]],
    scale_compliance: float,
) -> List[Tuple[int, str, List[int], float]]:
    """
    Build a weighted pool of candidate chords.

    Returns list of (chord_root, chord_type, midi_notes, weight).
    Higher weight = more likely to be picked.

    scale_compliance 0.0-1.0:
      1.0 = strictly diatonic extended types only
      0.7 = also borrow from parallel modes
      0.4 = also allow secondary dominants
      0.0 = allow any chromatic root / quality
    """
    pool: List[Tuple[int, str, List[int], float]] = []
    seen: set = set()

    def _add(cr: int, ct: str, w: float) -> None:
        cr12 = cr % 12
        if (cr12, ct) in seen:
            return
        if not _note_count_ok(ct, allowed_note_counts):
            return
        notes = get_chord_notes(cr12, ct, octave)
        inv = _pick_inversion(len(notes), allowed_inversions)
        notes = apply_inversion(notes, inv)
        pool.append((cr12, ct, notes, w))
        seen.add((cr12, ct))

    # --- 1. Diatonic: weight 1.0 ---
    for i, interval in enumerate(mode.intervals):
        cr = (root_note + interval) % 12
        bq = mode.chord_qualities[i] if i < len(mode.chord_qualities) else "Major"
        for ct in _EXTENDED_TYPES.get(bq, [bq]):
            _add(cr, ct, 1.0)

    # --- 2. Borrowed from parallel modes ---
    if scale_compliance < 0.95:
        borrow_w = (1.0 - scale_compliance) * 0.8
        for par_name in _PARALLEL_MODES.get(mode_name, []):
            par = SCALE_MODES.get(par_name)
            if not par:
                continue
            for i, interval in enumerate(par.intervals):
                cr = (root_note + interval) % 12
                bq = par.chord_qualities[i] if i < len(par.chord_qualities) else "Major"
                for ct in _EXTENDED_TYPES.get(bq, [bq]):
                    _add(cr, ct, borrow_w)

    # --- 3. Secondary dominants ---
    if scale_compliance < 0.70:
        sd_w = (0.70 - scale_compliance) * 0.9
        for i, interval in enumerate(mode.intervals):
            target = (root_note + interval) % 12
            dom_root = (target + 7) % 12  # V of target
            for ct in ("Dominant 7th", "Dominant 9th", "Major"):
                _add(dom_root, ct, sd_w)

    # --- 4. Chromatic chords (any root) ---
    if scale_compliance < 0.40:
        ch_w = (0.40 - scale_compliance) * 0.6
        scale_roots = {(root_note + iv) % 12 for iv in mode.intervals}
        for semi in range(12):
            if semi not in scale_roots:
                for ct in ("Major", "Minor", "Dominant 7th", "Major 7th", "Minor 7th"):
                    _add(semi, ct, ch_w)

    return pool


# ---------------------------------------------------------------------------
# Lock-aware analysis
# ---------------------------------------------------------------------------
def _analyze_locked_chords(
    locked_chords: List[Tuple[int, str]],
) -> Dict[str, float]:
    """
    Analyze locked chords and return a family-preference dict.

    Returns {family_name: weight_boost} based on what's in the locked set.
    """
    if not locked_chords:
        return {}
    family_counts: Dict[str, int] = {}
    for _, ct in locked_chords:
        fam = _CHORD_FAMILY.get(ct, "triad")
        family_counts[fam] = family_counts.get(fam, 0) + 1
    total = sum(family_counts.values())
    if total == 0:
        return {}
    return {fam: count / total for fam, count in family_counts.items()}


def _apply_lock_influence(
    pool: List[Tuple[int, str, List[int], float]],
    locked_prefs: Dict[str, float],
    lock_influence: float,
) -> List[Tuple[int, str, List[int], float]]:
    """
    Re-weight pool entries based on lock influence and locked chord preferences.

    lock_influence 0.0-1.0:
      1.0 = heavily favour families that match locked chords
      0.0 = ignore locked chords entirely
    """
    if not locked_prefs or lock_influence <= 0.0:
        return pool
    result = []
    for cr, ct, notes, w in pool:
        fam = _CHORD_FAMILY.get(ct, "triad")
        pref = locked_prefs.get(fam, 0.0)
        # Boost weight: at full influence a chord in the dominant family
        # gets up to 2x weight; unrepresented families get slight penalty
        boost = 1.0 + (pref * 2.0 - 0.3) * lock_influence
        boost = max(boost, 0.15)  # never fully suppress
        result.append((cr, ct, notes, w * boost))
    return result


# ---------------------------------------------------------------------------
# Weighted sampling helper
# ---------------------------------------------------------------------------
def _weighted_sample_unique(
    pool: List[Tuple[int, str, List[int], float]],
    count: int,
    existing: set,
) -> List[Tuple[int, str, List[int]]]:
    """Sample up to *count* unique (root, type) combos from weighted pool."""
    available = [(cr, ct, n, w) for cr, ct, n, w in pool if (cr, ct) not in existing]
    results: List[Tuple[int, str, List[int]]] = []
    for _ in range(count):
        if not available:
            break
        weights = [max(w, 0.01) for _, _, _, w in available]
        total = sum(weights)
        r = random.random() * total
        cumulative = 0.0
        idx = 0
        for i, wt in enumerate(weights):
            cumulative += wt
            if cumulative >= r:
                idx = i
                break
        cr, ct, n, _ = available.pop(idx)
        results.append((cr, ct, n))
        existing.add((cr, ct))
        # Remove other entries with same (root, type) from available
        available = [(c, t, ns, w) for c, t, ns, w in available if (c, t) not in existing]
    return results


# ---------------------------------------------------------------------------
# Public generation functions
# ---------------------------------------------------------------------------
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


def generate_varied_diatonic_chords(
    root_note: int,
    mode: ScaleMode,
    octave: int = 4,
    count: int = 16,
    allowed_note_counts: Optional[List[int]] = None,
    allowed_inversions: Optional[List[int]] = None,
    scale_compliance: float = 1.0,
    lock_influence: float = 0.0,
    locked_chords: Optional[List[Tuple[int, str]]] = None,
    mode_name: Optional[str] = None,
) -> List[Tuple[int, str, List[int]]]:
    """
    Generate *count* varied chords for a key and mode.

    scale_compliance: 0.0-1.0, how strictly to stick to the scale.
    lock_influence: 0.0-1.0, how much to learn from locked chords.
    locked_chords: list of (root, chord_type) from locked cards.
    """
    if mode_name is None:
        mode_name = mode.name

    # Build weighted candidate pool
    pool = _build_weighted_pool(
        root_note, mode, mode_name, octave,
        allowed_note_counts, allowed_inversions, scale_compliance,
    )

    # Apply lock influence
    if locked_chords and lock_influence > 0:
        prefs = _analyze_locked_chords(locked_chords)
        pool = _apply_lock_influence(pool, prefs, lock_influence)

    # Start with basic diatonic triads (filtered)
    base_chords = generate_diatonic_chords(root_note, mode, octave)
    chords: List[Tuple[int, str, List[int]]] = []
    for chord_root, ct, notes in base_chords:
        if not _note_count_ok(ct, allowed_note_counts):
            continue
        inv = _pick_inversion(len(notes), allowed_inversions)
        notes = apply_inversion(notes, inv)
        chords.append((chord_root, ct, notes))

    # Fill remaining slots via weighted sampling
    existing = {(c[0], c[1]) for c in chords}
    needed = count - len(chords)
    if needed > 0:
        extras = _weighted_sample_unique(pool, needed, existing)
        chords.extend(extras)

    # Shuffle the non-base portion so it isn't always diatonic-first
    if len(chords) > len(base_chords):
        tail = chords[len(base_chords):]
        random.shuffle(tail)
        chords = chords[:len(base_chords)] + tail

    return chords[:count]


def generate_single_alternative(
    root_note: int,
    mode: ScaleMode,
    degree_index: int,
    current_type: str,
    octave: int = 4,
    allowed_note_counts: Optional[List[int]] = None,
    allowed_inversions: Optional[List[int]] = None,
    scale_compliance: float = 1.0,
    lock_influence: float = 0.0,
    locked_chords: Optional[List[Tuple[int, str]]] = None,
    mode_name: Optional[str] = None,
) -> Tuple[int, str, List[int]]:
    """
    Generate a random alternative chord for a given scale degree.

    Respects scale_compliance and lock_influence settings.
    """
    if mode_name is None:
        mode_name = mode.name

    interval = mode.intervals[degree_index % len(mode.intervals)]
    chord_root = (root_note + interval) % 12

    # Build weighted pool for this specific root
    full_pool = _build_weighted_pool(
        root_note, mode, mode_name, octave,
        allowed_note_counts, allowed_inversions, scale_compliance,
    )
    # Filter to candidates on this chord root
    candidates = [(cr, ct, n, w) for cr, ct, n, w in full_pool if cr == chord_root and ct != current_type]

    # If compliance is low enough, also allow candidates on nearby roots
    if scale_compliance < 0.70 and not candidates:
        candidates = [(cr, ct, n, w) for cr, ct, n, w in full_pool if ct != current_type]

    # Apply lock influence
    if locked_chords and lock_influence > 0 and candidates:
        prefs = _analyze_locked_chords(locked_chords)
        candidates = _apply_lock_influence(candidates, prefs, lock_influence)

    if candidates:
        # Weighted random pick
        weights = [max(w, 0.01) for _, _, _, w in candidates]
        total = sum(weights)
        r = random.random() * total
        cumulative = 0.0
        pick = candidates[0]
        for item in candidates:
            cumulative += max(item[3], 0.01)
            if cumulative >= r:
                pick = item
                break
        return (pick[0], pick[1], pick[2])

    # Fallback: original diatonic logic
    base_quality = (
        mode.chord_qualities[degree_index]
        if degree_index < len(mode.chord_qualities)
        else "Major"
    )
    options = _EXTENDED_TYPES.get(base_quality, [base_quality])
    if allowed_note_counts:
        options = [ct for ct in options if _note_count_ok(ct, allowed_note_counts)]
        if not options:
            options = _EXTENDED_TYPES.get(base_quality, [base_quality])
    alternatives = [ct for ct in options if ct != current_type]
    if not alternatives:
        alternatives = options
    ct = random.choice(alternatives)
    notes = get_chord_notes(chord_root, ct, octave)
    inv = _pick_inversion(len(notes), allowed_inversions)
    notes = apply_inversion(notes, inv)
    return (chord_root, ct, notes)


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
    """Dialog for autofilling the chord pad with diatonic chords."""
    
    def __init__(self, midi_out: 'MidiOut', midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.midi = midi_out
        self.midi_channel = midi_channel
        self._preview_notes: List[int] = []
        
        self.setWindowTitle("Autofill Chord Pad")
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
        title = QLabel("Autofill Chord Pad")
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
        
        # Source selection: Algorithmic vs MIDI Library
        source_group = QGroupBox("Chord Source")
        source_layout = QHBoxLayout(source_group)
        self._source_btn_group = QButtonGroup(self)
        
        self._algo_radio = QRadioButton("Algorithmic")
        self._algo_radio.setStyleSheet("color: #fff;")
        self._algo_radio.setChecked(True)
        self._source_btn_group.addButton(self._algo_radio, 0)
        source_layout.addWidget(self._algo_radio)
        
        self._midi_radio = QRadioButton("MIDI Library")
        self._midi_radio.setStyleSheet("color: #fff;")
        self._midi_radio.setEnabled(midi_library_available())
        self._source_btn_group.addButton(self._midi_radio, 1)
        source_layout.addWidget(self._midi_radio)
        
        if not midi_library_available():
            no_lib_label = QLabel("(library not found)")
            no_lib_label.setStyleSheet("color: #888; font-size: 10px;")
            source_layout.addWidget(no_lib_label)
        
        source_layout.addStretch()
        self._source_btn_group.idToggled.connect(self._on_source_changed)
        layout.addWidget(source_group)
        
        # MIDI Library options (hidden when Algorithmic is selected)
        self._midi_options_group = QGroupBox("MIDI Library Options")
        midi_opts_layout = QHBoxLayout(self._midi_options_group)
        
        midi_mode_label = QLabel("Mode:")
        midi_opts_layout.addWidget(midi_mode_label)
        
        self._midi_mode_combo = QComboBox()
        self._midi_mode_combo.addItems(["Major", "Minor"])
        self._midi_mode_combo.setStyleSheet(self._combo_style())
        self._midi_mode_combo.currentTextChanged.connect(self._update_preview)
        midi_opts_layout.addWidget(self._midi_mode_combo)
        
        cat_label = QLabel("Category:")
        midi_opts_layout.addWidget(cat_label)
        
        self._midi_category_combo = QComboBox()
        for cat_name in CHORD_CATEGORIES:
            self._midi_category_combo.addItem(cat_name)
        self._midi_category_combo.setStyleSheet(self._combo_style())
        self._midi_category_combo.currentTextChanged.connect(self._update_preview)
        midi_opts_layout.addWidget(self._midi_category_combo)
        
        midi_opts_layout.addStretch()
        self._midi_options_group.setVisible(False)
        layout.addWidget(self._midi_options_group)
        
        # Mode/Scale selection with emotion hints
        self._algo_mode_group = QGroupBox("Select Mode / Scale")
        mode_layout = QVBoxLayout(self._algo_mode_group)
        
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
        
        layout.addWidget(self._algo_mode_group)
        
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
        
        # Generation options: note counts and inversions
        gen_opts_group = QGroupBox("Generation Options")
        gen_opts_layout = QVBoxLayout(gen_opts_group)
        
        # Note count row
        nc_row = QHBoxLayout()
        nc_label = QLabel("Note counts:")
        nc_label.setStyleSheet("color: #aaa; font-size: 11px;")
        nc_row.addWidget(nc_label)
        
        self._nc_3 = QCheckBox("Triads (3)")
        self._nc_3.setChecked(True)
        self._nc_3.setStyleSheet("color: #fff;")
        nc_row.addWidget(self._nc_3)
        
        self._nc_4 = QCheckBox("7ths / 6ths (4)")
        self._nc_4.setChecked(True)
        self._nc_4.setStyleSheet("color: #fff;")
        nc_row.addWidget(self._nc_4)
        
        self._nc_5 = QCheckBox("9ths / Ext (5)")
        self._nc_5.setChecked(True)
        self._nc_5.setStyleSheet("color: #fff;")
        nc_row.addWidget(self._nc_5)
        
        nc_row.addStretch()
        gen_opts_layout.addLayout(nc_row)
        
        # Inversions row
        inv_row = QHBoxLayout()
        inv_label = QLabel("Inversions:")
        inv_label.setStyleSheet("color: #aaa; font-size: 11px;")
        inv_row.addWidget(inv_label)
        
        self._inv_0 = QCheckBox("Root")
        self._inv_0.setChecked(True)
        self._inv_0.setStyleSheet("color: #fff;")
        inv_row.addWidget(self._inv_0)
        
        self._inv_1 = QCheckBox("1st")
        self._inv_1.setStyleSheet("color: #fff;")
        inv_row.addWidget(self._inv_1)
        
        self._inv_2 = QCheckBox("2nd")
        self._inv_2.setStyleSheet("color: #fff;")
        inv_row.addWidget(self._inv_2)
        
        self._inv_3 = QCheckBox("3rd")
        self._inv_3.setStyleSheet("color: #fff;")
        inv_row.addWidget(self._inv_3)
        
        inv_row.addStretch()
        gen_opts_layout.addLayout(inv_row)
        
        layout.addWidget(gen_opts_group)
        
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
    
    def _get_allowed_note_counts(self) -> Optional[List[int]]:
        """Read the note-count checkboxes and return allowed counts, or None for all."""
        counts = []
        if self._nc_3.isChecked():
            counts.append(3)
        if self._nc_4.isChecked():
            counts.append(4)
        if self._nc_5.isChecked():
            counts.append(5)
        return counts if counts else None  # None means allow all
    
    def _get_allowed_inversions(self) -> Optional[List[int]]:
        """Read the inversion checkboxes and return allowed inversions, or None for root only."""
        inversions = []
        if self._inv_0.isChecked():
            inversions.append(0)
        if self._inv_1.isChecked():
            inversions.append(1)
        if self._inv_2.isChecked():
            inversions.append(2)
        if self._inv_3.isChecked():
            inversions.append(3)
        return inversions if inversions else None
    
    def _is_midi_source(self) -> bool:
        """Return True if MIDI Library source is selected."""
        return self._source_btn_group.checkedId() == 1
    
    def _on_source_changed(self, btn_id: int, checked: bool) -> None:
        """Handle source radio button toggle."""
        if not checked:
            return
        is_midi = (btn_id == 1)
        self._midi_options_group.setVisible(is_midi)
        self._algo_mode_group.setVisible(not is_midi)
        self._update_preview()
    
    def _get_current_chords(self) -> List[Tuple[int, str, List[int]]]:
        """Get chord tuples for the current source/settings (used by preview and fill)."""
        if self._is_midi_source():
            key = self.key_combo.currentText()
            mode = self._midi_mode_combo.currentText()
            category = self._midi_category_combo.currentText()
            midi_chords = load_chords_for_key(key, mode, category)
            return [mc.as_autofill_tuple() for mc in midi_chords]
        else:
            root_note = NOTE_TO_INDEX.get(self.key_combo.currentText(), 0)
            mode_name = self.mode_combo.currentData()
            if mode_name and mode_name in SCALE_MODES:
                mode = SCALE_MODES[mode_name]
                return generate_varied_diatonic_chords(
                    root_note, mode, octave=4, count=16,
                    allowed_note_counts=self._get_allowed_note_counts(),
                    allowed_inversions=self._get_allowed_inversions(),
                )
        return []
    
    def _update_preview(self) -> None:
        """Update the chord preview based on current selections."""
        # Clear existing previews
        while self.chord_preview_layout.count():
            item = self.chord_preview_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        if self._is_midi_source():
            # MIDI Library source
            key = self.key_combo.currentText()
            mode = self._midi_mode_combo.currentText()
            category = self._midi_category_combo.currentText()
            midi_chords = load_chords_for_key(key, mode, category)
            
            all_notes = []
            for mc in midi_chords:
                preview = ChordPreviewWidget(
                    mc.root_midi, mc.quality, mc.notes, mc.degree, self
                )
                self.chord_preview_layout.addWidget(preview)
                all_notes.extend(mc.notes)
            
            # Update mini keyboard to show loaded chord notes
            self.mini_keyboard.set_selected_notes(all_notes)
        else:
            # Algorithmic source
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
        chords = self._get_current_chords()
        if not chords:
            return
        
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
        return self._get_current_chords()
    
    def get_autofill_context(self) -> Optional[Dict]:
        """Return context needed for per-card regeneration (key, mode name, root note)."""
        if self._is_midi_source():
            return None  # Regeneration only for algorithmic mode
        mode_name = self.mode_combo.currentData()
        if mode_name and mode_name in SCALE_MODES:
            return {
                "root_note": NOTE_TO_INDEX.get(self.key_combo.currentText(), 0),
                "mode_name": mode_name,
                "allowed_note_counts": self._get_allowed_note_counts(),
                "allowed_inversions": self._get_allowed_inversions(),
            }
        return None
    
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
