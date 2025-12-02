"""
Harmony module for Modulune.

Provides scale definitions, chord structures, and harmonic progression rules
inspired by impressionistic harmony. Supports modal interchange, extended
chords, and voice leading principles.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


class ScaleType(Enum):
    """Scale types commonly used in impressionistic music."""
    
    MAJOR = "major"
    NATURAL_MINOR = "natural_minor"
    HARMONIC_MINOR = "harmonic_minor"
    MELODIC_MINOR = "melodic_minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    AEOLIAN = "aeolian"
    LOCRIAN = "locrian"
    WHOLE_TONE = "whole_tone"
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"
    BLUES = "blues"


# Interval patterns (semitones from root)
SCALE_INTERVALS: dict[ScaleType, tuple[int, ...]] = {
    ScaleType.MAJOR: (0, 2, 4, 5, 7, 9, 11),
    ScaleType.NATURAL_MINOR: (0, 2, 3, 5, 7, 8, 10),
    ScaleType.HARMONIC_MINOR: (0, 2, 3, 5, 7, 8, 11),
    ScaleType.MELODIC_MINOR: (0, 2, 3, 5, 7, 9, 11),
    ScaleType.DORIAN: (0, 2, 3, 5, 7, 9, 10),
    ScaleType.PHRYGIAN: (0, 1, 3, 5, 7, 8, 10),
    ScaleType.LYDIAN: (0, 2, 4, 6, 7, 9, 11),
    ScaleType.MIXOLYDIAN: (0, 2, 4, 5, 7, 9, 10),
    ScaleType.AEOLIAN: (0, 2, 3, 5, 7, 8, 10),
    ScaleType.LOCRIAN: (0, 1, 3, 5, 6, 8, 10),
    ScaleType.WHOLE_TONE: (0, 2, 4, 6, 8, 10),
    ScaleType.PENTATONIC_MAJOR: (0, 2, 4, 7, 9),
    ScaleType.PENTATONIC_MINOR: (0, 3, 5, 7, 10),
    ScaleType.BLUES: (0, 3, 5, 6, 7, 10),
}


@dataclass
class Scale:
    """
    A musical scale rooted at a specific pitch.
    
    Attributes:
        root: MIDI note number of the scale root (0-127, where 60 = middle C).
        scale_type: The type of scale (major, minor, modes, etc.).
    """
    
    root: int
    scale_type: ScaleType = ScaleType.MAJOR
    
    @property
    def intervals(self) -> tuple[int, ...]:
        """Return the interval pattern for this scale type."""
        return SCALE_INTERVALS[self.scale_type]
    
    def get_notes_in_range(self, low: int = 36, high: int = 96) -> list[int]:
        """
        Get all scale notes within a MIDI note range.
        
        Args:
            low: Lowest MIDI note to include.
            high: Highest MIDI note to include.
            
        Returns:
            List of MIDI note numbers in the scale within the range.
        """
        notes = []
        for octave in range(-2, 10):
            for interval in self.intervals:
                note = self.root + (octave * 12) + interval
                if low <= note <= high:
                    notes.append(note)
        return sorted(notes)
    
    def quantize(self, note: int) -> int:
        """
        Snap a note to the nearest scale degree.
        
        Args:
            note: MIDI note number to quantize.
            
        Returns:
            The nearest note in the scale.
        """
        scale_notes = self.get_notes_in_range(note - 6, note + 6)
        if not scale_notes:
            return note
        return min(scale_notes, key=lambda n: abs(n - note))
    
    def degree_to_note(self, degree: int, octave: int = 4) -> int:
        """
        Convert a scale degree to a MIDI note.
        
        Args:
            degree: 1-indexed scale degree (1 = root, 2 = second, etc.).
            octave: Octave number (4 = middle octave, C4 = 60).
            
        Returns:
            MIDI note number.
        """
        idx = (degree - 1) % len(self.intervals)
        octave_offset = (degree - 1) // len(self.intervals)
        return self.root + (octave * 12) - 24 + self.intervals[idx] + (octave_offset * 12)


class ChordQuality(Enum):
    """Chord qualities for building chords."""
    
    MAJOR = "major"
    MINOR = "minor"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    MAJOR_7 = "major_7"
    MINOR_7 = "minor_7"
    DOMINANT_7 = "dominant_7"
    DIMINISHED_7 = "diminished_7"
    HALF_DIMINISHED_7 = "half_diminished_7"
    MINOR_MAJOR_7 = "minor_major_7"
    MAJOR_9 = "major_9"
    MINOR_9 = "minor_9"
    DOMINANT_9 = "dominant_9"
    ADD_9 = "add_9"
    MINOR_ADD_9 = "minor_add_9"
    SUS_2 = "sus_2"
    SUS_4 = "sus_4"
    MAJOR_6 = "major_6"
    MINOR_6 = "minor_6"


# Chord intervals from root
CHORD_INTERVALS: dict[ChordQuality, tuple[int, ...]] = {
    ChordQuality.MAJOR: (0, 4, 7),
    ChordQuality.MINOR: (0, 3, 7),
    ChordQuality.DIMINISHED: (0, 3, 6),
    ChordQuality.AUGMENTED: (0, 4, 8),
    ChordQuality.MAJOR_7: (0, 4, 7, 11),
    ChordQuality.MINOR_7: (0, 3, 7, 10),
    ChordQuality.DOMINANT_7: (0, 4, 7, 10),
    ChordQuality.DIMINISHED_7: (0, 3, 6, 9),
    ChordQuality.HALF_DIMINISHED_7: (0, 3, 6, 10),
    ChordQuality.MINOR_MAJOR_7: (0, 3, 7, 11),
    ChordQuality.MAJOR_9: (0, 4, 7, 11, 14),
    ChordQuality.MINOR_9: (0, 3, 7, 10, 14),
    ChordQuality.DOMINANT_9: (0, 4, 7, 10, 14),
    ChordQuality.ADD_9: (0, 4, 7, 14),
    ChordQuality.MINOR_ADD_9: (0, 3, 7, 14),
    ChordQuality.SUS_2: (0, 2, 7),
    ChordQuality.SUS_4: (0, 5, 7),
    ChordQuality.MAJOR_6: (0, 4, 7, 9),
    ChordQuality.MINOR_6: (0, 3, 7, 9),
}


@dataclass
class Chord:
    """
    A chord with a root and quality.
    
    Attributes:
        root: MIDI note number of the chord root.
        quality: The chord quality (major, minor, 7th variants, etc.).
        inversion: 0 = root position, 1 = first inversion, etc.
    """
    
    root: int
    quality: ChordQuality = ChordQuality.MAJOR
    inversion: int = 0
    
    @property
    def intervals(self) -> tuple[int, ...]:
        """Return the interval pattern for this chord quality."""
        return CHORD_INTERVALS[self.quality]
    
    def get_notes(self, base_octave: int = 3) -> list[int]:
        """
        Get the MIDI notes of this chord.
        
        Args:
            base_octave: The octave for the bass note (3 = C3 area).
            
        Returns:
            List of MIDI note numbers forming the chord.
        """
        base = self.root + (base_octave * 12) - 24
        notes = [base + interval for interval in self.intervals]
        
        # Apply inversion
        for _ in range(self.inversion % len(notes)):
            notes[0] += 12
            notes = notes[1:] + [notes[0]]
        
        return sorted(notes)
    
    def get_voicing(
        self,
        low: int = 36,
        high: int = 84,
        spread: bool = True,
        include_bass: bool = True,
    ) -> list[int]:
        """
        Get a voiced chord within a range, optionally spreading notes.
        
        This creates more pianistic voicings by spreading chord tones
        across a wider range, characteristic of impressionistic piano.
        
        Args:
            low: Lowest note allowed.
            high: Highest note allowed.
            spread: If True, spread notes across octaves.
            include_bass: If True, ensure bass note is in low register.
            
        Returns:
            List of MIDI notes forming the voiced chord.
        """
        base_notes = self.get_notes(base_octave=4)
        voiced = []
        
        if include_bass:
            # Place root in bass register
            bass = self.root % 12
            while bass + 24 < low:
                bass += 12
            while bass + 24 > low + 12:
                bass -= 12
            bass += 24
            if low <= bass <= high:
                voiced.append(bass)
        
        if spread:
            # Spread remaining chord tones
            for note in base_notes:
                pitch_class = note % 12
                # Find suitable octave
                target = pitch_class + 48  # Start around C3
                while target < low + 12:
                    target += 12
                while target > high - 6:
                    target -= 12
                # Add some randomness to voicing
                if random.random() < 0.3 and target + 12 <= high:
                    target += 12
                if low <= target <= high and target not in voiced:
                    voiced.append(target)
        else:
            # Compact voicing
            for note in base_notes:
                pitch_class = note % 12
                target = pitch_class + 48
                while target < low:
                    target += 12
                while target > high:
                    target -= 12
                if low <= target <= high and target not in voiced:
                    voiced.append(target)
        
        return sorted(voiced)


@dataclass
class ChordProgression:
    """
    A sequence of chords with timing information.
    
    Attributes:
        chords: List of Chord objects.
        durations: Duration of each chord in beats.
        name: Optional name for the progression.
    """
    
    chords: list[Chord]
    durations: list[float] = field(default_factory=list)
    name: str = ""
    
    def __post_init__(self):
        if not self.durations:
            # Default to 4 beats per chord
            self.durations = [4.0] * len(self.chords)
    
    def __len__(self) -> int:
        return len(self.chords)
    
    def __getitem__(self, idx: int) -> Chord:
        return self.chords[idx]
    
    def total_beats(self) -> float:
        """Return total duration in beats."""
        return sum(self.durations)


class HarmonyEngine:
    """
    Engine for generating impressionistic harmonic progressions.
    
    This engine creates chord progressions using rules inspired by
    impressionistic harmony: modal interchange, parallel motion,
    extended chords, and smooth voice leading.
    
    Attributes:
        current_scale: The current scale context.
        current_chord: The current chord.
        tension_level: 0.0-1.0, affects dissonance and complexity.
    """
    
    def __init__(
        self,
        root: int = 60,
        scale_type: ScaleType = ScaleType.MAJOR,
        tension_level: float = 0.3,
    ):
        """
        Initialize the harmony engine.
        
        Args:
            root: Root note of the starting scale.
            scale_type: Type of scale to use.
            tension_level: Initial tension (0.0 = consonant, 1.0 = dissonant).
        """
        self.current_scale = Scale(root, scale_type)
        self.current_chord: Optional[Chord] = None
        self.tension_level = tension_level
        self._progression_history: list[Chord] = []
        
        # Common impressionistic progressions (as scale degree patterns)
        self._progression_templates = [
            # Debussy-style parallel motion
            [(1, ChordQuality.MAJOR_7), (2, ChordQuality.MINOR_7),
             (4, ChordQuality.MAJOR_7), (1, ChordQuality.MAJOR_7)],
            # Modal interchange
            [(1, ChordQuality.MAJOR_7), (6, ChordQuality.MINOR_7),
             (4, ChordQuality.MAJOR_7), (5, ChordQuality.DOMINANT_7)],
            # Whole-tone influenced
            [(1, ChordQuality.AUGMENTED), (2, ChordQuality.DOMINANT_7),
             (6, ChordQuality.MINOR_7), (1, ChordQuality.MAJOR_9)],
            # Bill Evans voicings
            [(2, ChordQuality.MINOR_9), (5, ChordQuality.DOMINANT_9),
             (1, ChordQuality.MAJOR_9), (4, ChordQuality.MAJOR_7)],
            # Dreamy suspended
            [(1, ChordQuality.SUS_4), (1, ChordQuality.MAJOR_7),
             (4, ChordQuality.ADD_9), (5, ChordQuality.SUS_4)],
        ]
    
    def generate_progression(self, length: int = 4) -> ChordProgression:
        """
        Generate a new chord progression.
        
        Args:
            length: Number of chords in the progression.
            
        Returns:
            A ChordProgression object.
        """
        # Choose a template or generate freely based on tension
        if random.random() < 0.6 and length == 4:
            template = random.choice(self._progression_templates)
            chords = []
            for degree, quality in template:
                root = self.current_scale.degree_to_note(degree, octave=4)
                # Occasionally substitute quality based on tension
                if random.random() < self.tension_level * 0.5:
                    quality = self._substitute_quality(quality)
                chord = Chord(root % 12, quality)
                chords.append(chord)
        else:
            chords = self._generate_free_progression(length)
        
        # Vary durations slightly for organic feel
        durations = []
        for _ in range(len(chords)):
            base_duration = random.choice([2.0, 4.0, 4.0, 4.0, 8.0])
            durations.append(base_duration)
        
        return ChordProgression(chords, durations)
    
    def _generate_free_progression(self, length: int) -> list[Chord]:
        """Generate a progression without a template."""
        chords = []
        prev_root = self.current_scale.root
        
        for _ in range(length):
            # Choose next root with preference for smooth motion
            interval = random.choice([0, 2, 3, 4, 5, 7, -2, -3, -5])
            root = (prev_root + interval) % 12
            
            # Choose quality based on tension
            if self.tension_level < 0.3:
                qualities = [ChordQuality.MAJOR_7, ChordQuality.MINOR_7,
                           ChordQuality.ADD_9, ChordQuality.SUS_4]
            elif self.tension_level < 0.6:
                qualities = [ChordQuality.MAJOR_9, ChordQuality.MINOR_9,
                           ChordQuality.DOMINANT_7, ChordQuality.MINOR_7]
            else:
                qualities = [ChordQuality.AUGMENTED, ChordQuality.DIMINISHED_7,
                           ChordQuality.DOMINANT_9, ChordQuality.HALF_DIMINISHED_7]
            
            quality = random.choice(qualities)
            chords.append(Chord(root, quality))
            prev_root = root
        
        return chords
    
    def _substitute_quality(self, quality: ChordQuality) -> ChordQuality:
        """Substitute a chord quality with a related one."""
        substitutions = {
            ChordQuality.MAJOR: [ChordQuality.MAJOR_7, ChordQuality.ADD_9],
            ChordQuality.MINOR: [ChordQuality.MINOR_7, ChordQuality.MINOR_9],
            ChordQuality.MAJOR_7: [ChordQuality.MAJOR_9, ChordQuality.MAJOR_6],
            ChordQuality.MINOR_7: [ChordQuality.MINOR_9, ChordQuality.MINOR_6],
            ChordQuality.DOMINANT_7: [ChordQuality.DOMINANT_9, ChordQuality.SUS_4],
        }
        options = substitutions.get(quality, [quality])
        return random.choice(options)
    
    def get_next_chord(self) -> Chord:
        """
        Get the next chord based on current harmonic context.
        
        Uses voice leading rules and harmonic tendencies to choose
        a suitable next chord.
        
        Returns:
            The next Chord in the sequence.
        """
        if self.current_chord is None:
            # Start with tonic
            self.current_chord = Chord(
                self.current_scale.root % 12,
                ChordQuality.MAJOR_7
            )
            return self.current_chord
        
        # Determine likely next chords based on current chord
        current_root = self.current_chord.root
        
        # Common progressions from current chord
        movements = [
            (5, 0.3),   # Up a fourth (strong resolution)
            (7, 0.2),   # Up a fifth
            (2, 0.15),  # Up a step
            (-1, 0.15), # Down a half step (chromatic)
            (3, 0.1),   # Up a minor third
            (4, 0.1),   # Up a major third
        ]
        
        # Weight by tension level
        if self.tension_level > 0.5:
            movements = [(m[0], m[1] * (1 + self.tension_level)) for m in movements]
        
        # Choose movement
        total = sum(w for _, w in movements)
        r = random.random() * total
        cumulative = 0
        chosen_interval = 5  # Default to fourth
        for interval, weight in movements:
            cumulative += weight
            if r <= cumulative:
                chosen_interval = interval
                break
        
        new_root = (current_root + chosen_interval) % 12
        
        # Choose quality
        quality = self._choose_quality_for_context(new_root)
        
        self.current_chord = Chord(new_root, quality)
        self._progression_history.append(self.current_chord)
        
        return self.current_chord
    
    def _choose_quality_for_context(self, root: int) -> ChordQuality:
        """Choose an appropriate chord quality based on harmonic context."""
        # Check if root is in current scale
        scale_notes = [self.current_scale.root + i for i in self.current_scale.intervals]
        scale_degrees = [n % 12 for n in scale_notes]
        
        if root in scale_degrees:
            idx = scale_degrees.index(root)
            # Diatonic quality with impressionistic extensions
            if idx in [0, 3]:  # I, IV - major
                return random.choice([ChordQuality.MAJOR_7, ChordQuality.MAJOR_9,
                                     ChordQuality.ADD_9])
            elif idx in [1, 2, 5]:  # ii, iii, vi - minor
                return random.choice([ChordQuality.MINOR_7, ChordQuality.MINOR_9])
            elif idx == 4:  # V - dominant
                return random.choice([ChordQuality.DOMINANT_7, ChordQuality.DOMINANT_9,
                                     ChordQuality.SUS_4])
            else:  # vii - diminished
                return random.choice([ChordQuality.HALF_DIMINISHED_7,
                                     ChordQuality.DIMINISHED_7])
        else:
            # Chromatic chord - use more colorful qualities
            return random.choice([ChordQuality.MAJOR_7, ChordQuality.MINOR_7,
                                 ChordQuality.DOMINANT_7, ChordQuality.AUGMENTED])
    
    def modulate(self, new_root: Optional[int] = None, new_mode: Optional[ScaleType] = None):
        """
        Modulate to a new key or mode.
        
        Args:
            new_root: New root note (if None, keeps current root).
            new_mode: New scale type (if None, keeps current type).
        """
        root = new_root if new_root is not None else self.current_scale.root
        mode = new_mode if new_mode is not None else self.current_scale.scale_type
        self.current_scale = Scale(root, mode)
    
    def suggest_modulation(self) -> tuple[int, ScaleType]:
        """
        Suggest a musically sensible modulation.
        
        Returns:
            Tuple of (new_root, new_scale_type).
        """
        current_root = self.current_scale.root
        
        # Common modulation targets
        targets = [
            (current_root + 7, self.current_scale.scale_type),   # Dominant key
            (current_root + 5, self.current_scale.scale_type),   # Subdominant
            (current_root, ScaleType.DORIAN),                     # Modal change
            (current_root + 3, ScaleType.NATURAL_MINOR),         # Relative minor
            (current_root - 1, self.current_scale.scale_type),   # Down half step
        ]
        
        return random.choice(targets)
