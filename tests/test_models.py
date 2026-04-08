"""Tests for app.models — Pydantic data models."""

import pytest
from pydantic import ValidationError
from app.models import KeyDef, RowDef, Layout


class TestKeyDef:
    def test_minimal_creation(self):
        k = KeyDef(label="C", note=60)
        assert k.label == "C"
        assert k.note == 60
        assert k.velocity == 100
        assert k.channel == 0
        assert k.color is None

    def test_full_creation(self):
        k = KeyDef(label="D#", note=63, width=1.5, height=0.8, velocity=80, channel=2, color="#FF0000")
        assert k.width == 1.5
        assert k.color == "#FF0000"


class TestRowDef:
    def test_empty_row(self):
        r = RowDef(keys=[])
        assert r.keys == []

    def test_row_with_keys(self):
        keys = [KeyDef(label="C", note=60), KeyDef(label="D", note=62)]
        r = RowDef(keys=keys)
        assert len(r.keys) == 2


class TestLayout:
    def test_defaults(self):
        layout = Layout(name="test", rows=[])
        assert layout.columns == 12
        assert layout.gap == 4
        assert layout.base_octave == 4
        assert layout.allow_poly is True
        assert layout.quantize_scale == "chromatic"

    def test_columns_must_be_positive(self):
        with pytest.raises(ValidationError):
            Layout(name="bad", rows=[], columns=0)

    def test_custom_scale_list(self):
        layout = Layout(name="custom", rows=[], quantize_scale="custom", custom_scale=[0, 3, 7])
        assert layout.custom_scale == [0, 3, 7]

    def test_invalid_scale_rejected(self):
        with pytest.raises(ValidationError):
            Layout(name="bad", rows=[], quantize_scale="blues")
