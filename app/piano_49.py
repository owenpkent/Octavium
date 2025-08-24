"""
49-Key Piano Layout (4 Octaves)
"""

from .models import Layout, RowDef, KeyDef


def create_49_key_piano() -> Layout:
    """Create a 49-key piano layout (4 octaves, C2-C6)."""
    
    # White keys for 49-key piano (29 white keys)
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
        # Octave 4
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
        KeyDef(label="", note=48, color="white", width=1.0, height=1.0),  # C6
    ]
    
    # Black keys for 49-key piano (20 black keys)
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
        KeyDef(label="", note=-1, color="transparent", width=1.0, height=1.0),  # Spacer for C6
    ]
    
    white_row = RowDef(keys=white_keys)
    black_row = RowDef(keys=black_keys)
    
    return Layout(
        name="Piano 49-Key",
        columns=len(white_keys),
        gap=0,
        base_octave=2,
        allow_poly=True,
        quantize_scale="chromatic",
        rows=[white_row, black_row]
    )
