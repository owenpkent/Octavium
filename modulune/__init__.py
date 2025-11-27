"""
Modulune - Generative Impressionistic Piano Engine

Modulune is Octavium's generative counterpart. While Octavium gives users direct
expressive control over MIDI performance, Modulune creates musical intention
autonomously, generating continuously evolving piano textures in real time.

Inspired by the expressive, impressionistic qualities of Debussy's Clair de Lune
and Bill Evans, Modulune produces music that feels alive, organic, and never
exactly repeats.
"""

__version__ = "0.1.0"
__author__ = "Octavium Project"

from .engine import ModuluneEngine
from .harmony import HarmonyEngine, Scale, Chord, ChordProgression
from .melody import MelodyEngine, Phrase
from .rhythm import RhythmEngine, TimeSignature

__all__ = [
    "ModuluneEngine",
    "HarmonyEngine",
    "Scale",
    "Chord",
    "ChordProgression",
    "MelodyEngine",
    "Phrase",
    "RhythmEngine",
    "TimeSignature",
]
