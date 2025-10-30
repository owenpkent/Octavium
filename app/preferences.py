"""
Preferences Window Module

Provides a preferences dialog for configuring MIDI ports and keyboard sizes.
"""

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QComboBox, QPushButton, QGroupBox, QFormLayout)
from PySide6.QtCore import Qt, Signal
import pygame.midi


class PreferencesDialog(QDialog):
    """Preferences dialog for MIDI and keyboard settings"""
    
    # Signals emitted when settings change
    midi_port_changed = Signal(str)
    keyboard_size_changed = Signal(int)
    
    def __init__(self, parent=None, current_midi_port="", current_keyboard_size=61):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.setFixedSize(400, 300)
        
        self.current_midi_port = current_midi_port
        self.current_keyboard_size = current_keyboard_size
        
        self.setup_ui()
        self.load_midi_ports()
        
    def setup_ui(self):
        """Setup the preferences UI"""
        layout = QVBoxLayout(self)
        
        # MIDI Settings Group
        midi_group = QGroupBox("MIDI Settings")
        midi_layout = QFormLayout(midi_group)
        
        self.midi_port_combo = QComboBox()
        midi_layout.addRow("MIDI Output Port:", self.midi_port_combo)
        
        layout.addWidget(midi_group)
        
        # Keyboard Settings Group
        keyboard_group = QGroupBox("Keyboard Settings")
        keyboard_layout = QFormLayout(keyboard_group)
        
        self.keyboard_size_combo = QComboBox()
        self.keyboard_size_combo.addItems([
            "49 Keys (4 Octaves)", 
            "61 Keys (5 Octaves)",
            "73 Keys (6 Octaves)",
            "76 Keys (6+ Octaves)",
            "88 Keys (Full Piano)"
        ])
        
        # Set current selection
        size_map = {49: 0, 61: 1, 73: 2, 76: 3, 88: 4}
        if self.current_keyboard_size in size_map:
            self.keyboard_size_combo.setCurrentIndex(size_map[self.current_keyboard_size])
        
        keyboard_layout.addRow("Keyboard Size:", self.keyboard_size_combo)
        
        layout.addWidget(keyboard_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.apply_btn = QPushButton("Apply")
        self.ok_btn = QPushButton("OK")
        
        self.cancel_btn.clicked.connect(self.reject)
        self.apply_btn.clicked.connect(self.apply_settings)
        self.ok_btn.clicked.connect(self.accept_settings)
        
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
    def load_midi_ports(self):
        """Load available MIDI output ports"""
        self.midi_port_combo.clear()
        
        try:
            pygame.midi.init()
            port_count = pygame.midi.get_count()
            
            # Add a default "Auto" option
            self.midi_port_combo.addItem("Auto (First Available)")
            
            for i in range(port_count):
                port_info = pygame.midi.get_device_info(i)
                if port_info:
                    name, is_input, is_output = port_info[1].decode(), port_info[2], port_info[3]
                    if is_output:  # Only show output ports
                        self.midi_port_combo.addItem(name)
            
            pygame.midi.quit()
            
            # Try to select current port
            if self.current_midi_port:
                index = self.midi_port_combo.findText(self.current_midi_port)
                if index >= 0:
                    self.midi_port_combo.setCurrentIndex(index)
                    
        except Exception as e:
            print(f"Error loading MIDI ports: {e}")
            self.midi_port_combo.addItem("No MIDI ports available")
    
    def get_selected_keyboard_size(self):
        """Get the selected keyboard size"""
        size_map = {0: 49, 1: 61, 2: 73, 3: 76, 4: 88}
        return size_map.get(self.keyboard_size_combo.currentIndex(), 61)
    
    def get_selected_midi_port(self):
        """Get the selected MIDI port"""
        text = self.midi_port_combo.currentText()
        if text == "Auto (First Available)":
            return ""
        return text
    
    def apply_settings(self):
        """Apply the current settings without closing dialog"""
        midi_port = self.get_selected_midi_port()
        keyboard_size = self.get_selected_keyboard_size()
        
        if midi_port != self.current_midi_port:
            self.midi_port_changed.emit(midi_port)
            self.current_midi_port = midi_port
            
        if keyboard_size != self.current_keyboard_size:
            self.keyboard_size_changed.emit(keyboard_size)
            self.current_keyboard_size = keyboard_size
    
    def accept_settings(self):
        """Apply settings and close dialog"""
        self.apply_settings()
        self.accept()
