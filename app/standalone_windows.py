"""Top-level :class:`QMainWindow` wrappers for the launcher's child surfaces.

Each window owns a single Octavium widget (chord selector, pad grid, faders,
or XY fader), wires up a MIDI Channel submenu, and exposes
:meth:`update_midi_out` so the launcher can re-route audio when the port
changes.
"""
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QMenu
from PySide6.QtGui import QIcon, QAction, QActionGroup
from PySide6.QtCore import Qt
from pathlib import Path
from typing import Optional, List
from .midi_io import MidiOut


def _create_midi_channel_menu(window: QMainWindow, current_channel: int, on_channel_change) -> None:
    """Attach a MIDI > Channel submenu of 16 exclusive radio actions.

    Args:
        window: Window whose menu bar receives the new menu.
        current_channel: 1-based channel preselected in the submenu.
        on_channel_change: Callback invoked with the chosen 1-based channel.
    """
    menubar = window.menuBar()
    
    midi_menu = menubar.addMenu("&MIDI")
    chan_menu = midi_menu.addMenu("Channel")
    
    channel_group = QActionGroup(window)
    channel_group.setExclusive(True)
    
    channel_actions: List[QAction] = []
    for ch in range(1, 17):
        act = QAction(f"Channel {ch}", window)
        act.setCheckable(True)
        if ch == current_channel:
            act.setChecked(True)
        act.triggered.connect(lambda checked, c=ch: on_channel_change(c))
        channel_group.addAction(act)
        chan_menu.addAction(act)
        channel_actions.append(act)
    
    window._channel_actions = channel_actions  # type: ignore
    window._channel_group = channel_group  # type: ignore


class ChordSelectorWindow(QMainWindow):
    """Standalone window hosting the chord selector widget."""

    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        """Build the window and embed a fresh :class:`ChordSelectorWidget`."""
        super().__init__(parent)
        from .chord_selector import ChordSelectorWidget
        
        self.setWindowTitle("Chord Selector")
        self.setMinimumSize(400, 600)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        self.chord_selector = ChordSelectorWidget(midi_out, midi_channel, self)
        self.setCentralWidget(self.chord_selector)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)


class PadGridWindow(QMainWindow):
    """Standalone window hosting a 4x4 pad grid starting at C2."""

    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        """Build the window with a default 4x4 pad grid starting at MIDI C2."""
        super().__init__(parent)
        from .pad_grid import PadGridWidget, create_pad_grid_layout
        
        self.midi_channel = midi_channel
        self.setWindowTitle("Pad Grid")
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create a 4x4 pad grid layout with MIDI notes starting at C2 (36)
        # Use the create_pad_grid_layout function to ensure consistent ordering
        layout_model = create_pad_grid_layout(rows=4, cols=4, start_note=36)
        
        self.pad_grid = PadGridWidget(layout_model, midi_out, title="Pad Grid", scale=1.0)
        self.setCentralWidget(self.pad_grid)
        
        # Add MIDI channel menu
        _create_midi_channel_menu(self, midi_channel, self._set_channel)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)
    
    def _set_channel(self, channel: int) -> None:
        """Forward a channel change from the menu to the embedded pad grid."""
        self.midi_channel = channel
        if hasattr(self.pad_grid, 'set_channel'):
            self.pad_grid.set_channel(channel)
        elif hasattr(self.pad_grid, 'midi_channel'):
            self.pad_grid.midi_channel = channel

    def update_midi_out(self, new_midi: MidiOut) -> None:
        """Re-route the embedded pad grid to a new MIDI output."""
        try:
            if hasattr(self.pad_grid, 'set_midi_out'):
                self.pad_grid.set_midi_out(new_midi)
            else:
                self.pad_grid.midi = new_midi
        except Exception:
            pass


class FadersWindow(QMainWindow):
    """Standalone window hosting the faders widget."""

    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        """Build the window and embed a fresh :class:`FadersWidget`."""
        super().__init__(parent)
        from .faders import FadersWidget
        
        self.midi_channel = midi_channel
        self.setWindowTitle("Faders")
        self.setMinimumSize(400, 500)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        self.faders = FadersWidget(midi_out, scale=1.0)
        self.setCentralWidget(self.faders)
        
        # Add MIDI channel menu
        _create_midi_channel_menu(self, midi_channel, self._set_channel)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)
    
    def _set_channel(self, channel: int) -> None:
        """Forward a channel change from the menu to the embedded faders."""
        self.midi_channel = channel
        if hasattr(self.faders, 'set_channel'):
            self.faders.set_channel(channel)
        elif hasattr(self.faders, 'midi_channel'):
            self.faders.midi_channel = channel

    def update_midi_out(self, new_midi: MidiOut) -> None:
        """Re-route the embedded faders to a new MIDI output."""
        try:
            if hasattr(self.faders, 'set_midi_out'):
                self.faders.set_midi_out(new_midi)
            else:
                self.faders.midi = new_midi
        except Exception:
            pass


class XYFaderWindow(QMainWindow):
    """Standalone window hosting the XY fader widget."""

    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        """Build the window and embed a fresh :class:`XYFaderWidget`."""
        super().__init__(parent)
        from .xy_fader import XYFaderWidget
        
        self.midi_channel = midi_channel
        self.setWindowTitle("XY Fader")
        self.setMinimumSize(400, 400)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        self.xy_fader = XYFaderWidget(midi_out, scale=1.0)
        self.setCentralWidget(self.xy_fader)
        
        # Add MIDI channel menu
        _create_midi_channel_menu(self, midi_channel, self._set_channel)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
        """)
    
    def _set_channel(self, channel: int) -> None:
        """Forward a channel change from the menu to the embedded XY fader."""
        self.midi_channel = channel
        if hasattr(self.xy_fader, 'set_channel'):
            self.xy_fader.set_channel(channel)
        elif hasattr(self.xy_fader, 'midi_channel'):
            self.xy_fader.midi_channel = channel

    def update_midi_out(self, new_midi: MidiOut) -> None:
        """Re-route the embedded XY fader to a new MIDI output."""
        try:
            if hasattr(self.xy_fader, 'set_midi_out'):
                self.xy_fader.set_midi_out(new_midi)
            else:
                self.xy_fader.midi = new_midi
        except Exception:
            pass
