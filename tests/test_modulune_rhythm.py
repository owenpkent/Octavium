"""Tests for modulune.rhythm — timing, tempo, and rhythm pattern generation."""

import pytest
from modulune.rhythm import (
    RhythmEngine, RhythmPattern, TimeSignature, TempoEvent,
)


class TestRhythmPattern:
    def test_default_accents(self):
        p = RhythmPattern(durations=[1.0, 1.0, 1.0])
        assert p.accents == [0.5, 0.5, 0.5]

    def test_total_beats(self):
        p = RhythmPattern(durations=[1.0, 0.5, 1.5])
        assert p.total_beats() == 3.0

    def test_len(self):
        p = RhythmPattern(durations=[0.5, 0.5, 1.0, 1.0])
        assert len(p) == 4


class TestRhythmEngine:
    def test_beat_duration(self):
        engine = RhythmEngine(bpm=120)
        assert engine.beat_duration == 0.5  # 60/120

    def test_measure_beats_4_4(self):
        engine = RhythmEngine(time_signature=TimeSignature.FOUR_FOUR)
        assert engine.measure_beats == 4

    def test_measure_beats_3_4(self):
        engine = RhythmEngine(time_signature=TimeSignature.THREE_FOUR)
        assert engine.measure_beats == 3

    def test_beats_to_seconds(self):
        engine = RhythmEngine(bpm=60)
        assert engine.beats_to_seconds(4) == 4.0

    def test_seconds_to_beats(self):
        engine = RhythmEngine(bpm=120)
        assert engine.seconds_to_beats(1.0) == 2.0

    def test_apply_swing_no_swing(self):
        engine = RhythmEngine(swing_amount=0)
        assert engine.apply_swing(1.0) == 1.0

    def test_humanize_no_amount(self):
        engine = RhythmEngine()
        assert engine.humanize(1.0, amount=0) == 1.0

    def test_set_tempo_clamped(self):
        engine = RhythmEngine()
        engine.set_tempo(500)
        assert engine.bpm == 300
        engine.set_tempo(5)
        assert engine.bpm == 20

    def test_get_pattern_exists(self):
        engine = RhythmEngine()
        p = engine.get_pattern("flowing_eighth")
        assert p is not None
        assert len(p) == 8

    def test_get_pattern_missing(self):
        engine = RhythmEngine()
        assert engine.get_pattern("nonexistent") is None

    def test_generate_pattern(self):
        engine = RhythmEngine()
        pattern = engine.generate_pattern(length_beats=4.0, complexity=0.5)
        assert isinstance(pattern, RhythmPattern)
        assert abs(pattern.total_beats() - 4.0) < 0.01

    def test_generate_varied_pattern(self):
        engine = RhythmEngine()
        base = RhythmPattern([1.0, 1.0, 1.0, 1.0])
        varied = engine.generate_varied_pattern(base)
        assert isinstance(varied, RhythmPattern)

    def test_beat_strength_downbeat(self):
        engine = RhythmEngine(time_signature=TimeSignature.FOUR_FOUR)
        assert engine.get_beat_strength(0.0) == 1.0

    def test_beat_strength_weak(self):
        engine = RhythmEngine(time_signature=TimeSignature.FOUR_FOUR)
        # Off-beat position
        assert engine.get_beat_strength(0.5) == 0.3

    def test_fermata_reduces_tempo(self):
        engine = RhythmEngine(bpm=120)
        original = engine.bpm
        engine.fermata(duration_multiplier=2.0)
        assert engine.bpm == original / 2.0

    def test_rubato_off(self):
        engine = RhythmEngine(bpm=100, rubato_amount=0)
        assert engine._apply_rubato() == 100
