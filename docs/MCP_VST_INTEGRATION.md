# MCP-VST / Constellation Integration Guide

## Overview

This document explores integration possibilities between Octavium and the mcp-vst/Constellation project. Both projects share a common philosophy: **theory-grounded, accessible music creation**. Octavium provides direct expressive control, while Constellation (mcp-vst) enables AI-steered generative ambient music.

**Project Locations:**
- Octavium: `c:\Users\Owen\dev\Octavium`
- mcp-vst: `C:\Users\Owen\dev\mcp-vst`

---

## Shared Philosophy

| Principle | Octavium | Constellation |
|-----------|----------|---------------|
| **Theory-grounded harmony** | Chord suggestions (Neo-Riemannian, modal borrowing) | Harmony Engine (port of Octavium's system) |
| **Accessibility** | Mouse-first, visual feedback | Voice control, 7 macros |
| **Emotion as parameter** | Emotion presets (Dreamy, Jazzy, Dark) | Mood system (same presets) |
| **Compliance spectrum** | Scale compliance 0.0–1.0 | Tension parameter (maps to compliance) |
| **Context awareness** | Lock influence in chord generation | Lock influence in progression |
| **Expressive timing** | Humanize controls (drift, velocity) | Rubato, swing, humanization |

**Key Insight:** Octavium's chord engine (`chord_suggestions.py`, `chord_autofill.py`) is the proven foundation that Constellation plans to port to C++.

---

## Architecture Comparison

### Octavium Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                        Octavium (Python/Qt)                     │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Launcher    │  │  Keyboards   │  │  Chord Pad       │  │
│  │              │  │  (25-88 key) │  │  (4×4 grid)          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Harmonic    │  │  Pad Grid    │  │  Faders / XY Fader   │  │
│  │  Table       │  │  (4×4)       │  │                      │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Modulune (Generative Engine)                            │  │
│  │  • Dual-hand textures                                    │  │
│  │  • Impressionistic harmony                               │  │
│  │  • Real-time parameter control                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│                    ┌──────────────┐                             │
│                    │  MidiOut     │                             │
│                    │  (mido/pygame)│                            │
│                    └──────┬───────┘                             │
└───────────────────────────┼─────────────────────────────────────┘
                            │ MIDI
                            ▼
                    ┌──────────────┐
                    │  Virtual     │
                    │  MIDI Port   │
                    └──────────────┘
```

### Constellation Architecture (Planned)
```
┌─────────────────────────────────────────────────────────────────┐
│                    Constellation VST3 (C++/JUCE)                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  Harmony     │  │  Texture     │  │  Rhythm / Timing     │  │
│  │  Engine      │  │  Engine      │  │  Engine              │  │
│  │              │  │              │  │                      │  │
│  │ - Key/mode   │  │ - RH texture │  │ - Tempo (DAW sync)   │  │
│  │ - Chord prog │  │ - LH texture │  │ - Swing / rubato     │  │
│  │ - Tension    │  │ - Density    │  │ - Humanization       │  │
│  │ - Modulation │  │ - Register   │  │ - Groove patterns    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         └─────────────────┴──────────────────────┘             │
│                           │                                     │
│                    ┌──────▼──────┐                              │
│                    │  Synthesis  │  (Phase 2+)                  │
│                    │  Engine     │                              │
│                    └──────┬──────┘                              │
│                           │                                     │
│              ┌────────────▼────────────┐                        │
│              │   MCP Server (TCP:9999) │                        │
│              │   AI ←→ Plugin bridge   │                        │
│              └─────────────────────────┘                        │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │ MIDI/Audio
                            ▼
                    ┌──────────────┐
                    │  DAW         │
                    │  (Any VST3)  │
                    └──────────────┘
```

---

## Integration Opportunities

### 1. Harmony Engine Port (High Priority)

**Goal:** Port Octavium's proven chord system to C++ for Constellation's Harmony Engine

**What to Port:**
- `chord_suggestions.py` — Neo-Riemannian transformations (P, L, R, N, S, H)
- `chord_autofill.py` — Weighted pool sampling, modal borrowing, scale compliance
- `scale.py` — Scale quantization
- `models.py` — Chord data structures

**Implementation Path:**

```cpp
// constellation/src/harmony/ChordEngine.h
class ChordEngine {
public:
    // Core from chord_suggestions.py
    std::vector<Chord> suggestNextChords(
        const Chord& current,
        const std::string& key,
        const std::string& mode,
        float tension  // maps to scale_compliance
    );
    
    // Neo-Riemannian transformations
    Chord parallel(const Chord& chord);      // P
    Chord leadingTone(const Chord& chord);   // L
    Chord relative(const Chord& chord);      // R
    Chord nebenverwandt(const Chord& chord); // N
    Chord slide(const Chord& chord);         // S
    Chord hexatonicPole(const Chord& chord); // H
    
    // From chord_autofill.py
    std::vector<Chord> generateChordGrid(
        const std::string& key,
        const std::string& mode,
        float scaleCompliance,
        float lockInfluence,
        const std::vector<Chord>& lockedChords
    );
    
    // Emotion presets
    void setMood(const std::string& mood); // "dreamy", "jazzy", "dark"
};
```

**Advantages:**
- Proven musical intelligence from Octavium
- Saves months of R&D
- Consistent theory between projects
- Community-tested algorithms

**Timeline:**
- Phase 1: Port data structures (1-2 weeks)
- Phase 2: Port Neo-Riemannian transforms (1-2 weeks)
- Phase 3: Port weighted pool sampling (2-3 weeks)
- Phase 4: Integration testing (1 week)

---

### 2. Bidirectional MIDI Bridge

**Goal:** Octavium and Constellation communicate via MIDI

**Architecture:**
```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   Octavium      │  MIDI   │  Virtual MIDI    │  MIDI   │  Constellation  │
│   (Standalone)  │◄───────►│  Port            │◄───────►│  VST3 Plugin    │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

**Use Cases:**

**A. Octavium → Constellation (Chord Context)**
- User plays chord in Octavium Chord Pad
- Chord sent as MIDI notes to Constellation
- Constellation's Harmony Engine uses it as context for next chord
- Constellation generates texture around that harmony

**B. Constellation → Octavium (Generative Playback)**
- Constellation generates chord progression
- MIDI sent to Octavium
- Octavium visualizes on Harmonic Table or Keyboard
- User sees what AI is playing

**Implementation:**
- Octavium: Already has MIDI output (`midi_io.py`)
- Constellation: JUCE MIDI input in `processBlock()`
- Shared virtual MIDI port: "Octavium-Constellation Bridge"

**Example Workflow:**
1. User creates chord progression in Octavium Chord Pad
2. Locks favorite chords
3. Sends to Constellation via MIDI
4. Constellation analyzes locked chords (lock influence)
5. Generates evolving texture around that progression
6. Sends back to Octavium for visualization

---

### 3. MCP Tools for Octavium Control

**Goal:** AI assistant controls Octavium via MCP protocol

**Architecture:**
```
┌─────────────────┐   MCP    ┌──────────────────┐   MCP    ┌─────────────┐
│   Claude AI     │◄────────►│  Octavium MCP    │◄────────►│  Octavium   │
│   Assistant     │  TCP     │  Server Module   │  Python  │  App        │
└─────────────────┘          └──────────────────┘          └─────────────┘
```

**Proposed MCP Tools for Octavium:**

```json
{
  "name": "octavium_set_chord",
  "description": "Set a chord in the Chord Pad grid",
  "inputSchema": {
    "slot": {"type": "integer", "min": 0, "max": 15},
    "chord": {"type": "string", "example": "Cmaj7"},
    "notes": {"type": "array", "items": {"type": "integer"}}
  }
}

{
  "name": "octavium_generate_progression",
  "description": "Generate chord progression using Octavium's engine",
  "inputSchema": {
    "key": {"type": "string"},
    "mode": {"type": "string"},
    "tension": {"type": "number", "min": 0.0, "max": 1.0},
    "length": {"type": "integer"}
  }
}

{
  "name": "octavium_play_chord",
  "description": "Play a chord immediately",
  "inputSchema": {
    "chord": {"type": "string"},
    "velocity": {"type": "integer"},
    "humanize": {"type": "boolean"}
  }
}

{
  "name": "octavium_set_scale",
  "description": "Set scale quantization",
  "inputSchema": {
    "key": {"type": "string"},
    "mode": {"type": "string"}
  }
}
```

**Implementation:**
- Add `app/mcp_server.py` to Octavium
- TCP server on port 9998 (Constellation uses 9999)
- Qt signals to update UI from MCP commands
- Thread-safe command queue

**Use Cases:**
- AI generates chord progressions for user
- Voice command: "Make it more jazzy" → AI adjusts Octavium's settings
- AI analyzes user's playing and suggests next chords
- Cross-project workflows (AI controls both Octavium and Constellation)

---

### 4. Shared Modulune/Constellation Codebase

**Goal:** Modulune's generative engine informs Constellation's Texture Engine

**Current State:**
- Modulune: Python, in-progress, well-designed architecture
- Constellation: C++, planned, needs texture generation

**Approach:**
- Use Modulune as **reference implementation**
- Port proven concepts to C++ Texture Engine
- Keep Modulune as Python prototype/testing ground

**What to Port from Modulune:**

```python
# modulune/textures.py → constellation/src/texture/TextureEngine.cpp

Right-hand textures:
- flowing_arpeggios    → FlowingArpeggios class
- melodic_fragments    → MelodicFragments class
- shimmering_chords    → ShimmeringChords class
- sparse_meditation    → SparseMeditation class
- impressionist_wash   → ImpressionistWash class

Left-hand textures:
- sustained_bass       → SustainedBass class
- broken_chords        → BrokenChords class
- alberti_bass         → AlbertiBass class
- rolling_octaves      → RollingOctaves class
```

**Workflow:**
1. Develop texture in Modulune (Python, fast iteration)
2. Test with users in Octavium launcher
3. Once proven, port to C++ for Constellation
4. Constellation benefits from battle-tested algorithms

---

### 5. Unified Preset Library

**Goal:** Share presets between Octavium and Constellation

**Preset Format (JSON):**
```json
{
  "name": "Deep Space Ambient",
  "type": "octavium_constellation_preset",
  "version": "1.0",
  "octavium": {
    "chord_grid": [
      {"slot": 0, "chord": "Cmaj7", "notes": [60, 64, 67, 71]},
      {"slot": 1, "chord": "Am7", "notes": [57, 60, 64, 67]}
    ],
    "scale": {"key": "C", "mode": "lydian"},
    "humanize": {"drift_ms": 20, "velocity_range": [80, 100]}
  },
  "constellation": {
    "harmony": {
      "key": "C",
      "mode": "lydian",
      "tension": 0.3
    },
    "texture": {
      "rh": "shimmering_chords",
      "lh": "sustained_bass",
      "density": 0.4
    },
    "macros": {
      "warmth": 0.7,
      "space": 0.9,
      "movement": 0.3,
      "shimmer": 0.8
    }
  }
}
```

**Use Cases:**
- User creates progression in Octavium
- Exports as preset
- Loads in Constellation for generative version
- AI generates preset for both tools simultaneously

**Implementation:**
- `octavium/presets/` directory
- `constellation/presets/` directory
- Shared schema validation
- Cross-import functionality

---

## Technical Synergies

### MIDI I/O
- **Octavium:** `midi_io.py` (mido/pygame backends)
- **Constellation:** JUCE MIDI (cross-platform)
- **Bridge:** Virtual MIDI ports (loopMIDI, IAC Driver)

### Chord Data Structures
- **Octavium:** Python lists of MIDI note numbers
- **Constellation:** C++ `std::vector<int>` or custom `Chord` class
- **Conversion:** Direct mapping, no transformation needed

### Scale Theory
- **Octavium:** 12 modes with emotional descriptions
- **Constellation:** Same 12 modes (port from Octavium)
- **Shared:** Emotion preset mappings

### Humanization
- **Octavium:** Drift (ms), velocity range, direction
- **Constellation:** Rubato, swing, humanization amount
- **Alignment:** Map Octavium's drift → Constellation's rubato

---

## Development Workflow

### Shared Development Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    Development Workflow                         │
│                                                                 │
│  1. Design feature in Modulune (Python)                        │
│     ↓                                                           │
│  2. Test in Octavium launcher                                  │
│     ↓                                                           │
│  3. Gather user feedback                                       │
│     ↓                                                           │
│  4. Refine algorithm                                           │
│     ↓                                                           │
│  5. Port to Constellation (C++)                                │
│     ↓                                                           │
│  6. Integrate with MCP tools                                   │
│     ↓                                                           │
│  7. Deploy as VST3 plugin                                      │
└─────────────────────────────────────────────────────────────────┘
```

**Advantages:**
- Python for rapid prototyping
- C++ for production performance
- Shared musical knowledge
- Community testing in Octavium before Constellation release

---

## Roadmap

### Phase 1: Foundation (Now - 3 months)
- [x] Document integration opportunities (this file)
- [ ] Port Octavium's chord engine to C++ (Constellation Harmony Engine)
- [ ] Test MIDI bridge between Octavium and Constellation prototype
- [ ] Define shared preset format

### Phase 2: Bidirectional Communication (3-6 months)
- [ ] Add MCP server to Octavium
- [ ] Implement Octavium MCP tools
- [ ] Build MIDI bridge workflows
- [ ] Create example AI scripts controlling both tools

### Phase 3: Shared Texture Library (6-9 months)
- [ ] Stabilize Modulune textures
- [ ] Port proven textures to Constellation
- [ ] Create unified preset library
- [ ] Document cross-project workflows

### Phase 4: Ecosystem Integration (9-12 months)
- [ ] Octavium + Constellation + Reaper workflow
- [ ] AI-assisted composition pipeline
- [ ] Preset marketplace (shared between projects)
- [ ] Video tutorials and documentation

---

## Use Case Examples

### Use Case 1: AI-Assisted Composition
1. User describes intent: "Create a dreamy, evolving ambient piece"
2. AI (via MCP) sets Octavium to C Lydian, generates chord grid
3. AI configures Constellation: tension=0.3, texture=shimmering_chords
4. User plays chords in Octavium, Constellation generates texture
5. Both output to Reaper for recording

### Use Case 2: Live Performance
1. Octavium Chord Pad: user holds chord cards
2. MIDI sent to Constellation VST in Ableton
3. Constellation generates evolving texture around held chords
4. User transitions to next chord, Constellation smoothly modulates
5. Harmonic Table visualizes Constellation's output in real-time

### Use Case 3: Preset Exploration
1. User loads "Deep Space Ambient" preset
2. Octavium configures chord grid + scale
3. Constellation configures harmony + texture engines
4. User tweaks macros in Constellation
5. Exports updated preset for sharing

### Use Case 4: Generative Stems
1. Modulune generates 8-bar progression
2. Constellation renders as MIDI stems (harmony, texture, rhythm)
3. Octavium visualizes on Harmonic Table
4. User edits in Reaper MIDI editor
5. Re-imports to Octavium for further iteration

---

## Technical Challenges

### Challenge 1: Python ↔ C++ Interop
**Problem:** Octavium is Python, Constellation is C++

**Solutions:**
- MIDI bridge (no direct interop needed)
- MCP protocol (language-agnostic)
- Shared JSON preset format
- Port algorithms, not code

### Challenge 2: Real-Time Performance
**Problem:** Octavium's Python chord engine may be too slow for VST

**Solutions:**
- C++ port for Constellation (already planned)
- Octavium remains standalone (no real-time constraint)
- Pre-compute chord pools where possible

### Challenge 3: UI Consistency
**Problem:** Qt (Octavium) vs JUCE (Constellation) look different

**Solutions:**
- Don't force consistency
- Each tool has its own identity
- Shared concepts, not shared UI
- Focus on workflow integration, not visual parity

### Challenge 4: State Synchronization
**Problem:** Keeping Octavium and Constellation in sync

**Solutions:**
- MIDI as single source of truth
- MCP for explicit state updates
- Presets for snapshots
- Don't over-sync (allow divergence)

---

## Conclusion

Octavium and Constellation are complementary tools with shared DNA:

| Aspect | Octavium | Constellation |
|--------|----------|---------------|
| **Role** | The instrument | The player |
| **Control** | Direct, expressive | AI-steered, generative |
| **Platform** | Standalone Python/Qt | VST3 plugin C++/JUCE |
| **Strength** | Proven chord engine | Autonomous evolution |
| **Integration** | MIDI output | MIDI/Audio output + MCP |

**Key Integration Points:**
1. Port Octavium's chord engine to Constellation (high priority)
2. MIDI bridge for bidirectional communication
3. MCP tools for AI control of Octavium
4. Shared preset library
5. Modulune as texture prototype for Constellation

**Next Steps:**
1. Begin C++ port of `chord_suggestions.py` and `chord_autofill.py`
2. Test MIDI bridge with Constellation prototype
3. Define shared preset JSON schema
4. Document example workflows

Both projects benefit from collaboration while maintaining their unique identities.

---

*Last updated: March 8, 2026*
