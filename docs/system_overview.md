# Octavium System Overview

This diagram illustrates how control flows from the CLI launcher into the Qt application, how the main window manages different performance surfaces, and how MIDI messages reach external devices.

```mermaid
flowchart TD
    A["run.py launcher"] --> X["Import app.main (select mido backend: rtmidi -> pygame)"]
    X --> B["app.main.run()"]
    B --> C["QApplication + APP_STYLES"]
    B --> D["MainWindow"]
    D -->|initializes| E["MidiOut wrapper"]
    E --> F["mido backend (RtMidi or pygame)"]
    F --> G["External MIDI Device"]
    D --> H{Layout Type}
    H --> I["KeyboardWidget (default, create_piano_by_size)"]
    H --> J["PadGridWidget (create_pad_grid_layout)"]
    H --> K["FadersWidget"]
    H --> L["XYFaderWidget"]
    H --> M["HarmonicTableWidget"]
    I --> E
    J --> E
    K --> E
    L --> E
    M --> E
    D --> N["Menus & Shortcuts"]
    N --> D
    N --> P["File > New Keyboard Window"]
    P --> Q["MainWindow (new window)"]
    Q -. reuses same MidiOut .-> E
    D --> O["Window State (in-memory) (channel, zoom, sustain, voices)"]
    O --> D
```
