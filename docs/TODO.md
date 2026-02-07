# Octavium TODO

## Completed Features

- [x] **Chord Monitor - Hold to Play** - Hold cards to play chords continuously
- [x] **Chord Monitor - Humanize/Drift** - Stagger note playback with drift slider (direction, range, randomize)
- [x] **Auto-Fill Chords (Full Grid)** - Autofill populates all 16 slots with varied chord types (triads, 7ths, 9ths, sus, add, 6ths)
- [x] **Chord Card Keyboard Editing** - Right-click → "Edit with Keyboard..." with interactive mini-keyboard
- [x] **Lock & Regenerate** - Lock favourite cards, regenerate only the unlocked ones
- [x] **Generation Options Dialog** - On-the-fly control of key, mode, note counts, inversions, scale compliance, lock influence
- [x] **Scale Compliance** - Slider controls diatonic strictness vs borrowed/chromatic chord generation
- [x] **Lock Influence** - Slider controls how much locked chords bias new generation toward similar families
- [x] **Inversion Support** - Generated chords can be voiced in root, 1st, 2nd, or 3rd inversion
- [x] **MIDI Library Source** - Autofill can load chords from external MIDI chord pack files
- [x] **Context Menu Overhaul** - Right-click cards for Lock, Generate new chord, Regenerate unlocked

## Pending Features

- [ ] **Octavium Launcher** - First window displays a list of available windows that can be opened
- [ ] **Windows Installer** - Create installer using InnoSetup
- [ ] **Save Layouts** - Ability to save and restore window layouts
- [ ] **Finish Harmonic Table** - Complete harmonic table implementation
- [ ] **Chord Shape Module** - Take advantage of Harmonic Table's isomorphic properties
- [ ] **Diatonic Gradient Visualization** - Visual feedback when playing chords showing scale degree colour
- [ ] **Persist Chord Grid** - Save/load chord grid state (cards, locks, options) to JSON
- [ ] **Undo/Redo for Regeneration** - Track regeneration history so user can revert
- [ ] **Borrowed Chord Highlighting** - Visually distinguish borrowed/chromatic chords from diatonic
- [ ] **MIDI Library Regeneration** - Enable per-card regeneration when using MIDI file source
- [ ] **Voice-Leading Awareness** - Lock influence could also consider note proximity, not just chord family

## Research & Planning

- [ ] InnoSetup integration for Windows installer
- [ ] Protocol/ABC for ReplayArea to fix type-checking warnings (see KNOWN_ISSUES.md)

---

*Last updated: February 6, 2026*
