# Octavium Known Issues & Maintenance Guide

This document tracks known issues, type-checking warnings, and strategies for keeping the codebase healthy.

---

## Active Type-Checking Warnings

These are Pyright warnings in `app/chord_selector.py` related to the `ReplayArea` vs `ChordMonitorReplayArea` class hierarchy. They are **not runtime errors** — the code works correctly — but the type checker can't verify it statically.

### Cause

`ReplayCard` is typed against the base `ReplayArea` class, but when used inside the Chord Monitor, it's actually parented to `ChordMonitorReplayArea` (a subclass defined in `chord_monitor_window.py`). The subclass adds attributes like `grid_layout`, `placeholder_buttons`, `_create_card_at_slot`, and `sustain` that the base class doesn't declare.

### Affected Attributes

| Attribute | Defined On | Used In |
|-----------|-----------|---------|
| `grid_layout` | `ChordMonitorReplayArea` | `chord_selector.py:464-479` |
| `placeholder_buttons` | `ChordMonitorReplayArea` | `chord_selector.py:870-961` |
| `_create_card_at_slot` | `ChordMonitorReplayArea` | `chord_selector.py:879` |
| `sustain` | `ChordMonitorReplayArea` | `chord_selector.py:573` |

### Strategy

These can be resolved by either:
1. **Adding a Protocol/ABC** that declares the shared interface between `ReplayArea` and `ChordMonitorReplayArea`
2. **Using `TYPE_CHECKING` guards** with `cast()` in `ReplayCard` methods that access monitor-specific attributes
3. **Leaving as-is** — the `hasattr()` guards at runtime prevent crashes; only the type checker complains

**Priority**: Low — cosmetic type warnings only, no runtime impact.

---

## Resolved Issues

### Drift/Humanize Not Working (February 2026)

**Symptom**: Drift slider had no audible effect on chord monitor cards.

**Root cause**: `ChordMonitorReplayArea._play_exact_notes()` played all notes in a tight loop, bypassing the drift logic that only existed in `ReplayCard._play_notes_sustained()` (which was never called for monitor cards).

**Fix**: Added drift reading and `QTimer.singleShot` staggering directly to `_play_exact_notes()`.

**Regression risk**: If the note-off timer (`200 + drift_ms`) is too short for large drift values, notes may cut off. Monitor for drift values > 150ms.

---

### Context Menu Missing Lock/Regenerate Options (February 2026)

**Symptom**: Right-click menu only showed original options (Suggest Next, Next Chord, Edit with Keyboard, Remove).

**Root cause**: Two `contextMenuEvent` definitions in `ReplayCard`. Python silently replaces the first with the second, so the new menu items were overridden.

**Fix**: Merged into a single `contextMenuEvent`. The Lock/Regenerate section is conditionally shown only when the card is inside a Chord Monitor (checks `hasattr(monitor, '_regenerate_card')`).

**Regression risk**: If another `contextMenuEvent` override is added later, the same shadowing bug will recur. **Always search for existing definitions before adding event handlers.**

---

### Right-Click Not Triggering Context Menu (February 2026)

**Symptom**: Right-clicking a ReplayCard produced no response at all.

**Root cause**: `mousePressEvent` consumed all button events without calling `super()` for non-left clicks. Qt's context menu dispatch depends on the base `QWidget.mousePressEvent` being called.

**Fix**: Added `super().mousePressEvent(event)` in the `else` branch for non-left clicks. Also explicitly set `DefaultContextMenu` policy.

**Regression risk**: None — standard Qt pattern.

---

## Common Pitfalls

### 1. Event Handler Shadowing
Python allows redefining methods silently. If a class defines `contextMenuEvent` twice, only the last one survives. **Always grep for existing definitions** before adding/modifying event handlers.

### 2. ReplayArea vs ChordMonitorReplayArea
`ReplayCard` can live in either a basic `ReplayArea` or a `ChordMonitorReplayArea`. Code that accesses monitor-specific attributes must use `hasattr()` / `getattr()` guards. Never assume the card is in a monitor.

### 3. Autofill Context Lifecycle
`_autofill_context` is `None` until the user runs Autofill or opens the Options dialog. All methods reading from it (`_regenerate_card`, `_regenerate_unlocked`) must check for `None` first. The Options dialog creates a default context if none exists.

### 4. QTimer Garbage Collection
`QTimer.singleShot` lambdas can be garbage-collected before firing if nothing holds a reference. The drift implementation in `_play_exact_notes` uses closures with default arguments to avoid this. If adding more timed callbacks, ensure the timer or its parent stays alive.

### 5. Lock State Persistence
Card lock state (`_locked`) is stored in-memory on each `ReplayCard` instance. It is **not persisted** across sessions. If we add save/load for chord grids, lock state needs to be included.

---

## Future Considerations

- **Persistence**: Save/load chord grid state (cards, locks, generation options) to JSON
- **Undo/Redo**: Track regeneration history so the user can revert changes
- **Visual feedback**: Highlight borrowed/chromatic chords differently from diatonic ones
- **Lock influence refinement**: Consider voice-leading proximity, not just chord family matching
- **MIDI Library regeneration**: Currently disabled for MIDI source — could be enabled by randomly picking another file from the same degree/category

---

*Last updated: February 6, 2026*
