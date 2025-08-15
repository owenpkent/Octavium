from typing import List

SCALES = {
    "chromatic": list(range(12)),
    "major":     [0,2,4,5,7,9,11],
    "minor":     [0,2,3,5,7,8,10],
    "pentatonic":[0,2,4,7,9]
}

def quantize(note: int, scale_name: str, custom: List[int] | None = None) -> int:
    if scale_name == "chromatic":
        return note
    pcs = SCALES.get(scale_name) if scale_name != "custom" else (custom or SCALES["chromatic"])
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
