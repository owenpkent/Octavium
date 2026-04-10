"""Chord Pad Window - a multi-page 4x4 grid for storing and replaying chord cards."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout, QFrame, QSizePolicy, QMainWindow, QPushButton, QSlider, QCheckBox, QComboBox, QMenu
)
from PySide6.QtCore import Qt, QMimeData, QEvent, QTimer, QRectF
from PySide6.QtGui import QIcon, QPainter, QColor, QAction, QActionGroup
from typing import List, Optional, TYPE_CHECKING, Union, Any
from pathlib import Path
import json
import os
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
        """Play exact MIDI notes (preserves octave and voicing) with drift/humanize."""
        if not notes:
            return
        
        # Get velocity from parent window if available
        velocity = 100
        drift_ms = 0
        drift_direction = "Up"
        if self._parent_window is not None:
            if hasattr(self._parent_window, '_get_velocity'):
                velocity = self._parent_window._get_velocity()
            if hasattr(self._parent_window, '_get_drift'):
                drift_ms = self._parent_window._get_drift()
            if hasattr(self._parent_window, '_get_drift_direction'):
                drift_direction = self._parent_window._get_drift_direction()
        
        # If exclusive mode is enabled on parent, stop any currently active notes first
        try:
            if self._parent_window is not None and hasattr(self._parent_window, '_is_exclusive_mode'):
                if self._parent_window._is_exclusive_mode():
                    self._stop_active_notes()
        except Exception:
            pass
        
        # Order notes based on drift direction
        ordered_notes = list(notes)
        if drift_ms > 0 and len(ordered_notes) > 1:
            if drift_direction == "Down":
                ordered_notes.reverse()
            elif drift_direction == "Random":
                random.shuffle(ordered_notes)
            
            # Spread notes over the drift time
            for i, note in enumerate(ordered_notes):
                delay_ms = int((i / (len(ordered_notes) - 1)) * drift_ms) if len(ordered_notes) > 1 else 0
                if delay_ms == 0:
                    try:
                        self.midi.note_on(note, velocity, self.midi_channel)
                        self._active_notes.append(note)
                    except Exception:
                        pass
                else:
                    def play_delayed(n: int = note, v: int = velocity) -> None:
                        try:
                            self.midi.note_on(n, v, self.midi_channel)
                            self._active_notes.append(n)
                        except Exception:
                            pass
                    QTimer.singleShot(delay_ms, play_delayed)
        else:
            # No drift - play all notes immediately
            for note in ordered_notes:
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
            QTimer.singleShot(200 + drift_ms, release_notes)

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
        self.setWindowTitle("Chord Pad")
        
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
        header_layout.setSpacing(6)
        
        # Sustain button
        self.sustain_btn = QPushButton("Sustain")
        self.sustain_btn.setCheckable(True)
        self.sustain_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sustain_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                padding: 6px 10px;
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
        self.all_off_btn = QPushButton("Notes Off")
        self.all_off_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.all_off_btn.setStyleSheet("""
            QPushButton {
                padding: 6px 10px;
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
        
        # Autofill button
        self.autofill_btn = QPushButton("Autofill...")
        self.autofill_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.autofill_btn.setStyleSheet("""
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
        """)
        self.autofill_btn.clicked.connect(self._show_autofill_dialog)
        header_layout.addWidget(self.autofill_btn)

        # Clear All button
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                padding: 6px 10px;
                color: #e74c3c;
                font-weight: bold;
            }
            QPushButton:hover {
                border: 2px solid #e74c3c;
                background-color: #3a3f46;
            }
        """)
        self.clear_all_btn.clicked.connect(self._clear_all_clicked)
        header_layout.addWidget(self.clear_all_btn)
        
        # Generation options button (edit note counts / inversions on the fly)
        self.gen_opts_btn = QPushButton("Options...")
        self.gen_opts_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.gen_opts_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                padding: 6px 12px;
                color: #aaa;
                font-size: 11px;
            }
            QPushButton:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
                color: #fff;
            }
        """)
        self.gen_opts_btn.clicked.connect(self._show_gen_options_dialog)
        header_layout.addWidget(self.gen_opts_btn)
        
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

        # Multi-page state
        self._current_page = 0
        self._pages: List[List[Optional[dict]]] = [[None] * 16]  # Start with 1 page

        # Replay area (4x4 grid)
        self.replay_area = ChordMonitorReplayArea(midi_out, midi_channel, central_widget)
        # Store reference to parent window in replay area for velocity access
        self.replay_area._parent_window = self
        layout.addWidget(self.replay_area, 0, Qt.AlignmentFlag.AlignCenter)

        # Page navigation controls
        page_nav_layout = QHBoxLayout()
        page_nav_layout.setSpacing(6)
        page_nav_layout.addStretch()

        _page_btn_qss = """
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                padding: 4px 10px;
                color: #fff;
                font-weight: bold;
                min-width: 28px;
            }
            QPushButton:hover {
                border: 2px solid #2f82e6;
                background-color: #3a3f46;
            }
            QPushButton:disabled {
                color: #555;
                border: 2px solid #2b2f36;
            }
        """

        self.prev_page_btn = QPushButton("◀")
        self.prev_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_page_btn.setStyleSheet(_page_btn_qss)
        self.prev_page_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.prev_page_btn.clicked.connect(self._prev_page)
        page_nav_layout.addWidget(self.prev_page_btn)

        self.page_label = QLabel("Page 1 / 1")
        self.page_label.setStyleSheet("color: #aaa; font-size: 12px; font-weight: bold; min-width: 80px;")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_nav_layout.addWidget(self.page_label)

        self.next_page_btn = QPushButton("▶")
        self.next_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_page_btn.setStyleSheet(_page_btn_qss)
        self.next_page_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.next_page_btn.clicked.connect(self._next_page)
        page_nav_layout.addWidget(self.next_page_btn)

        # Spacer between nav and add/remove
        page_nav_layout.addSpacing(12)

        self.add_page_btn = QPushButton("+")
        self.add_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_page_btn.setToolTip("Add page")
        self.add_page_btn.setStyleSheet(_page_btn_qss)
        self.add_page_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.add_page_btn.clicked.connect(self._add_page)
        page_nav_layout.addWidget(self.add_page_btn)

        self.remove_page_btn = QPushButton("−")
        self.remove_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_page_btn.setToolTip("Remove current page")
        self.remove_page_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 4px;
                padding: 4px 10px;
                color: #e74c3c;
                font-weight: bold;
                min-width: 28px;
            }
            QPushButton:hover {
                border: 2px solid #e74c3c;
                background-color: #3a3f46;
            }
            QPushButton:disabled {
                color: #555;
                border: 2px solid #2b2f36;
            }
        """)
        self.remove_page_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.remove_page_btn.clicked.connect(self._remove_page)
        page_nav_layout.addWidget(self.remove_page_btn)

        page_nav_layout.addStretch()
        layout.addLayout(page_nav_layout)

        layout.addStretch()

        # Calculate appropriate window size for 4x4 grid + page nav
        width = 600
        height = 760
        self.resize(width, height)
        self.setMinimumSize(width, height)

        # Restore previously saved pad
        self._load_grid()
        self._update_page_controls()
    
    def update_midi_out(self, new_midi) -> None:
        """Update MIDI output (called by launcher on port change)."""
        try:
            self.replay_area.midi = new_midi
        except Exception:
            pass

    def set_channel(self, channel: int) -> None:
        """Update MIDI channel."""
        self.replay_area.set_channel(channel)
    
    def _toggle_sustain(self) -> None:
        """Toggle sustain mode."""
        sustain = self.sustain_btn.isChecked()
        self.replay_area.set_sustain(sustain)
    
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
    
    def _show_gen_options_dialog(self) -> None:
        """Show dialog to edit generation options (key, mode, note counts, inversions, compliance, lock influence)."""
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel,
            QGroupBox, QPushButton as _QPB, QComboBox, QSlider,
        )
        from .chord_autofill import NOTES, NOTE_TO_INDEX, SCALE_MODES
        
        ctx = getattr(self, '_autofill_context', None)
        if not ctx:
            ctx = {
                'root_note': 0, 'mode_name': 'Major (Ionian)',
                'allowed_note_counts': None, 'allowed_inversions': None,
                'scale_compliance': 1.0, 'lock_influence': 0.0,
            }
            self._autofill_context = ctx
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Generation Options")
        dlg.setMinimumWidth(400)
        _base_qss = """
            QDialog { background-color: #1e2127; }
            QLabel { color: #fff; }
            QGroupBox { color: #fff; border: 1px solid #3b4148; border-radius: 6px;
                        margin-top: 12px; padding-top: 8px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }
            QComboBox { background-color: #2b2f36; border: 2px solid #3b4148;
                        border-radius: 6px; padding: 6px 10px; color: #fff; min-width: 140px; }
            QComboBox:hover { border: 2px solid #2f82e6; }
            QComboBox::drop-down { border: none; width: 20px; }
            QComboBox QAbstractItemView { background-color: #2b2f36; border: 2px solid #3b4148;
                                          selection-background-color: #2f82e6; color: #fff; }
        """
        dlg.setStyleSheet(_base_qss)
        lay = QVBoxLayout(dlg)
        
        _slider_qss = """
            QSlider::groove:horizontal { border: 1px solid #3b4148; height: 6px;
                background: #2b2f36; border-radius: 3px; }
            QSlider::handle:horizontal { background: #2f82e6; border: none;
                width: 14px; margin: -4px 0; border-radius: 7px; }
            QSlider::sub-page:horizontal { background: #2f82e6; border-radius: 3px; }
        """
        
        # --- Key & Mode ---
        km_group = QGroupBox("Key && Scale")
        km_lay = QHBoxLayout(km_group)
        key_label = QLabel("Key:")
        km_lay.addWidget(key_label)
        key_combo = QComboBox()
        key_combo.addItems(NOTES)
        cur_root = ctx.get('root_note', 0)
        key_combo.setCurrentText(NOTES[cur_root % 12] if cur_root < 12 else "C")
        km_lay.addWidget(key_combo)
        
        mode_label = QLabel("Mode:")
        km_lay.addWidget(mode_label)
        mode_combo = QComboBox()
        cur_mode_name = ctx.get('mode_name', 'Major (Ionian)')
        current_idx = 0
        current_category = ""
        for i_m, (m_name, m_data) in enumerate(SCALE_MODES.items()):
            if m_data.category != current_category:
                if current_category:
                    mode_combo.insertSeparator(mode_combo.count())
                current_category = m_data.category
            mode_combo.addItem(m_name, m_name)
            if m_name == cur_mode_name:
                current_idx = mode_combo.count() - 1
        mode_combo.setCurrentIndex(current_idx)
        km_lay.addWidget(mode_combo)
        km_lay.addStretch()
        lay.addWidget(km_group)
        
        # --- Note Counts ---
        nc_group = QGroupBox("Note Counts")
        nc_lay = QHBoxLayout(nc_group)
        cur_nc = ctx.get('allowed_note_counts')
        nc3 = QCheckBox("Triads (3)"); nc3.setStyleSheet("color:#fff;")
        nc3.setChecked(cur_nc is None or 3 in cur_nc)
        nc4 = QCheckBox("7ths / 6ths (4)"); nc4.setStyleSheet("color:#fff;")
        nc4.setChecked(cur_nc is None or 4 in cur_nc)
        nc5 = QCheckBox("9ths / Ext (5)"); nc5.setStyleSheet("color:#fff;")
        nc5.setChecked(cur_nc is None or 5 in cur_nc)
        nc_lay.addWidget(nc3); nc_lay.addWidget(nc4); nc_lay.addWidget(nc5)
        lay.addWidget(nc_group)
        
        # --- Inversions ---
        inv_group = QGroupBox("Inversions")
        inv_lay = QHBoxLayout(inv_group)
        cur_inv = ctx.get('allowed_inversions')
        inv0 = QCheckBox("Root"); inv0.setStyleSheet("color:#fff;")
        inv0.setChecked(cur_inv is None or 0 in cur_inv)
        inv1 = QCheckBox("1st"); inv1.setStyleSheet("color:#fff;")
        inv1.setChecked(cur_inv is not None and 1 in cur_inv)
        inv2 = QCheckBox("2nd"); inv2.setStyleSheet("color:#fff;")
        inv2.setChecked(cur_inv is not None and 2 in cur_inv)
        inv3 = QCheckBox("3rd"); inv3.setStyleSheet("color:#fff;")
        inv3.setChecked(cur_inv is not None and 3 in cur_inv)
        inv_lay.addWidget(inv0); inv_lay.addWidget(inv1)
        inv_lay.addWidget(inv2); inv_lay.addWidget(inv3)
        lay.addWidget(inv_group)
        
        # --- Scale Compliance ---
        sc_group = QGroupBox("Scale Compliance")
        sc_lay = QVBoxLayout(sc_group)
        sc_desc = QLabel("100% = strictly diatonic  ·  lower = allow borrowed / chromatic chords")
        sc_desc.setStyleSheet("color: #888; font-size: 10px;")
        sc_lay.addWidget(sc_desc)
        sc_row = QHBoxLayout()
        sc_slider = QSlider(Qt.Orientation.Horizontal)
        sc_slider.setMinimum(0); sc_slider.setMaximum(100)
        sc_slider.setValue(int(ctx.get('scale_compliance', 1.0) * 100))
        sc_slider.setFixedHeight(20)
        sc_slider.setStyleSheet(_slider_qss)
        sc_val_label = QLabel(f"{sc_slider.value()}%")
        sc_val_label.setFixedWidth(40)
        sc_val_label.setStyleSheet("color: #2f82e6; font-weight: bold;")
        sc_slider.valueChanged.connect(lambda v: sc_val_label.setText(f"{v}%"))
        sc_row.addWidget(sc_slider)
        sc_row.addWidget(sc_val_label)
        sc_lay.addLayout(sc_row)
        lay.addWidget(sc_group)
        
        # --- Lock Influence ---
        li_group = QGroupBox("Lock Influence")
        li_lay = QVBoxLayout(li_group)
        li_desc = QLabel("How much new chords should match the style of your locked chords")
        li_desc.setStyleSheet("color: #888; font-size: 10px;")
        li_lay.addWidget(li_desc)
        li_row = QHBoxLayout()
        li_slider = QSlider(Qt.Orientation.Horizontal)
        li_slider.setMinimum(0); li_slider.setMaximum(100)
        li_slider.setValue(int(ctx.get('lock_influence', 0.0) * 100))
        li_slider.setFixedHeight(20)
        li_slider.setStyleSheet(_slider_qss)
        li_val_label = QLabel(f"{li_slider.value()}%")
        li_val_label.setFixedWidth(40)
        li_val_label.setStyleSheet("color: #2f82e6; font-weight: bold;")
        li_slider.valueChanged.connect(lambda v: li_val_label.setText(f"{v}%"))
        li_row.addWidget(li_slider)
        li_row.addWidget(li_val_label)
        li_lay.addLayout(li_row)
        lay.addWidget(li_group)
        
        # --- Buttons ---
        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        ok_btn = _QPB("Save")
        ok_btn.setStyleSheet("""
            QPushButton { background-color: #2f82e6; border: none; border-radius: 6px;
                          padding: 8px 20px; color: #fff; font-weight: bold; }
            QPushButton:hover { background-color: #4a9fff; }
        """)
        ok_btn.clicked.connect(dlg.accept)
        cancel_btn = _QPB("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton { background-color: #2b2f36; border: 2px solid #3b4148;
                          border-radius: 6px; padding: 8px 16px; color: #fff; }
            QPushButton:hover { border: 2px solid #2f82e6; background-color: #3a3f46; }
        """)
        cancel_btn.clicked.connect(dlg.reject)
        btn_lay.addWidget(cancel_btn)
        btn_lay.addWidget(ok_btn)
        lay.addLayout(btn_lay)
        
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # Key & mode
            ctx['root_note'] = NOTE_TO_INDEX.get(key_combo.currentText(), 0)
            ctx['mode_name'] = mode_combo.currentData() or 'Major (Ionian)'
            # Note counts
            counts = []
            if nc3.isChecked(): counts.append(3)
            if nc4.isChecked(): counts.append(4)
            if nc5.isChecked(): counts.append(5)
            ctx['allowed_note_counts'] = counts if counts else None
            # Inversions
            inversions = []
            if inv0.isChecked(): inversions.append(0)
            if inv1.isChecked(): inversions.append(1)
            if inv2.isChecked(): inversions.append(2)
            if inv3.isChecked(): inversions.append(3)
            ctx['allowed_inversions'] = inversions if inversions else None
            # Sliders
            ctx['scale_compliance'] = sc_slider.value() / 100.0
            ctx['lock_influence'] = li_slider.value() / 100.0
    
    def _show_autofill_dialog(self) -> None:
        """Show the autofill dialog and populate grid with selected chords."""
        try:
            from .chord_autofill import AutofillDialog
            
            dialog = AutofillDialog(
                self.replay_area.midi,
                self.replay_area.midi_channel,
                parent=self
            )
            
            if dialog.exec() == AutofillDialog.DialogCode.Accepted:
                chords = dialog.get_chords()
                self._autofill_context = dialog.get_autofill_context()
                self._autofill_grid(chords)
        except Exception:
            pass
    
    def _autofill_grid(self, chords: list) -> None:
        """Fill the grid with the given chords."""
        if not chords:
            return
        
        # Clear existing cards first
        self._clear_grid()
        
        # Precompute degree lookup from autofill context
        ctx = getattr(self, '_autofill_context', None)
        degree_map: dict = {}  # root_midi -> degree_index
        if ctx:
            from .chord_autofill import SCALE_MODES
            mode = SCALE_MODES.get(ctx['mode_name'])
            if mode:
                for deg_i, interval in enumerate(mode.intervals):
                    deg_root = (ctx['root_note'] + interval) % 12
                    degree_map[deg_root] = deg_i
        
        # Fill slots with chords (up to 16 slots)
        for i, (root, chord_type, notes) in enumerate(chords[:16]):
            # Remove placeholder at slot if exists
            if i < len(self.replay_area.placeholder_buttons):
                placeholder = self.replay_area.placeholder_buttons[i]
                if placeholder is not None:
                    placeholder.hide()
                    placeholder.setParent(None)
                    placeholder.deleteLater()
                    self.replay_area.placeholder_buttons[i] = None
            
            # Create card at slot
            self.replay_area._create_card_at_slot(i, root, chord_type, notes)
            
            # Store degree index on card for regeneration
            card = self.replay_area.grid_positions[i]
            if card is not None:
                card._degree_index = degree_map.get(root % 12)  # type: ignore
    
    def _get_locked_chords(self) -> list:
        """Return list of (root, chord_type) for all locked cards."""
        locked = []
        for card in self.replay_area.grid_positions:
            if card is not None and getattr(card, '_locked', False):
                locked.append((card.root_note, card.chord_type))
        return locked
    
    def _regenerate_card(self, slot_index: int) -> None:
        """Replace a single card with a new random chord for the same scale degree."""
        ctx = getattr(self, '_autofill_context', None)
        if not ctx:
            return
        card = self.replay_area.grid_positions[slot_index]
        if card is None:
            return
        
        degree_index = getattr(card, '_degree_index', None)
        if degree_index is None:
            return
        
        from .chord_autofill import SCALE_MODES, generate_single_alternative
        mode = SCALE_MODES.get(ctx['mode_name'])
        if not mode:
            return
        
        root, new_type, notes = generate_single_alternative(
            ctx['root_note'], mode, degree_index, card.chord_type,
            allowed_note_counts=ctx.get('allowed_note_counts'),
            allowed_inversions=ctx.get('allowed_inversions'),
            scale_compliance=ctx.get('scale_compliance', 1.0),
            lock_influence=ctx.get('lock_influence', 0.0),
            locked_chords=self._get_locked_chords() or None,
            mode_name=ctx.get('mode_name'),
        )
        
        # Remove old card
        card.deleteLater()
        self.replay_area.grid_positions[slot_index] = None
        if card in self.replay_area.cards:
            self.replay_area.cards.remove(card)
        
        # Create new card
        self.replay_area._create_card_at_slot(slot_index, root, new_type, notes)
        new_card = self.replay_area.grid_positions[slot_index]
        if new_card is not None:
            new_card._degree_index = degree_index  # type: ignore
    
    def _regenerate_unlocked(self) -> None:
        """Replace all unlocked cards with new random chords, keeping locked cards."""
        ctx = getattr(self, '_autofill_context', None)
        if not ctx:
            return
        
        from .chord_autofill import SCALE_MODES, generate_single_alternative
        mode = SCALE_MODES.get(ctx['mode_name'])
        if not mode:
            return
        
        locked_info = self._get_locked_chords() or None
        
        for slot_index in range(16):
            card = self.replay_area.grid_positions[slot_index]
            if card is None:
                continue
            if getattr(card, '_locked', False):
                continue  # Skip locked cards
            
            degree_index = getattr(card, '_degree_index', None)
            if degree_index is None:
                continue
            
            root, new_type, notes = generate_single_alternative(
                ctx['root_note'], mode, degree_index, card.chord_type,
                allowed_note_counts=ctx.get('allowed_note_counts'),
                allowed_inversions=ctx.get('allowed_inversions'),
                scale_compliance=ctx.get('scale_compliance', 1.0),
                lock_influence=ctx.get('lock_influence', 0.0),
                locked_chords=locked_info,
                mode_name=ctx.get('mode_name'),
            )
            
            # Remove old card
            card.deleteLater()
            self.replay_area.grid_positions[slot_index] = None
            if card in self.replay_area.cards:
                self.replay_area.cards.remove(card)
            
            # Create new card
            self.replay_area._create_card_at_slot(slot_index, root, new_type, notes)
            new_card = self.replay_area.grid_positions[slot_index]
            if new_card is not None:
                new_card._degree_index = degree_index  # type: ignore
    
    def _snapshot_current_page(self) -> None:
        """Save the current grid state into the pages list."""
        page_data: List[Optional[dict]] = []
        for card in self.replay_area.grid_positions:
            if card is None:
                page_data.append(None)
            else:
                page_data.append({
                    "root": card.root_note,
                    "type": card.chord_type,
                    "notes": list(getattr(card, 'actual_notes', []) or []),
                })
        self._pages[self._current_page] = page_data

    def _load_page(self, page_index: int) -> None:
        """Load a page from the pages list into the grid."""
        self._clear_grid()
        page_data = self._pages[page_index]
        for i, slot in enumerate(page_data[:16]):
            if slot is None:
                continue
            root = int(slot.get("root", 0))
            chord_type = str(slot.get("type", "Major"))
            notes_raw = slot.get("notes", [])
            notes = [int(n) for n in notes_raw] if notes_raw else None
            if i < len(self.replay_area.placeholder_buttons):
                ph = self.replay_area.placeholder_buttons[i]
                if ph is not None:
                    ph.hide()
                    ph.setParent(None)
                    ph.deleteLater()
                    self.replay_area.placeholder_buttons[i] = None
            self.replay_area._create_card_at_slot(i, root, chord_type, notes or [])

    def _update_page_controls(self) -> None:
        """Update page label and enable/disable nav buttons."""
        total = len(self._pages)
        self.page_label.setText(f"Page {self._current_page + 1} / {total}")
        self.prev_page_btn.setEnabled(self._current_page > 0)
        self.next_page_btn.setEnabled(self._current_page < total - 1)
        self.remove_page_btn.setEnabled(total > 1)

    def _prev_page(self) -> None:
        """Navigate to the previous page."""
        if self._current_page <= 0:
            return
        self._snapshot_current_page()
        self._current_page -= 1
        self._load_page(self._current_page)
        self._update_page_controls()

    def _next_page(self) -> None:
        """Navigate to the next page."""
        if self._current_page >= len(self._pages) - 1:
            return
        self._snapshot_current_page()
        self._current_page += 1
        self._load_page(self._current_page)
        self._update_page_controls()

    def _add_page(self) -> None:
        """Add a new empty page after the current one and navigate to it."""
        self._snapshot_current_page()
        self._current_page += 1
        self._pages.insert(self._current_page, [None] * 16)
        self._load_page(self._current_page)
        self._update_page_controls()

    def _remove_page(self) -> None:
        """Remove the current page (must have at least 1 page)."""
        if len(self._pages) <= 1:
            return
        self._pages.pop(self._current_page)
        if self._current_page >= len(self._pages):
            self._current_page = len(self._pages) - 1
        self._load_page(self._current_page)
        self._update_page_controls()

    def _clear_all_clicked(self) -> None:
        """Handle Clear All button click - clear all cards on current page and save."""
        self._clear_grid()
        self._snapshot_current_page()
        self._save_grid()

    def _clear_grid(self) -> None:
        """Clear all cards from the grid."""
        # Remove all existing cards
        for i, card in enumerate(self.replay_area.grid_positions):
            if card is not None:
                card.deleteLater()
                self.replay_area.grid_positions[i] = None
        
        self.replay_area.cards.clear()
        
        # Recreate placeholders for empty slots
        for i in range(16):
            if self.replay_area.grid_positions[i] is None:
                if self.replay_area.placeholder_buttons[i] is None:
                    self.replay_area._create_placeholder_at(i)
    
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
    
    @staticmethod
    def _pad_save_path() -> Path:
        """Return the path to the chord pad save file in AppData."""
        appdata = os.environ.get("APPDATA", str(Path.home()))
        save_dir = Path(appdata) / "Octavium"
        save_dir.mkdir(parents=True, exist_ok=True)
        return save_dir / "chord_pad.json"

    def _save_grid(self) -> None:
        """Persist all pages to AppData."""
        try:
            # Snapshot current page so in-memory pages list is up to date
            self._snapshot_current_page()
            data = {
                "version": 2,
                "current_page": self._current_page,
                "pages": self._pages,
            }
            with open(self._pad_save_path(), "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def _load_grid(self) -> None:
        """Restore pages from AppData if a save file exists."""
        try:
            save_path = self._pad_save_path()
            if not save_path.exists():
                return
            with open(save_path, "r", encoding="utf-8") as f:
                raw = json.load(f)

            # v2 format: {"version": 2, "pages": [...], "current_page": N}
            if isinstance(raw, dict) and raw.get("version") == 2:
                pages = raw.get("pages", [[None] * 16])
                if not pages:
                    pages = [[None] * 16]
                self._pages = pages
                self._current_page = min(raw.get("current_page", 0), len(pages) - 1)
            elif isinstance(raw, list):
                # Legacy v1 format: flat list of 16 slots
                self._pages = [raw[:16] + [None] * max(0, 16 - len(raw))]
                self._current_page = 0
            else:
                return

            self._load_page(self._current_page)
            self._update_page_controls()
        except Exception:
            pass

    def closeEvent(self, event):  # type: ignore[override]
        """Handle window close event."""
        self._snapshot_current_page()
        self._save_grid()
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
