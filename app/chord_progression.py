"""
Markov Chain Chord Progression Generator for Octavium.

Builds transition probability tables from the bundled MIDI progression library
(~176 unique progressions across Major, Minor, and Modal modes) and generates
novel chord sequences by walking the Markov chain.

Provides:
- ProgressionEntry: Metadata parsed from progression filenames
- TransitionTable: Per-mode chord-to-chord transition counts
- index_progressions: Scan library directories for progression entries
- build_transition_table: Build Markov table from entries
- generate_progression: Walk the chain to produce numeral sequences
- realize_progression: Convert numerals to playable MIDI note tuples
"""

import re
import random
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Base path to MIDI progression library
_PROJECT_ROOT = Path(__file__).parent.parent
_RESOURCES_DIR = _PROJECT_ROOT / "resources"

# Progression directories
_PROGRESSION_DIRS = {
    "Major": _RESOURCES_DIR / "Major",
    "Minor": _RESOURCES_DIR / "Minor",
    "Modal": _RESOURCES_DIR / "Modal",
}

# Cached tables (built lazily)
_CACHED_TABLES: Dict[str, "TransitionTable"] = {}
_CACHED_INDEX: Optional[List["ProgressionEntry"]] = None

# Filename regex: "{Key} - {Numerals} - {Moods}.mid"
_FILENAME_RE = re.compile(r"^([A-G][b#]?) - (.+?) - (.+)\.mid$")

# Roman numeral token parsing
# Matches: optional b/# prefix, roman numeral (upper or lower), optional quality suffix
_NUMERAL_RE = re.compile(
    r"^([b#]?)"           # accidental prefix
    r"(VII|VI|IV|V|III|II|I|vii|vi|iv|v|iii|ii|i)"  # roman numeral (greedy, longest first)
    r"(.*)$"              # quality suffix
)

# Core degree to semitone offset (from tonic)
_DEGREE_SEMITONES = {
    "I": 0, "II": 2, "III": 4, "IV": 5, "V": 7, "VI": 9, "VII": 11,
    "i": 0, "ii": 2, "iii": 4, "iv": 5, "v": 7, "vi": 9, "vii": 11,
}

# Quality suffix to chord type mapping
_SUFFIX_TO_CHORD_TYPE: Dict[str, str] = {
    "": None,  # use default from case (upper=Major, lower=Minor)
    "M7": "Major 7th",
    "m7": "Minor 7th",
    "7": "Dominant 7th",
    "dom7": "Dominant 7th",
    "dim": "Diminished",
    "dim7": "Diminished 7th",
    "aug": "Augmented",
    "sus2": "Sus2",
    "sus4": "Sus4",
    "add9": "Add9",
    "6": "Major 6th",
    "69": "6/9",
    "9": "Dominant 9th",
    "M-5": "Diminished",  # Major flat 5 treated as dim
    "m": "Minor",
    "M": "Major",
}


@dataclass
class ProgressionEntry:
    """Metadata for a single progression parsed from its filename."""
    key: str              # "C", "Bb", "F#"
    mode: str             # "Major", "Minor", "Modal"
    numerals: List[str]   # ["I", "V", "vi", "IV"]
    moods: List[str]      # ["Hopeful", "Romantic"]
    file_path: Path


@dataclass
class TransitionTable:
    """Markov transition counts for a single mode."""
    mode: str
    transitions: Dict[str, Dict[str, int]] = field(default_factory=dict)
    start_counts: Dict[str, int] = field(default_factory=dict)
    end_counts: Dict[str, int] = field(default_factory=dict)
    vocabulary: Set[str] = field(default_factory=set)

    @property
    def total_progressions(self) -> int:
        """Total number of source progressions that contributed to this table."""
        return sum(self.start_counts.values())

    def get_successors(self, token: str) -> Dict[str, int]:
        """Get successor counts for a token, with fallback to core degree."""
        successors = self.transitions.get(token)
        if successors:
            return successors
        # Fallback: strip quality suffix and try core degree
        core = _strip_suffix(token)
        if core != token:
            successors = self.transitions.get(core)
            if successors:
                return successors
        return {}


def _strip_suffix(token: str) -> str:
    """Strip quality suffix from a numeral token, returning core degree."""
    m = _NUMERAL_RE.match(token)
    if m:
        return m.group(1) + m.group(2)
    return token


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------

def index_progressions() -> List[ProgressionEntry]:
    """Scan progression directories and parse filenames into entries."""
    global _CACHED_INDEX
    if _CACHED_INDEX is not None:
        return _CACHED_INDEX

    entries: List[ProgressionEntry] = []

    for mode, dir_path in _PROGRESSION_DIRS.items():
        if not dir_path.exists():
            logger.warning("Progression directory not found: %s", dir_path)
            continue
        for filepath in dir_path.iterdir():
            if not filepath.suffix.lower() == ".mid":
                continue
            m = _FILENAME_RE.match(filepath.name)
            if not m:
                logger.debug("Skipping unrecognized filename: %s", filepath.name)
                continue
            key = m.group(1)
            numerals = m.group(2).split()
            moods = m.group(3).split()
            entries.append(ProgressionEntry(
                key=key, mode=mode, numerals=numerals,
                moods=moods, file_path=filepath,
            ))

    _CACHED_INDEX = entries
    logger.info("Indexed %d progression files", len(entries))
    return entries


def get_unique_progressions(
    entries: List[ProgressionEntry], mode: str
) -> List[List[str]]:
    """Deduplicate progressions by numeral sequence for a given mode."""
    seen: Set[Tuple[str, ...]] = set()
    unique: List[List[str]] = []
    for e in entries:
        if e.mode != mode:
            continue
        key = tuple(e.numerals)
        if key not in seen:
            seen.add(key)
            unique.append(e.numerals)
    return unique


def get_available_moods(entries: Optional[List[ProgressionEntry]] = None) -> List[str]:
    """Collect all unique mood tags from the progression library."""
    if entries is None:
        entries = index_progressions()
    moods: Set[str] = set()
    for e in entries:
        moods.update(e.moods)
    return sorted(moods)


# ---------------------------------------------------------------------------
# Building transition tables
# ---------------------------------------------------------------------------

def build_transition_table(
    entries: List[ProgressionEntry],
    mode: str,
    mood_filter: Optional[str] = None,
) -> TransitionTable:
    """Build a Markov transition table from progressions of a given mode."""
    table = TransitionTable(mode=mode)

    unique_progs = []
    seen: Set[Tuple[str, ...]] = set()

    for e in entries:
        if e.mode != mode:
            continue
        if mood_filter and mood_filter not in e.moods:
            continue
        key = tuple(e.numerals)
        if key in seen:
            continue
        seen.add(key)
        unique_progs.append(e.numerals)

    for numerals in unique_progs:
        if not numerals:
            continue

        # Track start/end tokens
        table.start_counts[numerals[0]] = table.start_counts.get(numerals[0], 0) + 1
        table.end_counts[numerals[-1]] = table.end_counts.get(numerals[-1], 0) + 1

        # Track vocabulary
        for token in numerals:
            table.vocabulary.add(token)

        # Count bigram transitions
        for i in range(len(numerals) - 1):
            from_token = numerals[i]
            to_token = numerals[i + 1]
            if from_token not in table.transitions:
                table.transitions[from_token] = {}
            table.transitions[from_token][to_token] = (
                table.transitions[from_token].get(to_token, 0) + 1
            )

    logger.info(
        "Built transition table for %s: %d unique progressions, %d tokens",
        mode, len(unique_progs), len(table.vocabulary),
    )
    return table


def get_transition_table(mode: str, mood_filter: Optional[str] = None) -> TransitionTable:
    """Get or build a cached transition table for a mode."""
    cache_key = f"{mode}:{mood_filter or ''}"
    if cache_key not in _CACHED_TABLES:
        entries = index_progressions()
        _CACHED_TABLES[cache_key] = build_transition_table(entries, mode, mood_filter)
    return _CACHED_TABLES[cache_key]


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _weighted_choice(counts: Dict[str, int], temperature: float = 1.0) -> str:
    """Pick a token from a count dict with optional temperature scaling."""
    if not counts:
        raise ValueError("Cannot choose from empty distribution")

    tokens = list(counts.keys())
    weights = list(counts.values())

    if temperature != 1.0:
        # Apply temperature: raise to power (1/temp) then renormalize
        weights = [w ** (1.0 / temperature) for w in weights]

    total = sum(weights)
    r = random.random() * total
    cumulative = 0.0
    for token, weight in zip(tokens, weights):
        cumulative += weight
        if r <= cumulative:
            return token
    return tokens[-1]


def generate_progression(
    table: TransitionTable,
    length: int = 4,
    start_token: Optional[str] = None,
    temperature: float = 1.0,
) -> List[str]:
    """Walk the Markov chain to produce a numeral sequence.

    Args:
        table: TransitionTable for the target mode
        length: Number of chords to generate (4-16)
        start_token: Optional starting chord (e.g., "I"). If None, sampled from start distribution.
        temperature: Controls randomness. <1.0 = conservative, >1.0 = adventurous.

    Returns:
        List of roman numeral tokens (e.g., ["I", "V", "vi", "IV"])
    """
    if not table.start_counts:
        logger.warning("Empty transition table for mode %s", table.mode)
        return ["I"] * length

    # Pick start token
    if start_token and start_token in table.vocabulary:
        current = start_token
    else:
        current = _weighted_choice(table.start_counts, temperature)

    result = [current]

    for _ in range(length - 1):
        successors = table.get_successors(current)
        if not successors:
            # Dead end: restart from start distribution
            current = _weighted_choice(table.start_counts, temperature)
        else:
            current = _weighted_choice(successors, temperature)
        result.append(current)

    return result


def regenerate_single(
    mode: str,
    predecessor: Optional[str],
    exclude: Optional[str] = None,
    temperature: float = 1.0,
    mood_filter: Optional[str] = None,
) -> str:
    """Generate a single replacement token based on Markov context.

    Used for per-card regeneration: given the predecessor chord,
    sample a new chord from the transition distribution.

    Args:
        mode: "Major", "Minor", or "Modal"
        predecessor: The numeral token of the preceding card (or None for slot 0)
        exclude: Token to avoid (the current chord being replaced)
        temperature: Randomness control

    Returns:
        A new numeral token
    """
    table = get_transition_table(mode, mood_filter)

    if predecessor:
        successors = table.get_successors(predecessor)
    else:
        successors = table.start_counts

    if not successors:
        successors = table.start_counts

    # Exclude current token if possible
    if exclude and len(successors) > 1:
        successors = {k: v for k, v in successors.items() if k != exclude}

    if not successors:
        # Fallback to full start distribution
        successors = table.start_counts

    return _weighted_choice(successors, temperature)


# ---------------------------------------------------------------------------
# Realization: numerals → MIDI notes
# ---------------------------------------------------------------------------

def parse_numeral_token(token: str) -> Tuple[int, str]:
    """Parse a roman numeral token into (semitone_offset, chord_type).

    Examples:
        "I"      → (0, "Major")
        "vi"     → (9, "Minor")
        "bVIIM"  → (10, "Major")
        "Idom7"  → (0, "Dominant 7th")
        "ivm"    → (5, "Minor")
        "Vsus2"  → (7, "Sus2")

    Returns:
        (semitone_offset_from_tonic, chord_type_string)
    """
    m = _NUMERAL_RE.match(token)
    if not m:
        logger.warning("Could not parse numeral token: %s", token)
        return (0, "Major")

    accidental = m.group(1)   # "b", "#", or ""
    numeral = m.group(2)      # "I", "vi", "bVII", etc.
    suffix = m.group(3)       # "dom7", "M7", "sus2", etc.

    # Get base semitone offset
    semitones = _DEGREE_SEMITONES.get(numeral, 0)

    # Apply accidental
    if accidental == "b":
        semitones -= 1
    elif accidental == "#":
        semitones += 1
    semitones = semitones % 12

    # Determine chord type
    # Check suffix first
    chord_type = _SUFFIX_TO_CHORD_TYPE.get(suffix)
    if chord_type is None:
        # Default from case: uppercase = Major, lowercase = Minor
        if numeral[0].isupper():
            chord_type = "Major"
        else:
            chord_type = "Minor"

    return (semitones, chord_type)


def realize_progression(
    numerals: List[str],
    key_root: int,
    octave: int = 4,
) -> List[Tuple[int, str, List[int]]]:
    """Convert a numeral sequence to playable chord tuples.

    Args:
        numerals: List of roman numeral tokens (e.g., ["I", "V", "vi", "IV"])
        key_root: Root note of the key (0-11, where 0=C)
        octave: Base octave for voicing (default 4)

    Returns:
        List of (root_note_0_11, chord_type, midi_notes) tuples,
        compatible with the autofill grid.
    """
    from .chord_autofill import CHORD_INTERVALS, get_chord_notes

    result: List[Tuple[int, str, List[int]]] = []

    for token in numerals:
        semitone_offset, chord_type = parse_numeral_token(token)
        root = (key_root + semitone_offset) % 12
        notes = get_chord_notes(root, chord_type, octave)
        result.append((root, chord_type, notes))

    return result


def generate_and_realize(
    mode: str,
    key_root: int,
    length: int = 4,
    start_token: Optional[str] = None,
    temperature: float = 1.0,
    mood_filter: Optional[str] = None,
    fill_to: int = 16,
    octave: int = 4,
) -> Tuple[List[Tuple[int, str, List[int]]], List[str]]:
    """Generate a Markov progression and realize it as MIDI chord tuples.

    This is the main entry point for the autofill dialog.

    Args:
        mode: "Major", "Minor", or "Modal"
        key_root: Root note of key (0-11)
        length: Unique chords to generate before looping
        start_token: Optional starting numeral
        temperature: Randomness (0.5-2.0)
        mood_filter: Optional mood tag filter
        fill_to: Total slots to fill (default 16, loops progression)
        octave: Base octave for voicing

    Returns:
        (chords, slot_numerals) where:
        - chords: List of (root, type, notes) tuples, length = fill_to
        - slot_numerals: List of numeral tokens per slot, length = fill_to
    """
    table = get_transition_table(mode, mood_filter)
    numerals = generate_progression(table, length, start_token, temperature)

    # Loop to fill all slots
    slot_numerals: List[str] = []
    while len(slot_numerals) < fill_to:
        slot_numerals.extend(numerals)
    slot_numerals = slot_numerals[:fill_to]

    chords = realize_progression(slot_numerals, key_root, octave)
    return chords, slot_numerals
