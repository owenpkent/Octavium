"""Simplified Chord Monitor Window - just a 2x4 grid replay area."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QSizePolicy, QMainWindow, QPushButton, QSlider, QCheckBox
)
from PySide6.QtCore import Qt, QMimeData, QEvent, QTimer, QRectF
from PySide6.QtGui import QDrag, QIcon, QPainter, QColor
from typing import List, Optional
from pathlib import Path
import random
from .midi_io import MidiOut
from .chord_selector import ReplayCard, NOTES, CHORD_DEFINITIONS

# Import RangeSlider from keyboard_widget
try:
    from .keyboard_widget import RangeSlider
except Exception:
    # Fallback minimal implementation if import fails
    class RangeSlider(QWidget):
        def __init__(self, minimum=1, maximum=127, low=64, high=100, parent=None):
            super().__init__(parent)
            self._min = int(minimum)
            self._max = int(maximum)
            self._low = int(max(self._min, min(low, maximum)))
            self._high = int(max(self._min, min(high, maximum)))
            self.setFixedHeight(22)
            self.setMinimumWidth(200)
        def setRange(self, minimum: int, maximum: int):
            self._min = int(minimum)
            self._max = int(maximum)
        def setValues(self, low: int, high: int):
            self._low, self._high = int(low), int(high)
            self.update()
        def values(self):
            return int(self._low), int(self._high)
        def _pos_to_value(self, x: float) -> int:
            w = max(1, self.width() - 10)
            frac = min(1.0, max(0.0, (x - 5) / w))
            return int(round(self._min + frac * (self._max - self._min)))
        def _value_to_pos(self, v: int) -> float:
            rng = max(1, self._max - self._min)
            frac = (int(v) - self._min) / rng
            return 5 + frac * (self.width() - 10)
        def paintEvent(self, _):  # type: ignore[override]
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing)
            groove_h = 8
            groove = QRectF(5, self.height() / 2 - groove_h/2, max(1, self.width() - 10), groove_h)
            p.setBrush(QColor('#3a3f46'))
            p.setPen(QColor('#2a2f35'))
            p.drawRoundedRect(groove, 3, 3)
            x1 = self._value_to_pos(self._low)
            x2 = self._value_to_pos(self._high)
            sel = QRectF(min(x1, x2), groove.top(), max(2.0, abs(x2 - x1)), groove_h)
            p.setBrush(QColor('#61b3ff'))
            p.setPen(QColor('#2f82e6'))
            p.drawRoundedRect(sel, 3, 3)
            handle_w, handle_h = 12, 20
            for xv in (x1, x2):
                handle = QRectF(xv - handle_w/2, self.height() / 2 - handle_h/2, handle_w, handle_h)
                p.setBrush(QColor('#eaeaea'))
                p.setPen(QColor('#5a5f66'))
                p.drawRoundedRect(handle, 3, 3)
            p.end()


class ChordMonitorReplayArea(QWidget):
    """A 2x4 grid replay area for chord cards - styled like pad grid."""
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: QWidget = None):
        super().__init__(parent)
        self.midi = midi_out
        self.midi_channel = midi_channel
        self.cards: List[ReplayCard] = []
        self.sustain: bool = False
        
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            ChordMonitorReplayArea {
                background-color: #1e2127;
            }
        """)
        
        # Create 2x4 grid layout
        grid_layout = QGridLayout(self)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(10)
        self.grid_layout = grid_layout
        
        # Button size (similar to pad grid)
        btn_size = 80
        
        # Create empty placeholder buttons for all 8 slots (2 rows x 4 columns)
        self.grid_positions: List[Optional[ReplayCard]] = [None] * 8
        self.placeholder_buttons: List[QPushButton] = []
        
        for i in range(8):
            row = i // 4
            col = i % 4
            
            # Create empty placeholder button styled like pad grid
            placeholder = QPushButton("")
            placeholder.setCheckable(False)
            placeholder.setFixedSize(btn_size, btn_size)
            placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            placeholder.setStyleSheet("""
                QPushButton {
                    background: #2b2f36;
                    color: #ddd;
                    border: 2px solid #3b4148;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    border: 2px solid #3b4148;
                }
            """)
            placeholder.setAcceptDrops(True)
            placeholder.setFocusPolicy(Qt.NoFocus)
            
            # Install event filter to handle drops on buttons
            placeholder.installEventFilter(self)
            
            self.placeholder_buttons.append(placeholder)
            self.grid_layout.addWidget(placeholder, row, col)
        
        # Calculate fixed size based on buttons and spacing
        gap = 10
        margins = 20
        width = (btn_size * 4) + (gap * 3) + margins
        height = (btn_size * 2) + (gap * 1) + margins
        self.setFixedSize(width, height)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    
    def eventFilter(self, obj, event):  # type: ignore
        """Handle drag and drop events on placeholder buttons."""
        if obj in self.placeholder_buttons:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasText():  # type: ignore
                    event.setDropAction(Qt.CopyAction)  # type: ignore
                    event.accept()  # type: ignore
                    return True
            elif event.type() == QEvent.Type.DragMove:
                if event.mimeData().hasText():  # type: ignore
                    event.setDropAction(Qt.CopyAction)  # type: ignore
                    event.accept()  # type: ignore
                    return True
            elif event.type() == QEvent.Type.Drop:
                if event.mimeData().hasText():  # type: ignore
                    # obj is the button being dropped on
                    button = obj  # type: ignore
                    
                    # Calculate which slot this button occupies
                    # Find the button's index in placeholder_buttons
                    try:
                        button_index = self.placeholder_buttons.index(button)
                    except ValueError:
                        # Button not found, use position calculation
                        drop_pos = event.pos()  # type: ignore
                        # Convert button local pos to widget pos
                        widget_pos = button.mapTo(self, drop_pos)  # type: ignore
                        button_index = self._find_slot_at_position(widget_pos)
                    
                    if button_index is not None:
                        # Get the chord data
                        data = event.mimeData().text()  # type: ignore
                        parts = data.split(":")
                        root_note_str = parts[0]
                        chord_type = parts[1]
                        root_note = int(root_note_str)
                        
                        # Parse actual notes if present
                        actual_notes = None
                        if len(parts) >= 3 and parts[2]:
                            try:
                                actual_notes = [int(n) for n in parts[2].split(",") if n.strip()]
                            except (ValueError, AttributeError):
                                actual_notes = None
                        
                        # Replace any existing card at this slot
                        old_card = self.grid_positions[button_index]
                        if old_card is not None:
                            old_card.deleteLater()
                            self.cards.remove(old_card)
                            self.grid_positions[button_index] = None
                        
                        # Remove placeholder button
                        button.hide()
                        button.setParent(None)
                        button.deleteLater()
                        self.placeholder_buttons[button_index] = None
                        
                        # Create new card at this slot
                        self._create_card_at_slot(button_index, root_note, chord_type, actual_notes)
                        event.setDropAction(Qt.CopyAction)  # type: ignore
                        event.accept()  # type: ignore
                        return True
                    
                    # Fallback: handle as regular button drop
                    self._handle_drop_on_button(button, event)  # type: ignore
                    return True
        return super().eventFilter(obj, event)
    
    def _handle_drop_on_button(self, button: QPushButton, event):  # type: ignore
        """Handle a drop event on a specific placeholder button."""
        if not event.mimeData().hasText():  # type: ignore
            return
        
        data = event.mimeData().text()  # type: ignore
        try:
            parts = data.split(":")
            root_note_str = parts[0]
            chord_type = parts[1]
            root_note = int(root_note_str)
            
            # Parse actual notes if present
            actual_notes = None
            if len(parts) >= 3 and parts[2]:
                try:
                    actual_notes = [int(n) for n in parts[2].split(",") if n.strip()]
                except (ValueError, AttributeError):
                    actual_notes = None
            
            # Find which slot this button is in
            slot_index = self.placeholder_buttons.index(button)
            
            # Remove placeholder button
            button.hide()
            button.setParent(None)
            button.deleteLater()
            self.placeholder_buttons[slot_index] = None
            
            # Replace any existing card at this slot
            old_card = self.grid_positions[slot_index]
            if old_card is not None:
                old_card.deleteLater()
                self.cards.remove(old_card)
                self.grid_positions[slot_index] = None
            
            # Create new card at this slot
            self._create_card_at_slot(slot_index, root_note, chord_type, actual_notes)
            
            event.setDropAction(Qt.CopyAction)  # type: ignore
            event.accept()  # type: ignore
        except Exception:
            pass

    def dragEnterEvent(self, event):
        """Accept drag events on the widget itself."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def dragMoveEvent(self, event):
        """Handle drag move on the widget itself."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.CopyAction)
            event.accept()

    def dropEvent(self, event):
        """Handle dropped chord card on the widget itself (fallback).
        
        This should only handle drops that don't land on a specific card or button.
        Individual cards handle their own drops via dropEvent.
        """
        if not event.mimeData().hasText():
            return
        
        # Check if drop was handled by a child widget (card or button)
        # If so, don't process here
        drop_pos = event.pos()  # type: ignore
        
        # Check if dropping on an existing card
        for slot_idx, card in enumerate(self.grid_positions):
            if card is not None and card.isVisible():
                # Get card's geometry
                card_geom = card.geometry()
                if card_geom.contains(self.mapFromGlobal(event.globalPos())):  # type: ignore
                    # Let the card handle its own drop
                    return
        
        # Check if dropping on a placeholder button
        for slot_idx, button in enumerate(self.placeholder_buttons):
            if button is not None and button.isVisible():
                button_geom = button.geometry()
                if button_geom.contains(self.mapFromGlobal(event.globalPos())):  # type: ignore
                    # Let the button's event filter handle it
                    return
        
        # If we get here, drop is in empty space - find slot by position
        data = event.mimeData().text()
        try:
            parts = data.split(":")
            root_note_str = parts[0]
            chord_type = parts[1]
            root_note = int(root_note_str)
            
            # Parse actual notes if present
            actual_notes = None
            if len(parts) >= 3 and parts[2]:
                try:
                    actual_notes = [int(n) for n in parts[2].split(",") if n.strip()]
                except (ValueError, AttributeError):
                    actual_notes = None
            
            # Find which slot the drop occurred over based on position
            slot_index = self._find_slot_at_position(drop_pos)
            
            # Only use the calculated slot - don't fallback to first slot
            # This ensures we replace the card where the drop actually happened
            if slot_index is not None:
                # Replace existing card at this slot if there is one
                old_card = self.grid_positions[slot_index]
                if old_card is not None:
                    old_card.deleteLater()
                    self.cards.remove(old_card)
                    self.grid_positions[slot_index] = None
                
                # Remove placeholder button if it exists
                button = self.placeholder_buttons[slot_index] if slot_index < len(self.placeholder_buttons) else None
                if button:
                    button.hide()
                    button.setParent(None)
                    button.deleteLater()
                    self.placeholder_buttons[slot_index] = None
                
                # Create new card at this slot
                self._create_card_at_slot(slot_index, root_note, chord_type, actual_notes)
            
            event.setDropAction(Qt.CopyAction)  # type: ignore
            event.accept()  # type: ignore
        except Exception:
            pass
    
    def _find_slot_at_position(self, pos) -> Optional[int]:
        """Find which grid slot (0-7) contains the given position."""
        try:
            btn_size = 80
            gap = 10
            margins = 10
            
            # Get position relative to this widget
            x = pos.x()  # type: ignore
            y = pos.y()  # type: ignore
            
            # Adjust for margins
            x = x - margins
            y = y - margins
            
            # Calculate which column (0-3) - check if within button bounds
            col = int(x // (btn_size + gap))
            if col < 0 or col >= 4:
                return None
            
            # Check if x is actually within a button (not in gap)
            col_start = col * (btn_size + gap)
            if x < col_start or x >= col_start + btn_size:
                return None
            
            # Calculate which row (0-1) - check if within button bounds
            row = int(y // (btn_size + gap))
            if row < 0 or row >= 2:
                return None
            
            # Check if y is actually within a button (not in gap)
            row_start = row * (btn_size + gap)
            if y < row_start or y >= row_start + btn_size:
                return None
            
            # Convert to slot index
            slot_index = row * 4 + col
            if 0 <= slot_index < 8:
                return slot_index
        except Exception:
            pass
        return None
    
    def _create_card_at_slot(self, slot_index: int, root_note: int, chord_type: str, actual_notes: Optional[List[int]]):
        """Create a new chord card at the specified slot."""
        row = slot_index // 4
        col = slot_index % 4
        
        # Create new card (styled like pad button)
        card = ReplayCard(root_note, chord_type, self, actual_notes)
        # Store slot index on card for easy lookup
        card._slot_index = slot_index  # type: ignore
        # Update card styling to match pad grid
        card.setFixedSize(80, 80)  # Match button size
        card.setStyleSheet("""
            ReplayCard {
                background: #2b2f36;
                color: #ddd;
                border: 2px solid #3b4148;
                border-radius: 10px;
                padding: 2px;
            }
            ReplayCard QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #fff;
            }
            ReplayCard:hover {
                border: 2px solid #2f82e6;
                background: #3a3f46;
            }
        """)
        
        # Adjust label sizes and layout margins for smaller button
        layout = card.layout()
        if layout:
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(2)
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    if isinstance(widget, QLabel):
                        # Make root note label larger, chord type smaller
                        if i == 0:  # Root note label
                            widget.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff;")
                        else:  # Chord type label
                            widget.setStyleSheet("font-size: 9px; color: #aaa;")
                            widget.setWordWrap(True)
        
        self.cards.append(card)
        self.grid_positions[slot_index] = card
        
        # Add to grid
        self.grid_layout.addWidget(card, row, col)
    
    def _create_placeholder_at(self, slot_index: int):
        """Create a placeholder button at the given slot index."""
        btn_size = 80
        row = slot_index // 4
        col = slot_index % 4
        
        placeholder = QPushButton("")
        placeholder.setCheckable(False)
        placeholder.setFixedSize(btn_size, btn_size)
        placeholder.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        placeholder.setStyleSheet("""
            QPushButton {
                background: #2b2f36;
                color: #ddd;
                border: 2px solid #3b4148;
                border-radius: 10px;
            }
            QPushButton:hover {
                border: 2px solid #3b4148;
            }
        """)
        placeholder.setAcceptDrops(True)
        placeholder.setFocusPolicy(Qt.NoFocus)
        placeholder.installEventFilter(self)
        
        self.placeholder_buttons[slot_index] = placeholder
        self.grid_layout.addWidget(placeholder, row, col)

    def _replay_chord(self, root_note: int, chord_type: str):
        """Play the chord when card is clicked."""
        self._play_chord(root_note, chord_type)
    
    def _play_exact_notes(self, notes: list[int]):
        """Play exact MIDI notes (preserves octave and voicing)."""
        if not notes:
            return
        
        # Get velocity from parent window if available
        velocity = 100
        if hasattr(self, '_parent_window'):
            parent = self._parent_window
            if hasattr(parent, '_get_velocity'):
                velocity = parent._get_velocity()
        
        # Play all notes
        for note in notes:
            self.midi.note_on(note, velocity, self.midi_channel)
        
        # Only schedule note offs if sustain is off
        if not self.sustain:
            def release_notes():
                for note in notes:
                    self.midi.note_off(note, self.midi_channel)
            QTimer.singleShot(200, release_notes)

    def _play_chord(self, root_note: int, chord_type: str):
        """Play a chord using MIDI."""
        if chord_type not in CHORD_DEFINITIONS:
            return
        
        _, intervals = CHORD_DEFINITIONS[chord_type]
        base_note = 60 + root_note  # C4 + root offset
        
        # Get velocity from parent window if available
        velocity = 100
        if hasattr(self, '_parent_window'):
            parent = self._parent_window
            if hasattr(parent, '_get_velocity'):
                velocity = parent._get_velocity()
        
        # Play all notes of the chord
        for interval in intervals:
            note = base_note + interval
            self.midi.note_on(note, velocity, self.midi_channel)
        
        # Only schedule note offs if sustain is off
        if not self.sustain:
            def release_notes():
                for interval in intervals:
                    note = base_note + interval
                    self.midi.note_off(note, self.midi_channel)
            QTimer.singleShot(200, release_notes)

    def set_channel(self, channel: int):
        """Update MIDI channel."""
        self.midi_channel = channel
    
    def set_sustain(self, sustain: bool):
        """Set sustain mode."""
        self.sustain = sustain
        # If turning sustain off, release all currently playing notes
        if not sustain:
            # Note: We don't track individual playing notes, so this is a limitation
            # In a full implementation, we'd track active notes per card
            pass


class ChordMonitorWindow(QMainWindow):
    """Simplified window containing just a 2x4 grid replay area."""
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Chord Monitor")
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Header with sustain and all notes off buttons
        header_layout = QHBoxLayout()
        header_label = QLabel("Chord Monitor")
        header_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff; padding: 10px;")
        header_layout.addWidget(header_label)
        
        # Sustain button
        self.sustain_btn = QPushButton("Sustain: Off")
        self.sustain_btn.setCheckable(True)
        self.sustain_btn.setCursor(Qt.PointingHandCursor)
        self.sustain_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                padding: 6px 16px;
                color: #fff;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
            }
            QPushButton:checked {
                background-color: #2f82e6;
                border: 2px solid #2a6fc2;
                color: white;
            }
            QPushButton:checked:hover {
                background-color: #2a6fc2;
            }
        """)
        self.sustain_btn.clicked.connect(self._toggle_sustain)
        header_layout.addWidget(self.sustain_btn)
        
        # All Notes Off button - match keyboard/pad grid style
        self.all_off_btn = QPushButton("All Notes Off")
        self.all_off_btn.setCursor(Qt.PointingHandCursor)
        self.all_off_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 16px;
                border-radius: 4px;
                border: 1px solid #888;
                background-color: #fafafa;
                color: #222;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
            }
            QPushButton:pressed {
                background-color: #e5e5e5;
            }
        """)
        # Store base stylesheet for flash/revert behavior
        try:
            self._all_off_btn_base_qss = str(self.all_off_btn.styleSheet())
        except Exception:
            self._all_off_btn_base_qss = ""
        self.all_off_btn.clicked.connect(self._all_notes_off_clicked)
        header_layout.addWidget(self.all_off_btn)
        
        layout.addLayout(header_layout)
        
        # Velocity controls
        velocity_layout = QHBoxLayout()
        velocity_layout.setSpacing(10)
        
        vel_label = QLabel("Velocity:")
        vel_label.setStyleSheet("color: #aaa;")
        velocity_layout.addWidget(vel_label)
        
        # Single velocity slider (when randomization is off)
        self.vel_slider = QSlider(Qt.Horizontal)
        self.vel_slider.setMinimum(1)
        self.vel_slider.setMaximum(127)
        self.vel_slider.setValue(100)
        self.vel_slider.setFixedWidth(200)
        self.vel_slider.setFixedHeight(20)
        self.vel_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3b4148;
                height: 6px;
                background: #2b2f36;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #2f82e6;
                border: 1px solid #2a6fc2;
                width: 16px;
                height: 16px;
                border-radius: 8px;
                margin: -5px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #4a9fff;
            }
        """)
        velocity_layout.addWidget(self.vel_slider)
        
        # Range slider (when randomization is on)
        self.vel_range = RangeSlider(1, 127, low=80, high=110, parent=self)
        self.vel_range.setFixedWidth(200)
        self.vel_range.setMinimumHeight(22)
        self.vel_range.setFixedHeight(22)
        self.vel_range.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        velocity_layout.addWidget(self.vel_range)
        
        # Randomize checkbox
        self.vel_random_chk = QCheckBox("Randomize")
        self.vel_random_chk.setChecked(True)
        self.vel_random_chk.setStyleSheet("""
            QCheckBox {
                color: #aaa;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 2px solid #3b4148;
                border-radius: 3px;
                background: #2b2f36;
            }
            QCheckBox::indicator:checked {
                background: #2f82e6;
                border: 2px solid #2a6fc2;
            }
        """)
        self.vel_random_chk.toggled.connect(self._toggle_vel_random)
        velocity_layout.addWidget(self.vel_random_chk)
        
        # Initialize visibility
        self.vel_slider.setVisible(False)  # Hide single slider initially (random is on)
        self.vel_range.setVisible(True)    # Show range slider
        
        velocity_layout.addStretch()
        layout.addLayout(velocity_layout)
        
        # Replay area (2x4 grid)
        self.replay_area = ChordMonitorReplayArea(midi_out, midi_channel, central_widget)
        # Store reference to parent window in replay area for velocity access
        self.replay_area._parent_window = self
        layout.addWidget(self.replay_area, alignment=Qt.AlignCenter)
        
        layout.addStretch()
        
        # Calculate appropriate window size for 2x4 grid
        # Each button is 80x80, with spacing and margins
        btn_size = 80
        spacing = 10
        margins = 20
        width = (btn_size * 4) + (spacing * 3) + margins + 40  # 4 columns
        height = (btn_size * 2) + (spacing * 1) + margins + 100  # 2 rows + header
        self.resize(width, height)
        self.setMinimumSize(width, height)
    
    def set_channel(self, channel: int):
        """Update MIDI channel."""
        self.replay_area.set_channel(channel)
    
    def _toggle_sustain(self):
        """Toggle sustain mode."""
        sustain = self.sustain_btn.isChecked()
        self.replay_area.set_sustain(sustain)
        self.sustain_btn.setText(f"Sustain: {'On' if sustain else 'Off'}")
    
    def _toggle_vel_random(self, checked: bool):
        """Switch between fixed velocity slider and range slider."""
        random_mode = bool(checked)
        try:
            self.vel_slider.setVisible(not random_mode)
            self.vel_range.setVisible(random_mode)
        except Exception:
            pass
    
    def _get_velocity(self) -> int:
        """Get velocity based on current settings (randomized or fixed)."""
        if self.vel_random_chk.isChecked():
            low, high = self.vel_range.values()
            return random.randint(min(low, high), max(low, high))
        else:
            return self.vel_slider.value()
    
    def _all_notes_off_clicked(self):
        """Handle All Notes Off button click."""
        try:
            self._flash_all_off_button()
        except Exception:
            pass
        self._perform_all_notes_off()
    
    def _perform_all_notes_off(self):
        """Send note_off for all MIDI notes (0-127) on the current channel."""
        try:
            # Send CC120: All Sound Off, CC123: All Notes Off
            self.replay_area.midi.cc(120, 0, self.replay_area.midi_channel)
            self.replay_area.midi.cc(123, 0, self.replay_area.midi_channel)
        except Exception:
            pass
        
        # Belt-and-suspenders: stop all notes 0..127
        try:
            for n in range(128):
                self.replay_area.midi.note_off(n, self.replay_area.midi_channel)
        except Exception:
            pass
    
    def _flash_all_off_button(self, duration_ms: int = 150):
        """Temporarily set All Notes Off button to blue to indicate action, then revert."""
        btn = getattr(self, 'all_off_btn', None)
        if not isinstance(btn, QPushButton):
            return
        try:
            base_qss = getattr(self, '_all_off_btn_base_qss', str(btn.styleSheet()))
        except Exception:
            base_qss = ""
        # Blue flash style matching Sustain/Latch blue
        flash_qss = (
            "QPushButton {"
            "  padding: 6px 16px;"
            "  border-radius: 4px;"
            "  color: white;"
            "  background-color: #3498db;"
            "  border: 1px solid #2980b9;"
            "  font-weight: bold;"
            "}"
            "QPushButton:hover { background-color: #2f8ccc; }"
            "QPushButton:pressed { background-color: #2a7fb8; }"
        )
        try:
            btn.setStyleSheet(flash_qss)
        except Exception:
            return
        # Revert after delay
        try:
            QTimer.singleShot(max(50, int(duration_ms)), lambda b=btn, q=base_qss: b.setStyleSheet(q))
        except Exception:
            # Fallback: immediate revert if timer unavailable
            try:
                btn.setStyleSheet(base_qss)
            except Exception:
                pass
    
    def closeEvent(self, event):  # type: ignore[override]
        """Handle window close event."""
        # Notify parent to update menu state
        try:
            if hasattr(self, '_parent_main') and self._parent_main:
                parent = self._parent_main
                if hasattr(parent, 'menu_actions') and 'chord_monitor' in parent.menu_actions:
                    parent.menu_actions['chord_monitor'].setChecked(False)
                    if hasattr(parent, 'keyboard') and hasattr(parent.keyboard, 'set_chord_monitor'):
                        parent.keyboard.set_chord_monitor(False)
                # Clear reference
                parent.chord_monitor_window = None
        except Exception:
            pass
        super().closeEvent(event)

