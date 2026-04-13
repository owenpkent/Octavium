# Chord Progression Generation

## Goal

Add a "Generate Progression" feature to the Chord Pad that fills the 4×4 grid with a musically coherent chord sequence, sourced from the bundled MIDI chord library (`resources/`).

Currently the Chord Pad can autofill the grid with individual diatonic chords (random or from MIDI files), but it has no concept of *sequential* chord relationships. This feature uses the ~48 progression patterns already present in the `resources/Major/`, `resources/Minor/`, and `resources/Modal/` directories to populate the grid with real progressions.

---

## Data Source

### Progression MIDI Files

The bundled free-midi-chords library contains progression files at:

```
resources/
├── Major/          ~48 progressions × 12 keys
├── Minor/          ~48 progressions × 12 keys
└── Modal/          ~30 progressions × 12 keys
```

Each file is a multi-chord MIDI file. The filename encodes the key, roman numeral sequence, and mood tags:

```
C - I V vi IV - Hopeful Romantic.mid
D - ii V I I - Triumphant.mid
A - I I7 Idom7 IV ivm I - Relaxed Nostalgic.mid
```

### Filename Schema

```
{Key} - {Roman Numerals} - {Mood Tags}.mid
```

| Field | Examples | Notes |
|-------|----------|-------|
| Key | `C`, `Db`, `F#` | Always the tonic |
| Roman Numerals | `I V vi IV` | Space-separated, case encodes quality (I=major, ii=minor) |
| Mood Tags | `Hopeful Romantic` | 1–2 adjectives, space-separated |

### Chord-Level Data Inside the MIDI Files

Each progression MIDI file contains multiple chords played in sequence. Each chord is a cluster of simultaneous `note_on` events at a distinct time offset. The existing `mido` infrastructure can extract these as groups of MIDI note numbers, giving us real voicings (not just root-position triads).

---

## Parsing

### Step 1: Index Progression Files

On first use (or app startup), scan the three progression directories and build an in-memory index. Each entry captures metadata parsed from the filename — no MIDI parsing needed at this stage.

```python
@dataclass
class ProgressionEntry:
    key: str                  # "C", "D", "Bb", etc.
    mode: str                 # "Major", "Minor", "Modal"
    numerals: list[str]       # ["I", "V", "vi", "IV"]
    moods: list[str]          # ["Hopeful", "Romantic"]
    file_path: Path
```

Filename parsing regex:

```
^(\w+#?b?) - (.+?) - (.+)\.mid$
  ^key        ^numerals  ^moods
```

Numerals split on whitespace. Moods split on whitespace.

### Step 2: Parse MIDI for Chord Notes

When a progression is selected, parse the MIDI file to extract the actual chord voicings. Group simultaneous `note_on` events (events at the same tick offset) into chords:

```python
def parse_progression_midi(filepath: Path) -> list[list[int]]:
    """Extract a list of chords (each a list of MIDI note numbers) from a progression MIDI file."""
    mid = mido.MidiFile(str(filepath))
    chords: list[list[int]] = []
    current_chord: list[int] = []
    current_time = 0

    for msg in mido.merge_tracks(mid.tracks):
        current_time += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            if current_chord and msg.time > 0:
                # Time gap means new chord
                chords.append(sorted(current_chord))
                current_chord = []
            current_chord.append(msg.note)

    if current_chord:
        chords.append(sorted(current_chord))

    return chords
```

This gives us the actual MIDI notes for each chord in the progression, preserving the voicings from the library.

### Transposition

The library includes every progression in all 12 keys, so transposition isn't strictly needed — just pick the file matching the user's selected key. However, for the Modal category (which may not cover every key), transposition is straightforward: shift all MIDI notes by the semitone difference between the file's key and the target key.

---

## Filling the Grid

The Chord Pad grid has 16 slots (4×4). Progressions vary in length (typically 4–8 chords). Strategy for filling:

| Progression Length | Grid Fill Strategy |
|---|---|
| 4 chords | Repeat 4× to fill 16, or fill first 4 only |
| 8 chords | Repeat 2× to fill 16, or fill first 8 only |
| 4 < n < 16 | Fill first n slots, leave rest empty (or loop) |
| 16+ | Truncate to 16 |

The default behaviour should be to **loop the progression** to fill all 16 slots. This matches how progressions work in practice — they repeat. The user can then lock individual cards and regenerate the rest.

Each slot receives:
- The MIDI note list from the parsed chord (real voicing)
- The roman numeral label from the filename
- The detected chord name via the existing `detect_chord()` function

---

## UI Integration

### Where It Lives

Add a **"Progression..."** button or menu item to the Chord Pad toolbar, next to the existing "Autofill..." button. This opens a `ProgressionDialog`.

### ProgressionDialog

```
┌──────────────────────────────────────────────────────┐
│ Generate Progression                            [×]  │
├──────────────────────────────────────────────────────┤
│ Key: [C ▼]   Mode: [Major ▼]                        │
│                                                      │
│ Mood: [Any ▼]  (or checkboxes for multi-select)      │
│                                                      │
│ ┌──────────────────────────────────────────────────┐ │
│ │  I  V  vi  IV          Hopeful Romantic      [▶] │ │
│ │  I  IV  V  IV          Joyful Triumphant     [▶] │ │
│ │  vi  IV  I  V          Hopeful Romantic      [▶] │ │
│ │  ii  V  I  IV          Hopeful Triumphant    [▶] │ │
│ │  I  V  vi  iii  IV     Hopeful Joyful        [▶] │ │
│ │  ...                                             │ │
│ └──────────────────────────────────────────────────┘ │
│                                                      │
│ Fill mode: (•) Loop to 16  ( ) Fill once             │
│                                                      │
│             [Cancel]              [Load to Pad]      │
└──────────────────────────────────────────────────────┘
```

- **Key/Mode** dropdowns filter the progression index
- **Mood** filter narrows by tag (Any shows all)
- **Progression list** shows matching entries with numeral labels and mood tags
- **Preview button** [▶] plays the progression using existing MIDI output
- **Fill mode** controls whether the progression loops to fill 16 slots
- **Load to Pad** parses the selected MIDI file and fills the grid

### Interaction with Existing Features

- **Locked cards** are preserved — only unlocked slots get filled
- **Generation Options** (scale compliance, inversions, etc.) do not apply — the MIDI voicings are used as-is since they're already real chord voicings
- After loading, the user can right-click individual cards to edit them with the existing chord edit keyboard

---

## Module Structure

### New: `app/chord_progression.py`

Pure data module, no UI dependencies. Contains:

- `ProgressionEntry` dataclass
- `index_progressions()` — scan directories, parse filenames, return list of entries
- `parse_progression_midi()` — extract chord note lists from a MIDI file
- `get_available_moods()` — collect unique mood tags from the index
- `filter_progressions()` — filter by key, mode, mood

### New: `app/progression_dialog.py`

Qt dialog for browsing and selecting progressions. Contains:

- `ProgressionDialog(QDialog)` — the UI shown above
- Uses `chord_progression.py` for data
- Emits the selected chord list back to the Chord Pad

### Modified: `app/chord_monitor_window.py`

- Add "Progression..." action to toolbar/menu
- Handle the result from `ProgressionDialog` to fill grid slots

### Modified: `app/midi_chord_loader.py`

- Add `parse_progression_midi()` here if we prefer to keep all MIDI parsing in one place (alternative to the new module above)

---

## Mood Tags

The full set of mood tags across the library (extracted from filenames):

**Major:** Hopeful, Romantic, Joyful, Triumphant, Nostalgic, Peaceful, Playful, Relaxed, Tender, Spiritual, Excited, Empowered

**Minor:** Dark, Mysterious, Melancholic, Dramatic, Tense, Rebellious, Haunting, Suspenseful, Nostalgic, Empowered, Triumphant

These can be presented as filter checkboxes or a dropdown.

---

## Markov Chain Generation (Implemented)

A Markov chain generator (`app/chord_progression.py`) learns chord-to-chord transition probabilities from the ~176 unique progressions in the library and generates novel sequences.

### How It Works

1. **Indexing**: On first use, scans all progression filenames (no MIDI parsing needed) and deduplicates by numeral sequence per mode
2. **Transition table**: Counts bigram transitions (e.g., how often `V` follows `I`) from the unique progressions for each mode (Major, Minor, Modal)
3. **Generation**: Walks the chain — picks a start token from observed starts, then samples successors weighted by transition counts
4. **Realization**: Converts numeral tokens to MIDI note tuples using the existing `CHORD_INTERVALS` and `get_chord_notes()` infrastructure

### Controls

| Parameter | Range | Effect |
|-----------|-------|--------|
| **Mode** | Major / Minor / Modal | Selects which transition table to use |
| **Length** | 4–16 | Unique chords before looping to fill 16 slots |
| **Temperature** | 0.3–2.0 | <1.0 = conservative (common progressions), >1.0 = adventurous (rare transitions) |
| **Mood filter** | Any / 21 mood tags | Builds table from only progressions matching the mood |
| **Start chord** | Any / I / IV / vi / etc. | Forces the first chord of the sequence |

### Token Parsing

The generator works at the roman numeral level so it generalizes across keys. Tokens from filenames (`I`, `bVIIM`, `Idom7`, `ivm`, `Vsus2`) are parsed into (semitone offset, chord type) pairs:

- Accidental prefix: `b` = flat, `#` = sharp
- Case encodes default quality: uppercase = Major, lowercase = Minor
- Suffixes override quality: `dom7`, `M7`, `m7`, `sus2`, `sus4`, `dim`, `add9`, `6`, `69`

Dead-end handling: if a token has no observed successors, the generator falls back to stripping the quality suffix (e.g., `Vsus2` → `V`), then restarts from the start distribution.

### Per-Card Regeneration

When regenerating a single card in the Chord Pad, the Markov context uses the predecessor card's numeral to sample from the transition distribution, preserving sequential coherence.

### Files

- `app/chord_progression.py` — Pure data module: indexing, table building, generation, realization
- `app/chord_autofill.py` — "Markov Chain" radio button and options in AutofillDialog
- `app/chord_monitor_window.py` — Markov-aware per-card and bulk regeneration

---

## Future Extensions

- **Progression browser dialog**: A dedicated `ProgressionDialog` for browsing and previewing curated progressions from the library (as described in the UI Integration section above), complementing the Markov generator.
- **MIDI library voicings for Markov**: Currently the Markov generator uses algorithmic voicings via `get_chord_notes()`. A future enhancement could look up matching voicings from the MIDI library for richer, more realistic chord sounds.
- **Rhythm variations**: The library includes `pop`, `pop2`, `hiphop2`, and `soul` timing variants under `resources/*/4 Progression/`. These contain the same progressions with different note timing. Could be used for a rhythm-aware playback mode.
- **Progression chaining**: Allow the user to select multiple short progressions and chain them to fill 16 slots with varied harmonic movement.
