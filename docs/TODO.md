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
<<<<<<< HEAD
- [ ] **Chord Shape Module** - Take advantage of Harmonic Table's isomorphic properties with right-click to select chord shapes
- [ ] **Chord Monitor - Hold to Play** - Allow holding down keys to play chords continuously
- [ ] **Chord Monitor - Humanize Option** - Add humanize option to stagger note playback instead of playing all at once
- [ ] **Auto-Fill Chords with Diatonic Gradient** - Auto-populate Chord Monitor with diatonic chords based on key and mode selection (WIP)
- [ ] **Chord Card Keyboard Editing** - Right-click chord cards to edit them using an interactive mini-keyboard (WIP)
- [ ] **Drum Beat Quantization** - Auto-sync mouse clicks to tempo and beat grid for drum sequencing

## In Progress Features

### Chord Monitor Autofill (January 2026) - WIP
- **Autofill Dialog** (WIP): Click "Autofill..." button to open dialog with:
  - Key selection (C through B)
  - Mode/scale selection with emotional descriptions (Major, Minor, Dorian, Lydian, etc.)
  - Quick emotion presets (Happy, Sad, Dreamy, Dark, Jazzy, etc.)
  - Mini keyboard preview showing scale notes
  - Chord preview widgets with Roman numeral degrees
  - "Preview All" to hear the chord progression
- **Edit with Keyboard** (WIP): Right-click any chord card → "Edit with Keyboard..." to:
  - Interactive 2-octave mini keyboard
  - Click keys to toggle note selection
  - Preview the chord before saving
  - Chord detection updates the card label automatically
- **TODO**: Test and debug autofill functionality
- **TODO**: Refine UI/UX for dialogs
- **TODO**: Add diatonic gradient visualization when playing chords
=======
- [ ] **Chord Shape Module** - Take advantage of Harmonic Table's isomorphic properties
- [ ] **Diatonic Gradient Visualization** - Visual feedback when playing chords showing scale degree colour
- [ ] **Persist Chord Grid** - Save/load chord grid state (cards, locks, options) to JSON
- [ ] **Undo/Redo for Regeneration** - Track regeneration history so user can revert
- [ ] **Borrowed Chord Highlighting** - Visually distinguish borrowed/chromatic chords from diatonic
- [ ] **MIDI Library Regeneration** - Enable per-card regeneration when using MIDI file source
- [ ] **Voice-Leading Awareness** - Lock influence could also consider note proximity, not just chord family
>>>>>>> 6dce6c45783a2f4399d6e0bc04c3b2fb8e1f1278

## Research & Planning

- [ ] InnoSetup integration for Windows installer
- [ ] Protocol/ABC for ReplayArea to fix type-checking warnings (see KNOWN_ISSUES.md)

---

*Last updated: February 6, 2026*
