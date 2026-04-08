"""Tests for modulune.melody — phrase generation and melodic transformations."""

import pytest
from modulune.melody import (
    Note, Phrase, ContourType, ArticulationType, MelodyEngine,
)
from modulune.harmony import Scale, ScaleType, Chord, ChordQuality


class TestNote:
    def test_pitch_clamped_to_midi_range(self):
        n = Note(pitch=200, duration=1.0)
        assert n.pitch == 127

    def test_pitch_clamped_lower(self):
        n = Note(pitch=-5, duration=1.0)
        assert n.pitch == 0

    def test_velocity_clamped(self):
        n = Note(pitch=60, duration=1.0, velocity=200)
        assert n.velocity == 127
        n2 = Note(pitch=60, duration=1.0, velocity=0)
        assert n2.velocity == 1


class TestPhrase:
    def test_empty_phrase(self):
        p = Phrase()
        assert len(p) == 0
        assert p.total_duration() == 0.0

    def test_total_duration(self):
        notes = [Note(60, 1.0), Note(62, 0.5), Note(64, 1.5)]
        p = Phrase(notes)
        assert p.total_duration() == 3.0

    def test_transpose(self):
        notes = [Note(60, 1.0), Note(64, 1.0)]
        p = Phrase(notes)
        transposed = p.transpose(7)
        assert transposed.notes[0].pitch == 67
        assert transposed.notes[1].pitch == 71
        # Original unchanged
        assert p.notes[0].pitch == 60

    def test_transpose_preserves_duration(self):
        notes = [Note(60, 1.5, velocity=80)]
        p = Phrase(notes)
        t = p.transpose(5)
        assert t.notes[0].duration == 1.5
        assert t.notes[0].velocity == 80


class TestMelodyEngine:
    def test_generate_phrase_returns_phrase(self):
        engine = MelodyEngine()
        phrase = engine.generate_phrase(length_beats=4.0)
        assert isinstance(phrase, Phrase)
        assert len(phrase) > 0

    def test_generate_phrase_with_contour(self):
        engine = MelodyEngine()
        phrase = engine.generate_phrase(length_beats=4.0, contour=ContourType.ASCENDING)
        assert isinstance(phrase, Phrase)

    def test_generate_phrase_with_chord(self):
        engine = MelodyEngine()
        chord = Chord(0, ChordQuality.MAJOR_7)
        phrase = engine.generate_phrase(length_beats=4.0, chord=chord)
        assert len(phrase) > 0

    def test_notes_within_register(self):
        engine = MelodyEngine(register_low=60, register_high=72)
        phrase = engine.generate_phrase(length_beats=4.0)
        for note in phrase.notes:
            # Allow +-1 for chromatic neighbors
            assert 59 <= note.pitch <= 73

    def test_generate_arpeggio(self):
        engine = MelodyEngine()
        chord = Chord(0, ChordQuality.MAJOR)
        arp = engine.generate_arpeggio(chord, pattern="up")
        assert len(arp) > 0

    def test_arpeggio_up_is_ascending(self):
        engine = MelodyEngine(register_low=48, register_high=84)
        chord = Chord(0, ChordQuality.MAJOR)
        arp = engine.generate_arpeggio(chord, pattern="up")
        pitches = [n.pitch for n in arp.notes]
        assert pitches == sorted(pitches)

    def test_develop_motif_no_stored(self):
        engine = MelodyEngine()
        # With no stored motifs, should generate a new phrase
        result = engine.develop_motif()
        assert isinstance(result, Phrase)

    def test_develop_motif_from_phrase(self):
        engine = MelodyEngine()
        motif = Phrase([Note(60, 1.0), Note(64, 1.0), Note(67, 1.0)])
        result = engine.develop_motif(motif)
        assert isinstance(result, Phrase)
        assert len(result) > 0
