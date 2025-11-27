#!/usr/bin/env python3
"""
Modulune - Generative Impressionistic Piano Engine

Entry point for running Modulune as a standalone application.
Streams generative MIDI to a virtual MIDI port for routing into a DAW.

Usage:
    python -m modulune.main [options]

Options:
    --tempo TEMPO       Set tempo in BPM (default: 72)
    --key KEY           Set key root as note name (default: C)
    --mode MODE         Set scale mode (default: major)
    --density DENSITY   Set note density 0.0-1.0 (default: 0.5)
    --tension TENSION   Set harmonic tension 0.0-1.0 (default: 0.3)
    --texture TEXTURE   Set texture type (default: impressionist_wash)
    --port PORT         MIDI port name to use
    --list-ports        List available MIDI ports and exit
"""

import argparse
import signal
import sys
import time

from .engine import ModuluneEngine, EngineConfig, TextureType
from .harmony import ScaleType


# Note name to MIDI number mapping
NOTE_TO_MIDI = {
    "C": 60, "C#": 61, "Db": 61,
    "D": 62, "D#": 63, "Eb": 63,
    "E": 64,
    "F": 65, "F#": 66, "Gb": 66,
    "G": 67, "G#": 68, "Ab": 68,
    "A": 69, "A#": 70, "Bb": 70,
    "B": 71,
}


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Modulune - Generative Impressionistic Piano Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Texture Types:
  flowing_arpeggios    Continuous flowing arpeggio patterns
  melodic_fragments    Melodic lines with sparse accompaniment
  shimmering_chords    Sustained shimmering chord textures
  sparse_meditation    Very sparse, contemplative textures
  layered_voices       Multiple independent melodic voices
  impressionist_wash   Combined impressionistic textures (default)

Scale Modes:
  major, natural_minor, harmonic_minor, melodic_minor,
  dorian, phrygian, lydian, mixolydian, aeolian, locrian,
  whole_tone, pentatonic_major, pentatonic_minor, blues

Examples:
  python -m modulune.main --tempo 60 --key Db --mode lydian
  python -m modulune.main --texture flowing_arpeggios --density 0.7
  python -m modulune.main --port "loopMIDI Port 1"
        """
    )
    
    parser.add_argument(
        "--tempo", type=float, default=72.0,
        help="Tempo in BPM (default: 72)"
    )
    parser.add_argument(
        "--key", type=str, default="C",
        help="Key root as note name, e.g., C, Db, F# (default: C)"
    )
    parser.add_argument(
        "--mode", type=str, default="major",
        help="Scale mode (default: major)"
    )
    parser.add_argument(
        "--density", type=float, default=0.5,
        help="Note density 0.0-1.0 (default: 0.5)"
    )
    parser.add_argument(
        "--tension", type=float, default=0.3,
        help="Harmonic tension 0.0-1.0 (default: 0.3)"
    )
    parser.add_argument(
        "--texture", type=str, default="impressionist_wash",
        help="Texture type (default: impressionist_wash)"
    )
    parser.add_argument(
        "--expressiveness", type=float, default=0.6,
        help="Expressiveness level 0.0-1.0 (default: 0.6)"
    )
    parser.add_argument(
        "--port", type=str, default=None,
        help="MIDI port name to use (auto-selects if not specified)"
    )
    parser.add_argument(
        "--list-ports", action="store_true",
        help="List available MIDI ports and exit"
    )
    
    return parser.parse_args()


def note_name_to_midi(name: str) -> int:
    """
    Convert note name to MIDI number.
    
    Args:
        name: Note name like 'C', 'Db', 'F#'.
        
    Returns:
        MIDI note number.
        
    Raises:
        ValueError: If note name is invalid.
    """
    name = name.strip().capitalize()
    if len(name) > 1:
        name = name[0].upper() + name[1:]
    
    if name not in NOTE_TO_MIDI:
        raise ValueError(f"Invalid note name: {name}")
    
    return NOTE_TO_MIDI[name]


def mode_name_to_scale_type(name: str) -> ScaleType:
    """
    Convert mode name string to ScaleType enum.
    
    Args:
        name: Mode name like 'major', 'dorian', 'whole_tone'.
        
    Returns:
        ScaleType enum value.
        
    Raises:
        ValueError: If mode name is invalid.
    """
    name = name.lower().replace("-", "_").replace(" ", "_")
    
    for scale_type in ScaleType:
        if scale_type.value == name:
            return scale_type
    
    raise ValueError(f"Invalid mode: {name}. Use --help to see available modes.")


def texture_name_to_type(name: str) -> TextureType:
    """
    Convert texture name string to TextureType enum.
    
    Args:
        name: Texture name like 'flowing_arpeggios'.
        
    Returns:
        TextureType enum value.
        
    Raises:
        ValueError: If texture name is invalid.
    """
    name = name.lower().replace("-", "_").replace(" ", "_")
    
    for texture_type in TextureType:
        if texture_type.value == name:
            return texture_type
    
    raise ValueError(f"Invalid texture: {name}. Use --help to see available textures.")


def print_banner():
    """Print the Modulune startup banner."""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███╗   ███╗ ██████╗ ██████╗ ██╗   ██╗██╗     ██╗   ██╗███╗ ║
║   ████╗ ████║██╔═══██╗██╔══██╗██║   ██║██║     ██║   ██║████╗║
║   ██╔████╔██║██║   ██║██║  ██║██║   ██║██║     ██║   ██║██╔██║
║   ██║╚██╔╝██║██║   ██║██║  ██║██║   ██║██║     ██║   ██║██║╚█║
║   ██║ ╚═╝ ██║╚██████╔╝██████╔╝╚██████╔╝███████╗╚██████╔╝██║ ║║
║   ╚═╝     ╚═╝ ╚═════╝ ╚═════╝  ╚═════╝ ╚══════╝ ╚═════╝ ╚═╝ ║║
║                                                              ║
║        Generative Impressionistic Piano Engine               ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def main():
    """Main entry point for Modulune."""
    args = parse_args()
    
    # List ports if requested
    if args.list_ports:
        ports = ModuluneEngine.list_midi_ports()
        print("\nAvailable MIDI output ports:")
        if ports:
            for port in ports:
                print(f"  - {port}")
        else:
            print("  (none found - create a virtual MIDI port like loopMIDI)")
        return
    
    print_banner()
    
    try:
        # Parse configuration
        key_root = note_name_to_midi(args.key)
        scale_type = mode_name_to_scale_type(args.mode)
        texture = texture_name_to_type(args.texture)
        
        config = EngineConfig(
            tempo=args.tempo,
            key_root=key_root,
            scale_type=scale_type,
            density=args.density,
            tension=args.tension,
            texture=texture,
            expressiveness=args.expressiveness,
        )
        
        # Create engine
        engine = ModuluneEngine(config, args.port)
        
        # Handle Ctrl+C gracefully
        def signal_handler(sig, frame):
            print("\n\nStopping Modulune...")
            engine.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Start engine
        engine.start()
        
        print("\nControls:")
        print("  Ctrl+C  - Stop and exit")
        print("\nGenerating music... (output to MIDI port)")
        print("-" * 50)
        
        # Keep running
        while True:
            time.sleep(0.1)
            
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"MIDI Error: {e}")
        print("\nMake sure you have a virtual MIDI port like loopMIDI installed.")
        print("Run with --list-ports to see available ports.")
        sys.exit(1)


if __name__ == "__main__":
    main()
