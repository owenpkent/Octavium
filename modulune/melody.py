"""
Melody module for Modulune.

Provides phrase generation, contour shapes, and melodic motif development.
Creates organic melodic lines with impressionistic phrasing and ornamentation.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random
import math

from .harmony import Scale, ScaleType, Chord


class ContourType(Enum):
    """Melodic contour shapes for phrase generation."""
    
    ASCENDING = "ascending"
    DESCENDING = "descending"
    ARCH = "arch"
    INVERSE_ARCH = "inverse_arch"
    WAVE = "wave"
    PLATEAU = "plateau"
    STATIC = "static"


class ArticulationType(Enum):
    """Articulation styles for notes."""
    
    LEGATO = "legato"
    STACCATO = "staccato"
    TENUTO = "tenuto"
    ACCENT = "accent"
    NORMAL = "normal"


@dataclass
class Note:
    """
    A single melodic note with timing and expression.
    
    Attributes:
        pitch: MIDI note number (0-127).
        duration: Duration in beats.
        velocity: MIDI velocity (1-127).
        articulation: How the note should be played.
        delay: Slight timing offset in beats (for humanization).
    """
    
    pitch: int
    duration: float
    velocity: int = 80
    articulation: ArticulationType = ArticulationType.NORMAL
    delay: float = 0.0
    
    def __post_init__(self):
        self.pitch = max(0, min(127, self.pitch))
        self.velocity = max(1, min(127, self.velocity))


@dataclass
class Phrase:
    """
    A melodic phrase consisting of multiple notes.
    
    Attributes:
        notes: List of Note objects.
        contour: The overall shape of the phrase.
        start_beat: When this phrase starts in beats.
    """
    
    notes: list[Note] = field(default_factory=list)
    contour: ContourType = ContourType.ARCH
    start_beat: float = 0.0
    
    def __len__(self) -> int:
        return len(self.notes)
    
    def total_duration(self) -> float:
        """Return total duration of the phrase in beats."""
        if not self.notes:
            return 0.0
        return sum(n.duration for n in self.notes)
    
    def transpose(self, semitones: int) -> "Phrase":
        """
        Return a transposed copy of this phrase.
        
        Args:
            semitones: Number of semitones to transpose.
            
        Returns:
            New Phrase with transposed notes.
        """
        new_notes = [
            Note(
                pitch=n.pitch + semitones,
                duration=n.duration,
                velocity=n.velocity,
                articulation=n.articulation,
                delay=n.delay,
            )
            for n in self.notes
        ]
        return Phrase(new_notes, self.contour, self.start_beat)


class MelodyEngine:
    """
    Engine for generating impressionistic melodic phrases.
    
    Creates flowing, organic melody lines with characteristic impressionistic
    features: wide intervals, chromatic neighbor tones, arpeggiated figures,
    and dynamic phrase shapes.
    
    Attributes:
        scale: The current scale context for melody generation.
        register_low: Lowest MIDI note for melodies.
        register_high: Highest MIDI note for melodies.
        density: 0.0-1.0, affects how many notes per beat.
        expressiveness: 0.0-1.0, affects velocity and timing variation.
    """
    
    def __init__(
        self,
        scale: Optional[Scale] = None,
        register_low: int = 60,
        register_high: int = 84,
        density: float = 0.5,
        expressiveness: float = 0.6,
    ):
        """
        Initialize the melody engine.
        
        Args:
            scale: Scale to use for melody generation.
            register_low: Lowest note in melody range.
            register_high: Highest note in melody range.
            density: Note density (0.0 = sparse, 1.0 = dense).
            expressiveness: Expression amount (affects dynamics, timing).
        """
        self.scale = scale or Scale(60, ScaleType.MAJOR)
        self.register_low = register_low
        self.register_high = register_high
        self.density = density
        self.expressiveness = expressiveness
        self._motifs: list[Phrase] = []
        self._last_note: int = 72  # Middle register default
    
    def generate_phrase(
        self,
        length_beats: float = 4.0,
        contour: Optional[ContourType] = None,
        chord: Optional[Chord] = None,
    ) -> Phrase:
        """
        Generate a melodic phrase.
        
        Args:
            length_beats: Duration of the phrase in beats.
            contour: Desired melodic contour (random if None).
            chord: Current chord for chord-tone emphasis.
            
        Returns:
            A Phrase object containing the generated notes.
        """
        if contour is None:
            contour = random.choice(list(ContourType))
        
        # Determine number of notes based on density
        base_notes = int(length_beats * 2)  # 2 notes per beat baseline
        note_count = max(1, int(base_notes * (0.5 + self.density)))
        
        # Generate contour curve
        contour_values = self._generate_contour(note_count, contour)
        
        # Get available pitches
        scale_notes = self.scale.get_notes_in_range(self.register_low, self.register_high)
        chord_tones = chord.get_voicing(self.register_low, self.register_high) if chord else []
        
        notes = []
        current_pitch = self._last_note
        
        for i, contour_val in enumerate(contour_values):
            # Map contour to pitch
            target_pitch = self._contour_to_pitch(contour_val)
            
            # Decide if this should be a chord tone
            use_chord_tone = chord_tones and random.random() < 0.4
            
            if use_chord_tone:
                # Find nearest chord tone
                pitch = min(chord_tones, key=lambda p: abs(p - target_pitch))
            else:
                # Find nearest scale tone
                pitch = min(scale_notes, key=lambda p: abs(p - target_pitch))
            
            # Occasionally add chromatic neighbor
            if random.random() < 0.1:
                pitch += random.choice([-1, 1])
            
            # Calculate duration
            remaining_beats = length_beats - sum(n.duration for n in notes)
            remaining_notes = note_count - i
            base_duration = remaining_beats / max(1, remaining_notes)
            duration = self._vary_duration(base_duration)
            
            # Calculate velocity with expression
            base_velocity = 70
            contour_velocity = int(contour_val * 30)
            velocity = base_velocity + contour_velocity
            velocity += random.randint(-10, 10) if self.expressiveness > 0.3 else 0
            velocity = max(40, min(110, velocity))
            
            # Humanize timing
            delay = 0.0
            if self.expressiveness > 0.4:
                delay = random.gauss(0, 0.02 * self.expressiveness)
            
            # Determine articulation
            articulation = self._choose_articulation(i, note_count, duration)
            
            note = Note(pitch, duration, velocity, articulation, delay)
            notes.append(note)
            current_pitch = pitch
        
        self._last_note = current_pitch
        
        phrase = Phrase(notes, contour)
        
        # Optionally store as motif for development
        if random.random() < 0.3 and len(notes) >= 3:
            self._motifs.append(phrase)
            if len(self._motifs) > 5:
                self._motifs.pop(0)
        
        return phrase
    
    def _generate_contour(self, length: int, contour_type: ContourType) -> list[float]:
        """
        Generate a contour curve (values from 0.0 to 1.0).
        
        Args:
            length: Number of points in the contour.
            contour_type: Shape of the contour.
            
        Returns:
            List of float values representing the contour.
        """
        if length <= 1:
            return [0.5]
        
        values = []
        for i in range(length):
            t = i / (length - 1)  # 0 to 1
            
            if contour_type == ContourType.ASCENDING:
                val = t
            elif contour_type == ContourType.DESCENDING:
                val = 1 - t
            elif contour_type == ContourType.ARCH:
                val = math.sin(t * math.pi)
            elif contour_type == ContourType.INVERSE_ARCH:
                val = 1 - math.sin(t * math.pi)
            elif contour_type == ContourType.WAVE:
                val = 0.5 + 0.5 * math.sin(t * math.pi * 2)
            elif contour_type == ContourType.PLATEAU:
                if t < 0.25:
                    val = t * 4
                elif t > 0.75:
                    val = (1 - t) * 4
                else:
                    val = 1.0
            else:  # STATIC
                val = 0.5
            
            # Add slight randomness
            val += random.gauss(0, 0.05)
            values.append(max(0, min(1, val)))
        
        return values
    
    def _contour_to_pitch(self, contour_value: float) -> int:
        """Map a contour value (0-1) to a pitch in the register."""
        pitch_range = self.register_high - self.register_low
        return int(self.register_low + contour_value * pitch_range)
    
    def _vary_duration(self, base_duration: float) -> float:
        """Add rhythmic variation to a duration."""
        if self.expressiveness < 0.2:
            return base_duration
        
        # Common rhythmic values
        rhythms = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
        
        # Find closest standard rhythm
        closest = min(rhythms, key=lambda r: abs(r - base_duration))
        
        # Sometimes use triplet feel
        if random.random() < 0.2:
            closest = closest * 2 / 3
        
        return max(0.125, closest)
    
    def _choose_articulation(
        self,
        note_index: int,
        total_notes: int,
        duration: float,
    ) -> ArticulationType:
        """Choose articulation based on context."""
        # Phrase endings tend to be tenuto
        if note_index == total_notes - 1:
            return ArticulationType.TENUTO
        
        # Short notes tend to be staccato
        if duration < 0.3:
            if random.random() < 0.5:
                return ArticulationType.STACCATO
        
        # Long notes tend to be legato
        if duration > 1.0:
            return ArticulationType.LEGATO
        
        # Occasional accents
        if random.random() < 0.1:
            return ArticulationType.ACCENT
        
        return ArticulationType.NORMAL
    
    def generate_arpeggio(
        self,
        chord: Chord,
        length_beats: float = 2.0,
        pattern: str = "up",
    ) -> Phrase:
        """
        Generate an arpeggiated figure from a chord.
        
        Args:
            chord: The chord to arpeggiate.
            length_beats: Duration of the arpeggio.
            pattern: "up", "down", "up_down", or "random".
            
        Returns:
            A Phrase containing the arpeggio.
        """
        chord_notes = chord.get_voicing(self.register_low, self.register_high)
        
        if not chord_notes:
            return Phrase()
        
        # Determine note order
        if pattern == "up":
            ordered = sorted(chord_notes)
        elif pattern == "down":
            ordered = sorted(chord_notes, reverse=True)
        elif pattern == "up_down":
            up = sorted(chord_notes)
            ordered = up + up[-2:0:-1]  # Up then down (without repeating top/bottom)
        else:  # random
            ordered = chord_notes.copy()
            random.shuffle(ordered)
        
        # Calculate note duration
        note_duration = length_beats / len(ordered)
        
        notes = []
        for i, pitch in enumerate(ordered):
            velocity = 60 + random.randint(0, 20)
            # Emphasize first note
            if i == 0:
                velocity += 15
            
            delay = random.gauss(0, 0.01) if self.expressiveness > 0.5 else 0
            
            note = Note(pitch, note_duration, velocity, ArticulationType.LEGATO, delay)
            notes.append(note)
        
        return Phrase(notes, ContourType.ASCENDING if pattern == "up" else ContourType.DESCENDING)
    
    def develop_motif(self, motif: Optional[Phrase] = None) -> Phrase:
        """
        Develop an existing motif through transformation.
        
        Args:
            motif: The motif to develop (uses stored motif if None).
            
        Returns:
            A transformed Phrase based on the motif.
        """
        if motif is None:
            if not self._motifs:
                return self.generate_phrase()
            motif = random.choice(self._motifs)
        
        # Choose transformation
        transformations = [
            self._transpose_motif,
            self._invert_motif,
            self._augment_motif,
            self._diminish_motif,
            self._ornament_motif,
        ]
        
        transform = random.choice(transformations)
        return transform(motif)
    
    def _transpose_motif(self, motif: Phrase) -> Phrase:
        """Transpose motif by a scale interval."""
        intervals = [-7, -5, -3, -2, 2, 3, 5, 7]
        return motif.transpose(random.choice(intervals))
    
    def _invert_motif(self, motif: Phrase) -> Phrase:
        """Invert the melodic contour."""
        if len(motif.notes) < 2:
            return motif
        
        pivot = motif.notes[0].pitch
        new_notes = []
        for note in motif.notes:
            interval = note.pitch - pivot
            new_pitch = pivot - interval
            new_pitch = max(self.register_low, min(self.register_high, new_pitch))
            new_notes.append(Note(
                new_pitch, note.duration, note.velocity,
                note.articulation, note.delay
            ))
        
        return Phrase(new_notes, motif.contour)
    
    def _augment_motif(self, motif: Phrase) -> Phrase:
        """Double the duration of all notes."""
        new_notes = [
            Note(n.pitch, n.duration * 2, n.velocity, n.articulation, n.delay)
            for n in motif.notes
        ]
        return Phrase(new_notes, motif.contour)
    
    def _diminish_motif(self, motif: Phrase) -> Phrase:
        """Halve the duration of all notes."""
        new_notes = [
            Note(n.pitch, max(0.125, n.duration / 2), n.velocity, n.articulation, n.delay)
            for n in motif.notes
        ]
        return Phrase(new_notes, motif.contour)
    
    def _ornament_motif(self, motif: Phrase) -> Phrase:
        """Add ornamental notes to the motif."""
        new_notes = []
        for note in motif.notes:
            # Occasionally add a grace note
            if random.random() < 0.3:
                grace_pitch = note.pitch + random.choice([-2, -1, 1, 2])
                grace = Note(grace_pitch, 0.125, note.velocity - 10,
                           ArticulationType.STACCATO, -0.05)
                new_notes.append(grace)
                new_notes.append(Note(
                    note.pitch, note.duration - 0.125, note.velocity,
                    note.articulation, note.delay
                ))
            else:
                new_notes.append(note)
        
        return Phrase(new_notes, motif.contour)
    
    def generate_accompaniment_figure(
        self,
        chord: Chord,
        length_beats: float = 4.0,
        style: str = "broken",
    ) -> Phrase:
        """
        Generate an accompaniment pattern for a chord.
        
        Args:
            chord: The chord to accompany.
            length_beats: Duration of the pattern.
            style: "broken", "alberti", "block", or "tremolo".
            
        Returns:
            A Phrase containing the accompaniment figure.
        """
        voicing = chord.get_voicing(self.register_low - 12, self.register_high - 12)
        
        if len(voicing) < 3:
            return Phrase()
        
        bass = min(voicing)
        upper = sorted([n for n in voicing if n != bass])
        
        notes = []
        current_beat = 0.0
        
        if style == "broken":
            # Broken chord pattern
            pattern = [bass] + upper
            note_dur = length_beats / len(pattern) / 2
            while current_beat < length_beats:
                for pitch in pattern:
                    if current_beat >= length_beats:
                        break
                    notes.append(Note(pitch, note_dur, 55))
                    current_beat += note_dur
        
        elif style == "alberti":
            # Alberti bass: low-high-mid-high
            if len(upper) >= 2:
                pattern = [bass, upper[-1], upper[0], upper[-1]]
                note_dur = 0.25
                while current_beat < length_beats:
                    for pitch in pattern:
                        if current_beat >= length_beats:
                            break
                        notes.append(Note(pitch, note_dur, 50))
                        current_beat += note_dur
        
        elif style == "block":
            # Block chords
            note_dur = 1.0
            while current_beat < length_beats:
                for pitch in voicing:
                    notes.append(Note(pitch, note_dur, 60 + random.randint(-5, 5)))
                current_beat += note_dur
        
        else:  # tremolo
            # Tremolo between two notes
            if len(upper) >= 1:
                pattern = [bass, upper[0]]
                note_dur = 0.125
                while current_beat < length_beats:
                    for pitch in pattern:
                        if current_beat >= length_beats:
                            break
                        notes.append(Note(pitch, note_dur, 45))
                        current_beat += note_dur
        
        return Phrase(notes)
