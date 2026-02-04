# Proposal: MIDI Library Integration for Octavium

## Overview

The two untracked MIDI libraries (`free-midi-chords-20231004` and `free-midi-progressions-20231004`) contain **15,000+ MIDI files** with single chords and chord progressions in all 12 keys. This proposal outlines how to leverage these resources across Octavium.

---

## Library Summary

### `free-midi-chords-20231004/` (8,800+ files)
| Category | Contents |
|----------|----------|
| **Triads** | Basic major/minor triads for each scale degree |
| **7th & 9th Chords** | Extended harmonies (Maj7, Min7, Dom7, 9ths) |
| **All Chords** | 136 chord types per key (sus, add, altered, etc.) |
| **Progressions** | 560 progressions per key with 3 rhythmic styles |

### `free-midi-progressions-20231004/` (6,700+ files)
| Category | Contents |
|----------|----------|
| **Major** | 3,264 major-key progressions (68 unique × 12 keys × 4 styles) |
| **Minor** | 3,456 minor-key progressions (72 unique × 12 keys × 4 styles) |

**File Naming Convention:**
- Single chords: `{degree} - {Root}{Quality}.mid` → `I-III - Cmaj7.mid`
- Progressions: `{Key} - {Roman Numerals}.mid` → `C - I V vi IV.mid`

---

## Application 1: Chord Monitor Auto-Population

### Current State
The Chord Monitor has an "Autofill" feature (`chord_autofill.py`) that generates diatonic chords programmatically from `SCALE_MODES` definitions.

### Enhancement: MIDI File-Based Autofill

**Concept:** Instead of generating chords algorithmically, parse actual MIDI files to populate the 4×4 grid with real chord voicings.

#### Implementation

```python
# New module: app/midi_chord_loader.py

import mido
from pathlib import Path
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class MidiChord:
    """Chord extracted from a MIDI file."""
    root: str           # "C", "D#", etc.
    quality: str        # "Major", "Minor 7th", etc.
    notes: List[int]    # MIDI note numbers
    degree: str         # "I", "ii", "V", etc.
    source_file: Path

def parse_midi_chord(filepath: Path) -> MidiChord:
    """Extract chord notes from a single-chord MIDI file."""
    mid = mido.MidiFile(filepath)
    notes = []
    for track in mid.tracks:
        for msg in track:
            if msg.type == 'note_on' and msg.velocity > 0:
                notes.append(msg.note)
    # Parse filename for metadata
    # e.g., "I-III - Cmaj7.mid" → degree="I-III", root="C", quality="maj7"
    ...
    return MidiChord(...)

def load_chords_for_key(key: str, mode: str = "Major") -> List[MidiChord]:
    """Load all single chords for a given key/mode."""
    base_path = Path("free-midi-chords-20231004")
    key_folder = find_key_folder(base_path, key, mode)
    ...
```

#### User Flow
1. User clicks "Autofill..." in Chord Monitor
2. Dialog shows Key and Mode selection (existing)
3. **New:** "Source" dropdown: `Algorithmic` | `MIDI Library`
4. If MIDI Library selected:
   - Show chord category filter (Triads, 7ths, All)
   - Preview shows actual voicings from MIDI files
5. Cards populated with real MIDI note data

#### Benefits
- **Authentic voicings**: Real chord inversions and voicings, not just root-position
- **Extended chords**: Access to 136 chord types beyond basic triads
- **Consistent with DAW workflow**: Same chords users drag into their DAW

---

## Application 2: Progression Browser & Player

### Concept
New standalone window: **Progression Browser** — browse, preview, and load chord progressions.

#### Features

| Feature | Description |
|---------|-------------|
| **Browse by Key** | Filter progressions by key (C, D, E, etc.) |
| **Browse by Mode** | Major vs Minor progressions |
| **Search by Numerals** | Find "I V vi IV" progressions |
| **Style Filter** | basic4, alt4, hiphop rhythmic variants |
| **Preview Playback** | Click to hear progression with timing |
| **Load to Monitor** | Drag or click to populate Chord Monitor grid |

#### UI Mockup

```
┌─────────────────────────────────────────────────┐
│ Progression Browser                         [×] │
├─────────────────────────────────────────────────┤
│ Key: [C ▼]  Mode: [Major ▼]  Style: [basic4 ▼] │
│ Search: [I V vi IV________________] [🔍]        │
├─────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────┐ │
│ │ I V vi IV           ▶ Preview   [Load →]   │ │
│ │ I IV V I            ▶ Preview   [Load →]   │ │
│ │ I V vi iii IV       ▶ Preview   [Load →]   │ │
│ │ ii V I I            ▶ Preview   [Load →]   │ │
│ │ vi IV I V           ▶ Preview   [Load →]   │ │
│ │ ...                                         │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

#### Implementation

```python
# New module: app/progression_browser.py

class ProgressionBrowserWindow(QMainWindow):
    def __init__(self, midi_out: MidiOut):
        ...
        self.progressions = self._index_progressions()
    
    def _index_progressions(self) -> Dict[str, List[ProgressionInfo]]:
        """Build searchable index of all progression files."""
        ...
    
    def _parse_progression_file(self, path: Path) -> List[MidiChord]:
        """Extract individual chords with timing from progression MIDI."""
        mid = mido.MidiFile(path)
        chords = []
        # Group simultaneous note_on events into chords
        # Track timing between chord changes
        ...
        return chords
    
    def _preview_progression(self, progression: ProgressionInfo):
        """Play back the progression with original timing."""
        ...
    
    def _load_to_monitor(self, progression: ProgressionInfo):
        """Send chords to Chord Monitor grid."""
        ...
```

---

## Application 3: Modulune Integration

### Concept
Use the progression library to seed Modulune's harmonic engine with real-world progressions instead of purely algorithmic generation.

#### Enhancement Options

1. **Progression Templates**: Load a progression as Modulune's harmonic backbone
2. **Chord Vocabulary**: Use the chord voicings from the library for Modulune's generated chords
3. **Style Presets**: Map rhythmic styles (hiphop, alt4) to Modulune texture parameters

#### Implementation Hook

In `modulune/harmony.py`:

```python
class HarmonyEngine:
    def load_progression_template(self, midi_path: Path):
        """Load external progression as harmonic template."""
        chords = parse_progression_midi(midi_path)
        self.progression_template = chords
        self.use_template = True
    
    def get_next_chord(self) -> List[int]:
        if self.use_template:
            return self._get_template_chord()
        return self._generate_chord()  # Original behavior
```

---

## Application 4: Chord Suggestion Enhancement

### Current State
`chord_suggestions.py` provides next-chord suggestions based on music theory rules.

### Enhancement
Supplement algorithmic suggestions with **empirical data** from the progression library.

#### Implementation

```python
# Enhance chord_suggestions.py

def get_empirical_suggestions(current_chord: str, key: str) -> List[ChordSuggestion]:
    """Find what chords commonly follow the current chord in real progressions."""
    # Scan progression files for patterns
    # Count occurrences of chord transitions
    # Return weighted suggestions based on real-world usage
    ...
```

#### Benefits
- Suggestions reflect real songwriting patterns
- "I V vi IV" and other common progressions naturally emerge
- Users learn practical harmony, not just theory

---

## Application 5: Drag-and-Drop from File Browser

### Concept
Allow users to drag MIDI files directly from system file browser onto:
- **Chord Monitor**: Populate cards with chord data
- **Keyboard Widget**: Load and play the chord
- **Progression Browser**: Queue for preview

#### Implementation
Already partially supported via existing drag-and-drop infrastructure. Extend `dropEvent` handlers to accept file paths:

```python
def dropEvent(self, event):
    if event.mimeData().hasUrls():
        for url in event.mimeData().urls():
            if url.toLocalFile().endswith('.mid'):
                self._load_midi_file(url.toLocalFile())
```

---

## Technical Considerations

### MIDI Parsing
- Use `mido` (already a dependency) for MIDI file parsing
- Handle note timing for progressions
- Normalize velocity values

### File Indexing
- Build index on first run, cache to JSON
- ~15,000 files, index once for fast search
- Watch for file changes (optional)

### Performance
- Lazy-load MIDI content (index metadata only upfront)
- Use worker thread for indexing
- Cache parsed chords in memory

### Storage
- Libraries are ~50MB total
- Consider optional download vs bundling
- Add to `.gitignore` (already there based on "untracked" status)

---

## Recommended Implementation Order

| Phase | Feature | Effort | Impact |
|-------|---------|--------|--------|
| **1** | MIDI Chord Parser module | Low | Foundation for all features |
| **2** | Autofill MIDI Source option | Medium | Quick win, enhances existing feature |
| **3** | Progression Browser window | Medium | Major new capability |
| **4** | Chord Suggestion enhancement | Low | Improves existing UX |
| **5** | Modulune integration | Medium | Advanced feature |
| **6** | External drag-and-drop | Low | Polish feature |

---

## Summary

The MIDI libraries are a rich resource that can significantly enhance Octavium:

1. **Real voicings** instead of algorithmic root-position chords
2. **15,000+ progressions** for learning and inspiration
3. **Consistent workflow** with DAW drag-and-drop
4. **Empirical suggestions** based on real music patterns

The modular approach allows incremental implementation while delivering value at each phase.

---

*Proposal Date: February 2026*
