"""Tests for app.scale — scale quantization logic."""

import pytest
from app.scale import SCALES, quantize


class TestScalesData:
    def test_chromatic_has_12_notes(self):
        assert SCALES["chromatic"] == list(range(12))

    def test_major_intervals(self):
        assert SCALES["major"] == [0, 2, 4, 5, 7, 9, 11]

    def test_minor_intervals(self):
        assert SCALES["minor"] == [0, 2, 3, 5, 7, 8, 10]

    def test_pentatonic_intervals(self):
        assert SCALES["pentatonic"] == [0, 2, 4, 7, 9]


class TestQuantize:
    def test_chromatic_returns_same_note(self):
        for note in range(128):
            assert quantize(note, "chromatic") == note

    def test_note_in_scale_unchanged(self):
        # C4 (60) is in C major (pc=0)
        assert quantize(60, "major") == 60
        # D4 (62) pc=2 is in major
        assert quantize(62, "major") == 62

    def test_note_outside_scale_snaps(self):
        # C#4 (61) pc=1 is NOT in C major, should snap to C4 (60) or D4 (62)
        result = quantize(61, "major")
        assert result in (60, 62)

    def test_quantize_respects_midi_bounds(self):
        result = quantize(0, "major")
        assert 0 <= result <= 127
        result = quantize(127, "major")
        assert 0 <= result <= 127

    def test_custom_scale(self):
        custom = [0, 3, 7]  # minor triad pitch classes
        # E4 (64) pc=4, nearest in [0,3,7] from root => 3 or 7 semitones
        result = quantize(64, "custom", custom)
        assert result % 12 in custom

    def test_custom_scale_none_falls_back_to_chromatic(self):
        # custom=None with scale_name="custom" should fall back to chromatic
        assert quantize(61, "custom", None) == 61

    @pytest.mark.parametrize("note", [0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 127])
    def test_quantize_across_octaves(self, note):
        result = quantize(note, "pentatonic")
        assert 0 <= result <= 127
        assert result % 12 in SCALES["pentatonic"]
