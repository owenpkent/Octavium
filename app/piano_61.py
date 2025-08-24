"""
61-Key Piano Layout (5 Octaves)
"""

from .models import Layout, RowDef, KeyDef


def create_61_key_piano() -> Layout:
    """Create a 61-key piano layout (5 octaves, C2-C7)."""
    
    # White keys for 61-key piano (36 white keys)
    white_keys = [
        # Octave 2
        KeyDef(label="", note=0, color="white", width=1.0, height=1.0),   # C2
        KeyDef(label="", note=2, color="white", width=1.0, height=1.0),   # D2
        KeyDef(label="", note=4, color="white", width=1.0, height=1.0),   # E2
        KeyDef(label="", note=5, color="white", width=1.0, height=1.0),   # F2
        KeyDef(label="", note=7, color="white", width=1.0, height=1.0),   # G2
        KeyDef(label="", note=9, color="white", width=1.0, height=1.0),   # A2
        KeyDef(label="", note=11, color="white", width=1.0, height=1.0),  # B2
        # Octave 3
        KeyDef(label="", note=12, color="white", width=1.0, height=1.0),  # C3
        KeyDef(label="", note=14, color="white", width=1.0, height=1.0),  # D3
        KeyDef(label="", note=16, color="white", width=1.0, height=1.0),  # E3
        KeyDef(label="", note=17, color="white", width=1.0, height=1.0),  # F3
        KeyDef(label="", note=19, color="white", width=1.0, height=1.0),  # G3
        KeyDef(label="", note=21, color="white", width=1.0, height=1.0),  # A3
        KeyDef(label="", note=23, color="white", width=1.0, height=1.0),  # B3
        # Octave 4 (Middle C)
        KeyDef(label="", note=24, color="white", width=1.0, height=1.0),  # C4
        KeyDef(label="", note=26, color="white", width=1.0, height=1.0),  # D4
        KeyDef(label="", note=28, color="white", width=1.0, height=1.0),  # E4
        KeyDef(label="", note=29, color="white", width=1.0, height=1.0),  # F4
        KeyDef(label="", note=31, color="white", width=1.0, height=1.0),  # G4
        KeyDef(label="", note=33, color="white", width=1.0, height=1.0),  # A4
        KeyDef(label="", note=35, color="white", width=1.0, height=1.0),  # B4
        # Octave 5
        KeyDef(label="", note=36, color="white", width=1.0, height=1.0),  # C5
        KeyDef(label="", note=38, color="white", width=1.0, height=1.0),  # D5
        KeyDef(label="", note=40, color="white", width=1.0, height=1.0),  # E5
        KeyDef(label="", note=41, color="white", width=1.0, height=1.0),  # F5
        KeyDef(label="", note=43, color="white", width=1.0, height=1.0),  # G5
        KeyDef(label="", note=45, color="white", width=1.0, height=1.0),  # A5
        KeyDef(label="", note=47, color="white", width=1.0, height=1.0),  # B5
        # Octave 6
        KeyDef(label="", note=48, color="white", width=1.0, height=1.0),  # C6
        KeyDef(label="", note=50, color="white", width=1.0, height=1.0),  # D6
        KeyDef(label="", note=52, color="white", width=1.0, height=1.0),  # E6
        KeyDef(label="", note=53, color="white", width=1.0, height=1.0),  # F6
        KeyDef(label="", note=55, color="white", width=1.0, height=1.0),  # G6
        KeyDef(label="", note=57, color="white", width=1.0, height=1.0),  # A6
        KeyDef(label="", note=59, color="white", width=1.0, height=1.0),  # B6
        KeyDef(label="", note=60, color="white", width=1.0, height=1.0),  # C7
    ]
    
    # Black keys for 61-key piano (25 black keys)
    black_keys = [
        # Octave 2
        KeyDef(label="", note=1, color="black", width=0.7, height=1.0),   # C#2
        KeyDef(label="", note=3, color="black", width=0.7, height=1.0),   # D#2
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=6, color="black", width=0.7, height=1.0),   # F#2
        KeyDef(label="", note=8, color="black", width=0.7, height=1.0),   # G#2
        KeyDef(label="", note=10, color="black", width=0.7, height=1.0),  # A#2
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        # Octave 3
        KeyDef(label="", note=13, color="black", width=0.7, height=1.0),  # C#3
        KeyDef(label="", note=15, color="black", width=0.7, height=1.0),  # D#3
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=18, color="black", width=0.7, height=1.0),  # F#3
        KeyDef(label="", note=20, color="black", width=0.7, height=1.0),  # G#3
        KeyDef(label="", note=22, color="black", width=0.7, height=1.0),  # A#3
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        # Octave 4
        KeyDef(label="", note=25, color="black", width=0.7, height=1.0),  # C#4
        KeyDef(label="", note=27, color="black", width=0.7, height=1.0),  # D#4
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=30, color="black", width=0.7, height=1.0),  # F#4
        KeyDef(label="", note=32, color="black", width=0.7, height=1.0),  # G#4
        KeyDef(label="", note=34, color="black", width=0.7, height=1.0),  # A#4
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        # Octave 5
        KeyDef(label="", note=37, color="black", width=0.7, height=1.0),  # C#5
        KeyDef(label="", note=39, color="black", width=0.7, height=1.0),  # D#5
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=42, color="black", width=0.7, height=1.0),  # F#5
        KeyDef(label="", note=44, color="black", width=0.7, height=1.0),  # G#5
        KeyDef(label="", note=46, color="black", width=0.7, height=1.0),  # A#5
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        # Octave 6
        KeyDef(label="", note=49, color="black", width=0.7, height=1.0),  # C#6
        KeyDef(label="", note=51, color="black", width=0.7, height=1.0),  # D#6
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for E
        KeyDef(label="", note=54, color="black", width=0.7, height=1.0),  # F#6
        KeyDef(label="", note=56, color="black", width=0.7, height=1.0),  # G#6
        KeyDef(label="", note=58, color="black", width=0.7, height=1.0),  # A#6
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for B
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for C7
    ]
    
    white_row = RowDef(keys=white_keys)
    black_row = RowDef(keys=black_keys)
    
    return Layout(
        name="Piano 61-Key",
        columns=len(white_keys),
        gap=0,
        base_octave=2,
        allow_poly=True,
        quantize_scale="chromatic",
        rows=[white_row, black_row]
    )
