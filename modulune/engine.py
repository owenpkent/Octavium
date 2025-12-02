"""
Main engine for Modulune.

The ModuluneEngine orchestrates harmony, melody, and rhythm generation
to produce continuously evolving impressionistic piano textures.
It streams MIDI events in real-time to a virtual MIDI port.
"""

import sys
import time
import random
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable
from pathlib import Path

# Add parent directory to path for app module access
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.midi_io import MidiOut, list_output_names

from .harmony import HarmonyEngine, Scale, ScaleType, Chord, ChordProgression
from .melody import MelodyEngine, Phrase, Note, ContourType
from .rhythm import RhythmEngine, TimeSignature, RhythmPattern


class EngineState(Enum):
    """Engine running states."""
    
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class TextureType(Enum):
    """Types of piano textures to generate (right hand / upper register)."""
    
    FLOWING_ARPEGGIOS = "flowing_arpeggios"
    MELODIC_FRAGMENTS = "melodic_fragments"
    SHIMMERING_CHORDS = "shimmering_chords"
    SPARSE_MEDITATION = "sparse_meditation"
    LAYERED_VOICES = "layered_voices"
    IMPRESSIONIST_WASH = "impressionist_wash"
    OFF = "off"


class LeftHandTexture(Enum):
    """Types of left hand / bass textures."""
    
    SUSTAINED_BASS = "sustained_bass"
    BROKEN_CHORDS = "broken_chords"
    ALBERTI_BASS = "alberti_bass"
    BLOCK_CHORDS = "block_chords"
    ROLLING_OCTAVES = "rolling_octaves"
    SPARSE_ROOTS = "sparse_roots"
    OFF = "off"


@dataclass
class EngineConfig:
    """
    Configuration for the Modulune engine.
    
    Attributes:
        tempo: Base tempo in BPM.
        key_root: MIDI note number for the key center (60 = C).
        scale_type: Scale/mode to use.
        time_signature: Time signature.
        tension: Harmonic tension (0.0 = consonant, 1.0 = dissonant).
        expressiveness: Expression amount (affects dynamics, timing).
        channel: MIDI channel (0-15).
        
        Right hand (upper register):
        rh_texture: Type of texture for right hand.
        rh_density: Note density for right hand.
        rh_register: (low, high) MIDI note range.
        rh_velocity: (min, max) velocity range.
        
        Left hand (lower register):
        lh_texture: Type of texture for left hand.
        lh_density: Note density for left hand.
        lh_register: (low, high) MIDI note range.
        lh_velocity: (min, max) velocity range.
    """
    
    tempo: float = 72.0
    key_root: int = 60  # C
    scale_type: ScaleType = ScaleType.MAJOR
    time_signature: TimeSignature = TimeSignature.FOUR_FOUR
    tension: float = 0.3
    expressiveness: float = 0.6
    channel: int = 0
    
    # Right hand settings
    rh_texture: TextureType = TextureType.SHIMMERING_CHORDS
    rh_density: float = 0.5
    rh_register: tuple[int, int] = (60, 96)  # C4 to C7
    rh_velocity: tuple[int, int] = (45, 85)
    
    # Left hand settings
    lh_texture: LeftHandTexture = LeftHandTexture.SUSTAINED_BASS
    lh_density: float = 0.4
    lh_register: tuple[int, int] = (36, 60)  # C2 to C4
    lh_velocity: tuple[int, int] = (50, 80)


@dataclass
class ScheduledEvent:
    """A MIDI event scheduled for future playback."""
    
    beat: float
    event_type: str  # "note_on", "note_off"
    note: int
    velocity: int = 80
    channel: int = 0


class ModuluneEngine:
    """
    The main generative engine for Modulune.
    
    Orchestrates harmony, melody, and rhythm generation to produce
    continuously evolving impressionistic piano textures. Streams
    MIDI events in real-time.
    
    Usage:
        >>> engine = ModuluneEngine()
        >>> engine.start()  # Begin generating
        >>> # ... music plays ...
        >>> engine.stop()   # Stop generating
    
    Attributes:
        config: Engine configuration.
        state: Current engine state.
        harmony: Harmony generation engine.
        melody: Melody generation engine.
        rhythm: Rhythm/timing engine.
    """
    
    def __init__(
        self,
        config: Optional[EngineConfig] = None,
        midi_port: Optional[str] = None,
    ):
        """
        Initialize the Modulune engine.
        
        Args:
            config: Engine configuration (uses defaults if None).
            midi_port: Name of MIDI port to use (auto-selects if None).
        """
        self.config = config or EngineConfig()
        self.state = EngineState.STOPPED
        
        # Initialize sub-engines
        self._init_engines()
        
        # MIDI output
        self._midi: Optional[MidiOut] = None
        self._midi_port_name = midi_port
        
        # Threading
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Event scheduling
        self._scheduled_events: list[ScheduledEvent] = []
        self._active_notes: set[tuple[int, int]] = set()  # (note, channel)
        
        # Generation state
        self._current_progression: Optional[ChordProgression] = None
        self._progression_index: int = 0
        self._chord_beat_counter: float = 0.0
        self._rh_phrase_counter: float = 0.0
        self._lh_pattern_counter: float = 0.0
        self._measures_until_modulation: int = 8
        
        # Callbacks
        self._on_chord_change: Optional[Callable[[Chord], None]] = None
        self._on_note: Optional[Callable[[int, int, bool], None]] = None
    
    def _init_engines(self):
        """Initialize the sub-engines with current config."""
        scale = Scale(self.config.key_root, self.config.scale_type)
        
        self.harmony = HarmonyEngine(
            root=self.config.key_root,
            scale_type=self.config.scale_type,
            tension_level=self.config.tension,
        )
        
        # Right hand melody engine (upper register)
        self.rh_melody = MelodyEngine(
            scale=scale,
            register_low=self.config.rh_register[0],
            register_high=self.config.rh_register[1],
            density=self.config.rh_density,
            expressiveness=self.config.expressiveness,
        )
        
        # Left hand melody engine (lower register)
        self.lh_melody = MelodyEngine(
            scale=scale,
            register_low=self.config.lh_register[0],
            register_high=self.config.lh_register[1],
            density=self.config.lh_density,
            expressiveness=self.config.expressiveness,
        )
        
        # Keep backward compat alias
        self.melody = self.rh_melody
        
        self.rhythm = RhythmEngine(
            bpm=self.config.tempo,
            time_signature=self.config.time_signature,
            rubato_amount=self.config.expressiveness * 0.5,
        )
    
    def start(self):
        """Start the generative engine."""
        if self.state == EngineState.PLAYING:
            return
        
        # Initialize MIDI
        if self._midi is None:
            self._midi = MidiOut(self._midi_port_name)
        
        self.state = EngineState.PLAYING
        self._stop_event.clear()
        
        # Generate initial progression
        self._current_progression = self.harmony.generate_progression(4)
        self._progression_index = 0
        
        # Start rhythm engine
        self.rhythm.start()
        
        # Start generation thread
        self._thread = threading.Thread(target=self._generation_loop, daemon=True)
        self._thread.start()
        
        print(f"Modulune started - Tempo: {self.config.tempo} BPM, "
              f"Key: {self._note_name(self.config.key_root)} {self.config.scale_type.value}")
    
    def stop(self):
        """Stop the generative engine."""
        if self.state == EngineState.STOPPED:
            return
        
        self._stop_event.set()
        self.state = EngineState.STOPPED
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        
        # Stop all active notes
        self._all_notes_off()
        
        print("Modulune stopped")
    
    def pause(self):
        """Pause generation (notes continue to ring)."""
        if self.state == EngineState.PLAYING:
            self.state = EngineState.PAUSED
            print("Modulune paused")
    
    def resume(self):
        """Resume generation after pause."""
        if self.state == EngineState.PAUSED:
            self.state = EngineState.PLAYING
            print("Modulune resumed")
    
    def _generation_loop(self):
        """Main generation loop running in separate thread."""
        last_time = time.perf_counter()
        
        while not self._stop_event.is_set():
            if self.state != EngineState.PLAYING:
                time.sleep(0.01)
                continue
            
            # Update timing
            current_time = time.perf_counter()
            delta_time = current_time - last_time
            last_time = current_time
            
            beats_elapsed = self.rhythm.tick()
            
            # Process scheduled events
            self._process_scheduled_events()
            
            # Update chord progression
            self._update_harmony(beats_elapsed)
            
            # Generate right hand (upper register)
            self._generate_right_hand(beats_elapsed)
            
            # Generate left hand (lower register)
            self._generate_left_hand(beats_elapsed)
            
            # Check for modulation
            self._check_modulation()
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.005)
    
    def _update_harmony(self, beats_elapsed: float):
        """Update chord progression timing."""
        self._chord_beat_counter += beats_elapsed
        
        if self._current_progression:
            chord_duration = self._current_progression.durations[self._progression_index]
            if self._chord_beat_counter >= chord_duration:
                self._chord_beat_counter = 0.0
                self._advance_chord()
    
    def _generate_right_hand(self, beats_elapsed: float):
        """Generate right hand textures based on selected type."""
        texture = self.config.rh_texture
        if texture == TextureType.OFF:
            return
        
        self._rh_phrase_counter += beats_elapsed
        current_chord = self._get_current_chord()
        
        if texture == TextureType.FLOWING_ARPEGGIOS:
            self._rh_arpeggios(current_chord)
        elif texture == TextureType.MELODIC_FRAGMENTS:
            self._rh_melodic(current_chord)
        elif texture == TextureType.SHIMMERING_CHORDS:
            self._rh_shimmering(current_chord)
        elif texture == TextureType.SPARSE_MEDITATION:
            self._rh_sparse(current_chord)
        elif texture == TextureType.LAYERED_VOICES:
            self._rh_layered(current_chord)
        else:  # IMPRESSIONIST_WASH
            self._rh_impressionist(current_chord)
    
    def _generate_left_hand(self, beats_elapsed: float):
        """Generate left hand textures based on selected type."""
        texture = self.config.lh_texture
        if texture == LeftHandTexture.OFF:
            return
        
        self._lh_pattern_counter += beats_elapsed
        current_chord = self._get_current_chord()
        
        if texture == LeftHandTexture.SUSTAINED_BASS:
            self._lh_sustained_bass(current_chord)
        elif texture == LeftHandTexture.BROKEN_CHORDS:
            self._lh_broken_chords(current_chord)
        elif texture == LeftHandTexture.ALBERTI_BASS:
            self._lh_alberti(current_chord)
        elif texture == LeftHandTexture.BLOCK_CHORDS:
            self._lh_block_chords(current_chord)
        elif texture == LeftHandTexture.ROLLING_OCTAVES:
            self._lh_rolling_octaves(current_chord)
        else:  # SPARSE_ROOTS
            self._lh_sparse_roots(current_chord)
    
    # =========================================================================
    # RIGHT HAND TEXTURES
    # =========================================================================
    
    def _rh_arpeggios(self, chord: Chord):
        """Right hand flowing arpeggios."""
        if random.random() < 0.04 * self.config.rh_density:
            patterns = ["up", "down", "up_down", "random"]
            pattern = random.choice(patterns)
            length = random.choice([1.0, 2.0, 2.0, 3.0])
            phrase = self.rh_melody.generate_arpeggio(chord, length, pattern)
            self._schedule_phrase(phrase, velocity_range=self.config.rh_velocity)
    
    def _rh_melodic(self, chord: Chord):
        """Right hand melodic fragments."""
        if self._rh_phrase_counter >= 4.0:
            self._rh_phrase_counter = 0.0
            length = random.choice([2.0, 3.0, 4.0, 4.0, 6.0])
            contour = random.choice(list(ContourType))
            if random.random() < 0.3:
                phrase = self.rh_melody.develop_motif()
            else:
                phrase = self.rh_melody.generate_phrase(length, contour, chord)
            self._schedule_phrase(phrase, velocity_range=self.config.rh_velocity)
    
    def _rh_shimmering(self, chord: Chord):
        """Right hand shimmering chords with sparkle notes."""
        # Schedule chord pad on chord change
        if self._chord_beat_counter < 0.1:
            voicing = chord.get_voicing(
                self.config.rh_register[0], 
                self.config.rh_register[1], 
                spread=True
            )
            velocity_base = random.randint(
                self.config.rh_velocity[0], 
                self.config.rh_velocity[0] + 15
            )
            duration = random.uniform(4.0, 8.0)
            for i, note in enumerate(voicing):
                vel = velocity_base + random.randint(-5, 5)
                delay = i * 0.02 + random.gauss(0, 0.01)
                self._schedule_note(note, vel, duration, delay)
        
        # Occasional sparkle notes
        if random.random() < 0.02 * self.config.rh_density:
            voicing = chord.get_voicing(
                self.config.rh_register[0] + 12,
                self.config.rh_register[1]
            )
            if voicing:
                note = random.choice(voicing)
                velocity = random.randint(30, 50)
                self._schedule_note(note, velocity, random.uniform(0.3, 0.8))
    
    def _rh_sparse(self, chord: Chord):
        """Right hand sparse meditation."""
        if random.random() < 0.005 * self.config.rh_density:
            voicing = chord.get_voicing(
                self.config.rh_register[0],
                self.config.rh_register[1]
            )
            if voicing:
                note = random.choice(voicing)
                velocity = random.randint(35, 60)
                duration = random.uniform(2.0, 6.0)
                self._schedule_note(note, velocity, duration)
    
    def _rh_layered(self, chord: Chord):
        """Right hand layered voices."""
        if self._rh_phrase_counter >= 3.0:
            self._rh_phrase_counter = 0.0
            phrase = self.rh_melody.generate_phrase(3.0, chord=chord)
            self._schedule_phrase(phrase, velocity_range=self.config.rh_velocity)
    
    def _rh_impressionist(self, chord: Chord):
        """Right hand impressionist wash - combination of textures."""
        # Arpeggios
        if random.random() < 0.02 * self.config.rh_density:
            patterns = ["up", "down", "up_down"]
            phrase = self.rh_melody.generate_arpeggio(
                chord, random.choice([1.0, 2.0]), random.choice(patterns)
            )
            self._schedule_phrase(phrase, velocity_range=self.config.rh_velocity)
        
        # Melodic phrases
        if self._rh_phrase_counter >= 2.0 + random.random() * 4.0:
            self._rh_phrase_counter = 0.0
            if random.random() < 0.6:
                length = random.choice([2.0, 3.0, 4.0])
                phrase = self.rh_melody.generate_phrase(length, chord=chord)
                self._schedule_phrase(phrase, velocity_range=self.config.rh_velocity)
    
    # =========================================================================
    # LEFT HAND TEXTURES
    # =========================================================================
    
    def _lh_sustained_bass(self, chord: Chord):
        """Left hand sustained bass notes."""
        if self._chord_beat_counter < 0.1:  # On chord change
            bass = chord.root + 36
            while bass < self.config.lh_register[0]:
                bass += 12
            while bass > self.config.lh_register[0] + 12:
                bass -= 12
            
            velocity = random.randint(
                self.config.lh_velocity[0],
                self.config.lh_velocity[1]
            )
            duration = random.uniform(3.0, 6.0)
            self._schedule_note(bass, velocity, duration)
            
            # Occasionally add fifth
            if random.random() < 0.4:
                fifth = bass + 7
                if fifth <= self.config.lh_register[1]:
                    self._schedule_note(fifth, velocity - 10, duration, 0.05)
    
    def _lh_broken_chords(self, chord: Chord):
        """Left hand broken chord patterns."""
        if random.random() < 0.03 * self.config.lh_density:
            voicing = chord.get_voicing(
                self.config.lh_register[0],
                self.config.lh_register[1],
                spread=False
            )
            if len(voicing) >= 2:
                phrase = self.lh_melody.generate_accompaniment_figure(
                    chord, 2.0, "broken"
                )
                self._schedule_phrase(phrase, velocity_range=self.config.lh_velocity)
    
    def _lh_alberti(self, chord: Chord):
        """Left hand Alberti bass pattern."""
        if self._lh_pattern_counter >= 2.0:
            self._lh_pattern_counter = 0.0
            phrase = self.lh_melody.generate_accompaniment_figure(
                chord, 2.0, "alberti"
            )
            self._schedule_phrase(phrase, velocity_range=self.config.lh_velocity)
    
    def _lh_block_chords(self, chord: Chord):
        """Left hand block chord accompaniment."""
        if self._chord_beat_counter < 0.1:  # On chord change
            voicing = chord.get_voicing(
                self.config.lh_register[0],
                self.config.lh_register[1],
                spread=False
            )
            velocity_base = random.randint(
                self.config.lh_velocity[0],
                self.config.lh_velocity[0] + 15
            )
            duration = random.uniform(2.0, 4.0)
            
            for i, note in enumerate(voicing[:4]):  # Limit to 4 notes
                vel = velocity_base + random.randint(-5, 5)
                delay = i * 0.015
                self._schedule_note(note, vel, duration, delay)
    
    def _lh_rolling_octaves(self, chord: Chord):
        """Left hand rolling octave bass."""
        if random.random() < 0.02 * self.config.lh_density:
            bass = chord.root + 36
            while bass < self.config.lh_register[0]:
                bass += 12
            while bass > self.config.lh_register[0] + 12:
                bass -= 12
            
            velocity = random.randint(
                self.config.lh_velocity[0],
                self.config.lh_velocity[1]
            )
            
            # Lower octave
            self._schedule_note(bass, velocity, 0.4, 0.0)
            # Upper octave
            if bass + 12 <= self.config.lh_register[1]:
                self._schedule_note(bass + 12, velocity - 5, 0.4, 0.15)
    
    def _lh_sparse_roots(self, chord: Chord):
        """Left hand very sparse root notes."""
        if random.random() < 0.008 * self.config.lh_density:
            bass = chord.root + 36
            while bass < self.config.lh_register[0]:
                bass += 12
            while bass > self.config.lh_register[1]:
                bass -= 12
            
            velocity = random.randint(45, 65)
            duration = random.uniform(3.0, 8.0)
            self._schedule_note(bass, velocity, duration)
    
    # =========================================================================
    # SCHEDULING
    # =========================================================================
    
    def _schedule_phrase(
        self,
        phrase: Phrase,
        velocity_offset: int = 0,
        velocity_range: Optional[tuple[int, int]] = None,
    ):
        """Schedule all notes in a phrase."""
        beat_offset = 0.0
        for note in phrase.notes:
            velocity = max(1, min(127, note.velocity + velocity_offset))
            # Clamp to velocity range if provided
            if velocity_range:
                velocity = max(velocity_range[0], min(velocity_range[1], velocity))
            delay = beat_offset + note.delay
            self._schedule_note(note.pitch, velocity, note.duration, delay)
            beat_offset += note.duration
    
    def _schedule_note(
        self,
        note: int,
        velocity: int,
        duration: float,
        delay: float = 0.0,
    ):
        """Schedule a single note."""
        current_beat = self.rhythm.current_beat
        
        # Apply humanization
        delay = self.rhythm.humanize(delay, self.config.expressiveness)
        
        # Clamp velocity to valid MIDI range
        velocity = max(1, min(127, velocity))
        
        on_beat = current_beat + delay
        off_beat = on_beat + duration
        
        self._scheduled_events.append(ScheduledEvent(
            on_beat, "note_on", note, velocity, self.config.channel
        ))
        self._scheduled_events.append(ScheduledEvent(
            off_beat, "note_off", note, 0, self.config.channel
        ))
        
        # Keep events sorted
        self._scheduled_events.sort(key=lambda e: e.beat)
    
    def _process_scheduled_events(self):
        """Process any scheduled events that are due."""
        current_beat = self.rhythm.current_beat
        
        while self._scheduled_events and self._scheduled_events[0].beat <= current_beat:
            event = self._scheduled_events.pop(0)
            
            if event.event_type == "note_on":
                self._note_on(event.note, event.velocity, event.channel)
            elif event.event_type == "note_off":
                self._note_off(event.note, event.channel)
    
    def _note_on(self, note: int, velocity: int, channel: int):
        """Send note on and track active note."""
        if self._midi:
            self._midi.note_on(note, velocity, channel)
            self._active_notes.add((note, channel))
            if self._on_note:
                self._on_note(note, velocity, True)
    
    def _note_off(self, note: int, channel: int):
        """Send note off and untrack active note."""
        if self._midi:
            self._midi.note_off(note, channel)
            self._active_notes.discard((note, channel))
            if self._on_note:
                self._on_note(note, 0, False)
    
    def _all_notes_off(self):
        """Turn off all active notes."""
        for note, channel in list(self._active_notes):
            self._note_off(note, channel)
        self._active_notes.clear()
        self._scheduled_events.clear()
    
    def _get_current_chord(self) -> Chord:
        """Get the current chord from the progression."""
        if self._current_progression and self._progression_index < len(self._current_progression):
            return self._current_progression[self._progression_index]
        return Chord(self.config.key_root % 12)
    
    def _advance_chord(self):
        """Advance to the next chord in the progression."""
        if not self._current_progression:
            return
        
        self._progression_index += 1
        
        if self._progression_index >= len(self._current_progression):
            # Generate new progression
            self._current_progression = self.harmony.generate_progression(
                random.choice([3, 4, 4, 4, 5, 6])
            )
            self._progression_index = 0
            self._measures_until_modulation -= 1
        
        chord = self._get_current_chord()
        if self._on_chord_change:
            self._on_chord_change(chord)
    
    def _check_modulation(self):
        """Check if it's time to modulate to a new key."""
        if self._measures_until_modulation <= 0:
            new_root, new_mode = self.harmony.suggest_modulation()
            self.harmony.modulate(new_root, new_mode)
            new_scale = Scale(new_root, new_mode)
            self.rh_melody.scale = new_scale
            self.lh_melody.scale = new_scale
            self._measures_until_modulation = random.randint(6, 12)
            print(f"Modulating to {self._note_name(new_root)} {new_mode.value}")
    
    def _note_name(self, midi_note: int) -> str:
        """Convert MIDI note to note name."""
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        return names[midi_note % 12]
    
    # Public configuration methods
    
    def set_tempo(self, bpm: float):
        """
        Set the engine tempo.
        
        Args:
            bpm: Tempo in beats per minute.
        """
        self.config.tempo = bpm
        self.rhythm.set_tempo(bpm)
    
    def set_key(self, root: int, scale_type: Optional[ScaleType] = None):
        """
        Set the key center.
        
        Args:
            root: Root note (MIDI number, 60 = C).
            scale_type: Scale type (keeps current if None).
        """
        self.config.key_root = root
        if scale_type:
            self.config.scale_type = scale_type
        
        self.harmony.modulate(root, scale_type)
        new_scale = Scale(root, scale_type or self.config.scale_type)
        self.rh_melody.scale = new_scale
        self.lh_melody.scale = new_scale
    
    def set_rh_density(self, density: float):
        """
        Set right hand note density.
        
        Args:
            density: 0.0 (sparse) to 1.0 (dense).
        """
        self.config.rh_density = max(0.0, min(1.0, density))
        self.rh_melody.density = self.config.rh_density
    
    def set_lh_density(self, density: float):
        """
        Set left hand note density.
        
        Args:
            density: 0.0 (sparse) to 1.0 (dense).
        """
        self.config.lh_density = max(0.0, min(1.0, density))
        self.lh_melody.density = self.config.lh_density
    
    def set_tension(self, tension: float):
        """
        Set harmonic tension.
        
        Args:
            tension: 0.0 (consonant) to 1.0 (dissonant).
        """
        self.config.tension = max(0.0, min(1.0, tension))
        self.harmony.tension_level = self.config.tension
    
    def set_rh_texture(self, texture: TextureType):
        """
        Set the right hand texture type.
        
        Args:
            texture: Type of texture to generate.
        """
        self.config.rh_texture = texture
    
    def set_lh_texture(self, texture: LeftHandTexture):
        """
        Set the left hand texture type.
        
        Args:
            texture: Type of left hand texture to generate.
        """
        self.config.lh_texture = texture
    
    def set_expressiveness(self, expressiveness: float):
        """
        Set expressiveness level.
        
        Args:
            expressiveness: 0.0 (mechanical) to 1.0 (very expressive).
        """
        self.config.expressiveness = max(0.0, min(1.0, expressiveness))
        self.rh_melody.expressiveness = self.config.expressiveness
        self.lh_melody.expressiveness = self.config.expressiveness
        self.rhythm.rubato_amount = self.config.expressiveness * 0.5
    
    def on_chord_change(self, callback: Callable[[Chord], None]):
        """
        Register a callback for chord changes.
        
        Args:
            callback: Function called with new Chord on change.
        """
        self._on_chord_change = callback
    
    def on_note(self, callback: Callable[[int, int, bool], None]):
        """
        Register a callback for note events.
        
        Args:
            callback: Function called with (note, velocity, is_on).
        """
        self._on_note = callback
    
    @staticmethod
    def list_midi_ports() -> list[str]:
        """
        List available MIDI output ports.
        
        Returns:
            List of port names.
        """
        return list_output_names()
