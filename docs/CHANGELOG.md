# Octavium Changelog

All notable changes to the Octavium project are documented here.

---

## February 2026 — Chord Monitor Overhaul

### New Features

#### Varied Chord Autofill (16-slot grid)
The autofill system now generates a full **16 chords** (filling the entire 4×4 grid) with a mix of triads, 7ths, 9ths, sus, add, and 6th chords — not just the 7 basic diatonic triads.

- **File**: `app/chord_autofill.py` — `generate_varied_diatonic_chords()`
- **How it works**: Builds a pool from `_EXTENDED_TYPES` for each scale degree, seeds with the 7 diatonic triads, then fills remaining slots via weighted random sampling.

#### MIDI Library Source
Autofill can now load chords from the external MIDI chord library instead of generating them algorithmically.

- **File**: `app/midi_chord_loader.py` — parses MIDI filenames, loads notes from `.mid` files
- **UI**: Radio buttons in the Autofill dialog toggle between "Algorithmic" and "MIDI Library" sources
- **Limitation**: Regeneration (right-click "Generate new chord") only works with the algorithmic source; MIDI source disables it.

#### Lock & Regenerate Pattern
Each chord card in the grid now supports locking. Locked cards are preserved during regeneration.

- **Lock toggle**: Right-click any card → "Lock" / "Unlock"
- **Visual indicator**: Locked cards show a small lock icon (top-right corner, painted in `ReplayCard.paintEvent`)
- **Regenerate unlocked**: Right-click → "Regenerate unlocked" replaces all unlocked cards with new chords from the same key/mode
- **Single regeneration**: Right-click → "Generate new chord" replaces just that one card
- **Files**: `app/chord_selector.py` (lock state, context menu), `app/chord_monitor_window.py` (`_regenerate_card`, `_regenerate_unlocked`)

#### Generation Options Dialog
An **"Options..."** button in the chord monitor header opens a dialog to tweak generation parameters on the fly — no need to re-run the full Autofill dialog.

Contains:

| Section | Controls | Default |
|---------|----------|---------|
| **Key & Scale** | Key dropdown (C–B), Mode dropdown (all SCALE_MODES) | From last autofill |
| **Note Counts** | Checkboxes: Triads (3), 7ths/6ths (4), 9ths/Ext (5) | All checked |
| **Inversions** | Checkboxes: Root, 1st, 2nd, 3rd | Root only |
| **Scale Compliance** | Slider 0–100% | 100% |
| **Lock Influence** | Slider 0–100% | 0% |

- **File**: `app/chord_monitor_window.py` — `_show_gen_options_dialog()`
- Changes are saved to `_autofill_context` and take effect on the next regeneration without re-filling the grid.

#### Scale Compliance System
Controls how strictly generated chords stick to the selected scale.

| Compliance | Behaviour |
|------------|-----------|
| **100%** | Only diatonic chords and their extended types |
| **70–95%** | Also borrows chords from parallel/related modes (modal interchange) |
| **40–70%** | Also allows secondary dominants (V7/ii, V7/V, etc.) |
| **0–40%** | Also allows fully chromatic roots with common qualities |

- **Implementation**: `_build_weighted_pool()` in `app/chord_autofill.py` assigns weights to 4 tiers of chords. Lower compliance = higher weight for borrowed/chromatic chords.
- **Parallel modes map**: `_PARALLEL_MODES` dict maps each mode to its related modes for borrowing.

#### Lock Influence System
Controls how much locked chords influence the style of newly generated chords.

- **0%**: Ignore locks entirely, generate based on scale/compliance only
- **100%**: Heavily favour chord families matching your locked chords
- **Implementation**: `_analyze_locked_chords()` classifies locked chords by family (triad/seventh/sixth/add/extended), then `_apply_lock_influence()` re-weights the candidate pool.
- **Families** (`_CHORD_FAMILY` dict): triad, seventh, sixth, add, extended

#### Inversion Support
Generated chords can now be voiced in inversions, not just root position.

- `apply_inversion(notes, inversion)` — moves the N lowest notes up an octave
- `_pick_inversion()` — randomly selects from allowed inversions, clamped to note count
- Applied during both initial autofill and per-card regeneration

---

### Bug Fixes

#### Drift (Humanize Strum) Not Working on Chord Monitor Cards

**Symptom**: The drift slider had no effect — all notes in a chord played simultaneously when clicking a card in the chord monitor.

**Root cause**: Card clicks route through `mouseReleaseEvent` → `replay_area._play_exact_notes()`. This method played all notes in a tight loop with zero timing. The existing drift code lived in `ReplayCard._play_notes_sustained()`, which was **never called** for chord monitor cards.

**Fix**: Rewrote `ChordMonitorReplayArea._play_exact_notes()` to:
1. Read `_get_drift()` and `_get_drift_direction()` from the parent window
2. Order notes based on drift direction (Up/Down/Random)
3. Stagger note playback using `QTimer.singleShot(delay_ms, ...)` 
4. Extend auto-release timer by `drift_ms` to avoid cutting off late notes

**File**: `app/chord_monitor_window.py`, lines ~480–552

#### Context Menu Not Showing Lock/Regenerate Options

**Symptom**: Right-clicking a `ReplayCard` in the chord monitor only showed "Suggest Next", "Next Chord", "Edit with Keyboard", and "Remove" — none of the new Lock/Regenerate options.

**Root cause**: Two separate `contextMenuEvent` definitions existed in the `ReplayCard` class. The second definition (around line 758) was overriding the first, but only the first had the new menu items.

**Fix**: Removed the duplicate `contextMenuEvent` and integrated Lock/Unlock, Generate new chord, and Regenerate unlocked actions into the single surviving definition.

**File**: `app/chord_selector.py`, `contextMenuEvent` method

#### Right-Click Not Triggering Context Menu at All

**Symptom**: Right-clicking a `ReplayCard` did nothing — no context menu appeared.

**Root cause**: `mousePressEvent` was consuming all button events without calling `super()` for non-left clicks. Qt needs the base implementation to propagate the event to `contextMenuEvent`.

**Fix**: 
1. Added `super().mousePressEvent(event)` for non-left button clicks
2. Explicitly set `self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)` in `__init__`

**File**: `app/chord_selector.py`, `mousePressEvent` and `__init__`

---

### Architecture Notes

#### Autofill Context
Generation settings are stored as a dict on `ChordMonitorWindow._autofill_context`:

```python
{
    "root_note": int,           # 0-11 (C=0, C#=1, ...)
    "mode_name": str,           # Key into SCALE_MODES
    "allowed_note_counts": [int] | None,  # e.g. [3, 4, 5]
    "allowed_inversions": [int] | None,   # e.g. [0, 1, 2]
    "scale_compliance": float,  # 0.0–1.0
    "lock_influence": float,    # 0.0–1.0
}
```

This context is:
- Set by `AutofillDialog.get_autofill_context()` on initial autofill
- Updated by the Options dialog (`_show_gen_options_dialog`)
- Read by `_regenerate_card` and `_regenerate_unlocked` for per-card generation

#### Degree Index Tracking
Each `ReplayCard` in the chord monitor stores `_degree_index` (the scale degree it was generated from, 0–6). This allows regeneration to produce a new chord **for the same scale degree**, not a random degree.

#### Weighted Pool Generation
`_build_weighted_pool()` constructs a list of `(root, chord_type, notes, weight)` tuples across 4 tiers:

```
Tier 1: Diatonic          (weight = 1.0, always)
Tier 2: Modal interchange  (weight = (1-compliance) * 0.8, when compliance < 95%)
Tier 3: Secondary dominants (weight = (0.7-compliance) * 0.9, when compliance < 70%)
Tier 4: Chromatic          (weight = (0.4-compliance) * 0.6, when compliance < 40%)
```

`_weighted_sample_unique()` then picks from this pool without duplicating (root, type) combos.

---

### Files Changed

| File | Summary |
|------|---------|
| `app/chord_autofill.py` | Added `apply_inversion`, `_build_weighted_pool`, `_analyze_locked_chords`, `_apply_lock_influence`, `_weighted_sample_unique`; expanded `generate_varied_diatonic_chords` and `generate_single_alternative` with compliance/influence params; added Generation Options UI to AutofillDialog |
| `app/chord_monitor_window.py` | Added `_show_gen_options_dialog`, `_get_locked_chords`, `_regenerate_card`, `_regenerate_unlocked`; fixed drift in `_play_exact_notes`; added Options button to header |
| `app/chord_selector.py` | Added lock state (`_locked`, `toggle_lock`, `paintEvent`); fixed context menu and mouse event handling; integrated Lock/Regenerate actions |
| `app/midi_chord_loader.py` | New module for parsing MIDI chord library files |

---

*Last updated: February 6, 2026*
