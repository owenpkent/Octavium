# Reaper Integration Guide

## Overview

This document explores integration possibilities between Octavium and Reaper DAW. Reaper is a key target for integration due to its powerful scripting capabilities, extensive MIDI routing, and the proven demand for intelligent chord tools in Reaper workflows (see ChordGun).

---

## Why Reaper?

### Strengths for Octavium Integration

1. **Powerful Scripting API**
   - ReaScript (Lua, Python, EEL2) provides deep DAW control
   - Access to MIDI editing, track management, FX routing
   - Active community with extensive documentation

2. **Flexible MIDI Routing**
   - Virtual MIDI routing without external tools
   - MIDI send/receive between tracks
   - JS MIDI plugins for custom processing

3. **Proven Demand**
   - ChordGun demonstrates users want theory-grounded chord tools
   - Reaper users embrace workflow automation
   - Strong music theory community

4. **Cross-Platform**
   - Windows, macOS, Linux support
   - Consistent API across platforms
   - Portable project files

---

## Integration Approaches

### Approach 1: MIDI Bridge (Recommended for Phase 1)

**Architecture:**
```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Octavium      │  MIDI   │  Virtual MIDI    │  MIDI   │   Reaper    │
│   (Standalone)  │────────►│  Port (loopMIDI) │────────►│   Track     │
└─────────────────┘         └──────────────────┘         └─────────────┘
```

**How It Works:**
1. Octavium sends MIDI to virtual port (e.g., "Octavium Out")
2. Reaper track receives from same virtual port
3. Reaper routes to VST instruments
4. Full chord pad, pad grid, and keyboard functionality

**Advantages:**
- Works today with zero code changes
- Octavium remains DAW-agnostic
- Users control routing in Reaper
- Multiple Octavium windows → multiple Reaper tracks

**Limitations:**
- No bidirectional communication
- No tempo sync from Reaper
- Manual MIDI port configuration

**Setup Instructions:**
1. Create virtual MIDI port (loopMIDI on Windows, IAC Driver on macOS)
2. In Octavium: MIDI → Select Output Port → Choose virtual port
3. In Reaper: Create track → Set input to virtual port → Arm for recording
4. Add VST instrument to track
5. Play from Octavium → sounds in Reaper

---

### Approach 2: ReaScript Integration

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                           Reaper                                │
│                                                                 │
│  ┌──────────────┐         ┌─────────────────────────────┐      │
│  │  ReaScript   │◄───────►│  Octavium Python Module     │      │
│  │  (Python)    │  Import │  (chord_suggestions.py,     │      │
│  │              │         │   chord_autofill.py, etc.)  │      │
│  └──────┬───────┘         └─────────────────────────────┘      │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────┐                   │
│  │  MIDI Editor / Media Items              │                   │
│  │  • Insert chords directly               │                   │
│  │  • Apply scale quantization             │                   │
│  │  • Generate progressions                │                   │
│  └─────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

**How It Works:**
1. Port Octavium's chord engine to importable Python module
2. ReaScript imports and calls Octavium functions
3. Script inserts MIDI notes directly into Reaper MIDI items
4. Similar to ChordGun but with Octavium's theory engine

**Example ReaScript (Conceptual):**
```python
from octavium.chord_suggestions import suggest_next_chords
from octavium.chord_autofill import generate_chord_grid
from reaper_python import *

# Get current chord from selected MIDI item
current_chord = get_selected_chord()

# Generate suggestions using Octavium's engine
suggestions = suggest_next_chords(
    current_chord,
    key="C",
    mode="major",
    tension=0.5
)

# Insert chosen chord into MIDI editor
for suggestion in suggestions:
    insert_chord_to_midi_item(suggestion)
```

**Advantages:**
- Deep Reaper integration
- Direct MIDI editing workflow
- Leverage Octavium's proven harmony engine
- No external MIDI routing needed

**Challenges:**
- Requires refactoring Octavium code for modularity
- ReaScript Python environment may differ from Octavium's
- No GUI (unless building custom Reaper UI)
- Maintenance of two codebases

**Implementation Path:**
1. Extract core engines to standalone modules:
   - `octavium_core/harmony.py` (chord_suggestions, chord_autofill)
   - `octavium_core/scale.py` (scale quantization)
   - `octavium_core/models.py` (chord data structures)
2. Create ReaScript wrapper: `octavium_reaper.py`
3. Publish as Reaper ReaPack package
4. Document installation and usage

---

### Approach 3: OSC Bridge (Bidirectional Control)

**Architecture:**
```
┌─────────────────┐   OSC    ┌──────────────────┐   OSC    ┌─────────────┐
│   Octavium      │◄────────►│  OSC Bridge      │◄────────►│   Reaper    │
│   (Qt App)      │  UDP     │  (Python/Node)   │  UDP     │  (ReaScript)│
└─────────────────┘          └──────────────────┘          └─────────────┘
```

**How It Works:**
1. Octavium sends OSC messages on chord changes, scale changes, etc.
2. Reaper receives OSC via ReaScript
3. Reaper sends tempo, transport state back to Octavium via OSC
4. Bidirectional sync

**OSC Message Examples:**
```
/octavium/chord/played    ["Cmaj7", 60, 64, 67, 71]
/octavium/scale/changed   ["C", "major"]
/octavium/velocity        100

/reaper/tempo             120.0
/reaper/transport/play    1
/reaper/transport/stop    0
/reaper/time/beats        4.5
```

**Advantages:**
- Bidirectional communication
- Tempo sync from Reaper → Octavium
- Transport control (play/stop)
- Network-based (can run on different machines)

**Challenges:**
- Requires OSC library integration in Octavium (Qt + OSC)
- Additional complexity
- Network latency considerations
- ReaScript OSC handling

**Use Cases:**
- Modulune tempo sync with Reaper
- Octavium follows Reaper's key/scale from markers
- Reaper controls Octavium's chord grid remotely

---

### Approach 4: VST Plugin Wrapper (Long-Term)

**Architecture:**
```
┌─────────────────────────────────────────────────────────────────┐
│                           Reaper                                │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Octavium VST3 Plugin                                    │  │
│  │                                                           │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐ │  │
│  │  │  Keyboard  │  │   Chord    │  │   Pad Grid         │ │  │
│  │  │  Widget    │  │  Monitor   │  │                    │ │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘ │  │
│  │                                                           │  │
│  │  MIDI Output ──────────────────────────────────────────► │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                  │
│                              ▼                                  │
│                    ┌─────────────────┐                         │
│                    │  VST Instrument │                         │
│                    └─────────────────┘                         │
└─────────────────────────────────────────────────────────────────┘
```

**How It Works:**
1. Port Octavium to JUCE framework (C++)
2. Build as VST3/AU plugin
3. Load directly in Reaper FX chain
4. MIDI output routed to downstream instruments

**Advantages:**
- Native DAW integration
- Tempo sync built-in
- Preset management via DAW
- Professional distribution model

**Challenges:**
- Complete rewrite from Python/Qt to C++/JUCE
- Significant development effort
- Loss of standalone flexibility
- Complex UI in plugin context

**Timeline:**
- Phase 1: Proof of concept (single keyboard)
- Phase 2: Full feature parity
- Phase 3: Plugin-specific features (automation, presets)

---

## Recommended Integration Path

### Phase 1: MIDI Bridge (Immediate)
**Status:** Works today, zero code changes

**Action Items:**
- Document setup in README
- Create video tutorial
- Add Reaper-specific tips

### Phase 2: ReaScript Module (3-6 months)
**Status:** Requires refactoring

**Action Items:**
1. Extract core engines to `octavium_core/` package
2. Create `octavium_reaper.py` ReaScript
3. Implement ChordGun-style "fire chord to MIDI item" workflow
4. Publish to ReaPack
5. Document API for community scripts

**Key Features:**
- `insert_chord(chord, position, track)` — Insert chord at timeline position
- `quantize_to_scale(midi_item, key, mode)` — Apply scale quantization
- `suggest_progression(current_chord, length)` — Generate chord sequence
- `apply_humanize(midi_item, drift_ms, velocity_range)` — Humanization

### Phase 3: OSC Sync (6-12 months)
**Status:** Requires Qt OSC integration

**Action Items:**
1. Add QtNetwork OSC support to Octavium
2. Create Reaper OSC receiver ReaScript
3. Implement tempo sync
4. Implement transport sync
5. Document OSC API

### Phase 4: VST Plugin (12-24 months)
**Status:** Major rewrite

**Action Items:**
1. Evaluate JUCE vs. other frameworks
2. Port core engines to C++
3. Build minimal VST3 prototype
4. Iterate on plugin UX
5. Full feature parity
6. Distribution via VST marketplaces

---

## ChordGun Lessons Learned

ChordGun (github.com/benjohnson2001/ChordGun) is prior art demonstrating demand for intelligent chord tools in Reaper. Key takeaways:

### What ChordGun Does Well
- **Direct MIDI Editor integration** — Chords inserted where cursor is
- **Scale awareness** — Respects key/mode selection
- **Reaper-native workflow** — Feels like built-in feature

### What Octavium Adds
- **Neo-Riemannian transformations** — Smooth voice-leading moves (P, L, R, N, S, H)
- **Scale compliance slider** — Continuous dial from diatonic to chromatic
- **Lock influence** — Context-aware generation based on existing chords
- **Emotion presets** — High-level intent ("Dreamy", "Jazzy", "Dark")
- **Chord Pad GUI** — Visual 4×4 grid with drag-and-drop
- **Humanization controls** — Velocity range, note drift, direction

### Integration Strategy
- Study ChordGun's Reaper API usage
- Adopt similar "fire to MIDI item" UX
- Add Octavium's advanced theory engine
- Provide both GUI (standalone) and script (ReaScript) workflows

---

## Technical Considerations

### MIDI Timing
- Reaper's MIDI items use PPQ (pulses per quarter note)
- Octavium uses milliseconds for drift/humanization
- Conversion needed: `ppq = (ms / 1000.0) * (tempo / 60.0) * ppq_resolution`

### Scale Quantization
- Reaper has built-in MIDI quantization (grid-based)
- Octavium's scale quantization is pitch-based
- ReaScript can modify note pitches directly

### Chord Voicing
- Octavium stores chords as MIDI note arrays
- Reaper MIDI items store notes with position, length, velocity
- Direct mapping possible

### State Persistence
- Standalone Octavium: in-memory state
- ReaScript: could use Reaper's ExtState for persistence
- VST: use plugin state save/recall

---

## Community & Distribution

### ReaPack Integration
- ReaPack is Reaper's package manager for scripts
- Publish `octavium_reaper.py` as ReaPack package
- Automatic updates for users
- Discoverability via ReaPack browser

### Documentation
- Video tutorials for MIDI bridge setup
- ReaScript API documentation
- Example workflows (chord progressions, humanization)
- Integration with popular Reaper templates

### Support Channels
- Reaper forum thread
- GitHub Discussions for Octavium
- Discord community
- Video tutorials on YouTube

---

## Future Possibilities

### Modulune + Reaper
- Modulune's generative engine synced to Reaper tempo
- Reaper markers define key changes
- Modulune follows Reaper's transport (play/stop)
- Record Modulune output as MIDI items

### Harmonic Table Integration
- ReaScript to visualize Reaper MIDI items on Harmonic Table
- Click hex to insert note in MIDI editor
- Isomorphic chord shapes as Reaper MIDI templates

### Collaborative Workflows
- Multiple users running Octavium → single Reaper session (OSC)
- Octavium as remote controller for Reaper
- Reaper as "recorder" for Octavium performances

---

## Conclusion

Reaper integration is highly viable and valuable for Octavium. The recommended path:

1. **Now:** Document MIDI bridge setup (works today)
2. **Next:** Build ReaScript module (ChordGun-style workflow + Octavium theory)
3. **Later:** Add OSC for bidirectional sync
4. **Future:** Consider VST plugin for native integration

Reaper's scripting power + Octavium's theory engine = powerful combination for composers and producers.

---

*Last updated: March 8, 2026*
