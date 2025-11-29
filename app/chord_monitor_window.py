"""Simplified Chord Monitor Window - just a 2x4 grid replay area."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QSizePolicy, QMainWindow, QPushButton, QSlider, QCheckBox, QComboBox, QMenu
)
from PySide6.QtCore import Qt, QMimeData, QEvent, QTimer, QRectF
from PySide6.QtGui import QIcon, QPainter, QColor, QAction, QActionGroup
from typing import List, Optional, TYPE_CHECKING, Union, Any
from pathlib import Path
import random
from .midi_io import MidiOut
from .chord_selector import ReplayCard, NOTES, CHORD_DEFINITIONS

if TYPE_CHECKING:
    from .keyboard_widget import RangeSlider


class ChordMonitorReplayArea(QWidget):
    """A 4x4 grid replay area for chord cards - styled like pad grid."""
    _parent_window: Optional['ChordMonitorWindow']  # For velocity access
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.midi = midi_out
        self.midi_channel = midi_channel
        self.cards: List[ReplayCard] = []
        self.sustain: bool = False
        self._parent_window = None
        self._active_notes: List[int] = []
        
        self.setAcceptDrops(True)
        self.setStyleSheet("""
            ChordMonitorReplayArea {
                background-color: #1e2127;
            }
        """)
        
        # Create 4x4 grid layout
        grid_layout = QGridLayout(self)
        grid_layout.setContentsMargins(10, 10, 10, 10)
        grid_layout.setSpacing(10)
        self.grid_layout = grid_layout
        
        # Button size (similar to pad grid)
        btn_size = 80
        
        # Create empty placeholder buttons for all 16 slots (4 rows x 4 columns)
        self.grid_positions: List[Optional[ReplayCard]] = [None] * 16
        self.placeholder_buttons: List[Optional[QPushButton]] = []
        
        for i in range(16):
            row = i // 4
            col = i % 4
            
            # Create empty placeholder button styled like pad grid
            placeholder = QPushButton("")
            placeholder.setCheckable(False)
            placeholder.setFixedSize(btn_size, btn_size)
            placeholder.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
            placeholder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            
            # Install event filter to handle drops on buttons
            placeholder.installEventFilter(self)
            
            self.placeholder_buttons.append(placeholder)
            self.grid_layout.addWidget(placeholder, row, col)
        
        # Calculate fixed size based on buttons and spacing
        gap = 10
        margins = 20
        width = (btn_size * 4) + (gap * 3) + margins
        height = (btn_size * 4) + (gap * 3) + margins
        self.setFixedSize(width, height)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    
    def eventFilter(self, obj, event):  # type: ignore
        """Handle drag and drop events on placeholder buttons."""
        if obj in self.placeholder_buttons:
            if event.type() == QEvent.Type.DragEnter:
                if event.mimeData().hasText():  # type: ignore
                    event.setDropAction(Qt.DropAction.CopyAction)  # type: ignore
                    event.accept()  # type: ignore
                    return True
            elif event.type() == QEvent.Type.DragMove:
                if event.mimeData().hasText():  # type: ignore
                    event.setDropAction(Qt.DropAction.CopyAction)  # type: ignore
                    event.accept()  # type: ignore
                    return True
            elif event.type() == QEvent.Type.Drop:
                # Check if drop was handled by a child widget (card or button)
                # If so, don't process here
                drop_pos = event.pos()  # type: ignore
                # Convert button local pos to widget pos
                widget_pos = obj.mapTo(self, drop_pos)  # type: ignore
                for slot_idx, card in enumerate(self.grid_positions):
                    if card is not None and card.isVisible():
                        # Get card's geometry
                        card_geom = card.geometry()
                        if card_geom.contains(widget_pos):  
                            # Let the card handle its own drop
                            return super().eventFilter(obj, event)  # type: ignore[arg-type]
                
                # If we get here, drop is in empty space - find slot by position
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
                    
                    # Check if this is a rearrange operation (has slot index in 4th part)
                    source_slot = None
                    if len(parts) >= 4 and parts[3] and parts[3].lstrip('-').isdigit():
                        source_slot = int(parts[3])
                    
                    # Handle rearrange operations - move card to empty slot
                    if source_slot is not None:
                        self._handle_rearrange_to_empty_slot(button_index, source_slot)
                        event.setDropAction(Qt.DropAction.MoveAction)  # type: ignore
                        event.accept()  # type: ignore
                        return True
                    
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
                    
                    # Check if the drop is a rearrange operation
                    if self.grid_positions[button_index] is not None:
                        return True
                    
                    # Create new card at this slot
                    self._create_card_at_slot(button_index, root_note, chord_type, actual_notes)
                    event.setDropAction(Qt.DropAction.CopyAction)  # type: ignore
                    event.accept()  # type: ignore
                    return True
                
                # Fallback: handle as regular button drop
                if isinstance(button, QPushButton):
                    self._handle_drop_on_button(button, event)  # type: ignore
                return True
        return super().eventFilter(obj, event)  # type: ignore[arg-type]
    
    def _handle_rearrange_to_empty_slot(self, target_slot: int, source_slot: int) -> None:
        """Handle moving a card to an empty slot."""
        try:
            if source_slot == target_slot:
                return  # Dropped on itself
            
            # Get the card being dragged
            dragged_card = self.grid_positions[source_slot]
            if dragged_card is None:
                return
            
            # Remove card from old position
            self.grid_layout.removeWidget(dragged_card)
            self.grid_positions[source_slot] = None
            
            # Remove placeholder button at target if it exists
            target_button = self.placeholder_buttons[target_slot]
            if target_button is not None:
                target_button.hide()
                target_button.setParent(None)
                target_button.deleteLater()
                self.placeholder_buttons[target_slot] = None
            
            # Move card to new position
            self.grid_positions[target_slot] = dragged_card
            dragged_card._slot_index = target_slot
            target_row, target_col = target_slot // 4, target_slot % 4
            self.grid_layout.addWidget(dragged_card, target_row, target_col)
            
            # Create placeholder at old position
            self._create_placeholder_at(source_slot)
        except Exception:
            pass

    def _handle_drop_on_button(self, button: QPushButton, event):  # type: ignore
        """Handle a drop event on a specific placeholder button."""
        if not event.mimeData().hasText():  # type: ignore
            return
        
        data = event.mimeData().text()  # type: ignore
        parts = data.split(":")
        
        # Check if this is a rearrange operation (has slot index in 4th part)
        source_slot = None
        if len(parts) >= 4 and parts[3] and parts[3].lstrip('-').isdigit():
            source_slot = int(parts[3])
        
        # Handle rearrange operations - move card to this empty slot
        if source_slot is not None:
            try:
                slot_index = self.placeholder_buttons.index(button)
                self._handle_rearrange_to_empty_slot(slot_index, source_slot)
            except ValueError:
                pass
            return
        
        try:
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
            
            event.setDropAction(Qt.DropAction.CopyAction)  # type: ignore
            event.accept()  # type: ignore
        except Exception:
            pass

    def dragEnterEvent(self, event):  # type: ignore[override]
        """Accept drag events on the widget itself."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

    def dragMoveEvent(self, event):  # type: ignore[override]
        """Handle drag move on the widget itself."""
        if event.mimeData().hasText():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()

    def dropEvent(self, event):  # type: ignore[override]
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
                if card_geom.contains(drop_pos):  # type: ignore
                    # Let the card handle its own drop
                    return
        
        # Check if dropping on a placeholder button
        for slot_idx, button in enumerate(self.placeholder_buttons):
            if button is not None and button.isVisible():
                button_geom = button.geometry()
                if button_geom.contains(drop_pos):  # type: ignore
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
            
            event.setDropAction(Qt.DropAction.CopyAction)  # type: ignore
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
            
            # Calculate which row (0-3) - check if within button bounds
            row = int(y // (btn_size + gap))
            if row < 0 or row >= 4:
                return None
            
            # Check if y is actually within a button (not in gap)
            row_start = row * (btn_size + gap)
            if y < row_start or y >= row_start + btn_size:
                return None
            
            # Convert to slot index
            slot_index = row * 4 + col
            if 0 <= slot_index < 16:
                return slot_index
        except Exception:
            pass
        return None
    
    def _create_card_at_slot(self, slot_index: int, root_note: int, chord_type: str, actual_notes: Optional[List[int]]) -> None:
        """Create a new chord card at the specified slot."""
        row = slot_index // 4
        col = slot_index % 4
        
        # Create new card (styled like pad button)
        card = ReplayCard(root_note, chord_type, self, actual_notes)  # type: ignore[arg-type]
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
    
    def _create_placeholder_at(self, slot_index: int) -> None:
        """Create a placeholder button at the given slot index."""
        btn_size = 80
        row = slot_index // 4
        col = slot_index % 4
        
        placeholder = QPushButton("")
        placeholder.setCheckable(False)
        placeholder.setFixedSize(btn_size, btn_size)
        placeholder.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
        placeholder.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        placeholder.installEventFilter(self)
        
        self.placeholder_buttons[slot_index] = placeholder
        self.grid_layout.addWidget(placeholder, row, col)

    def _replay_chord(self, root_note: int, chord_type: str) -> None:
        """Play the chord when card is clicked."""
        self._play_chord(root_note, chord_type)
    
    def _play_exact_notes(self, notes: List[int]) -> None:
        """Play exact MIDI notes (preserves octave and voicing)."""
        if not notes:
            return
        
        # Get velocity from parent window if available
        velocity = 100
        if self._parent_window is not None:
            if hasattr(self._parent_window, '_get_velocity'):
                velocity = self._parent_window._get_velocity()
        
        # If exclusive mode is enabled on parent, stop any currently active notes first
        try:
            if self._parent_window is not None and hasattr(self._parent_window, '_is_exclusive_mode'):
                if self._parent_window._is_exclusive_mode():
                    self._stop_active_notes()
        except Exception:
            pass
        
        # Play all notes
        for note in notes:
            try:
                self.midi.note_on(note, velocity, self.midi_channel)
                self._active_notes.append(note)
            except Exception:
                pass
        
        # Only schedule note offs if sustain is off
        if not self.sustain:
            def release_notes() -> None:
                try:
                    for note in notes:
                        self.midi.note_off(note, self.midi_channel)
                except Exception:
                    pass
                # Remove released notes from active tracking
                try:
                    self._active_notes = [n for n in self._active_notes if n not in notes]
                except Exception:
                    self._active_notes.clear()
            QTimer.singleShot(200, release_notes)

    def _play_chord(self, root_note: int, chord_type: str) -> None:
        """Play a chord using MIDI."""
        if chord_type not in CHORD_DEFINITIONS:
            return
        
        _, intervals = CHORD_DEFINITIONS[chord_type]
        base_note = 60 + root_note  # C4 + root offset
        
        # Get velocity from parent window if available
        velocity = 100
        if self._parent_window is not None:
            if hasattr(self._parent_window, '_get_velocity'):
                velocity = self._parent_window._get_velocity()
        
        # If exclusive mode is enabled on parent, stop any currently active notes first
        try:
            if self._parent_window is not None and hasattr(self._parent_window, '_is_exclusive_mode'):
                if self._parent_window._is_exclusive_mode():
                    self._stop_active_notes()
        except Exception:
            pass
        
        # Play all notes of the chord
        for interval in intervals:
            note = base_note + interval
            try:
                self.midi.note_on(note, velocity, self.midi_channel)
                self._active_notes.append(note)
            except Exception:
                pass
        
        # Only schedule note offs if sustain is off
        if not self.sustain:
            def release_notes() -> None:
                try:
                    for interval in intervals:
                        note = base_note + interval
                        self.midi.note_off(note, self.midi_channel)
                except Exception:
                    pass
                # Remove released notes from active tracking
                try:
                    remaining: List[int] = []
                    for n in self._active_notes:
                        if n < base_note or n > base_note + max(intervals):
                            remaining.append(n)
                    self._active_notes = remaining
                except Exception:
                    self._active_notes.clear()
            QTimer.singleShot(200, release_notes)

    def set_channel(self, channel: int) -> None:
        """Update MIDI channel."""
        self.midi_channel = channel
    
    def set_sustain(self, sustain: bool) -> None:
        """Set sustain mode."""
        self.sustain = sustain
        # If turning sustain off, release all currently playing notes
        if not sustain:
            # Note: We don't track individual playing notes, so this is a limitation
            # In a full implementation, we'd track active notes per card
            self._stop_active_notes()

    def _stop_active_notes(self) -> None:
        """Stop any notes currently tracked as active for this replay area."""
        if not getattr(self, '_active_notes', None):
            return
        try:
            for note in self._active_notes:
                self.midi.note_off(note, self.midi_channel)
        except Exception:
            pass
        self._active_notes.clear()

    def clear_active_notes(self) -> None:
        """Public wrapper to clear any active notes (used by parent window)."""
        self._stop_active_notes()


class ChordMonitorWindow(QMainWindow):
    """Simplified window containing just a 4x4 grid replay area."""
    _parent_main: Optional['Any']  # Reference to main window for close event handling
    
    def __init__(self, midi_out: MidiOut, midi_channel: int = 0, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # Late import to avoid circular dependency
        from .keyboard_widget import RangeSlider  # noqa: F811
        self._RangeSlider = RangeSlider
        
        self.midi_channel = midi_channel
        self.setWindowTitle("Chord Monitor")
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        # Create MIDI channel menu
        self._create_menu_bar()
        
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
        self.sustain_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        self.all_off_btn.setCursor(Qt.CursorShape.PointingHandCursor)
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
        
        # Humanize section
        humanize_frame = QFrame()
        humanize_frame.setStyleSheet("""
            QFrame {
                background-color: #1e2127;
                border: 1px solid #3b4148;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        humanize_layout = QVBoxLayout(humanize_frame)
        humanize_layout.setSpacing(8)
        humanize_layout.setContentsMargins(8, 8, 8, 8)
        
        # Humanize header
        humanize_header = QLabel("Humanize")
        humanize_header.setStyleSheet("font-size: 12px; font-weight: bold; color: #fff;")
        humanize_layout.addWidget(humanize_header)
        
        # Velocity controls
        velocity_layout = QHBoxLayout()
        velocity_layout.setSpacing(10)
        
        vel_label = QLabel("Velocity:")
        vel_label.setStyleSheet("color: #aaa; min-width: 60px;")
        velocity_layout.addWidget(vel_label)
        
        # Container for sliders (to stack them in same space)
        vel_slider_container = QWidget()
        vel_slider_container.setFixedWidth(200)
        vel_slider_layout = QHBoxLayout(vel_slider_container)
        vel_slider_layout.setContentsMargins(0, 0, 0, 0)
        
        # Single velocity slider (when randomization is off)
        self.vel_slider = QSlider(Qt.Orientation.Horizontal)
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
        vel_slider_layout.addWidget(self.vel_slider)
        
        # Range slider (when randomization is on)
        self.vel_range = self._RangeSlider(1, 127, low=64, high=88, parent=self)
        self.vel_range.setFixedWidth(200)
        self.vel_range.setMinimumHeight(22)
        self.vel_range.setFixedHeight(22)
        self.vel_range.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        vel_slider_layout.addWidget(self.vel_range)
        
        velocity_layout.addWidget(vel_slider_container)
        velocity_layout.addSpacing(20)  # Add space between slider and checkbox
        
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
        humanize_layout.addLayout(velocity_layout)
        
        # Drift controls
        drift_layout = QHBoxLayout()
        drift_layout.setSpacing(10)
        
        # Drift direction dropdown (styled to match velocity label)
        self.drift_direction = QComboBox()
        self.drift_direction.addItems(["Drift: ↑", "Drift: ↓", "Drift: Random"])
        self.drift_direction.setCurrentIndex(0)  # Default to "Up"
        self.drift_direction.setFixedWidth(100)
        self.drift_direction.setFixedHeight(36)
        self.drift_direction.setStyleSheet("""
            QComboBox {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 8px;
                padding: 8px 12px;
                color: #fff;
                text-align: left;
            }
            QComboBox:hover {
                border: 2px solid #2f82e6;
            }
            QComboBox::drop-down {
                border: none;
                width: 0px;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                selection-background-color: #2f82e6;
                color: #fff;
                padding: 4px;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 6px 12px;
                min-height: 24px;
                border: none;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #2f82e6;
            }
        """)
        drift_layout.addWidget(self.drift_direction)
        
        # Container for drift sliders (to stack them in same space)
        drift_slider_container = QWidget()
        drift_slider_container.setFixedWidth(200)
        drift_slider_layout = QHBoxLayout(drift_slider_container)
        drift_slider_layout.setContentsMargins(0, 0, 0, 0)
        
        # Single drift slider (when randomization is off)
        self.drift_slider = QSlider(Qt.Orientation.Horizontal)
        self.drift_slider.setMinimum(0)
        self.drift_slider.setMaximum(200)
        self.drift_slider.setValue(0)
        self.drift_slider.setFixedWidth(200)
        self.drift_slider.setFixedHeight(20)
        self.drift_slider.setStyleSheet("""
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
        drift_slider_layout.addWidget(self.drift_slider)
        
        # Range slider for drift (when randomization is on)
        self.drift_range = self._RangeSlider(0, 200, low=0, high=50, parent=self)
        self.drift_range.setFixedWidth(200)
        self.drift_range.setMinimumHeight(22)
        self.drift_range.setFixedHeight(22)
        self.drift_range.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        drift_slider_layout.addWidget(self.drift_range)
        
        drift_layout.addWidget(drift_slider_container)
        drift_layout.addSpacing(20)  # Add space between slider and checkbox
        
        # Randomize checkbox for drift
        self.drift_random_chk = QCheckBox("Randomize")
        self.drift_random_chk.setChecked(True)
        self.drift_random_chk.setStyleSheet("""
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
        self.drift_random_chk.toggled.connect(self._toggle_drift_random)
        drift_layout.addWidget(self.drift_random_chk)
        
        # Initialize visibility (randomize is on by default)
        self.drift_slider.setVisible(False)  # Hide single slider initially (random is on)
        self.drift_range.setVisible(True)    # Show range slider
        
        drift_layout.addStretch()
        humanize_layout.addLayout(drift_layout)
        
        # Exclusive chord mode
        exclusive_layout = QHBoxLayout()
        self.exclusive_chk = QCheckBox("Exclusive chord mode")
        self.exclusive_chk.setChecked(False)
        self.exclusive_chk.setStyleSheet("""
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
        exclusive_layout.addWidget(self.exclusive_chk)
        exclusive_layout.addStretch()
        humanize_layout.addLayout(exclusive_layout)
        
        layout.addWidget(humanize_frame)
        
        # Replay area (4x4 grid)
        self.replay_area = ChordMonitorReplayArea(midi_out, midi_channel, central_widget)
        # Store reference to parent window in replay area for velocity access
        self.replay_area._parent_window = self
        layout.addWidget(self.replay_area, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        # Calculate appropriate window size for 4x4 grid
        # Each button is 80x80, with spacing and margins
        # Need extra space for header and Humanize section
        btn_size = 80
        spacing = 10
        margins = 20
        width = (btn_size * 4) + (spacing * 3) + margins + 80  # 4 columns + extra width for controls
        height = (btn_size * 4) + (spacing * 3) + margins + 260  # 4 rows + header + humanize section + extra padding
        self.resize(width, height)
        self.setMinimumSize(width, height)
    
    def set_channel(self, channel: int) -> None:
        """Update MIDI channel."""
        self.replay_area.set_channel(channel)
    
    def _toggle_sustain(self) -> None:
        """Toggle sustain mode."""
        sustain = self.sustain_btn.isChecked()
        self.replay_area.set_sustain(sustain)
        self.sustain_btn.setText(f"Sustain: {'On' if sustain else 'Off'}")
    
    def _toggle_vel_random(self, checked: bool) -> None:
        """Switch between fixed velocity slider and range slider."""
        random_mode = bool(checked)
        try:
            self.vel_slider.setVisible(not random_mode)
            self.vel_range.setVisible(random_mode)
        except Exception:
            pass
    
    def _toggle_drift_random(self, checked: bool) -> None:
        """Switch between fixed drift slider and range slider."""
        random_mode = bool(checked)
        try:
            self.drift_slider.setVisible(not random_mode)
            self.drift_range.setVisible(random_mode)
        except Exception:
            pass
    
    def _get_velocity(self) -> int:
        """Get velocity based on current settings (randomized or fixed)."""
        if self.vel_random_chk.isChecked():
            low, high = self.vel_range.values()
            return random.randint(min(low, high), max(low, high))
        else:
            return self.vel_slider.value()
    
    def _get_drift(self) -> int:
        """Get drift value in milliseconds (randomized or fixed)."""
        if self.drift_random_chk.isChecked():
            low, high = self.drift_range.values()
            return random.randint(min(low, high), max(low, high))
        else:
            return self.drift_slider.value()
    
    def _get_drift_direction(self) -> str:
        """Get the selected drift direction (Up, Down, or Random)."""
        # Parse direction from "Drift: ↑" format
        text = self.drift_direction.currentText()
        if "↑" in text:
            return "Up"
        elif "↓" in text:
            return "Down"
        elif "Random" in text:
            return "Random"
        return "Up"  # Default
    
    def _is_exclusive_mode(self) -> bool:
        """Return True if Exclusive chord mode is enabled."""
        chk = getattr(self, 'exclusive_chk', None)
        try:
            return bool(chk and chk.isChecked())
        except Exception:
            return False
    
    def _all_notes_off_clicked(self) -> None:
        """Handle All Notes Off button click."""
        try:
            self._flash_all_off_button()
        except Exception:
            pass
        self._perform_all_notes_off()
    
    def _perform_all_notes_off(self) -> None:
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
        
        # Clear any locally tracked active notes so exclusive mode stays in sync
        try:
            if hasattr(self.replay_area, 'clear_active_notes'):
                self.replay_area.clear_active_notes()
        except Exception:
            pass
    
    def _flash_all_off_button(self, duration_ms: int = 150) -> None:
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
    
    def _create_menu_bar(self) -> None:
        """Create menu bar with MIDI channel selection."""
        menubar = self.menuBar()
        
        midi_menu = menubar.addMenu("&MIDI")
        chan_menu = midi_menu.addMenu("Channel")
        
        self._channel_group = QActionGroup(self)
        self._channel_group.setExclusive(True)
        
        self._channel_actions: List[QAction] = []
        for ch in range(1, 17):
            act = QAction(f"Channel {ch}", self)
            act.setCheckable(True)
            if ch == self.midi_channel:
                act.setChecked(True)
            act.triggered.connect(lambda checked, c=ch: self._set_channel(c))
            self._channel_group.addAction(act)
            chan_menu.addAction(act)
            self._channel_actions.append(act)
    
    def _set_channel(self, channel: int) -> None:
        """Set MIDI channel for chord monitor."""
        self.midi_channel = channel
        if hasattr(self, 'replay_area'):
            self.replay_area.set_channel(channel)
    
    def closeEvent(self, event):  # type: ignore[override]
        """Handle window close event."""
        # Notify parent to update menu state
        try:
            if hasattr(self, '_parent_main') and self._parent_main is not None:
                parent = self._parent_main
                if hasattr(parent, 'menu_actions') and 'chord_monitor' in parent.menu_actions:
                    parent.menu_actions['chord_monitor'].setChecked(False)
                    # Don't disable inline chord display - it should always be on
                    # if hasattr(parent, 'keyboard') and hasattr(parent.keyboard, 'set_chord_monitor'):
                    #     parent.keyboard.set_chord_monitor(False)
                # Clear reference
                parent.chord_monitor_window = None
        except Exception:
            pass
        super().closeEvent(event)
