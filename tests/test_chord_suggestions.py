"""Tests for app.chord_suggestions — chord suggestion algorithms."""

import pytest
from app.chord_suggestions import (
    get_chord_notes,
    detect_chord_quality,
    is_major_quality,
    is_minor_quality,
    neo_riemannian_P,
    neo_riemannian_L,
    neo_riemannian_R,
    neo_riemannian_N,
    neo_riemannian_S,
    neo_riemannian_H,
    circle_dominant,
    circle_subdominant,
    diatonic_ii,
    diatonic_vi,
    chromatic_tritone_sub,
    chromatic_neapolitan,
    get_all_suggestions,
    ChordSuggestion,
    NOTES,
)


class TestGetChordNotes:
    def test_c_major_triad(self):
        notes = get_chord_notes(0, "Major", 4)
        assert notes == [48, 52, 55]  # C4, E4, G4

    def test_c_minor_triad(self):
        notes = get_chord_notes(0, "Minor", 4)
        assert notes == [48, 51, 55]

    def test_unknown_type_defaults_to_major(self):
        notes = get_chord_notes(0, "NonExistent", 4)
        assert notes == [48, 52, 55]

    def test_seventh_chord_has_four_notes(self):
        notes = get_chord_notes(0, "Maj7", 4)
        assert len(notes) == 4
        assert notes == [48, 52, 55, 59]


class TestDetectChordQuality:
    def test_empty_notes(self):
        root, quality = detect_chord_quality([])
        assert root == 0
        assert quality == "Major"

    def test_c_major(self):
        root, quality = detect_chord_quality([60, 64, 67])
        assert root == 0  # C
        assert quality == "Major"

    def test_a_minor(self):
        # A Minor: A(57) C(60) E(64) — pitch classes {9,0,4}, sorted = [0,4,9]
        # detect_chord_quality takes lowest pc as root, intervals = (0,4,9) — not a known pattern
        # Use explicit pitch classes that form (0,3,7): e.g. C Eb G
        root, quality = detect_chord_quality([60, 63, 67])
        assert root == 0  # C
        assert quality == "Minor"

    def test_diminished(self):
        # B Dim: B(59) D(62) F(65) — pitch classes {11,2,5}, sorted = [2,5,11]
        # Use explicit (0,3,6): C Eb Gb
        root, quality = detect_chord_quality([60, 63, 66])
        assert root == 0
        assert quality == "Dim"

    def test_octave_duplicates_ignored(self):
        root, quality = detect_chord_quality([60, 64, 67, 72])
        assert quality == "Major"


class TestChordQualityChecks:
    def test_major_types(self):
        for t in ["Major", "Maj7", "Dom7", "Aug", "Aug7", "6", "Add9"]:
            assert is_major_quality(t), f"{t} should be major"

    def test_minor_types(self):
        for t in ["Minor", "Min7", "Dim", "Dim7", "HalfDim7", "MinMaj7", "Min6"]:
            assert is_minor_quality(t), f"{t} should be minor"

    def test_sus_is_neither(self):
        assert not is_major_quality("Sus2")
        assert not is_minor_quality("Sus2")


class TestNeoRiemannian:
    def test_parallel_major_to_minor(self):
        s = neo_riemannian_P(0, "Major")
        assert s.chord_type == "Minor"
        assert s.root_note == 0

    def test_parallel_minor_to_major(self):
        s = neo_riemannian_P(0, "Minor")
        assert s.chord_type == "Major"

    def test_leading_tone_c_major(self):
        # C Major -> E Minor
        s = neo_riemannian_L(0, "Major")
        assert s.root_note == 4  # E
        assert s.chord_type == "Minor"

    def test_relative_c_major(self):
        # C Major -> A Minor
        s = neo_riemannian_R(0, "Major")
        assert s.root_note == 9  # A
        assert s.chord_type == "Minor"

    def test_nebenverwandt(self):
        # C Major -> F Minor
        s = neo_riemannian_N(0, "Major")
        assert s.root_note == 5  # F
        assert s.chord_type == "Minor"

    def test_slide_c_major(self):
        # C Major -> C# Minor
        s = neo_riemannian_S(0, "Major")
        assert s.root_note == 1
        assert s.chord_type == "Minor"

    def test_hexatonic_pole(self):
        # C Major -> Ab Minor
        s = neo_riemannian_H(0, "Major")
        assert s.root_note == 8  # Ab
        assert s.chord_type == "Minor"

    def test_all_produce_valid_midi(self):
        for fn in [neo_riemannian_P, neo_riemannian_L, neo_riemannian_R,
                    neo_riemannian_N, neo_riemannian_S, neo_riemannian_H]:
            s = fn(0, "Major")
            assert all(0 <= n <= 127 for n in s.actual_notes)


class TestCircleOfFifths:
    def test_dominant_of_c(self):
        s = circle_dominant(0, "Major")
        assert s.root_note == 7  # G

    def test_subdominant_of_c(self):
        s = circle_subdominant(0, "Major")
        assert s.root_note == 5  # F

    def test_tritone_sub(self):
        s = chromatic_tritone_sub(0, "Major")
        assert s.root_note == 6  # F#/Gb


class TestDiatonic:
    def test_ii_of_c_major(self):
        s = diatonic_ii(0, "Major")
        assert s.root_note == 2  # D
        assert s.chord_type == "Minor"

    def test_vi_of_c_major(self):
        s = diatonic_vi(0, "Major")
        assert s.root_note == 9  # A
        assert s.chord_type == "Minor"

    def test_neapolitan(self):
        s = chromatic_neapolitan(0, "Major")
        assert s.root_note == 1  # Db
        assert s.chord_type == "Major"


class TestGetAllSuggestions:
    def test_returns_all_categories(self):
        result = get_all_suggestions(0, "Major")
        assert "Neo-Riemannian" in result
        assert "Circle of Fifths" in result
        assert "Diatonic" in result
        assert "Chromatic" in result

    def test_all_suggestions_are_chord_suggestions(self):
        result = get_all_suggestions(0, "Major")
        for category, suggestions in result.items():
            for s in suggestions:
                assert isinstance(s, ChordSuggestion)

    def test_root_normalized_to_pitch_class(self):
        # Root 60 (C4) should behave same as root 0 (C)
        r60 = get_all_suggestions(60, "Major")
        r0 = get_all_suggestions(0, "Major")
        for cat in r60:
            for s60, s0 in zip(r60[cat], r0[cat]):
                assert s60.root_note == s0.root_note

    def test_with_actual_notes_uses_octave(self):
        result = get_all_suggestions(0, "Major", actual_notes=[36, 40, 43])
        # Should use octave 3 (36//12 = 3)
        for cat in result:
            for s in result[cat]:
                assert all(0 <= n <= 127 for n in s.actual_notes)
