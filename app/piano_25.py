"""
25-Key Piano Layout (2 Octaves)
"""

from .models import Layout, RowDef, KeyDef


def create_25_key_piano() -> Layout:
    """Create a 25-key piano layout (2 octaves, C3-C5)."""
    
    # White keys for 25-key piano (15 white keys)
    white_keys = [
        # Octave 3
        KeyDef(label="", note=0, color="white", width=1.0, height=1.0),   # C3
        KeyDef(label="", note=2, color="white", width=1.0, height=1.0),   # D3
        KeyDef(label="", note=4, color="white", width=1.0, height=1.0),   # E3
        KeyDef(label="", note=5, color="white", width=1.0, height=1.0),   # F3
        KeyDef(label="", note=7, color="white", width=1.0, height=1.0),   # G3
        KeyDef(label="", note=9, color="white", width=1.0, height=1.0),   # A3
        KeyDef(label="", note=11, color="white", width=1.0, height=1.0),  # B3
        # Octave 4
        KeyDef(label="", note=12, color="white", width=1.0, height=1.0),  # C4
        KeyDef(label="", note=14, color="white", width=1.0, height=1.0),  # D4
        KeyDef(label="", note=16, color="white", width=1.0, height=1.0),  # E4
        KeyDef(label="", note=17, color="white", width=1.0, height=1.0),  # F4
        KeyDef(label="", note=19, color="white", width=1.0, height=1.0),  # G4
        KeyDef(label="", note=21, color="white", width=1.0, height=1.0),  # A4
        KeyDef(label="", note=23, color="white", width=1.0, height=1.0),  # B4
        KeyDef(label="", note=24, color="white", width=1.0, height=1.0),  # C5
    ]
    
    # Black keys for 25-key piano (10 black keys)
    black_keys = [
        # Octave 3
        KeyDef(label="", note=1, color="black", width=0.7, height=1.0),   # C#3
        KeyDef(label="", note=3, color="black", width=0.7, height=1.0),   # D#3
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=6, color="black", width=0.7, height=1.0),   # F#3
        KeyDef(label="", note=8, color="black", width=0.7, height=1.0),   # G#3
        KeyDef(label="", note=10, color="black", width=0.7, height=1.0),  # A#3
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        # Octave 4
        KeyDef(label="", note=13, color="black", width=0.7, height=1.0),  # C#4
        KeyDef(label="", note=15, color="black", width=0.7, height=1.0),  # D#4
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=18, color="black", width=0.7, height=1.0),  # F#4
        KeyDef(label="", note=20, color="black", width=0.7, height=1.0),  # G#4
        KeyDef(label="", note=22, color="black", width=0.7, height=1.0),  # A#4
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for C5
    ]
    
    white_row = RowDef(keys=white_keys)
    black_row = RowDef(keys=black_keys)
    
    return Layout(
        name="Piano 25-Key",
        columns=len(white_keys),
        gap=0,
        base_octave=4,
        allow_poly=True,
        quantize_scale="chromatic",
        rows=[white_row, black_row]
    )
