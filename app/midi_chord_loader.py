"""
MIDI Chord Loader Module for Octavium.

Parses MIDI files from the bundled chord libraries to extract real chord voicings.
Supports the free-midi-chords and free-midi-progressions libraries.

Provides:
- MidiChord: Dataclass representing a chord extracted from a MIDI file
- parse_midi_chord: Extract notes from a single-chord MIDI file
- load_chords_for_key: Load all single chords for a given key/category
- get_available_keys: List available keys in the library
- find_key_folder: Locate the folder for a given key
"""

import mido
import re
import logging
from pathlib import Path
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Base path to MIDI chord library relative to project root
_PROJECT_ROOT = Path(__file__).parent.parent
_RESOURCES_DIR = _PROJECT_ROOT / "resources"


def _find_library_dir(prefix: str) -> Path:
    """Find the latest version of a MIDI library directory by prefix.

    Checks in order:
    1. resources/free-midi-chords-<date>/  (versioned wrapper from ZIP)
    2. resources/                          (flat extraction — keys like "01 - C Major - A minor")
    """
    if _RESOURCES_DIR.exists():
        candidates = sorted(
            (d for d in _RESOURCES_DIR.iterdir()
             if d.is_dir() and d.name.startswith(prefix)),
            reverse=True,
        )
        if candidates:
            return candidates[0]
        # Fallback: chord keys may have been extracted flat into resources/
        # Detect by looking for any "NN - * Major - * minor" folder directly
        if prefix.startswith("free-midi-chords"):
            import re as _re
            flat_keys = [
                d for d in _RESOURCES_DIR.iterdir()
                if d.is_dir() and _re.match(r'^\d+\s*-\s*\S+\s+Major', d.name)
            ]
            if flat_keys:
                return _RESOURCES_DIR
    return _RESOURCES_DIR / prefix


CHORDS_LIB = _find_library_dir("free-midi-chords-")
PROGRESSIONS_LIB = _find_library_dir("free-midi-progressions-")

# Note name mappings
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
NOTE_TO_MIDI = {note: i for i, note in enumerate(NOTES)}

# Flat-to-sharp equivalents for filename parsing
FLAT_TO_SHARP = {
    "Db": "C#", "Eb": "D#", "Fb": "E", "Gb": "F#",
    "Ab": "G#", "Bb": "A#", "Cb": "B",
}

# Chord quality abbreviation mapping (filename suffix -> display name)
QUALITY_MAP = {
    # Major types
    "": "Major", "M7": "Major 7th", "M9": "Major 9th",
    "maj7": "Major 7th", "maj9": "Major 9th",
    "6": "6th", "69": "6/9",
    "add9": "Add9", "add11": "Add11", "add4": "Add4",
    "sus2": "Sus2", "sus4": "Sus4", "sus4add9": "Sus4 Add9",
    "7": "Dominant 7th", "9": "9th",
    "7sus4": "7sus4", "9sus4": "9sus4",
    "7+5": "7#5", "7-5": "7b5", "7-9": "7b9", "7+11": "7#11",
    "M7+5": "Maj7#5", "2": "Add2",
    # Minor types
    "m": "Minor", "m7": "Minor 7th", "m9": "Minor 9th",
    "m6": "Minor 6th", "m69": "Minor 6/9",
    "m7+5": "Min7#5", "m7-5": "Half Diminished",
    "m7add11": "Min7 Add11", "m7b9b5": "Min7b9b5",
    "mM7": "Minor Major 7th", "mM7add11": "MinMaj7 Add11",
    "madd4": "Minor Add4", "madd9": "Minor Add9",
    # Diminished types
    "dim": "Diminished", "dim6": "Dim6", "dim7": "Diminished 7th",
}

# Chord categories available in the library
CHORD_CATEGORIES = {
    "Triads": "1 Triad",
    "7ths & 9ths": "2 7th and 9th",
    "All Chords": "3 All chords",
}


@dataclass
class MidiChord:
    """Chord extracted from a MIDI file."""
    root: str           # "C", "D#", etc. (sharp notation)
    quality: str        # "Major", "Minor 7th", etc.
    notes: List[int]    # MIDI note numbers as found in the file
    degree: str         # "I", "ii", "V", etc.
    source_file: Path = field(repr=False)
    root_midi: int = 0  # MIDI note number of the root (mod 12)

    @property
    def display_name(self) -> str:
        """Human-readable chord name, e.g. 'C Major 7th'."""
        return f"{self.root} {self.quality}"

    def as_autofill_tuple(self) -> Tuple[int, str, List[int]]:
        """Return (root_note, chord_type, midi_notes) for chord monitor grid."""
        return (self.root_midi, self.quality, list(self.notes))


def _normalize_note_name(name: str) -> str:
    """Convert a note name to sharp notation. 'Db' -> 'C#', 'C' -> 'C'."""
    return FLAT_TO_SHARP.get(name, name)


def _note_name_to_midi(name: str) -> int:
    """Convert note name to MIDI pitch class (0-11). Handles sharps and flats."""
    normalized = _normalize_note_name(name)
    return NOTE_TO_MIDI.get(normalized, 0)


def _parse_chord_filename(filename: str) -> Tuple[str, str, str]:
    """
    Parse a chord MIDI filename into (degree, root, quality_abbrev).

    Examples:
        "I - C.mid"         -> ("I", "C", "")
        "ii - Dm.mid"       -> ("ii", "D", "m")
        "I - CM7.mid"       -> ("I", "C", "M7")
        "I-III - Cmaj7.mid" -> ("I-III", "C", "maj7")
        "vi-i - Am7.mid"    -> ("vi-i", "A", "m7")
    """
    stem = Path(filename).stem  # Remove .mid
    # Split on " - " to get degree and chord parts
    parts = stem.split(" - ", 1)
    if len(parts) != 2:
        return ("", "", "")

    degree = parts[0].strip()
    chord_str = parts[1].strip()

    # Parse root note and quality from chord string
    # Root is 1-2 chars: letter + optional # or b
    match = re.match(r'^([A-G][#b]?)(.*)', chord_str)
    if not match:
        return (degree, "", "")

    root = match.group(1)
    quality_abbrev = match.group(2)

    return (degree, root, quality_abbrev)


def _parse_quality(abbrev: str) -> str:
    """Convert a quality abbreviation to a display name."""
    return QUALITY_MAP.get(abbrev, abbrev if abbrev else "Major")


def parse_midi_chord(filepath: Path) -> Optional[MidiChord]:
    """
    Extract chord data from a single-chord MIDI file.

    Returns None if the file cannot be parsed or contains no notes.
    """
    try:
        mid = mido.MidiFile(str(filepath))
    except Exception as e:
        logger.warning("Failed to read MIDI file %s: %s", filepath, e)
        return None

    # Collect all note_on events with velocity > 0
    notes = []
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                if msg.note not in notes:
                    notes.append(msg.note)

    if not notes:
        return None

    notes.sort()

    # Parse metadata from filename
    degree, root_name, quality_abbrev = _parse_chord_filename(filepath.name)
    if not root_name:
        # Fallback: derive root from lowest note
        root_name = NOTES[notes[0] % 12]

    root_normalized = _normalize_note_name(root_name)
    root_midi = _note_name_to_midi(root_name)
    quality = _parse_quality(quality_abbrev)

    return MidiChord(
        root=root_normalized,
        quality=quality,
        notes=notes,
        degree=degree,
        source_file=filepath,
        root_midi=root_midi,
    )


def get_available_keys() -> List[Dict[str, str]]:
    """
    List all available keys in the chord library.

    Returns list of dicts: [{"folder": "01 - C Major - A minor", "major": "C", "minor": "A"}, ...]
    """
    if not CHORDS_LIB.exists():
        logger.warning("Chord library not found at %s", CHORDS_LIB)
        return []

    keys = []
    for folder in sorted(CHORDS_LIB.iterdir()):
        if not folder.is_dir():
            continue
        # Parse folder name: "01 - C Major - A minor"
        match = re.match(r'^\d+\s*-\s*(\S+)\s+Major\s*-\s*(\S+)\s+minor$', folder.name)
        if match:
            major_key = match.group(1)
            minor_key = match.group(2)
            keys.append({
                "folder": folder.name,
                "major": major_key,
                "minor": minor_key,
                "path": str(folder),
            })
    return keys


def find_key_folder(key: str, mode: str = "Major") -> Optional[Path]:
    """
    Find the library folder for a given key and mode.

    Args:
        key: Root note name, e.g. "C", "F#", "Bb"
        mode: "Major" or "Minor"

    Returns:
        Path to the key folder, or None if not found.
    """
    if not CHORDS_LIB.exists():
        return None

    key_normalized = _normalize_note_name(key)

    for folder in CHORDS_LIB.iterdir():
        if not folder.is_dir():
            continue
        match = re.match(r'^\d+\s*-\s*(\S+)\s+Major\s*-\s*(\S+)\s+minor$', folder.name)
        if not match:
            continue

        folder_major = _normalize_note_name(match.group(1))
        folder_minor = _normalize_note_name(match.group(2))

        if mode == "Major" and folder_major == key_normalized:
            return folder
        elif mode == "Minor" and folder_minor == key_normalized:
            return folder

    return None


def load_chords_for_key(
    key: str,
    mode: str = "Major",
    category: str = "Triads",
) -> List[MidiChord]:
    """
    Load all single chords for a given key, mode, and category.

    Args:
        key: Root note, e.g. "C", "F#"
        mode: "Major" or "Minor"
        category: One of "Triads", "7ths & 9ths", "All Chords"

    Returns:
        List of MidiChord objects sorted by scale degree.
    """
    key_folder = find_key_folder(key, mode)
    if key_folder is None:
        logger.info("No folder found for key=%s mode=%s", key, mode)
        return []

    # Determine subfolder for category
    category_subfolder = CHORD_CATEGORIES.get(category, "1 Triad")
    category_path = key_folder / category_subfolder

    if not category_path.exists():
        logger.info("Category path does not exist: %s", category_path)
        return []

    # For Triads and 7ths, there are Major/Minor subfolders
    chords: List[MidiChord] = []

    if category in ("Triads", "7ths & 9ths"):
        # Use the mode-matching subfolder
        mode_subfolder = category_path / mode
        if mode_subfolder.exists():
            for midi_file in sorted(mode_subfolder.glob("*.mid")):
                chord = parse_midi_chord(midi_file)
                if chord is not None:
                    chords.append(chord)
        else:
            # Fallback: try Major subfolder
            fallback = category_path / "Major"
            if fallback.exists():
                for midi_file in sorted(fallback.glob("*.mid")):
                    chord = parse_midi_chord(midi_file)
                    if chord is not None:
                        chords.append(chord)
    else:
        # "All Chords" — flat directory of .mid files
        for midi_file in sorted(category_path.glob("*.mid")):
            chord = parse_midi_chord(midi_file)
            if chord is not None:
                chords.append(chord)

    return chords


def load_diatonic_triads(key: str, mode: str = "Major") -> List[MidiChord]:
    """
    Load just the 7 diatonic triads for a key/mode from the MIDI library.
    This is the most direct replacement for algorithmic autofill.
    """
    return load_chords_for_key(key, mode, category="Triads")


def load_seventh_chords(key: str, mode: str = "Major") -> List[MidiChord]:
    """Load 7th and 9th chord voicings for a key/mode."""
    return load_chords_for_key(key, mode, category="7ths & 9ths")


def load_all_chords(key: str, mode: str = "Major") -> List[MidiChord]:
    """Load all available chord voicings for a key/mode (136 per key)."""
    return load_chords_for_key(key, mode, category="All Chords")


def midi_library_available() -> bool:
    """Check if the MIDI chord library is present on disk."""
    return CHORDS_LIB.exists() and any(CHORDS_LIB.iterdir())
