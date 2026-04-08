# Octavium TODO

## Completed ✅

### v1.1.1 — Build & Distribution Pipeline (February 2026)
- [x] **EV Code Signing** — Signed Octavium.exe with OK Studio Inc. EV certificate (Sectigo)
- [x] **Windows Installer (InnoSetup)** — Admin install, version detection, optional MIDI library component
- [x] **Build Pipeline** — `build_installer.ps1` automates build → sign → package → sign
- [x] **MIDI Library Externalized** — Removed 15K files from git; fetch via `fetch_midi_library.ps1`
- [x] **Documentation** — CODE_SIGNING.md, BUILD.md rewrite, THIRD_PARTY_LICENSES.md

### v1.1.0 — Chord Monitor Overhaul (January–February 2026)
- [x] **Chord Monitor - Hold to Play** — Hold cards to play chords continuously
- [x] **Chord Monitor - Humanize/Drift** — Stagger note playback with drift slider
- [x] **Auto-Fill Chords (Full Grid)** — 16 slots with varied chord types
- [x] **Chord Card Keyboard Editing** — Right-click → "Edit with Keyboard..."
- [x] **Lock & Regenerate** — Lock favourite cards, regenerate only unlocked
- [x] **Generation Options Dialog** — Key, mode, note counts, inversions, scale compliance, lock influence
- [x] **Scale Compliance** — Slider controls diatonic strictness vs borrowed/chromatic
- [x] **Lock Influence** — Locked chords bias new generation toward similar families
- [x] **Inversion Support** — Root, 1st, 2nd, or 3rd inversion voicings
- [x] **MIDI Library Source** — Autofill from external MIDI chord pack files
- [x] **Context Menu Overhaul** — Lock, Generate new chord, Regenerate unlocked
- [x] **Octavium Launcher** — First window displays available windows

## In Progress 🚧

### Distribution & Revenue
- [ ] **Gumroad Product Listing** — Sell signed installer, pay-what-you-want or tiered
- [ ] **GitHub Sponsors** — Enable sponsorship tiers for ongoing support
- [ ] **Landing Page / Website** — Product page with screenshots, demo video, download link
- [ ] **Product Hunt Launch** — Submit for visibility in the music/creative tools category

## Pending Features 📋

### Product
- [ ] **Save Layouts** — Save and restore window layouts
- [ ] **Persist Chord Grid** — Save/load chord grid state (cards, locks, options) to JSON
- [ ] **Finish Harmonic Table** — Complete harmonic table implementation
- [ ] **Chord Shape Module** — Harmonic Table isomorphic chord shapes
- [ ] **Diatonic Gradient Visualization** — Visual feedback showing scale degree colour
- [ ] **Undo/Redo for Regeneration** — Track regeneration history
- [ ] **Borrowed Chord Highlighting** — Visually distinguish borrowed/chromatic chords
- [ ] **MIDI Library Regeneration** — Per-card regeneration with MIDI file source
- [ ] **Voice-Leading Awareness** — Lock influence considers note proximity
- [ ] **Drum Beat Quantization** — Auto-sync mouse clicks to tempo and beat grid

### Testing & CI
- [x] **Unit Test Suite** — pytest with 119 tests covering scale quantization, chord suggestions, models, Modulune harmony/melody/rhythm engines
- [x] **GitHub Actions CI** — Automated test runs on push/PR (Ubuntu + Windows, Python 3.11 + 3.13), Pyright type-checking
- [ ] **Integration Tests** — MIDI output integration tests (requires loopback MIDI port)
- [ ] **Test Coverage Reporting** — Add pytest-cov and coverage thresholds

### Technical Debt
- [ ] Protocol/ABC for ReplayArea to fix type-checking warnings (see KNOWN_ISSUES.md)

---

*Last updated: April 8, 2026*
