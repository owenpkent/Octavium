"""Tests for modulune.harmony — scales, chords, and harmonic progression engine."""

import pytest
from modulune.harmony import (
    Scale, ScaleType, SCALE_INTERVALS,
    Chord, ChordQuality, CHORD_INTERVALS,
    ChordProgression, HarmonyEngine,
)


class TestScaleIntervals:
    def test_major_scale(self):
        assert SCALE_INTERVALS[ScaleType.MAJOR] == (0, 2, 4, 5, 7, 9, 11)

    def test_all_scales_start_at_zero(self):
        for scale_type, intervals in SCALE_INTERVALS.items():
            assert intervals[0] == 0, f"{scale_type} should start at 0"

    def test_all_intervals_within_octave(self):
        for scale_type, intervals in SCALE_INTERVALS.items():
            assert all(0 <= i < 12 for i in intervals), f"{scale_type} has out-of-range interval"

    def test_intervals_are_ascending(self):
        for scale_type, intervals in SCALE_INTERVALS.items():
            assert intervals == tuple(sorted(intervals)), f"{scale_type} not ascending"


class TestScale:
    def test_get_notes_in_range(self):
        s = Scale(60, ScaleType.MAJOR)  # C4 major
        notes = s.get_notes_in_range(60, 72)
        assert 60 in notes
        assert all(60 <= n <= 72 for n in notes)

    def test_quantize_in_scale(self):
        s = Scale(60, ScaleType.MAJOR)
        assert s.quantize(60) == 60  # C is in C major

    def test_quantize_outside_scale(self):
        s = Scale(60, ScaleType.MAJOR)
        result = s.quantize(61)  # C# not in C major
        # Should snap to C (60) or D (62)
        assert result in (60, 62)

    def test_degree_to_note_root(self):
        s = Scale(0, ScaleType.MAJOR)  # C major, root = C0
        # Degree 1 in octave 4 should give C4-ish
        note = s.degree_to_note(1, octave=4)
        assert note % 12 == 0  # Should be a C

    def test_degree_to_note_fifth(self):
        s = Scale(0, ScaleType.MAJOR)
        note = s.degree_to_note(5, octave=4)
        assert note % 12 == 7  # G

    def test_whole_tone_has_6_notes(self):
        s = Scale(60, ScaleType.WHOLE_TONE)
        assert len(s.intervals) == 6


class TestChord:
    def test_major_triad_notes(self):
        c = Chord(0, ChordQuality.MAJOR)
        notes = c.get_notes(base_octave=4)
        intervals = [n - notes[0] for n in notes]
        assert intervals == [0, 4, 7]

    def test_minor_triad_notes(self):
        c = Chord(0, ChordQuality.MINOR)
        notes = c.get_notes(base_octave=4)
        intervals = [n - notes[0] for n in notes]
        assert intervals == [0, 3, 7]

    def test_first_inversion(self):
        c = Chord(0, ChordQuality.MAJOR, inversion=1)
        notes = c.get_notes(base_octave=4)
        # First inversion: E should be lowest
        assert notes[0] % 12 == 4  # E

    def test_get_voicing_within_range(self):
        c = Chord(0, ChordQuality.MAJOR_7)
        voicing = c.get_voicing(low=48, high=84, spread=False)
        assert all(48 <= n <= 84 for n in voicing)

    def test_all_chord_qualities_have_intervals(self):
        for quality in ChordQuality:
            assert quality in CHORD_INTERVALS


class TestChordProgression:
    def test_default_durations(self):
        chords = [Chord(0), Chord(5), Chord(7), Chord(0)]
        prog = ChordProgression(chords)
        assert prog.durations == [4.0, 4.0, 4.0, 4.0]

    def test_total_beats(self):
        chords = [Chord(0), Chord(5)]
        prog = ChordProgression(chords, durations=[4.0, 8.0])
        assert prog.total_beats() == 12.0

    def test_len(self):
        chords = [Chord(0), Chord(5), Chord(7)]
        prog = ChordProgression(chords)
        assert len(prog) == 3

    def test_getitem(self):
        c = Chord(5, ChordQuality.MINOR)
        prog = ChordProgression([Chord(0), c])
        assert prog[1] is c


class TestHarmonyEngine:
    def test_generate_progression_length(self):
        engine = HarmonyEngine(root=60)
        prog = engine.generate_progression(length=4)
        assert len(prog) == 4

    def test_get_next_chord_returns_chord(self):
        engine = HarmonyEngine()
        chord = engine.get_next_chord()
        assert isinstance(chord, Chord)

    def test_get_next_chord_first_is_tonic(self):
        engine = HarmonyEngine(root=60)
        chord = engine.get_next_chord()
        assert chord.root == 60 % 12

    def test_modulate_changes_scale(self):
        engine = HarmonyEngine(root=60, scale_type=ScaleType.MAJOR)
        engine.modulate(new_root=65)
        assert engine.current_scale.root == 65

    def test_modulate_changes_mode(self):
        engine = HarmonyEngine(root=60, scale_type=ScaleType.MAJOR)
        engine.modulate(new_mode=ScaleType.DORIAN)
        assert engine.current_scale.scale_type == ScaleType.DORIAN

    def test_suggest_modulation_returns_valid(self):
        engine = HarmonyEngine()
        root, mode = engine.suggest_modulation()
        assert 0 <= root < 128
        assert isinstance(mode, ScaleType)
