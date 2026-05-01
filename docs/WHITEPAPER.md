# Octavium: An Accessibility-First Virtual MIDI Performance and Generation Environment

**A Technical White Paper**

Version 1.0 — May 2026
Author: Owen Kent

---

## Abstract

Octavium is a desktop software environment that decouples MIDI musical performance from physical keyboards, replacing the keybed with mouse-driven virtual surfaces designed for users with limited or no physical keyboard access — including users with motor disabilities. The system pairs a multi-window Qt-based performance suite (pianos of various sizes, an isomorphic Harmonic Table, a chord pad, drum pads, and CC controllers) with **Modulune**, an algorithmic generative engine that produces continuously evolving impressionistic piano textures and streams them as MIDI to any DAW. This paper describes the design goals, system architecture, harmonic and rhythmic generation algorithms, MIDI subsystem, and the testing and continuous-integration practices that make the codebase maintainable across platforms.

---

## 1. Introduction

### 1.1 Motivation

Most virtual instruments assume a physical MIDI keyboard. For users who rely primarily on a mouse — whether due to ergonomic preference, workspace constraints, or motor impairment — the on-screen keyboards bundled with DAWs are typically afterthoughts: hard to read at common zoom levels, easy to mis-click, and unable to sustain notes beyond the duration of a mouse press. Octavium reframes the on-screen keyboard as a first-class instrument. Every interaction — click, drag, right-click, sustain, latch — is designed around the assumption that the mouse is the only input device.

### 1.2 Goals

Octavium pursues four design goals:

1. **Accessibility-first interaction.** Mouse-only operation must be sufficient for expressive performance. No interaction should require simultaneous keypresses or fine modifier-key timing.
2. **Surface diversity.** Different musical tasks call for different control surfaces. A pianist may want a 61-key piano; a producer may want a chord pad; a sound designer may want an XY pad routed to filter cutoff.
3. **DAW interoperability.** The host environment must remain MIDI-out only — Octavium produces no audio itself and stays compatible with any DAW or hardware synthesizer that accepts MIDI.
4. **Generative complement.** Beyond direct performance, the system should be capable of self-driving music generation, so that a user can produce evolving piano textures hands-free.

### 1.3 Contributions

This paper documents:

- A multi-surface, multi-window Qt application architecture in which all surfaces share a single MIDI output.
- Mouse-interaction primitives — drag-glide, right-click latch, sustain-with-clearing-visuals — that recover the expressive affordances of physical keys.
- Modulune, a real-time piano-texture engine built on modal harmony, contour-shaped melody, and probabilistic rhythm.
- A pragmatic CI/typing strategy that draws a hard line between pure-logic modules (type-checked) and GUI modules (test-checked), avoiding the cost of fighting Pyright over PySide6 types.

---

## 2. System Overview

Octavium ships as a Python package with two top-level subsystems:

| Subsystem | Role | Primary Modules |
|-----------|------|-----------------|
| **Octavium** (`app/`) | The instrument: user-driven, mouse-first MIDI performance | `launcher.py`, `main.py`, `keyboard_widget.py`, `harmonic_table.py`, `chord_monitor_window.py`, `pad_grid.py`, `faders.py`, `xy_fader.py`, `midi_io.py`, `scale.py` |
| **Modulune** (`modulune/`) | The player: algorithmic generative piano engine | `engine.py`, `harmony.py`, `melody.py`, `rhythm.py`, `window.py` |

The two share a single MIDI output abstraction (`app.midi_io.MidiOut`) so that performance surfaces and the generator can coexist on the same virtual port without conflict.

### 2.1 Control Flow

```
run.py
  └── app.main.run()
        ├── QApplication + APP_STYLES
        ├── MidiOut (shared, mido backend: rtmidi -> pygame fallback)
        └── Launcher
              ├── MainWindow (per-surface)
              │     ├── KeyboardWidget (25/49/61/73/76/88-key)
              │     ├── HarmonicTableWidget
              │     ├── PadGridWidget
              │     ├── FadersWidget
              │     └── XYFaderWidget
              ├── ChordMonitorWindow (Chord Pad)
              └── ModuluneWindow → ModuluneEngine
```

All windows reuse the same `MidiOut` instance. Opening a second piano window does not open a second port; this avoids "MIDI port in use" errors common to multi-window MIDI apps on Windows.

### 2.2 Tech Stack

- **Language:** Python 3.9+ (tested through 3.13).
- **GUI:** PySide6 (Qt 6 bindings).
- **MIDI:** `mido` with a runtime-selected backend — `rtmidi` when available, `pygame.midi` as a fallback. The fallback exists because not every Python build ships with a working `python-rtmidi` wheel, and pygame-bundled MIDI keeps the project installable on stock Python distributions.
- **Audio output:** Octavium produces no audio. It is MIDI-out only and depends on the user's DAW or external synthesizer for sound generation.
- **Tests:** `pytest`. **Type checking:** Pyright (logic modules only).

---

## 3. Performance Surfaces

Octavium exposes seven distinct control surfaces, each tuned to a different musical task.

### 3.1 Pianos (25 / 49 / 61 / 73 / 76 / 88-key)

The piano widget is a custom-painted QWidget rather than a row of QPushButton instances. The reasons are practical:

- **Hit-testing accuracy.** Black keys overlap white keys; a rectangular widget hierarchy mis-routes clicks at the boundary. Custom painting plus a polygonal hit-test gives correct behavior at all zoom levels.
- **Drag-glide.** Click-and-drag must continuously update which note is sounding as the cursor crosses key boundaries. Implementing this on top of widget hierarchies requires global mouse tracking that fights the Qt event model. A single widget with a `mouseMoveEvent` handler is simpler and faster.
- **Visual feedback.** "Pressed" and "held" states need to be visually distinct: pressed keys are darker, held (latched or sustained) keys are highlighted. Custom painting renders both states in one repaint pass.

#### 3.1.1 Sustain semantics

Most software pianos implement sustain by suppressing `note_off` until the sustain pedal lifts — and as a side effect, leave the keys looking pressed for as long as they sound. This makes it impossible to see *what you just touched* during a held chord. Octavium decouples the two:

- `note_off` is suppressed while sustain is on (correct musical behavior).
- The visual "pressed" state clears on mouse release (so the user can see which keys they last hit).

A `Hold Visuals During Sustain` view option restores the conventional behavior for users who prefer it.

#### 3.1.2 Right-click latch

Latch is a per-note toggle: right-clicking a key starts it sounding indefinitely; right-clicking again stops it. Crucially, latch operates *per note*. A user can latch a bass note, then play melody on top with normal clicks, without the melody notes being latched. This is the design feature that makes mouse-only chord-plus-melody performance practical.

### 3.2 Harmonic Table

The Harmonic Table is an isomorphic hexagonal layout where:

- Horizontal movement = a perfect fifth.
- One diagonal = major third; the other diagonal = minor third.

The result is that any chord shape is the same physical shape in any key — a geometric property the standard 12-tone keyboard lacks. Octavium colors the hexagons by octave for navigation and highlights all instances of a duplicate pitch when one is played, which makes the harmonic relationships visible at a glance.

### 3.3 Chord Pad

A 4×4 grid of "chord cards." Each card holds a chord (set of MIDI notes) and is hold-to-play: pressing the card sounds the chord, releasing stops it. Cards support drag-and-drop reordering, and a *drag-to-edit* gesture: dragging a card onto an adjacent piano window loads the chord onto the keyboard for editing, and dragging the resulting selection back to a card slot saves it.

The Chord Pad supports a "humanize" mode that adds bounded random offsets to per-note velocity and onset timing, so repeated triggers do not sound mechanically identical.

### 3.4 Pad Grid, Faders, and XY Fader

- **Pad Grid:** a 4×4 drum grid emitting fixed-pitch `note_on`/`note_off` pairs, suitable for triggering sample slots in a DAW.
- **Faders:** 8 vertical sliders, each mapped to a configurable MIDI CC (control change) number.
- **XY Fader:** a 2D pad whose X and Y coordinates each emit a configurable CC. The natural mapping is (X = filter cutoff, Y = resonance) but any pair of CCs works.

---

## 4. MIDI Subsystem

### 4.1 Backend Selection

`app/midi_io.py` selects a `mido` backend at import time, preferring `rtmidi` when its Python binding is installed and falling back to `pygame.midi`. The fallback exists because `python-rtmidi` requires a compiled C extension; on machines without a build toolchain or matching wheel, falling back to the always-bundled `pygame.midi` keeps the application launchable.

### 4.2 Shutdown Robustness

Mido's `BasePort.__del__` raises `RuntimeError: pygame.midi not initialised` if `pygame.midi.quit()` ran before the port was garbage-collected — a routine condition during interpreter shutdown. Octavium monkey-patches `BasePort.__del__` to swallow that specific error, eliminating spurious tracebacks on exit. All other exceptions propagate normally.

### 4.3 Shared Output Across Windows

`MidiOut` is created once in the launcher and passed to every surface window. This pattern:

- Avoids contention on virtual MIDI ports (loopMIDI on Windows refuses concurrent senders to the same port).
- Simplifies channel routing — channel selection is per-surface, but the underlying port is shared.
- Centralizes the panic / all-notes-off behavior triggered by `Esc`.

---

## 5. Modulune: Generative Piano Engine

Modulune is Octavium's algorithmic counterpart. Where Octavium asks "what does the user want to play?", Modulune asks "what should the system play, given a small parameter set?". It is intentionally not an AI/ML system — it is a deterministic-with-controlled-randomness composition engine grounded in tonal music theory.

### 5.1 Engine Architecture

Modulune separates concerns across three modules:

| Module | Responsibility |
|--------|----------------|
| `harmony.py` | Scale definitions, chord construction, chord-progression rules |
| `melody.py` | Phrase generation along contour shapes |
| `rhythm.py` | Time signature handling, density-driven onset patterns |
| `engine.py` | Orchestrates harmony + melody + rhythm, schedules MIDI events on a real-time loop, exposes runtime control |

A central `EngineConfig` dataclass holds every tunable parameter (tempo, key root, scale, tension, density, dual-hand textures, MIDI channel) and is updated atomically while the engine runs.

### 5.2 Harmony

`harmony.py` defines 14 scale types, encoded as semitone-interval tuples:

```python
SCALE_INTERVALS = {
    ScaleType.MAJOR:           (0, 2, 4, 5, 7, 9, 11),
    ScaleType.LYDIAN:          (0, 2, 4, 6, 7, 9, 11),
    ScaleType.WHOLE_TONE:      (0, 2, 4, 6, 8, 10),
    ScaleType.PENTATONIC_MAJOR:(0, 2, 4, 7, 9),
    # ...etc.
}
```

A `Scale` is a `(root_midi, scale_type)` pair; chord construction stacks intervals from the scale to build triads, sevenths, and extensions (9th, 11th, 13th). The "tension" knob biases the chord chooser toward extensions and modal-interchange substitutions when high, and toward consonant root-position triads when low.

### 5.3 Melody

The melody engine generates phrases shaped by *contour types* — abstract gestures (ascending, arch, wave, descending) that constrain the next-note search. For each phrase:

1. A contour is chosen (or specified by the caller).
2. A target note count and rhythmic skeleton are sampled from the rhythm engine.
3. Notes are drawn from the active scale, with each step's pitch chosen to keep the running line within the contour envelope.

This produces melodic lines that feel directional rather than random-walk.

### 5.4 Rhythm

The rhythm engine generates onset patterns from a time signature and a density parameter (0.0–1.0). Onsets are placed on a metric grid (16th- or 32nd-note resolution), with metric weights biasing onsets toward strong beats. Higher density loosens the bias, producing busier, more uniform textures.

### 5.5 Dual-Hand Textures

Modulune renders right-hand and left-hand textures independently, each with its own register, density, velocity range, and pattern type:

- **Right hand:** Shimmering Chords, Flowing Arpeggios, Melodic Fragments, Sparse Meditation, Layered Voices, Impressionist Wash.
- **Left hand:** Sustained Bass, Broken Chords, Alberti Bass, Block Chords, Rolling Octaves, Sparse Roots.

A user can run only the right hand (an arpeggiator), only the left hand (a bass generator), or both (a duet).

### 5.6 Real-Time Control

The engine runs on a worker thread, sleeping to the next scheduled tick and emitting MIDI on the shared `MidiOut`. All `EngineConfig` fields can be mutated from the GUI thread mid-performance. Tempo, key, mode, density, and tension all respond on the next bar boundary; texture switches respond on the next phrase.

---

## 6. CI and Type-Checking Strategy

Octavium runs CI on every push and PR via GitHub Actions. The workflow has two jobs:

### 6.1 Test Matrix

Tests run on the cross product of:

- **OS:** Ubuntu, Windows
- **Python:** 3.11, 3.13

That is four configurations per CI run. Cross-OS matters because `mido` backend behavior, default file-path semantics, and Qt event timing differ between platforms.

### 6.2 Selective Type Checking

Pyright runs only on **pure-logic modules**:

```
app/scale.py
app/models.py
app/chord_suggestions.py
app/preferences.py
modulune/harmony.py
modulune/melody.py
modulune/rhythm.py
```

GUI modules (PySide6/pygame-heavy) are deliberately excluded. The rationale: PySide6's signal/slot stubs have known typing gaps, and Pyright errors against them are noise, not bugs. Type-checking the logic modules gets the safety benefit where it matters (scale arithmetic, chord construction, persistence) without paying the cost of fighting framework stubs. Tests catch regressions in the GUI layer.

---

## 7. Accessibility Considerations

Octavium's accessibility posture is concrete, not aspirational:

| Concern | Octavium's Response |
|---------|-------------------|
| User cannot press multiple keys simultaneously | Right-click latch holds individual notes indefinitely. Sustain holds an entire performance. |
| User cannot drag without losing track of position | Visual feedback for *both* "pressed" and "held" states; held state persists across releases. |
| User has limited fine-motor precision | Variable zoom (50%–200%) scales hit targets. Larger key sizes are available without changing layout. |
| User cannot use a physical MIDI keyboard | Every musical interaction is reachable from the mouse alone. Keyboard shortcuts are conveniences, never requirements. |
| User cannot perform fast lines | Modulune generates lines algorithmically; the user becomes a conductor adjusting tempo/density/key in real time. |

The Modulune integration is itself an accessibility feature: a user who cannot perform fast keyboard runs can still produce evolving piano textures by manipulating high-level musical parameters.

---

## 8. Distribution

Octavium is a Python source distribution today, with PyInstaller-based packaging in the `installer/` directory for producing standalone executables. The chord library — a ~30 MB collection of MIDI chord files used by the Chord Pad's autofill feature — is **not** bundled by default; users opt in by running `scripts/fetch_midi_library.ps1`. This keeps the base install small and avoids redistributing third-party MIDI material.

---

## 9. Limitations and Future Work

- **No internal audio engine.** Octavium is MIDI-out only and depends on a virtual MIDI port (loopMIDI on Windows, IAC on macOS). A built-in sampler would remove the DAW-setup step for new users.
- **No MIDI input.** The system does not currently accept incoming MIDI; e.g., a foot-switch sustain pedal cannot drive Octavium's sustain. MIDI input is a natural extension and would not require architectural change.
- **Modulune is rule-based.** It does not learn from user input. A future version could bias generation toward chord progressions or melodic motifs the user has saved in the Chord Pad.
- **VST hosting.** A documented but unimplemented direction (`docs/MCP_VST_INTEGRATION.md`) is to host a VST instrument inside Octavium so the application can be self-contained.

---

## 10. Conclusion

Octavium demonstrates that a mouse-only musical instrument can be expressive rather than merely functional, given careful attention to interaction primitives (drag-glide, per-note latch, sustain with clearing visuals) and a willingness to ship multiple specialized surfaces rather than one compromise surface. Its companion engine, Modulune, extends the same philosophy to autonomous music generation: a small set of musically meaningful parameters drives an evolving texture engine that any user — regardless of motor ability or keyboard skill — can steer in real time. Together, the two subsystems offer a complete MIDI environment for mouse-first, keyboard-free music making.

---

## Appendix A: References

- **PySide6** — Qt for Python bindings.
- **mido** — MIDI Objects for Python; backend abstraction over rtmidi and pygame.midi.
- **pygame** — Used here only for its `pygame.midi` backend.
- **loopMIDI** — Windows virtual MIDI port driver (Tobias Erichsen).
- **IAC Driver** — macOS Inter-Application Communication MIDI driver, built into Audio MIDI Setup.

## Appendix B: Repository Layout (Selected)

```
Octavium/
├── run.py                      # Entry point
├── app/
│   ├── launcher.py             # Launcher window
│   ├── main.py                 # MainWindow + run()
│   ├── keyboard_widget.py      # Custom-painted piano
│   ├── harmonic_table.py       # Isomorphic hex layout
│   ├── chord_monitor_window.py # Chord Pad
│   ├── pad_grid.py             # 4x4 drum pad grid
│   ├── faders.py               # 8 CC faders
│   ├── xy_fader.py             # 2D CC pad
│   ├── midi_io.py              # MidiOut + backend selection
│   ├── scale.py                # Scale quantization
│   ├── models.py               # Shared dataclasses
│   └── themes.py               # Stylesheets
├── modulune/
│   ├── engine.py               # Real-time generative engine
│   ├── harmony.py              # Scales, chords, progressions
│   ├── melody.py               # Phrase / contour generation
│   ├── rhythm.py               # Onset patterns
│   └── window.py               # Modulune GUI
├── docs/                       # Design docs and integration notes
├── tests/                      # pytest suite
└── .github/workflows/ci.yml    # Test matrix + Pyright
```

---

*Octavium is released under the MIT License. See `LICENSE` for details.*
