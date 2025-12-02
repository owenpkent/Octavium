"""
Chord suggestion algorithms for harmonic sequencing.

Provides various methods for suggesting the next chord in a progression:
- Neo-Riemannian transformations (P, L, R, N, S, H)
- Circle of Fifths (dominant, subdominant)
- Diatonic progressions
- Common progressions
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass


# Note names for display
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


@dataclass
class ChordSuggestion:
    """A suggested chord with metadata."""
    root_note: int  # MIDI note number (0-127)
    chord_type: str  # e.g., "Major", "Minor", "Dim", "Aug"
    actual_notes: List[int]  # The actual MIDI notes to play
    name: str  # Display name (e.g., "C Major")
    transformation: str  # Name of the transformation that produced this
    category: str  # Category for menu grouping


def get_chord_notes(root: int, chord_type: str, octave: int = 4) -> List[int]:
    """Generate MIDI notes for a chord given root and type."""
    base = (octave * 12) + (root % 12)
    
    # Chord intervals (semitones from root)
    intervals = {
        "Major": [0, 4, 7],
        "Minor": [0, 3, 7],
        "Dim": [0, 3, 6],
        "Aug": [0, 4, 8],
        "Maj7": [0, 4, 7, 11],
        "Min7": [0, 3, 7, 10],
        "Dom7": [0, 4, 7, 10],
        "Dim7": [0, 3, 6, 9],
        "HalfDim7": [0, 3, 6, 10],
        "MinMaj7": [0, 3, 7, 11],
        "Aug7": [0, 4, 8, 10],
        "Sus2": [0, 2, 7],
        "Sus4": [0, 5, 7],
        "Add9": [0, 4, 7, 14],
        "6": [0, 4, 7, 9],
        "Min6": [0, 3, 7, 9],
    }
    
    chord_intervals = intervals.get(chord_type, [0, 4, 7])  # Default to major
    return [base + i for i in chord_intervals]


def detect_chord_quality(actual_notes: List[int]) -> Tuple[int, str]:
    """Detect chord root and quality from actual notes."""
    if not actual_notes:
        return (0, "Major")
    
    # Normalize to pitch classes
    pitch_classes = sorted(set(n % 12 for n in actual_notes))
    if not pitch_classes:
        return (0, "Major")
    
    root = pitch_classes[0]
    
    # Calculate intervals from root
    intervals = tuple((pc - root) % 12 for pc in pitch_classes)
    
    # Match against known chord types
    chord_patterns = {
        (0, 4, 7): "Major",
        (0, 3, 7): "Minor",
        (0, 3, 6): "Dim",
        (0, 4, 8): "Aug",
        (0, 4, 7, 11): "Maj7",
        (0, 3, 7, 10): "Min7",
        (0, 4, 7, 10): "Dom7",
        (0, 3, 6, 9): "Dim7",
        (0, 3, 6, 10): "HalfDim7",
        (0, 3, 7, 11): "MinMaj7",
        (0, 4, 8, 10): "Aug7",
        (0, 2, 7): "Sus2",
        (0, 5, 7): "Sus4",
    }
    
    return (root, chord_patterns.get(intervals, "Major"))


def is_major_quality(chord_type: str) -> bool:
    """Check if chord has major third."""
    major_types = {"Major", "Maj7", "Dom7", "Aug", "Aug7", "6", "Add9"}
    return chord_type in major_types


def is_minor_quality(chord_type: str) -> bool:
    """Check if chord has minor third."""
    minor_types = {"Minor", "Min7", "Dim", "Dim7", "HalfDim7", "MinMaj7", "Min6"}
    return chord_type in minor_types


# =============================================================================
# Neo-Riemannian Transformations
# =============================================================================

def neo_riemannian_P(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """
    Parallel transformation: Major <-> Minor
    Keeps root and fifth, moves third by semitone.
    """
    new_type = "Minor" if is_major_quality(chord_type) else "Major"
    name = f"{NOTES[root % 12]} {new_type}"
    return ChordSuggestion(
        root_note=root,
        chord_type=new_type,
        actual_notes=get_chord_notes(root, new_type, octave),
        name=name,
        transformation="P (Parallel)",
        category="Neo-Riemannian"
    )


def neo_riemannian_L(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """
    Leading-tone exchange: 
    Major -> Minor (root down semitone)
    Minor -> Major (fifth up semitone)
    """
    if is_major_quality(chord_type):
        # C Major -> E Minor (root becomes fifth of new chord)
        new_root = (root + 4) % 12  # Major third becomes root
        new_type = "Minor"
    else:
        # A Minor -> F Major (fifth becomes root of new chord)
        new_root = (root + 8) % 12  # Minor sixth (down 4) becomes root
        new_type = "Major"
    
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="L (Leading-tone)",
        category="Neo-Riemannian"
    )


def neo_riemannian_R(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """
    Relative transformation:
    Major -> Relative Minor (down 3 semitones)
    Minor -> Relative Major (up 3 semitones)
    """
    if is_major_quality(chord_type):
        new_root = (root + 9) % 12  # Down 3 = up 9
        new_type = "Minor"
    else:
        new_root = (root + 3) % 12  # Up 3
        new_type = "Major"
    
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="R (Relative)",
        category="Neo-Riemannian"
    )


def neo_riemannian_N(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """
    Nebenverwandt (RLP): Major/Minor to its minor/major subdominant.
    C Major -> F Minor, C Minor -> F Major
    """
    new_root = (root + 5) % 12  # Up a fourth
    new_type = "Minor" if is_major_quality(chord_type) else "Major"
    
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="N (Nebenverwandt)",
        category="Neo-Riemannian"
    )


def neo_riemannian_S(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """
    Slide transformation (LPR):
    Moves root by semitone, changes quality.
    C Major -> C# Minor, C Minor -> B Major
    """
    if is_major_quality(chord_type):
        new_root = (root + 1) % 12  # Up semitone
        new_type = "Minor"
    else:
        new_root = (root - 1) % 12  # Down semitone
        new_type = "Major"
    
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="S (Slide)",
        category="Neo-Riemannian"
    )


def neo_riemannian_H(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """
    Hexatonic pole (LPL): Maximally distant chord.
    C Major -> Ab Minor, C Minor -> E Major
    """
    if is_major_quality(chord_type):
        new_root = (root + 8) % 12  # Up major sixth
        new_type = "Minor"
    else:
        new_root = (root + 4) % 12  # Up major third
        new_type = "Major"
    
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="H (Hexatonic Pole)",
        category="Neo-Riemannian"
    )


# =============================================================================
# Circle of Fifths
# =============================================================================

def circle_dominant(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Move up a fifth (dominant direction)."""
    new_root = (root + 7) % 12
    name = f"{NOTES[new_root]} {chord_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=chord_type,
        actual_notes=get_chord_notes(new_root, chord_type, octave),
        name=name,
        transformation="V (Dominant)",
        category="Circle of Fifths"
    )


def circle_subdominant(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Move down a fifth (subdominant direction)."""
    new_root = (root + 5) % 12  # Down 5 = up 7, but we want up 5 for subdominant
    name = f"{NOTES[new_root]} {chord_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=chord_type,
        actual_notes=get_chord_notes(new_root, chord_type, octave),
        name=name,
        transformation="IV (Subdominant)",
        category="Circle of Fifths"
    )


def circle_dominant_seventh(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Dominant seventh chord (V7)."""
    new_root = (root + 7) % 12
    name = f"{NOTES[new_root]} Dom7"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Dom7",
        actual_notes=get_chord_notes(new_root, "Dom7", octave),
        name=name,
        transformation="V7 (Dominant 7th)",
        category="Circle of Fifths"
    )


def circle_secondary_dominant(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Secondary dominant (V/V) - dominant of the dominant."""
    new_root = (root + 2) % 12  # Whole step up (V of V)
    name = f"{NOTES[new_root]} Dom7"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Dom7",
        actual_notes=get_chord_notes(new_root, "Dom7", octave),
        name=name,
        transformation="V/V (Secondary Dom)",
        category="Circle of Fifths"
    )


# =============================================================================
# Diatonic Progressions
# =============================================================================

def diatonic_ii(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """ii chord (supertonic) - minor in major key."""
    new_root = (root + 2) % 12
    new_type = "Minor" if is_major_quality(chord_type) else "Dim"
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="ii (Supertonic)",
        category="Diatonic"
    )


def diatonic_iii(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """iii chord (mediant)."""
    new_root = (root + 4) % 12
    new_type = "Minor" if is_major_quality(chord_type) else "Major"
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="iii (Mediant)",
        category="Diatonic"
    )


def diatonic_vi(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """vi chord (submediant) - relative minor/major."""
    new_root = (root + 9) % 12
    new_type = "Minor" if is_major_quality(chord_type) else "Major"
    name = f"{NOTES[new_root]} {new_type}"
    return ChordSuggestion(
        root_note=new_root,
        chord_type=new_type,
        actual_notes=get_chord_notes(new_root, new_type, octave),
        name=name,
        transformation="vi (Submediant)",
        category="Diatonic"
    )


def diatonic_vii(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """vii° chord (leading tone diminished)."""
    new_root = (root + 11) % 12
    name = f"{NOTES[new_root]} Dim"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Dim",
        actual_notes=get_chord_notes(new_root, "Dim", octave),
        name=name,
        transformation="vii° (Leading Tone)",
        category="Diatonic"
    )


# =============================================================================
# Chromatic / Jazz
# =============================================================================

def chromatic_tritone_sub(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Tritone substitution - common jazz voicing."""
    new_root = (root + 6) % 12
    name = f"{NOTES[new_root]} Dom7"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Dom7",
        actual_notes=get_chord_notes(new_root, "Dom7", octave),
        name=name,
        transformation="Tritone Sub",
        category="Chromatic"
    )


def chromatic_minor_plagal(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Minor plagal (iv -> I) - the "Amen" cadence variation."""
    new_root = (root + 5) % 12
    name = f"{NOTES[new_root]} Minor"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Minor",
        actual_notes=get_chord_notes(new_root, "Minor", octave),
        name=name,
        transformation="iv (Minor Plagal)",
        category="Chromatic"
    )


def chromatic_neapolitan(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Neapolitan chord (bII) - flat second major."""
    new_root = (root + 1) % 12
    name = f"{NOTES[new_root]} Major"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Major",
        actual_notes=get_chord_notes(new_root, "Major", octave),
        name=name,
        transformation="bII (Neapolitan)",
        category="Chromatic"
    )


def chromatic_augmented_sixth(root: int, chord_type: str, octave: int = 4) -> ChordSuggestion:
    """Augmented sixth approach - typically resolves to V."""
    new_root = (root + 8) % 12  # bVI
    name = f"{NOTES[new_root]} Aug"
    return ChordSuggestion(
        root_note=new_root,
        chord_type="Aug",
        actual_notes=get_chord_notes(new_root, "Aug", octave),
        name=name,
        transformation="Aug6 (Approach)",
        category="Chromatic"
    )


# =============================================================================
# Main API
# =============================================================================

def get_all_suggestions(root: int, chord_type: str, actual_notes: Optional[List[int]] = None) -> dict[str, List[ChordSuggestion]]:
    """
    Get all chord suggestions organized by category.
    
    Args:
        root: Root note (0-11 for C-B, or full MIDI note)
        chord_type: Current chord type (e.g., "Major", "Minor")
        actual_notes: Optional list of actual MIDI notes for octave detection
        
    Returns:
        Dictionary mapping category names to lists of suggestions.
    """
    # Detect octave from actual notes if provided
    if actual_notes:
        octave = min(actual_notes) // 12
    else:
        octave = 4
    
    root = root % 12  # Normalize to pitch class
    
    suggestions: dict[str, List[ChordSuggestion]] = {
        "Neo-Riemannian": [],
        "Circle of Fifths": [],
        "Diatonic": [],
        "Chromatic": [],
    }
    
    # Neo-Riemannian transformations
    suggestions["Neo-Riemannian"] = [
        neo_riemannian_P(root, chord_type, octave),
        neo_riemannian_L(root, chord_type, octave),
        neo_riemannian_R(root, chord_type, octave),
        neo_riemannian_N(root, chord_type, octave),
        neo_riemannian_S(root, chord_type, octave),
        neo_riemannian_H(root, chord_type, octave),
    ]
    
    # Circle of fifths
    suggestions["Circle of Fifths"] = [
        circle_dominant(root, chord_type, octave),
        circle_subdominant(root, chord_type, octave),
        circle_dominant_seventh(root, chord_type, octave),
        circle_secondary_dominant(root, chord_type, octave),
    ]
    
    # Diatonic
    suggestions["Diatonic"] = [
        diatonic_ii(root, chord_type, octave),
        diatonic_iii(root, chord_type, octave),
        diatonic_vi(root, chord_type, octave),
        diatonic_vii(root, chord_type, octave),
    ]
    
    # Chromatic
    suggestions["Chromatic"] = [
        chromatic_tritone_sub(root, chord_type, octave),
        chromatic_minor_plagal(root, chord_type, octave),
        chromatic_neapolitan(root, chord_type, octave),
        chromatic_augmented_sixth(root, chord_type, octave),
    ]
    
    return suggestions
