import sys
import traceback
from datetime import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMenu, QInputDialog, QMessageBox,
    QDialog, QDialogButtonBox, QFormLayout, QComboBox, QLabel, QWidget
)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QPixmap, QShortcut, QKeySequence
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QUrl
import mido

# Prefer RtMidi backend; silently fall back to pygame if unavailable
try:
    mido.set_backend('mido.backends.rtmidi')
except Exception:
    try:
        mido.set_backend('mido.backends.pygame')
    except Exception:
        pass

from .keyboard_widget import KeyboardWidget
from .midi_io import MidiOut, list_output_names
from .themes import APP_STYLES
from .piano_layout import create_piano_by_size
from .pad_grid import PadGridWidget, create_pad_grid_layout
from .faders import FadersWidget
from .xy_fader import XYFaderWidget
from .harmonic_table import HarmonicTableWidget
from .chord_monitor_window import ChordMonitorWindow


class MainWindow(QMainWindow):
    def __init__(self, app_ref: QApplication, size: int = 49, port_hint: str = "loopMIDI Port 1", midi: MidiOut | None = None):
        super().__init__()
        self.app_ref = app_ref
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception as e:
            try:
                QMessageBox.critical(self, "Harmonic Table Error", f"Failed to switch to Harmonic Table:\n{e}\n\n{traceback.format_exc()}")
            except Exception:
                print("Failed to switch to Harmonic Table:", e)
                print(traceback.format_exc())
        # Initialize state and build default Piano keyboard
        self.current_size = size
        self.current_scale = 1.0
        self.current_channel = 1
        self.chord_monitor_window: ChordMonitorWindow | None = None
        # Track if MIDI is shared (from launcher) to prevent port changes
        self.midi_is_shared = midi is not None
        # Create or reuse MIDI
        if midi is None:
            try:
                midi = MidiOut(port_name_contains=port_hint)
            except Exception as e:
                QMessageBox.critical(self, "MIDI Error", f"Failed to open MIDI output (hint '{port_hint}'):\n{e}")
                raise
        # Build initial widget
        self.current_layout_type = 'piano'
        layout = create_piano_by_size(size)
        # Show header only on 25-key keyboard
        show_header = (size == 25)
        self.keyboard = KeyboardWidget(layout, midi, title=f"Piano {size}-Key -> {port_hint}", show_header=show_header, scale=self.current_scale)
        self.keyboard.port_name = port_hint
        self.keyboard.set_channel(self.current_channel)
        self.setCentralWidget(self.keyboard)
        self._update_window_title()
        self._resize_for_layout(self.keyboard.layout_model)
        QTimer.singleShot(0, lambda: (
            self.keyboard.adjustSize(),
            self._resize_for_layout(None),
            self.adjustSize()
        ))
        # Ensure MIDI closes on exit
        try:
            self.app_ref.aboutToQuit.connect(lambda: self._safe_close_midi())
        except Exception:
            pass
        # Build menus last
        self._build_menus()

    def set_harmonic_table(self):
        """Switch to the Harmonic Table widget."""
        try:
            self.current_layout_type = 'harmonic'
            new_widget = HarmonicTableWidget(self.keyboard.midi, scale=getattr(self.keyboard, 'ui_scale', 1.0))
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
            self.setCentralWidget(new_widget)
            try:
                self.keyboard.deleteLater()
            except Exception:
                pass
            self.keyboard = new_widget
            self.keyboard.set_channel(self.current_channel)
            # Update menu checks
            try:
                for k, act in getattr(self, 'size_actions', {}).items():
                    if isinstance(k, int):
                        act.setChecked(False)
                if 'pad4x4' in self.size_actions:
                    self.size_actions['pad4x4'].setChecked(False)
                if 'faders' in self.size_actions:
                    self.size_actions['faders'].setChecked(False)
                if 'xy' in self.size_actions:
                    self.size_actions['xy'].setChecked(False)
                if 'harmonic' in self.size_actions:
                    self.size_actions['harmonic'].setChecked(True)
                if 'chord_selector' in self.size_actions:
                    self.size_actions['chord_selector'].setChecked(False)
            except Exception:
                pass
            try:
                self._update_faders_menu_enabled(); self._update_xy_menu_enabled()
            except Exception:
                pass
            self._update_window_title()
            self._resize_for_layout(None)
            self.keyboard.adjustSize()
            self.adjustSize()
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(None),
                self.adjustSize()
            ))
        except Exception:
            pass

    def _update_xy_menu_enabled(self):
        try:
            act = self.menu_actions.get('xy_cc')
            if isinstance(act, QAction):
                act.setEnabled(isinstance(self.keyboard, XYFaderWidget))
        except Exception:
            pass

    def open_xy_cc_dialog(self):
        """Dropdowns for two CC numbers (X and Y)."""
        try:
            if not isinstance(self.keyboard, XYFaderWidget):
                QMessageBox.information(self, "XY Fader", "Switch to Keyboard > XY Fader to edit CC assignments.")
                return
            # current
            try:
                ccx, ccy = self.keyboard.get_cc_numbers()  # type: ignore[attr-defined]
            except Exception:
                ccx, ccy = 1, 74
            dlg = QDialog(self)
            dlg.setWindowTitle("Configure XY CCs")
            form = QFormLayout(dlg)
            cbx, cby = QComboBox(dlg), QComboBox(dlg)
            for n in range(128):
                cbx.addItem(str(n), n)
                cby.addItem(str(n), n)
            cbx.setCurrentIndex(max(0, min(127, int(ccx))))
            cby.setCurrentIndex(max(0, min(127, int(ccy))))
            form.addRow(QLabel("X CC"), cbx)
            form.addRow(QLabel("Y CC"), cby)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg)  # type: ignore[attr-defined]
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            form.addRow(buttons)
            if dlg.exec() != QDialog.Accepted:  # type: ignore[attr-defined]
                return
            try:
                self.keyboard.set_cc_numbers(int(cbx.currentData()), int(cby.currentData()))  # type: ignore[attr-defined]
            except Exception:
                QMessageBox.warning(self, "XY Fader", "Unable to apply CC numbers to XY Fader.")
                return
        except Exception:
            pass

    def _build_menus(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        new_action = QAction("New Keyboard Window", self)
        new_action.triggered.connect(self.new_keyboard_window)
        file_menu.addAction(new_action)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu (Mod/Pitch wheels) — place right after File
        view_menu = menubar.addMenu("&View")
        self.menu_actions = getattr(self, 'menu_actions', {})
        show_mod = QAction("Show Mod Wheel", self)
        show_mod.setCheckable(True)
        show_mod.setChecked(bool(self.menu_actions.get('show_mod', False)))
        show_mod.toggled.connect(lambda checked: (
            self.menu_actions.__setitem__('show_mod', bool(checked)),
            self._apply_show_mod_wheel(checked),
            self._resize_for_layout(None),
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(None),
                self.adjustSize()
            ))
        ))
        view_menu.addAction(show_mod)
        show_pitch = QAction("Show Pitch Wheel", self)
        show_pitch.setCheckable(True)
        show_pitch.setChecked(bool(self.menu_actions.get('show_pitch', False)))
        show_pitch.toggled.connect(lambda checked: (
            self.menu_actions.__setitem__('show_pitch', bool(checked)),
            self._apply_show_pitch_wheel(checked),
            self._resize_for_layout(None),
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(None),
                self.adjustSize()
            ))
        ))
        view_menu.addAction(show_pitch)
        # Visual hold preference (keep visuals pressed during sustain): moved here; default unchecked
        visual_hold = QAction("Hold Visuals During Sustain", self)
        visual_hold.setCheckable(True)
        # default unchecked unless previously set
        visual_hold.setChecked(bool(self.menu_actions.get('visual_hold_checked', False)))
        def _toggle_visual_hold(checked: bool):
            try:
                self.keyboard.visual_hold_on_sustain = checked  # type: ignore[attr-defined]
                # Persist the checked state
                self.menu_actions['visual_hold_checked'] = checked
                # Re-sync visuals when toggled, without touching notes
                try:
                    st = self.keyboard.style()
                    for btn in self.keyboard.key_buttons.values():  # type: ignore[attr-defined]
                        st.unpolish(btn)
                        st.polish(btn)
                        btn.update()
                except Exception:
                    pass
            except Exception:
                pass
        visual_hold.triggered.connect(_toggle_visual_hold)
        view_menu.addAction(visual_hold)
        # Chord Monitor option (window only, inline display is always on)
        chord_monitor = QAction("Chord Monitor", self)
        chord_monitor.setCheckable(True)
        chord_monitor.setChecked(bool(self.menu_actions.get('chord_monitor', False)))
        def _toggle_chord_monitor(checked: bool):
            try:
                # The inline chord display is always on (keyboard.chord_monitor = True)
                # This menu only controls the separate chord monitor window
                self.menu_actions['chord_monitor'] = checked
                # Open or close chord monitor window
                if checked:
                    self._open_chord_monitor_window()
                else:
                    self._close_chord_monitor_window()
            except Exception:
                pass
        chord_monitor.triggered.connect(_toggle_chord_monitor)
        view_menu.addAction(chord_monitor)
        # Drag While Sustain option
        drag_while_sustain = QAction("Drag While Sustain", self)
        drag_while_sustain.setCheckable(True)
        drag_while_sustain.setChecked(bool(self.menu_actions.get('drag_while_sustain_checked', False)))
        def _toggle_drag_while_sustain(checked: bool):
            try:
                self.keyboard.drag_while_sustain = checked  # type: ignore[attr-defined]
                # Persist the checked state
                self.menu_actions['drag_while_sustain_checked'] = checked
            except Exception:
                pass
        drag_while_sustain.triggered.connect(_toggle_drag_while_sustain)
        view_menu.addAction(drag_while_sustain)
        # Persist
        self.menu_actions['show_mod'] = show_mod.isChecked()
        self.menu_actions['show_pitch'] = show_pitch.isChecked()
        self.menu_actions['view_show_mod'] = show_mod
        self.menu_actions['view_show_pitch'] = show_pitch
        self.menu_actions['visual_hold'] = visual_hold
        self.menu_actions['chord_monitor'] = chord_monitor
        self.menu_actions['drag_while_sustain'] = drag_while_sustain
        # Apply current selections
        try:
            self._apply_show_mod_wheel(show_mod.isChecked())
            self._apply_show_pitch_wheel(show_pitch.isChecked())
            # Apply visual hold default (unchecked) or previous
            try:
                self.keyboard.visual_hold_on_sustain = visual_hold.isChecked()  # type: ignore[attr-defined]
            except Exception:
                pass
            # Inline chord display is always on by default (keyboard.chord_monitor = True)
            # Don't open the chord monitor window automatically
            # User can open it via View > Chord Monitor menu if desired
            # Ensure styles reflect any change
            try:
                st = self.keyboard.style()
                for btn in self.keyboard.key_buttons.values():  # type: ignore[attr-defined]
                    st.unpolish(btn)
                    st.polish(btn)
                    btn.update()
            except Exception:
                pass
            # Ensure window reflects current selection after menus are built
            self._resize_for_layout(None)
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(None),
                self.adjustSize()
            ))
        except Exception:
            pass

        # Build the rest of the menus (Zoom, Keyboard, MIDI, Voices, Channel, Help)
        self._build_remaining_menus(menubar, view_menu)

    def set_xy_fader(self):
        """Switch to the XY Fader widget."""
        try:
            self.current_layout_type = 'xy'
            new_widget = XYFaderWidget(self.keyboard.midi, scale=getattr(self.keyboard, 'ui_scale', 1.0))
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
            self.setCentralWidget(new_widget)
            try:
                self.keyboard.deleteLater()
            except Exception:
                pass
            self.keyboard = new_widget
            self.keyboard.set_channel(self.current_channel)
            # Update menu checks
            try:
                for k, act in getattr(self, 'size_actions', {}).items():
                    if isinstance(k, int):
                        act.setChecked(False)
                if 'pad4x4' in self.size_actions:
                    self.size_actions['pad4x4'].setChecked(False)
                if 'faders' in self.size_actions:
                    self.size_actions['faders'].setChecked(False)
                if 'xy' in self.size_actions:
                    self.size_actions['xy'].setChecked(True)
                if 'chord_selector' in self.size_actions:
                    self.size_actions['chord_selector'].setChecked(False)
            except Exception:
                pass
            try:
                self._update_faders_menu_enabled(); self._update_xy_menu_enabled()
            except Exception:
                pass
            self._update_window_title()
            # use widget sizeHint for window sizing
            self._resize_for_layout(None)
            self.keyboard.adjustSize()
            self.adjustSize()
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(None),
                self.adjustSize()
            ))
        except Exception:
            pass

    def _build_remaining_menus(self, menubar, view_menu):
        # Zoom submenu with preset levels
        try:
            zoom_menu = view_menu.addMenu("Zoom")
            self.zoom_group = QActionGroup(self)
            self.zoom_group.setExclusive(True)
            presets: list[tuple[str, float]] = [
                ("50%", 0.50), ("75%", 0.75), ("90%", 0.90), ("100% (default)", 1.00),
                ("110%", 1.10), ("125%", 1.25), ("150%", 1.50), ("200%", 2.00),
            ]
            prev_zoom = float(self.menu_actions.get('zoom_scale', self.current_scale))
            self.zoom_actions: list[QAction] = []
            for label, scale in presets:
                act = QAction(label, self)
                act.setCheckable(True)
                if abs(scale - prev_zoom) < 1e-6:
                    act.setChecked(True)
                    self.current_scale = scale
                act.triggered.connect(lambda checked, sc=scale: self.set_zoom(sc))
                self.zoom_group.addAction(act)
                zoom_menu.addAction(act)
                self.zoom_actions.append(act)
            self.menu_actions['zoom_actions'] = self.zoom_actions
            self.menu_actions['zoom_group'] = self.zoom_group
            self.menu_actions['zoom_scale'] = self.current_scale
            try:
                QShortcut(QKeySequence("Ctrl++"), self, activated=self._zoom_in_step)  # type: ignore[arg-type]
                QShortcut(QKeySequence("Ctrl+="), self, activated=self._zoom_in_step)  # type: ignore[arg-type]
                QShortcut(QKeySequence("Ctrl+-"), self, activated=self._zoom_out_step)  # type: ignore[arg-type]
            except Exception:
                pass
        except Exception:
            pass

        # Keyboard menu (exclusive size selection)
        kb_menu = menubar.addMenu("&Keyboard")
        self.size_group = QActionGroup(self)
        self.size_group.setExclusive(True)
        self.size_actions = {}
        for size in [25, 49, 61, 73, 76, 88]:
            act = QAction(f"{size} Keys", self)
            act.setCheckable(True)
            if size == self.current_size:
                act.setChecked(True)
            act.triggered.connect(lambda checked, s=size: self.set_keyboard_size(s))
            self.size_group.addAction(act)
            kb_menu.addAction(act)
            self.size_actions[size] = act
        kb_menu.addSeparator()
        pad_act = QAction("4x4 Beat Grid", self)
        pad_act.setCheckable(True)
        pad_act.setChecked(False)
        pad_act.triggered.connect(lambda checked: self.set_pad_grid())
        self.size_group.addAction(pad_act)
        kb_menu.addAction(pad_act)
        self.size_actions['pad4x4'] = pad_act
        faders_act = QAction("Faders", self)
        faders_act.setCheckable(True)
        faders_act.setChecked(False)
        faders_act.triggered.connect(lambda checked: self.set_faders())
        self.size_group.addAction(faders_act)
        kb_menu.addAction(faders_act)
        self.size_actions['faders'] = faders_act
        xy_act = QAction("XY Fader", self)
        xy_act.setCheckable(True)
        xy_act.setChecked(False)
        xy_act.triggered.connect(lambda checked: self.set_xy_fader())
        self.size_group.addAction(xy_act)
        kb_menu.addAction(xy_act)
        self.size_actions['xy'] = xy_act
        # Harmonic Table option
        harm_act = QAction("Harmonic Table", self)
        harm_act.setCheckable(True)
        harm_act.setChecked(False)
        harm_act.triggered.connect(lambda checked: self.set_harmonic_table())
        self.size_group.addAction(harm_act)
        kb_menu.addAction(harm_act)
        self.size_actions['harmonic'] = harm_act

        # MIDI menu
        midi_menu = menubar.addMenu("&MIDI")
        select_port = QAction("Select Output Port", self)
        select_port.triggered.connect(self.select_midi_port)
        midi_menu.addAction(select_port)
        faders_cc_act = QAction("Configure Faders CCs…", self)
        faders_cc_act.setToolTip("Edit the 8 CC numbers used by the Faders surface (comma-separated)")
        faders_cc_act.triggered.connect(self.open_faders_cc_dialog)
        midi_menu.addAction(faders_cc_act)
        self.menu_actions['faders_cc'] = faders_cc_act
        self._update_faders_menu_enabled()
        xy_cc_act = QAction("Configure XY CCs…", self)
        xy_cc_act.setToolTip("Edit the CC numbers used by the XY Fader (X and Y)")
        xy_cc_act.triggered.connect(self.open_xy_cc_dialog)
        midi_menu.addAction(xy_cc_act)
        self.menu_actions['xy_cc'] = xy_cc_act
        self._update_xy_menu_enabled()

        # Voices (polyphony)
        voices_menu = menubar.addMenu("&Voices")
        self.voices_group = QActionGroup(self)
        self.voices_group.setExclusive(True)
        self.voices_actions = []
        prev_sel = self.menu_actions.get('voices_selected', 'Unlimited')
        unlimited_act = QAction("Unlimited", self)
        unlimited_act.setCheckable(True)
        unlimited_act.setChecked(prev_sel == 'Unlimited')
        def _select_unlimited():
            try:
                self.keyboard.set_polyphony_enabled(False)  # type: ignore[attr-defined]
            except Exception:
                pass
            self.menu_actions['voices_selected'] = 'Unlimited'
        unlimited_act.triggered.connect(lambda checked: _select_unlimited())
        self.voices_group.addAction(unlimited_act)
        voices_menu.addAction(unlimited_act)
        def _select_limited(n: int):
            try:
                self.keyboard.set_polyphony_enabled(True)  # type: ignore[attr-defined]
                self.keyboard.set_polyphony_max(n)  # type: ignore[attr-defined]
            except Exception:
                pass
            self.menu_actions['voices_selected'] = str(n)
        for n in range(1,9):
            act = QAction(f"{n}", self)
            act.setCheckable(True)
            act.setChecked(prev_sel == str(n))
            act.triggered.connect(lambda checked, val=n: _select_limited(val))
            self.voices_group.addAction(act)
            voices_menu.addAction(act)
            self.voices_actions.append(act)
        try:
            labels = [a.text() for a in self.voices_group.actions() if a.isChecked()]
            if not labels:
                unlimited_act.setChecked(True)
                _select_unlimited()
            else:
                sel = labels[0]
                if sel == 'Unlimited':
                    _select_unlimited()
                else:
                    try:
                        _select_limited(int(sel))
                    except Exception:
                        _select_unlimited()
        except Exception:
            pass
        self.menu_actions['voices_actions'] = self.voices_actions
        self.menu_actions['voices_group'] = self.voices_group

        # Channel submenu
        chan_menu = midi_menu.addMenu("Channel")
        self.channel_group = QActionGroup(self)
        self.channel_group.setExclusive(True)
        self.channel_actions = []
        for ch in range(1,17):
            act = QAction(f"{ch}", self)
            act.setCheckable(True)
            if ch == self.current_channel:
                act.setChecked(True)
            act.triggered.connect(lambda checked, c=ch: self.set_channel(c))
            self.channel_group.addAction(act)
            chan_menu.addAction(act)
            self.channel_actions.append(act)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        kb_shortcuts = QAction("Keyboard Shortcuts", self)
        kb_shortcuts.triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(kb_shortcuts)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

    def set_keyboard_size(self, size: int):
        # If already on piano with the same size, do nothing; otherwise allow switch (e.g., from pad grid)
        if size == self.current_size and getattr(self, 'current_layout_type', 'piano') == 'piano':
            return
        self.current_size = size
        self.current_layout_type = 'piano'
        # Rebuild keyboard with same MIDI out
        layout = create_piano_by_size(size)
        # Show header only on 25-key keyboard
        show_header = (size == 25)
        new_keyboard = KeyboardWidget(layout, self.keyboard.midi, show_header=show_header, scale=getattr(self.keyboard, 'ui_scale', 1.0))
        new_keyboard.port_name = self.keyboard.port_name
        new_keyboard.update_window_title()
        self.setCentralWidget(new_keyboard)
        self.keyboard.deleteLater()
        self.keyboard = new_keyboard
        self.keyboard.set_channel(self.current_channel)
        self._update_window_title()
        # Preserve sustain and visual hold preferences
        try:
            if hasattr(self, 'menu_actions'):
                # Visual hold
                if 'visual_hold' in self.menu_actions:
                    self.keyboard.visual_hold_on_sustain = self.menu_actions['visual_hold'].isChecked()
                # Chord monitor
                if 'chord_monitor' in self.menu_actions:
                    chord_monitor_checked = self.menu_actions['chord_monitor'].isChecked() if hasattr(self.menu_actions['chord_monitor'], 'isChecked') else bool(self.menu_actions.get('chord_monitor', False))
                    if hasattr(self.keyboard, 'set_chord_monitor'):
                        self.keyboard.set_chord_monitor(chord_monitor_checked)
                # Drag while sustain
                if 'drag_while_sustain' in self.menu_actions:
                    drag_while_sustain_checked = self.menu_actions['drag_while_sustain'].isChecked() if hasattr(self.menu_actions['drag_while_sustain'], 'isChecked') else bool(self.menu_actions.get('drag_while_sustain_checked', False))
                    self.keyboard.drag_while_sustain = drag_while_sustain_checked
                # Voices (polyphony): apply current selection (Unlimited or 1-8)
                sel = self.menu_actions.get('voices_selected', 'Unlimited')
                try:
                    if sel == 'Unlimited':
                        self.keyboard.set_polyphony_enabled(False)
                    else:
                        self.keyboard.set_polyphony_enabled(True)  # type: ignore[attr-defined]
                        try:
                            self.keyboard.set_polyphony_max(int(sel))
                        except Exception:
                            self.keyboard.set_polyphony_max(8)
                except Exception:
                    pass
                # View menu: wheels visibility
                try:
                    # Prefer live QAction checked states if available
                    mod_checked = bool(self.menu_actions['view_show_mod'].isChecked()) if 'view_show_mod' in self.menu_actions else bool(self.menu_actions.get('show_mod', False))
                    pitch_checked = bool(self.menu_actions['view_show_pitch'].isChecked()) if 'view_show_pitch' in self.menu_actions else bool(self.menu_actions.get('show_pitch', False))
                    self.keyboard.set_show_mod_wheel(mod_checked)
                    self.keyboard.set_show_pitch_wheel(pitch_checked)
                except Exception:
                    pass
        except Exception:
            pass
        # Exclusive check is handled by QActionGroup, ensure correct one is checked
        if hasattr(self, 'size_actions') and size in self.size_actions:
            self.size_actions[size].setChecked(True)
        # Uncheck pad grid if present
        try:
            if hasattr(self, 'size_actions') and 'pad4x4' in self.size_actions:
                self.size_actions['pad4x4'].setChecked(False)
            if hasattr(self, 'size_actions') and 'faders' in self.size_actions:
                self.size_actions['faders'].setChecked(False)
            if hasattr(self, 'size_actions') and 'chord_selector' in self.size_actions:
                self.size_actions['chord_selector'].setChecked(False)
        except Exception:
            pass
        # Resize window for the new layout (immediate + deferred)
        self._resize_for_layout(layout)
        self.keyboard.adjustSize()
        self.adjustSize()
        QTimer.singleShot(0, lambda: (
            self.keyboard.adjustSize(),
            self._resize_for_layout(layout),
            self.adjustSize()
        ))

        # Update checkmarks in menu
        kb_menu: QMenu = self.menuBar().findChild(QMenu, None)  # type: ignore[arg-type,assignment]
        # Not strictly necessary to update checks programmatically; actions will visually toggle by selection.

    def _open_chord_monitor_window(self):
        """Open the chord monitor window."""
        try:
            if self.chord_monitor_window is None or not hasattr(self.chord_monitor_window, 'isVisible') or not self.chord_monitor_window.isVisible():
                self.chord_monitor_window = ChordMonitorWindow(
                    self.keyboard.midi, 
                    self.current_channel - 1,
                    self
                )
                # Store reference to parent for menu updates
                self.chord_monitor_window._parent_main = self  # type: ignore[attr-defined]
                self.chord_monitor_window.set_channel(self.current_channel - 1)
                # Keep reference to prevent GC
                if not hasattr(self.app_ref, "_chord_monitor_windows"):
                    self.app_ref._chord_monitor_windows = []  # type: ignore[attr-defined]
                self.app_ref._chord_monitor_windows.append(self.chord_monitor_window)  # type: ignore[attr-defined]
                self.chord_monitor_window.show()
            else:
                self.chord_monitor_window.raise_()
                self.chord_monitor_window.activateWindow()
        except Exception:
            pass
    
    def _close_chord_monitor_window(self):
        """Close the chord monitor window."""
        try:
            if self.chord_monitor_window is not None:
                self.chord_monitor_window.close()
                self.chord_monitor_window = None
        except Exception:
            pass
    
    def select_midi_port(self):
        # Don't allow port changes when using shared MIDI from launcher
        if self.midi_is_shared:
            QMessageBox.information(
                self,
                "MIDI Port",
                "MIDI port is managed by the launcher and cannot be changed.\n\n"
                "Close this window and use the launcher to open windows with different MIDI settings."
            )
            return
        
        ports = list_output_names()
        if not ports:
            QMessageBox.warning(self, "MIDI", "No MIDI output ports found.")
            return
        current = self.keyboard.port_name or (ports[0] if ports else "")
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Select MIDI Output")
        dlg.setLabelText("Port:")
        try:
            dlg.setComboBoxItems(ports)
        except Exception:
            pass
        # preselect current
        try:
            idx = ports.index(current) if current in ports else 0
            dlg.setComboBoxEditable(False)
            dlg.setTextValue(ports[idx])
        except Exception:
            pass
        # Blue bounding box around OK and Cancel
        dlg.setStyleSheet(
            "QPushButton { border: 2px solid #3399ff; border-radius: 4px; padding: 4px 10px; }"
        )
        if dlg.exec() != QMessageBox.Accepted:  # type: ignore[attr-defined]
            return
        port = dlg.textValue()
        if not port:
            return
        midi = MidiOut(port_name_contains=port)
        self.keyboard.set_midi_out(midi, port_name=port)

    def new_keyboard_window(self):
        win = MainWindow(self.app_ref, size=self.current_size, port_hint=self.keyboard.port_name or "", midi=self.keyboard.midi)
        win.set_channel(self.current_channel)
        # Apply current zoom to the new window
        try:
            curr_scale = float(getattr(self.keyboard, 'ui_scale', 1.0))
            win.set_zoom(curr_scale)
        except Exception:
            pass
        # If current layout is pad grid, switch the new window as well
        try:
            cur = getattr(self, 'current_layout_type', 'piano')
            if cur == 'pad4x4':
                win.set_pad_grid()
            elif cur == 'faders':
                win.set_faders()
            elif cur == 'xy':
                win.set_xy_fader()
        except Exception:
            pass
        # Keep reference on QApplication to prevent GC
        if not hasattr(self.app_ref, "_windows"):
            self.app_ref._windows = []  # type: ignore[attr-defined]
        self.app_ref._windows.append(win)  # type: ignore[attr-defined]
        win.show()

    def set_channel(self, channel: int):
        """Set the global MIDI channel (1-16) and update the current keyboard widget and UI."""
        try:
            ch = int(channel)
        except Exception:
            ch = 1
        if ch < 1:
            ch = 1
        if ch > 16:
            ch = 16
        self.current_channel = ch
        # Apply to current keyboard widget
        try:
            if hasattr(self, 'keyboard') and self.keyboard is not None:
                self.keyboard.set_channel(ch)
        except Exception:
            pass
        # Update menu checkmarks if the group exists
        try:
            if hasattr(self, 'channel_group') and self.channel_group is not None:
                for act in self.channel_group.actions():
                    try:
                        act.setChecked(int(act.text()) == ch)
                    except Exception:
                        pass
        except Exception:
            pass
        # Refresh window title
        self._update_window_title()

    def set_zoom(self, scale: float):
        try:
            scale = float(scale)
        except Exception:
            scale = 1.0
        if scale <= 0:
            scale = 1.0
        # If no change, do nothing
        try:
            curr = float(getattr(self.keyboard, 'ui_scale', 1.0))
        except Exception:
            curr = 1.0
        if abs(curr - scale) < 1e-6:
            return
        self.current_scale = scale
        # Rebuild central widget with same layout type and MIDI out, preserving state
        if getattr(self, 'current_layout_type', 'piano') == 'pad4x4':
            layout = create_pad_grid_layout(4, 4)
            new_widget = PadGridWidget(layout, self.keyboard.midi, scale=scale)
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
        elif getattr(self, 'current_layout_type', 'piano') == 'faders':
            layout = None  # not used by FadersWidget
            # Capture current fader state before rebuild
            try:
                prev_vals = self.keyboard.get_values()  # type: ignore[attr-defined]
            except Exception:
                prev_vals = None
            try:
                prev_ccs = self.keyboard.get_cc_numbers()  # type: ignore[attr-defined]
            except Exception:
                prev_ccs = None
            new_widget = FadersWidget(self.keyboard.midi, scale=scale)
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
            # Restore CCs and values without emitting extra CC messages
            try:
                if prev_ccs is not None:
                    new_widget.set_cc_numbers(prev_ccs)
            except Exception:
                pass
            try:
                if prev_vals is not None:
                    new_widget.set_values(prev_vals, emit=False)
            except Exception:
                pass
        elif getattr(self, 'current_layout_type', 'piano') == 'xy':
            layout = None  # not used by XYFaderWidget
            # Capture current xy state
            try:
                prev_xy = self.keyboard.get_values()  # type: ignore[attr-defined]
            except Exception:
                prev_xy = None
            try:
                ccx, ccy = self.keyboard.get_cc_numbers()  # type: ignore[attr-defined]
            except Exception:
                ccx, ccy = (1, 74)
            new_widget = XYFaderWidget(self.keyboard.midi, scale=scale)
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                new_widget.set_cc_numbers(ccx, ccy)
            except Exception:
                pass
            try:
                if prev_xy is not None:
                    new_widget.set_values(prev_xy[0], prev_xy[1], emit=False)
            except Exception:
                pass
        else:
            layout = create_piano_by_size(self.current_size)
            # Show header only on 25-key keyboard
            show_header = (self.current_size == 25)
            new_widget = KeyboardWidget(layout, self.keyboard.midi, show_header=show_header, scale=scale)
            try:
                new_widget.port_name = self.keyboard.port_name  # type: ignore[attr-defined]
            except Exception:
                pass
            try:
                new_widget.update_window_title()  # type: ignore[attr-defined]
            except Exception:
                pass
        self.setCentralWidget(new_widget)
        try:
            self.keyboard.deleteLater()
        except Exception:
            pass
        self.keyboard = new_widget  # keep attribute name consistent
        # Update menus enabled state after rebuild
        try:
            self._update_faders_menu_enabled()
            self._update_xy_menu_enabled()
        except Exception:
            pass
        # Restore channel
        try:
            self.keyboard.set_channel(self.current_channel)
        except Exception:
            pass
        # Restore view menu selections
        try:
            self._apply_show_mod_wheel(bool(self.menu_actions.get('show_mod', False)))
            self._apply_show_pitch_wheel(bool(self.menu_actions.get('show_pitch', False)))
            self.keyboard.visual_hold_on_sustain = bool(self.menu_actions.get('visual_hold_checked', False))  # type: ignore[attr-defined]
            # Restore chord monitor state
            try:
                chord_monitor_action = self.menu_actions.get('chord_monitor')
                if chord_monitor_action and hasattr(chord_monitor_action, 'isChecked'):
                    chord_monitor_checked = chord_monitor_action.isChecked()
                else:
                    chord_monitor_checked = bool(self.menu_actions.get('chord_monitor', False))
                if hasattr(self.keyboard, 'set_chord_monitor'):
                    self.keyboard.set_chord_monitor(chord_monitor_checked)  # type: ignore[attr-defined]
            except Exception:
                pass
        except Exception:
            pass
        # Restore voices (polyphony)
        try:
            sel = self.menu_actions.get('voices_selected', 'Unlimited')
            if sel == 'Unlimited':
                self.keyboard.set_polyphony_enabled(False)  # type: ignore[attr-defined]
            else:
                self.keyboard.set_polyphony_enabled(True)  # type: ignore[attr-defined]
                try:
                    self.keyboard.set_polyphony_max(int(sel))  # type: ignore[attr-defined]
                except Exception:
                    self.keyboard.set_polyphony_max(8)  # type: ignore[attr-defined]
        except Exception:
            pass
        # Persist zoom selection
        self.menu_actions['zoom_scale'] = self.current_scale
        # Update checkmarks in menu
        try:
            if hasattr(self, 'zoom_group'):
                for act in self.zoom_group.actions():
                    txt = act.text()
                    try:
                        pct = 1.0
                        if '%' in txt:
                            pct = float(txt.split('%')[0]) / 100.0
                        if 'default' in txt.lower():
                            pct = 1.0
                    except Exception:
                        pct = 1.0
                    act.setChecked(abs(pct - scale) < 1e-6)
        except Exception:
            pass
        # Resize window for new scale
        self._resize_for_layout(layout)
        self.keyboard.adjustSize()
        self.adjustSize()
        QTimer.singleShot(0, lambda: (
            self.keyboard.adjustSize(),
            self._resize_for_layout(layout),
            self.adjustSize()
        ))

    def _resize_for_layout(self, layout):
        """Resize the window to fit current keyboard content width.
        Prefers the actual `piano_container.width()`; falls back to `columns * 44`.
        """
        # Prefer the central widget's own size hint; this works for both piano and pad grid.
        try:
            kb_hint = self.keyboard.sizeHint()
            content_width = int(kb_hint.width())
            content_height = int(kb_hint.height())
        except Exception:
            content_width = None
            content_height = None

        if content_width is None or content_height is None:
            # Compute content width from piano + optional left panel and controls (whichever is wider)
            content_width = None
            if hasattr(self, 'keyboard') and hasattr(self.keyboard, 'piano_container'):
                try:
                    w_piano = int(self.keyboard.piano_container.width())  # type: ignore[attr-defined]
                except Exception:
                    w_piano = None
                # Include left panel (wheels) width when visible
                try:
                    left_panel = getattr(self.keyboard, 'left_panel', None)
                    w_left = int(left_panel.width()) if (left_panel is not None and left_panel.isVisible()) else 0
                except Exception:
                    w_left = 0
                try:
                    controls_widget = getattr(self.keyboard, 'controls_widget', None)
                    w_controls = int(controls_widget.width()) if controls_widget is not None else 0
                except Exception:
                    w_controls = 0
                if w_piano is not None:
                    content_width = max(w_piano + w_left, w_controls)
            if content_width is None:
                try:
                    columns = getattr(layout, 'columns', 36) or 36
                except Exception:
                    columns = 36
                # Respect current UI scale as used by KeyboardWidget
                try:
                    scale = float(getattr(self.keyboard, 'ui_scale', 1.0))
                except Exception:
                    scale = 1.0
                content_width = int(columns * 44 * scale)  # matches KeyboardWidget white key base width
            # Height: central widget hint if available
            try:
                content_height = max(self.keyboard.minimumSizeHint().height(), self.keyboard.sizeHint().height())
            except Exception:
                content_height = 180

        side_padding = 56  # modest side padding for window chrome
        target_width = int(content_width + side_padding)
        # Height: add menubar height + margin
        try:
            menu_h = self.menuBar().sizeHint().height()
        except Exception:
            menu_h = 0
        # Safety buffer to ensure the menu is never clipped (accounts for DPI/titlebar quirks)
        vertical_padding = 32
        target_height = int(content_height + menu_h + vertical_padding)

        # Update child geometry (piano-specific safe guard)
        try:
            if hasattr(self.keyboard, 'piano_container'):
                self.keyboard.piano_container.updateGeometry()  # type: ignore[attr-defined]
            self.keyboard.updateGeometry()
        except Exception:
            pass

        # For piano widgets, we constrain width to content_width to prevent stretching.
        # For pad grid/other fixed widgets, let their sizeHint govern.
        is_fixed = isinstance(self.keyboard, (PadGridWidget, FadersWidget, XYFaderWidget, HarmonicTableWidget))
        if not is_fixed:
            try:
                self.keyboard.setMinimumWidth(int(content_width))
                self.keyboard.setMaximumWidth(int(content_width))
                self.keyboard.setFixedWidth(int(content_width))
            except Exception:
                pass
        else:
            try:
                # Ensure pad grid uses its hint without external constraints
                self.keyboard.setMinimumSize(self.keyboard.sizeHint())
                self.keyboard.setMaximumSize(self.keyboard.sizeHint())
            except Exception:
                pass

        # Temporarily drop min/max to allow shrinking, then resize, then release
        self.setMinimumSize(0, 0)
        self.setMaximumSize(target_width, target_height)
        self.resize(target_width, target_height)
        self.setMaximumSize(16777215, 16777215)
    def _get_zoom_presets(self) -> list[float]:
        scales: list[float] = []
        try:
            acts = getattr(self, 'zoom_actions', [])
            for act in acts:
                txt = act.text()
                sc = 1.0
                try:
                    if '%' in txt:
                        pct = float(txt.split('%')[0].split()[0])
                        sc = pct / 100.0
                    elif 'default' in txt.lower():
                        sc = 1.0
                except Exception:
                    sc = 1.0
                scales.append(sc)
        except Exception:
            pass
        # Fallback
        if not scales:
            scales = [0.50, 0.75, 0.90, 1.00, 1.10, 1.25, 1.50, 2.00]
        return scales

    def _zoom_in_step(self):
        scales = self._get_zoom_presets()
        curr = float(getattr(self, 'current_scale', 1.0))
        # find nearest index >= curr
        try:
            # ensure ascending
            scales_sorted = sorted(scales)
            idx = 0
            for i, sc in enumerate(scales_sorted):
                if sc >= curr - 1e-6:
                    idx = i
                    break
            # step up if possible, else stay at last
            new_idx = min(idx + 1, len(scales_sorted) - 1)
            self.set_zoom(scales_sorted[new_idx])
        except Exception:
            self.set_zoom(min(2.0, curr * 1.1))

    def _zoom_out_step(self):
        scales = self._get_zoom_presets()
        curr = float(getattr(self, 'current_scale', 1.0))
        try:
            scales_sorted = sorted(scales)
            idx = 0
            for i, sc in enumerate(scales_sorted):
                if sc > curr + 1e-6:
                    idx = max(0, i - 1)
                    break
                idx = i
            new_idx = max(0, idx - 1)
            self.set_zoom(scales_sorted[new_idx])
        except Exception:
            self.set_zoom(max(0.5, curr / 1.1))
    def show_keyboard_shortcuts(self):
        text = (
            "Keyboard shortcuts:\n\n"
            "- Z / X: Octave Down / Up\n"
            "- 1 / 2 / 3: Velocity curve (soft / linear / hard)\n"
            "- Q: Toggle quantize to scale\n"
            "- Esc: All Notes Off\n\n"
            "Mouse:\n"
            "- Click keys to play\n"
            "- Click and drag across keys to glide\n"
        )
        QMessageBox.information(self, "Keyboard Shortcuts", text)

    def show_about_dialog(self):
        year = datetime.now().year
        # Build logo HTML at the top, centered
        logo_html = ""
        try:
            logo_path = Path(__file__).resolve().parent.parent / "Octavium logo.png"
            if logo_path.exists():
                logo_url = QUrl.fromLocalFile(str(logo_path)).toString()
                logo_html = f"<div style='text-align:center; margin-bottom:10px'><img src='{logo_url}' width='320'></div>"
        except Exception:
            pass
        text = (
            f"{logo_html}"
            "<b>Octavium - Virtual MIDI Keyboard</b><br><br>"
            f"(c) {year} Owen Kent<br><br>"
            "Octavium is a virtual on-screen MIDI keyboard designed to be played with the mouse.<br>"
            "It focuses on simple, precise mouse input—no computer keyboard required.<br><br>"
            "<b>Features</b>:<br>"
            "- Multiple keyboard sizes (25/49/61/73/76/88) with realistic black/white key layout<br>"
            "- MIDI output (rtmidi if available, otherwise pygame backend)<br>"
            "- Velocity control with selectable curves (linear/soft/hard)<br>"
            "- Sustain and Latch modes<br>"
            "- Channel selection and quick All Notes Off<br><br>"
            f"Current MIDI Port: {self.keyboard.port_name or 'N/A'}"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("About Octavium")
        msg.setTextFormat(Qt.TextFormat.RichText)  
        msg.setText(text)
        # Blue bounding box around the OK button
        msg.setStyleSheet(
            "QPushButton { border: 2px solid #3399ff; border-radius: 4px; padding: 4px 10px; }"
        )
        msg.exec()

    def _update_window_title(self):
        try:
            title_part = None
            # If the widget exposes a layout_model, use its name
            try:
                title_part = getattr(self.keyboard.layout_model, 'name', None)  # type: ignore[attr-defined]
            except Exception:
                title_part = None
            # If this is the Faders widget, label accordingly
            try:
                if isinstance(self.keyboard, FadersWidget):
                    title_part = 'Faders'
            except Exception:
                pass
            if not title_part:
                title_part = 'Keyboard'
            self.setWindowTitle(f"Octavium [Ch {self.current_channel}] - {title_part}")
        except Exception:
            self.setWindowTitle(f"Octavium [Ch {self.current_channel}]")

    def _safe_close_midi(self):
        try:
            if hasattr(self, 'keyboard') and hasattr(self.keyboard, 'midi') and self.keyboard.midi is not None:
                self.keyboard.midi.close()
        except Exception:
            pass

    def closeEvent(self, event):  # type: ignore[override]
        # Close chord monitor window if open
        try:
            self._close_chord_monitor_window()
        except Exception:
            pass
        # Explicitly close MIDI port before widgets are torn down
        try:
            self._safe_close_midi()
        except Exception:
            pass
        try:
            super().closeEvent(event)
        except Exception:
            try:
                event.accept()
            except Exception:
                pass

    def _apply_show_mod_wheel(self, checked: bool):
        try:
            fn = getattr(self.keyboard, 'set_show_mod_wheel', None)
            if callable(fn):
                fn(bool(checked))
        except Exception:
            pass

    def _apply_show_pitch_wheel(self, checked: bool):
        try:
            fn = getattr(self.keyboard, 'set_show_pitch_wheel', None)
            if callable(fn):
                fn(bool(checked))
        except Exception:
            pass

    def set_pad_grid(self):
        """Switch to a 4x4 beat grid layout/widget."""
        try:
            self.current_layout_type = 'pad4x4'
            layout = create_pad_grid_layout(4, 4)
            new_widget = PadGridWidget(layout, self.keyboard.midi, scale=getattr(self.keyboard, 'ui_scale', 1.0))
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
            self.setCentralWidget(new_widget)
            try:
                self.keyboard.deleteLater()
            except Exception:
                pass
            self.keyboard = new_widget
            self.keyboard.set_channel(self.current_channel)
            # Update menu checks
            try:
                for k, act in getattr(self, 'size_actions', {}).items():
                    if isinstance(k, int):
                        act.setChecked(False)
                if 'pad4x4' in self.size_actions:
                    self.size_actions['pad4x4'].setChecked(True)
                if 'faders' in self.size_actions:
                    self.size_actions['faders'].setChecked(False)
                if 'xy' in self.size_actions:
                    self.size_actions['xy'].setChecked(False)
                if 'chord_selector' in self.size_actions:
                    self.size_actions['chord_selector'].setChecked(False)
            except Exception:
                pass
            try:
                self._update_faders_menu_enabled(); self._update_xy_menu_enabled()
            except Exception:
                pass
            try:
                self._update_faders_menu_enabled()
            except Exception:
                pass
            self._update_window_title()
            self._resize_for_layout(layout)
            self.keyboard.adjustSize()
            self.adjustSize()
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(layout),
                self.adjustSize()
            ))
        except Exception:
            pass

    def set_faders(self):
        """Switch to the Faders surface widget."""
        try:
            self.current_layout_type = 'faders'
            new_widget = FadersWidget(self.keyboard.midi, scale=getattr(self.keyboard, 'ui_scale', 1.0))
            try:
                new_widget.port_name = getattr(self.keyboard, 'port_name', "")  # type: ignore[attr-defined]
            except Exception:
                pass
            self.setCentralWidget(new_widget)
            try:
                self.keyboard.deleteLater()
            except Exception:
                pass
            self.keyboard = new_widget
            self.keyboard.set_channel(self.current_channel)
            # Update menu checks
            try:
                for k, act in getattr(self, 'size_actions', {}).items():
                    if isinstance(k, int):
                        act.setChecked(False)
                if 'pad4x4' in self.size_actions:
                    self.size_actions['pad4x4'].setChecked(False)
                if 'faders' in self.size_actions:
                    self.size_actions['faders'].setChecked(True)
                if 'xy' in self.size_actions:
                    self.size_actions['xy'].setChecked(False)
                if 'chord_selector' in self.size_actions:
                    self.size_actions['chord_selector'].setChecked(False)
            except Exception:
                pass
            try:
                self._update_faders_menu_enabled(); self._update_xy_menu_enabled()
            except Exception:
                pass
            self._update_window_title()
            # use widget sizeHint for window sizing
            self._resize_for_layout(None)
            self.keyboard.adjustSize()
            self.adjustSize()
            QTimer.singleShot(0, lambda: (
                self.keyboard.adjustSize(),
                self._resize_for_layout(None),
                self.adjustSize()
            ))
        except Exception:
            pass

    def _update_faders_menu_enabled(self):
        try:
            act = self.menu_actions.get('faders_cc')
            if isinstance(act, QAction):
                act.setEnabled(isinstance(self.keyboard, FadersWidget))
        except Exception:
            pass

    def open_faders_cc_dialog(self):
        """Prompt for 8 comma-separated CC numbers and apply to the FadersWidget."""
        try:
            if not isinstance(self.keyboard, FadersWidget):
                QMessageBox.information(self, "Faders", "Switch to Keyboard > Faders to edit CC assignments.")
                return
            # Current values
            try:
                current = self.keyboard.get_cc_numbers()  # type: ignore[attr-defined]
            except Exception:
                current = [1, 7, 74, 10, 71, 73, 11, 91]

            dlg = QDialog(self)
            dlg.setWindowTitle("Configure Faders CCs")
            form = QFormLayout(dlg)
            combos: list[QComboBox] = []
            for i in range(8):
                cb = QComboBox(dlg)
                for n in range(128):
                    cb.addItem(str(n), n)
                try:
                    sel = int(current[i]) if i < len(current) else 0
                except Exception:
                    sel = 0
                cb.setCurrentIndex(max(0, min(127, sel)))
                combos.append(cb)
                form.addRow(QLabel(f"Fader {i+1}"), cb)
            buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dlg)  # type: ignore[attr-defined]
            buttons.accepted.connect(dlg.accept)
            buttons.rejected.connect(dlg.reject)
            form.addRow(buttons)
            if dlg.exec() != QDialog.Accepted:  # type: ignore[attr-defined]
                return
            cleaned = [int(cb.currentData()) for cb in combos]
            try:
                self.keyboard.set_cc_numbers(cleaned)  # type: ignore[attr-defined]
            except Exception:
                QMessageBox.warning(self, "Faders", "Unable to apply CC numbers to the current Faders view.")
                return
        except Exception:
            pass

# --- Simple data-entry dialog classes (module-local) could be added here if needed ---

def run():
    from .faders import FadersWidget
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLES)
    # Set application icon as well (project-relative)
    try:
        icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
        app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        pass
    main = MainWindow(app)
    # Keep a ref so it isn't GC'd
    app._windows = [main]  # type: ignore[attr-defined]
    main.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run()
