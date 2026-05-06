"""Musical scale definitions and pitch quantization helpers.

Scales are represented as lists of pitch classes (0-11) relative to the tonic.
Quantization snaps an arbitrary MIDI note to the nearest in-scale pitch.
"""

from typing import List

SCALES = {
    "chromatic": list(range(12)),
    "major":     [0,2,4,5,7,9,11],
    "minor":     [0,2,3,5,7,8,10],
    "pentatonic":[0,2,4,7,9]
}

def quantize(note: int, scale_name: str, custom: List[int] | None = None) -> int:
    """Snap a MIDI note to the nearest pitch in the given scale.

    Args:
        note: Source MIDI note number (0-127).
        scale_name: Key into ``SCALES`` or ``"custom"`` to use ``custom``.
        custom: Pitch classes (0-11) used when ``scale_name == "custom"``.

    Returns:
        The closest in-scale MIDI note in [0, 127]. Returns ``note`` unchanged
        for the chromatic scale or when ``note`` is already in scale.
    """
    if scale_name == "chromatic":
        return note
    pcs = (custom or SCALES["chromatic"]) if scale_name == "custom" else SCALES.get(scale_name, SCALES["chromatic"])
    pc = note % 12
    if pc in pcs:
        return note
    best = note
    dist = 128
    for o in range(-2, 3):
        for s in pcs:
            cand = 12 * o + s + (note - pc)
            d = abs(cand - note)
            if 0 <= cand <= 127 and d < dist:
                best, dist = cand, d
    return best
