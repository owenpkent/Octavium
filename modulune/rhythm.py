"""
Rhythm module for Modulune.

Provides timing, tempo control, and rhythmic pattern generation.
Supports rubato, swing, and expressive timing variations characteristic
of impressionistic piano performance.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Generator
import random
import time
import math


class TimeSignature(Enum):
    """Common time signatures."""
    
    FOUR_FOUR = (4, 4)
    THREE_FOUR = (3, 4)
    SIX_EIGHT = (6, 8)
    TWO_FOUR = (2, 4)
    FIVE_FOUR = (5, 4)
    SEVEN_EIGHT = (7, 8)
    TWELVE_EIGHT = (12, 8)


@dataclass
class TempoEvent:
    """
    A tempo change event.
    
    Attributes:
        beat: Beat position where tempo change occurs.
        bpm: New tempo in beats per minute.
        transition_beats: Beats over which to gradually change.
    """
    
    beat: float
    bpm: float
    transition_beats: float = 0.0


@dataclass
class RhythmPattern:
    """
    A rhythmic pattern of note durations and accents.
    
    Attributes:
        durations: List of note durations in beats.
        accents: List of accent strengths (0.0-1.0) for each note.
        name: Optional pattern name.
    """
    
    durations: list[float]
    accents: list[float] = field(default_factory=list)
    name: str = ""
    
    def __post_init__(self):
        if not self.accents:
            self.accents = [0.5] * len(self.durations)
    
    def total_beats(self) -> float:
        """Return total duration in beats."""
        return sum(self.durations)
    
    def __len__(self) -> int:
        return len(self.durations)


class RhythmEngine:
    """
    Engine for generating and managing musical timing.
    
    Provides tempo control, beat tracking, rubato, swing, and
    humanization features for expressive timing.
    
    Attributes:
        bpm: Current tempo in beats per minute.
        time_signature: Current time signature.
        swing_amount: 0.0-1.0, amount of swing feel.
        rubato_amount: 0.0-1.0, amount of tempo flexibility.
    """
    
    def __init__(
        self,
        bpm: float = 72.0,
        time_signature: TimeSignature = TimeSignature.FOUR_FOUR,
        swing_amount: float = 0.0,
        rubato_amount: float = 0.3,
    ):
        """
        Initialize the rhythm engine.
        
        Args:
            bpm: Starting tempo.
            time_signature: Time signature to use.
            swing_amount: Amount of swing (0 = straight, 1 = full swing).
            rubato_amount: Amount of rubato (tempo flexibility).
        """
        self.bpm = bpm
        self.time_signature = time_signature
        self.swing_amount = swing_amount
        self.rubato_amount = rubato_amount
        
        self._base_bpm = bpm
        self._current_beat: float = 0.0
        self._start_time: Optional[float] = None
        self._tempo_events: list[TempoEvent] = []
        self._last_tick_time: float = 0.0
        
        # Rubato state
        self._rubato_phase: float = 0.0
        self._rubato_direction: int = 1
        
        # Common rhythm patterns for impressionistic music
        self._patterns = {
            "flowing_eighth": RhythmPattern(
                [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5],
                [0.8, 0.4, 0.6, 0.4, 0.7, 0.4, 0.5, 0.4],
                "flowing_eighth"
            ),
            "dotted_quarter": RhythmPattern(
                [1.5, 0.5, 1.5, 0.5],
                [0.9, 0.5, 0.7, 0.5],
                "dotted_quarter"
            ),
            "triplet": RhythmPattern(
                [1/3, 1/3, 1/3, 1/3, 1/3, 1/3],
                [0.8, 0.5, 0.5, 0.7, 0.5, 0.5],
                "triplet"
            ),
            "syncopated": RhythmPattern(
                [0.5, 1.0, 0.5, 1.0, 1.0],
                [0.7, 0.9, 0.6, 0.8, 0.7],
                "syncopated"
            ),
            "sparse": RhythmPattern(
                [2.0, 1.0, 1.0],
                [0.9, 0.6, 0.5],
                "sparse"
            ),
            "gentle_waltz": RhythmPattern(
                [1.0, 0.5, 0.5, 1.0],
                [0.9, 0.4, 0.5, 0.7],
                "gentle_waltz"
            ),
            "impressionist_flow": RhythmPattern(
                [0.75, 0.25, 0.5, 0.5, 1.0, 1.0],
                [0.8, 0.4, 0.6, 0.5, 0.7, 0.6],
                "impressionist_flow"
            ),
        }
    
    @property
    def beat_duration(self) -> float:
        """Duration of one beat in seconds at current tempo."""
        return 60.0 / self.bpm
    
    @property
    def measure_beats(self) -> int:
        """Number of beats in a measure."""
        return self.time_signature.value[0]
    
    @property
    def current_beat(self) -> float:
        """Current beat position."""
        return self._current_beat
    
    @property
    def current_measure(self) -> int:
        """Current measure number (0-indexed)."""
        return int(self._current_beat // self.measure_beats)
    
    @property
    def beat_in_measure(self) -> float:
        """Current beat within the measure."""
        return self._current_beat % self.measure_beats
    
    def start(self):
        """Start the timing clock."""
        self._start_time = time.perf_counter()
        self._current_beat = 0.0
        self._last_tick_time = self._start_time
    
    def tick(self) -> float:
        """
        Update timing and return beats elapsed since last tick.
        
        Returns:
            Number of beats elapsed since last tick.
        """
        if self._start_time is None:
            self.start()
        
        current_time = time.perf_counter()
        elapsed_seconds = current_time - self._last_tick_time
        self._last_tick_time = current_time
        
        # Apply rubato
        effective_bpm = self._apply_rubato()
        
        # Calculate beats elapsed
        beats_elapsed = (elapsed_seconds * effective_bpm) / 60.0
        self._current_beat += beats_elapsed
        
        # Update rubato phase
        self._rubato_phase += beats_elapsed * 0.1
        if self._rubato_phase > math.pi:
            self._rubato_phase -= math.pi * 2
        
        return beats_elapsed
    
    def _apply_rubato(self) -> float:
        """Apply rubato to get effective tempo."""
        if self.rubato_amount == 0:
            return self.bpm
        
        # Sinusoidal rubato
        variation = math.sin(self._rubato_phase) * self.rubato_amount * 0.15
        return self.bpm * (1 + variation)
    
    def beats_to_seconds(self, beats: float) -> float:
        """
        Convert beats to seconds at current tempo.
        
        Args:
            beats: Number of beats.
            
        Returns:
            Duration in seconds.
        """
        return beats * self.beat_duration
    
    def seconds_to_beats(self, seconds: float) -> float:
        """
        Convert seconds to beats at current tempo.
        
        Args:
            seconds: Duration in seconds.
            
        Returns:
            Number of beats.
        """
        return seconds / self.beat_duration
    
    def apply_swing(self, beat_offset: float) -> float:
        """
        Apply swing to a beat offset.
        
        Args:
            beat_offset: Original beat offset.
            
        Returns:
            Swung beat offset.
        """
        if self.swing_amount == 0:
            return beat_offset
        
        # Swing affects off-beat eighth notes
        eighth_position = (beat_offset * 2) % 2
        if 0.4 < eighth_position < 0.6:
            # This is an off-beat - delay it
            swing_delay = 0.167 * self.swing_amount  # Max 1/6 beat delay
            return beat_offset + swing_delay
        
        return beat_offset
    
    def humanize(self, beat_offset: float, amount: float = 0.3) -> float:
        """
        Add human-like timing variation.
        
        Args:
            beat_offset: Original beat offset.
            amount: Amount of humanization (0-1).
            
        Returns:
            Humanized beat offset.
        """
        if amount == 0:
            return beat_offset
        
        # Gaussian timing variation
        variation = random.gauss(0, 0.02 * amount)
        return beat_offset + variation
    
    def schedule_tempo_change(self, target_bpm: float, in_beats: float, transition_beats: float = 4.0):
        """
        Schedule a tempo change.
        
        Args:
            target_bpm: Target tempo.
            in_beats: Beats from now when change should occur.
            transition_beats: Beats over which to transition.
        """
        event = TempoEvent(
            self._current_beat + in_beats,
            target_bpm,
            transition_beats
        )
        self._tempo_events.append(event)
        self._tempo_events.sort(key=lambda e: e.beat)
    
    def get_pattern(self, name: str) -> Optional[RhythmPattern]:
        """
        Get a named rhythm pattern.
        
        Args:
            name: Name of the pattern.
            
        Returns:
            The RhythmPattern or None if not found.
        """
        return self._patterns.get(name)
    
    def generate_pattern(
        self,
        length_beats: float = 4.0,
        complexity: float = 0.5,
    ) -> RhythmPattern:
        """
        Generate a random rhythm pattern.
        
        Args:
            length_beats: Total duration in beats.
            complexity: 0.0 = simple, 1.0 = complex.
            
        Returns:
            A new RhythmPattern.
        """
        durations = []
        accents = []
        total = 0.0
        
        # Available durations based on complexity
        if complexity < 0.3:
            available = [1.0, 2.0, 1.5]
        elif complexity < 0.7:
            available = [0.5, 1.0, 1.5, 0.75, 0.25]
        else:
            available = [0.25, 0.5, 0.75, 1.0, 1/3, 0.125]
        
        while total < length_beats:
            remaining = length_beats - total
            valid = [d for d in available if d <= remaining + 0.01]
            
            if not valid:
                if remaining > 0.1:
                    durations.append(remaining)
                    accents.append(0.5)
                break
            
            dur = random.choice(valid)
            durations.append(dur)
            
            # Accent on beat
            beat_pos = total % 1.0
            if beat_pos < 0.1:
                accent = 0.7 + random.random() * 0.3
            else:
                accent = 0.3 + random.random() * 0.4
            accents.append(accent)
            
            total += dur
        
        return RhythmPattern(durations, accents)
    
    def generate_varied_pattern(self, base_pattern: RhythmPattern) -> RhythmPattern:
        """
        Create a variation of an existing pattern.
        
        Args:
            base_pattern: Pattern to vary.
            
        Returns:
            A varied RhythmPattern.
        """
        new_durations = list(base_pattern.durations)
        new_accents = list(base_pattern.accents)
        
        # Apply random variations
        for i in range(len(new_durations)):
            if random.random() < 0.3:
                # Split or merge notes
                if random.random() < 0.5 and new_durations[i] >= 0.5:
                    # Split
                    half = new_durations[i] / 2
                    new_durations[i] = half
                    new_durations.insert(i + 1, half)
                    new_accents.insert(i + 1, new_accents[i] * 0.7)
                elif i < len(new_durations) - 1:
                    # Merge
                    new_durations[i] += new_durations[i + 1]
                    new_durations.pop(i + 1)
                    new_accents.pop(i + 1)
        
        # Vary accents
        for i in range(len(new_accents)):
            new_accents[i] += random.gauss(0, 0.1)
            new_accents[i] = max(0.1, min(1.0, new_accents[i]))
        
        return RhythmPattern(new_durations, new_accents)
    
    def wait_until_beat(self, target_beat: float) -> Generator[None, None, None]:
        """
        Generator that yields until target beat is reached.
        
        Args:
            target_beat: Beat to wait for.
            
        Yields:
            None while waiting.
        """
        while self._current_beat < target_beat:
            yield
            self.tick()
    
    def get_beat_strength(self, beat: Optional[float] = None) -> float:
        """
        Get the metric strength of a beat position.
        
        Args:
            beat: Beat position (uses current if None).
            
        Returns:
            Strength value from 0.0 (weak) to 1.0 (strong).
        """
        if beat is None:
            beat = self._current_beat
        
        beat_in_measure = beat % self.measure_beats
        
        # Downbeat is strongest
        if beat_in_measure < 0.1:
            return 1.0
        
        # In 4/4, beat 3 is also strong
        if self.time_signature == TimeSignature.FOUR_FOUR:
            if abs(beat_in_measure - 2) < 0.1:
                return 0.8
            if abs(beat_in_measure - 1) < 0.1 or abs(beat_in_measure - 3) < 0.1:
                return 0.6
        
        # In 3/4, beats 2 and 3 are equal
        if self.time_signature == TimeSignature.THREE_FOUR:
            if abs(beat_in_measure - 1) < 0.1 or abs(beat_in_measure - 2) < 0.1:
                return 0.5
        
        # Off-beats are weak
        return 0.3
    
    def set_tempo(self, bpm: float):
        """
        Set the current tempo immediately.
        
        Args:
            bpm: New tempo in beats per minute.
        """
        self.bpm = max(20, min(300, bpm))
        self._base_bpm = self.bpm
    
    def accelerando(self, target_bpm: float, over_beats: float):
        """
        Gradually increase tempo.
        
        Args:
            target_bpm: Target tempo.
            over_beats: Duration of the accelerando.
        """
        self.schedule_tempo_change(target_bpm, 0, over_beats)
    
    def ritardando(self, target_bpm: float, over_beats: float):
        """
        Gradually decrease tempo.
        
        Args:
            target_bpm: Target tempo.
            over_beats: Duration of the ritardando.
        """
        self.schedule_tempo_change(target_bpm, 0, over_beats)
    
    def fermata(self, duration_multiplier: float = 2.0):
        """
        Pause on the current beat (fermata effect).
        
        Args:
            duration_multiplier: How much to extend the pause.
        """
        # Temporarily reduce tempo for the pause effect
        original_bpm = self.bpm
        self.bpm = self.bpm / duration_multiplier
        self.schedule_tempo_change(original_bpm, 1.0, 0.5)
