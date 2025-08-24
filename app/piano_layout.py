"""
Piano Layout Generator Module

This module provides functions to generate realistic piano keyboard layouts
with proper black and white key positioning.
"""

from typing import List, Tuple, Optional
from .models import Layout, RowDef, KeyDef


def create_piano_layout(
    num_keys: int = 61,
    start_note: int = 0,
    base_octave: int = 2,
    white_key_width: float = 1.0,
    white_key_height: float = 2.5,
    black_key_width: float = 0.7,
    black_key_height: float = 1.5,
    white_key_color: str = "#f8f8f8",
    black_key_color: str = "#1a1a1a"
) -> Layout:
    """
    Generate a realistic piano keyboard layout with traditional overlaid black keys.
    
    Args:
        num_keys: Total number of keys (default 61 for standard keyboard)
        start_note: Starting MIDI note (default 0 for C)
        base_octave: Base octave for MIDI calculations
        white_key_width: Width of white keys
        white_key_height: Height of white keys
        black_key_width: Width of black keys
        black_key_height: Height of black keys
        white_key_color: Color for white keys
        black_key_color: Color for black keys
    
    Returns:
        Layout object with proper piano key arrangement
    """
    
    # Note names for labeling
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    # Generate white keys first
    current_note = start_note
    white_key_count = 0
    white_notes = {0, 2, 4, 5, 7, 9, 11}  # C, D, E, F, G, A, B
    
    white_keys = []
    while white_key_count < num_keys:
        note_in_octave = current_note % 12
        
        if note_in_octave in white_notes:
            note_name = note_names[note_in_octave]
            white_key = KeyDef(
                label="",
                note=current_note,
                width=white_key_width,
                height=white_key_height,
                color=white_key_color
            )
            white_keys.append(white_key)
            white_key_count += 1
        
        current_note += 1
    
    # Generate black keys with proper positioning
    black_keys = []
    black_key_positions_map = {
        'C': 'C#',  # C# goes between C and D
        'D': 'D#',  # D# goes between D and E
        'F': 'F#',  # F# goes between F and G
        'G': 'G#',  # G# goes between G and A
        'A': 'A#'   # A# goes between A and B
    }
    
    for white_key in white_keys:
        note_in_octave = white_key.note % 12
        white_note_name = note_names[note_in_octave]
        
        if white_note_name in black_key_positions_map:
            # Calculate the black key note
            black_note = white_key.note + 1
            
            # Create black key
            black_key = KeyDef(
                label="",
                note=black_note,
                width=black_key_width,
                height=black_key_height,
                color=black_key_color
            )
            black_keys.append(black_key)
    
    # Create layout with white keys first, then black keys overlaid
    white_row = RowDef(keys=white_keys)
    black_row = RowDef(keys=black_keys)
    
    return Layout(
        name=f"Piano {num_keys}-Key",
        columns=len(white_keys),
        gap=0,
        base_octave=base_octave,
        allow_poly=True,
        quantize_scale="chromatic",
        rows=[white_row, black_row]
    )


def _create_black_key_row(
    white_keys: List[KeyDef], 
    black_keys: List[KeyDef], 
    white_key_width: float,
    black_key_width: float
) -> RowDef:
    """
    Create the black key row with proper spacing between white keys.
    """
    black_key_row_items = []
    black_key_index = 0
    
    # Piano pattern: which white keys have black keys after them
    # C -> C#, D -> D#, (E -> no black), F -> F#, G -> G#, A -> A#, (B -> no black)
    white_notes_with_black_after = {'C', 'D', 'F', 'G', 'A'}
    
    for i, white_key in enumerate(white_keys):
        note_name = white_key.label
        
        # Add spacing before first black key in each group
        if i == 0:
            spacing_width = (white_key_width - black_key_width) / 2
            black_key_row_items.append(KeyDef(
                label="",
                note=-1,
                color="transparent",
                width=spacing_width,
                height=1.0
            ))
        
        # Check if this white key should have a black key after it
        if note_name in white_notes_with_black_after and black_key_index < len(black_keys):
            # Add the black key
            black_key_row_items.append(black_keys[black_key_index])
            black_key_index += 1
            
            # Add spacing after the black key
            spacing_width = (white_key_width - black_key_width) / 2
            
            # Check if next white key also has a black key (for proper spacing)
            if i + 1 < len(white_keys):
                next_note_name = white_keys[i + 1].label
                if next_note_name in white_notes_with_black_after:
                    # Small gap between adjacent black keys
                    spacing_width = (white_key_width - black_key_width) / 2
                else:
                    # Larger gap before E or B (no black key)
                    spacing_width = white_key_width + (white_key_width - black_key_width) / 2
            
            black_key_row_items.append(KeyDef(
                label="",
                note=-1,
                color="transparent",
                width=spacing_width,
                height=1.0
            ))
        else:
            # No black key after this white key, add spacing for the full white key width
            if i < len(white_keys) - 1:  # Don't add spacing after the last key
                black_key_row_items.append(KeyDef(
                    label="",
                    note=-1,
                    color="transparent",
                    width=white_key_width,
                    height=1.0
                ))
    
    return RowDef(keys=black_key_row_items)


def create_piano_by_size(size: int) -> Layout:
    """Create a piano layout based on total key count."""
    configs = {
        25: {"white_keys": 15, "start_note": 0, "base_octave": 4},   # 25-key (2 octaves)
        49: {"white_keys": 29, "start_note": 0, "base_octave": 3},   # 49-key (4 octaves)
        61: {"white_keys": 36, "start_note": 0, "base_octave": 3},   # 61-key (5 octaves)
        73: {"white_keys": 43, "start_note": 0, "base_octave": 1},   # 73-key (6 octaves)
        76: {"white_keys": 45, "start_note": 0, "base_octave": 1},   # 76-key (6+ octaves)
        88: {"white_keys": 52, "start_note": 9, "base_octave": 0}    # 88-key (full piano, A0-C8)
    }
    
    if size not in configs:
        # Default to 61-key if size not found
        size = 61
    
    config = configs[size]
    return create_piano_layout(
        num_keys=config["white_keys"],
        start_note=config["start_note"],
        base_octave=config["base_octave"]
    )


def create_25_key_piano() -> Layout:
    """Create a 25-key piano layout (2 octaves)."""
    return create_piano_by_size(25)


def create_49_key_piano() -> Layout:
    """Create a 49-key piano layout (4 octaves)."""
    return create_piano_by_size(49)


def create_61_key_piano() -> Layout:
    """Create a standard 61-key piano layout (5 octaves)."""
    return create_piano_by_size(61)


def create_73_key_piano() -> Layout:
    """Create a 73-key piano layout (6 octaves)."""
    return create_piano_by_size(73)


def create_76_key_piano() -> Layout:
    """Create a 76-key piano layout (6+ octaves)."""
    return create_piano_by_size(76)


def create_88_key_piano() -> Layout:
    """Create a full 88-key piano layout (A0 to C8)."""
    return create_piano_by_size(88)
