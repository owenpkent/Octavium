"""Pydantic models describing controller layouts.

A :class:`Layout` is composed of one or more :class:`RowDef` rows, each
containing :class:`KeyDef` entries that map a visual cell to a MIDI note.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class KeyDef(BaseModel):
    """A single playable key in a layout.

    Attributes:
        label: Text drawn on the key (empty for unlabeled).
        note: MIDI note number; ``-1`` denotes a non-playable spacer.
        width: Relative width in grid units.
        height: Relative height in grid units.
        velocity: Default Note On velocity (1-127).
        channel: 0-based MIDI channel.
        color: Optional CSS-style color override.
    """

    label: str
    note: int
    width: float = 1.0
    height: float = 1.0
    velocity: int = 100
    channel: int = 0
    color: Optional[str] = None

class RowDef(BaseModel):
    """An ordered row of keys rendered horizontally."""

    keys: List[KeyDef]

class Layout(BaseModel):
    """A complete controller layout.

    Attributes:
        name: Human-readable layout name shown in the UI.
        rows: Rows of keys rendered top-to-bottom.
        columns: Logical column count used for grid sizing.
        gap: Pixel gap between cells.
        base_octave: Octave offset applied to displayed note labels.
        allow_poly: Whether multiple notes may sound simultaneously.
        quantize_scale: Scale used to snap played notes; see :mod:`app.scale`.
        custom_scale: Pitch classes used when ``quantize_scale == "custom"``.
    """

    name: str
    rows: List[RowDef]
    columns: int = Field(ge=1, default=12)
    gap: int = 4
    base_octave: int = 4
    allow_poly: bool = True
    quantize_scale: Optional[Literal["chromatic","major","minor","pentatonic","custom"]] = "chromatic"
    custom_scale: Optional[List[int]] = None
