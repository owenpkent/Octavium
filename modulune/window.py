"""
Modulune Window - GUI for the generative engine.

Provides a control panel for starting/stopping generation and adjusting
parameters in real-time with separate left/right hand controls.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QGridLayout, QSlider, QComboBox,
    QFrame, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QFont
from pathlib import Path
from typing import Optional

from .engine import ModuluneEngine, EngineConfig, TextureType, LeftHandTexture
from .harmony import ScaleType, Chord


# Note names for display
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Texture display names
RH_TEXTURE_NAMES = [
    ("Shimmering Chords", TextureType.SHIMMERING_CHORDS),
    ("Flowing Arpeggios", TextureType.FLOWING_ARPEGGIOS),
    ("Melodic Fragments", TextureType.MELODIC_FRAGMENTS),
    ("Sparse Meditation", TextureType.SPARSE_MEDITATION),
    ("Layered Voices", TextureType.LAYERED_VOICES),
    ("Impressionist Wash", TextureType.IMPRESSIONIST_WASH),
    ("Off", TextureType.OFF),
]

LH_TEXTURE_NAMES = [
    ("Sustained Bass", LeftHandTexture.SUSTAINED_BASS),
    ("Broken Chords", LeftHandTexture.BROKEN_CHORDS),
    ("Alberti Bass", LeftHandTexture.ALBERTI_BASS),
    ("Block Chords", LeftHandTexture.BLOCK_CHORDS),
    ("Rolling Octaves", LeftHandTexture.ROLLING_OCTAVES),
    ("Sparse Roots", LeftHandTexture.SPARSE_ROOTS),
    ("Off", LeftHandTexture.OFF),
]


class ModuluneWindow(QMainWindow):
    """
    GUI window for controlling the Modulune generative engine.
    
    Provides real-time controls for tempo, key, mode, density, tension,
    and texture selection.
    """
    
    def __init__(self, midi_out, channel: int = 0, parent=None):
        """
        Initialize the Modulune window.
        
        Args:
            midi_out: Shared MidiOut instance.
            channel: MIDI channel to use.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.midi_out = midi_out
        self.channel = channel
        
        # Create engine config with dual-hand defaults
        self.config = EngineConfig(
            tempo=72.0,
            key_root=60,
            scale_type=ScaleType.MAJOR,
            tension=0.3,
            expressiveness=0.6,
            channel=channel,
            rh_texture=TextureType.SHIMMERING_CHORDS,
            rh_density=0.5,
            lh_texture=LeftHandTexture.SUSTAINED_BASS,
            lh_density=0.4,
        )
        
        # Engine will be created when started
        self.engine: Optional[ModuluneEngine] = None
        self.is_playing = False
        
        self._setup_ui()
        self._apply_theme()
        
        # Update display timer
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_display)
        self.update_timer.start(100)
    
    def _setup_ui(self):
        """Set up the user interface with separate left/right hand controls."""
        self.setWindowTitle("Modulune - Generative Engine")
        self.setMinimumSize(500, 750)
        
        # Set window icon
        try:
            icon_path = Path(__file__).resolve().parent.parent / "Octavium icon.png"
            self.setWindowIcon(QIcon(str(icon_path)))
        except Exception:
            pass
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)
        
        # Header
        header = QLabel("Modulune")
        header.setFont(QFont("", 24, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("color: #9b7fd4;")
        layout.addWidget(header)
        
        # Status display
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame {
                background-color: #2b2f36;
                border: 2px solid #3b4148;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        status_layout = QHBoxLayout(self.status_frame)
        
        self.status_label = QLabel("● Stopped")
        self.status_label.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        self.chord_label = QLabel("—")
        self.chord_label.setStyleSheet("color: #9b7fd4; font-size: 16px; font-weight: bold;")
        self.chord_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_layout.addWidget(self.chord_label)
        
        layout.addWidget(self.status_frame)
        
        # Play/Stop button
        self.play_btn = QPushButton("▶  Start")
        self.play_btn.setMinimumHeight(45)
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d;
                border: 2px solid #3d7a3d;
                border-radius: 8px;
                color: #fff;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3d7a3d; }
            QPushButton:pressed { background-color: #4d9a4d; }
        """)
        self.play_btn.clicked.connect(self._toggle_play)
        layout.addWidget(self.play_btn)
        
        # Key & Mode section
        key_group = QGroupBox("Key & Mode")
        key_layout = QGridLayout(key_group)
        key_layout.setSpacing(8)
        
        key_layout.addWidget(QLabel("Key:"), 0, 0)
        self.key_combo = QComboBox()
        self.key_combo.addItems(NOTE_NAMES)
        self.key_combo.setCurrentIndex(0)
        self.key_combo.currentIndexChanged.connect(self._on_key_changed)
        key_layout.addWidget(self.key_combo, 0, 1)
        
        key_layout.addWidget(QLabel("Mode:"), 0, 2)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems([
            "Major", "Natural Minor", "Dorian", "Phrygian", 
            "Lydian", "Mixolydian", "Whole Tone", "Pentatonic"
        ])
        self.mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        key_layout.addWidget(self.mode_combo, 0, 3)
        
        layout.addWidget(key_group)
        
        # =========================================================
        # RIGHT HAND section
        # =========================================================
        rh_group = QGroupBox("Right Hand (Upper)")
        rh_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #b8d4f0;
                border: 2px solid #4a6080;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        rh_layout = QGridLayout(rh_group)
        rh_layout.setSpacing(6)
        
        rh_layout.addWidget(QLabel("Texture:"), 0, 0)
        self.rh_texture_combo = QComboBox()
        self.rh_texture_combo.addItems([name for name, _ in RH_TEXTURE_NAMES])
        self.rh_texture_combo.setCurrentIndex(0)  # Shimmering Chords
        self.rh_texture_combo.currentIndexChanged.connect(self._on_rh_texture_changed)
        rh_layout.addWidget(self.rh_texture_combo, 0, 1, 1, 2)
        
        rh_layout.addWidget(QLabel("Density:"), 1, 0)
        self.rh_density_slider = QSlider(Qt.Orientation.Horizontal)
        self.rh_density_slider.setRange(0, 100)
        self.rh_density_slider.setValue(50)
        self.rh_density_slider.valueChanged.connect(self._on_rh_density_changed)
        rh_layout.addWidget(self.rh_density_slider, 1, 1)
        self.rh_density_value = QLabel("50%")
        self.rh_density_value.setMinimumWidth(35)
        rh_layout.addWidget(self.rh_density_value, 1, 2)
        
        layout.addWidget(rh_group)
        
        # =========================================================
        # LEFT HAND section
        # =========================================================
        lh_group = QGroupBox("Left Hand (Lower)")
        lh_group.setStyleSheet("""
            QGroupBox {
                font-size: 13px;
                font-weight: bold;
                color: #d4b8f0;
                border: 2px solid #6a4a80;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        lh_layout = QGridLayout(lh_group)
        lh_layout.setSpacing(6)
        
        lh_layout.addWidget(QLabel("Texture:"), 0, 0)
        self.lh_texture_combo = QComboBox()
        self.lh_texture_combo.addItems([name for name, _ in LH_TEXTURE_NAMES])
        self.lh_texture_combo.setCurrentIndex(0)  # Sustained Bass
        self.lh_texture_combo.currentIndexChanged.connect(self._on_lh_texture_changed)
        lh_layout.addWidget(self.lh_texture_combo, 0, 1, 1, 2)
        
        lh_layout.addWidget(QLabel("Density:"), 1, 0)
        self.lh_density_slider = QSlider(Qt.Orientation.Horizontal)
        self.lh_density_slider.setRange(0, 100)
        self.lh_density_slider.setValue(40)
        self.lh_density_slider.valueChanged.connect(self._on_lh_density_changed)
        lh_layout.addWidget(self.lh_density_slider, 1, 1)
        self.lh_density_value = QLabel("40%")
        self.lh_density_value.setMinimumWidth(35)
        lh_layout.addWidget(self.lh_density_value, 1, 2)
        
        layout.addWidget(lh_group)
        
        # =========================================================
        # Global Parameters section
        # =========================================================
        params_group = QGroupBox("Global")
        params_layout = QGridLayout(params_group)
        params_layout.setSpacing(6)
        
        # Tempo
        params_layout.addWidget(QLabel("Tempo:"), 0, 0)
        self.tempo_slider = QSlider(Qt.Orientation.Horizontal)
        self.tempo_slider.setRange(40, 140)
        self.tempo_slider.setValue(72)
        self.tempo_slider.valueChanged.connect(self._on_tempo_changed)
        params_layout.addWidget(self.tempo_slider, 0, 1)
        self.tempo_value = QLabel("72")
        self.tempo_value.setMinimumWidth(35)
        params_layout.addWidget(self.tempo_value, 0, 2)
        
        # Tension
        params_layout.addWidget(QLabel("Tension:"), 1, 0)
        self.tension_slider = QSlider(Qt.Orientation.Horizontal)
        self.tension_slider.setRange(0, 100)
        self.tension_slider.setValue(30)
        self.tension_slider.valueChanged.connect(self._on_tension_changed)
        params_layout.addWidget(self.tension_slider, 1, 1)
        self.tension_value = QLabel("30%")
        self.tension_value.setMinimumWidth(35)
        params_layout.addWidget(self.tension_value, 1, 2)
        
        # Expressiveness
        params_layout.addWidget(QLabel("Expression:"), 2, 0)
        self.expr_slider = QSlider(Qt.Orientation.Horizontal)
        self.expr_slider.setRange(0, 100)
        self.expr_slider.setValue(60)
        self.expr_slider.valueChanged.connect(self._on_expr_changed)
        params_layout.addWidget(self.expr_slider, 2, 1)
        self.expr_value = QLabel("60%")
        self.expr_value.setMinimumWidth(35)
        params_layout.addWidget(self.expr_value, 2, 2)
        
        layout.addWidget(params_group)
        
        layout.addStretch()
    
    def _apply_theme(self):
        """Apply dark theme styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e2127;
            }
            QWidget {
                background-color: #1e2127;
                color: #fff;
            }
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #fff;
                border: 2px solid #3b4148;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QComboBox {
                background-color: #2b2f36;
                border: 1px solid #3b4148;
                border-radius: 4px;
                padding: 5px 10px;
                color: #fff;
                min-height: 25px;
            }
            QComboBox:hover {
                border: 1px solid #2f82e6;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #2b2f36;
                color: #fff;
                selection-background-color: #2f82e6;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #3b4148;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #9b7fd4;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::handle:horizontal:hover {
                background: #b99fe4;
            }
            QLabel {
                color: #ccc;
            }
        """)
    
    def _toggle_play(self):
        """Toggle play/stop state."""
        if self.is_playing:
            self._stop()
        else:
            self._start()
    
    def _start(self):
        """Start the generative engine."""
        if self.engine is None:
            # Create engine with current config using the shared MIDI
            self.engine = ModuluneEngine(self.config)
            # Replace the engine's MIDI with our shared one
            self.engine._midi = self.midi_out
            self.engine.on_chord_change(self._on_chord_changed)
        
        self.engine.start()
        self.is_playing = True
        
        self.play_btn.setText("■  Stop")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #5a2d2d;
                border: 2px solid #7a3d3d;
                border-radius: 8px;
                color: #fff;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7a3d3d;
            }
            QPushButton:pressed {
                background-color: #9a4d4d;
            }
        """)
        self.status_label.setText("● Playing")
        self.status_label.setStyleSheet("color: #5d5; font-size: 16px; font-weight: bold;")
    
    def _stop(self):
        """Stop the generative engine."""
        if self.engine:
            self.engine.stop()
        
        self.is_playing = False
        
        self.play_btn.setText("▶  Start")
        self.play_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d5a2d;
                border: 2px solid #3d7a3d;
                border-radius: 8px;
                color: #fff;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3d7a3d;
            }
            QPushButton:pressed {
                background-color: #4d9a4d;
            }
        """)
        self.status_label.setText("● Stopped")
        self.status_label.setStyleSheet("color: #888; font-size: 16px; font-weight: bold;")
        self.chord_label.setText("—")
    
    def _on_key_changed(self, index: int):
        """Handle key change."""
        self.config.key_root = 60 + index  # C4 + offset
        if self.engine:
            self.engine.set_key(self.config.key_root)
    
    def _on_mode_changed(self, index: int):
        """Handle mode change."""
        mode_map = [
            ScaleType.MAJOR,
            ScaleType.NATURAL_MINOR,
            ScaleType.DORIAN,
            ScaleType.PHRYGIAN,
            ScaleType.LYDIAN,
            ScaleType.MIXOLYDIAN,
            ScaleType.WHOLE_TONE,
            ScaleType.PENTATONIC_MAJOR,
        ]
        self.config.scale_type = mode_map[index]
        if self.engine:
            self.engine.set_key(self.config.key_root, self.config.scale_type)
    
    def _on_rh_texture_changed(self, index: int):
        """Handle right hand texture change."""
        _, texture = RH_TEXTURE_NAMES[index]
        self.config.rh_texture = texture
        if self.engine:
            self.engine.set_rh_texture(texture)
    
    def _on_rh_density_changed(self, value: int):
        """Handle right hand density slider change."""
        self.config.rh_density = value / 100.0
        self.rh_density_value.setText(f"{value}%")
        if self.engine:
            self.engine.set_rh_density(self.config.rh_density)
    
    def _on_lh_texture_changed(self, index: int):
        """Handle left hand texture change."""
        _, texture = LH_TEXTURE_NAMES[index]
        self.config.lh_texture = texture
        if self.engine:
            self.engine.set_lh_texture(texture)
    
    def _on_lh_density_changed(self, value: int):
        """Handle left hand density slider change."""
        self.config.lh_density = value / 100.0
        self.lh_density_value.setText(f"{value}%")
        if self.engine:
            self.engine.set_lh_density(self.config.lh_density)
    
    def _on_tempo_changed(self, value: int):
        """Handle tempo slider change."""
        self.config.tempo = float(value)
        self.tempo_value.setText(str(value))
        if self.engine:
            self.engine.set_tempo(value)
    
    def _on_tension_changed(self, value: int):
        """Handle tension slider change."""
        self.config.tension = value / 100.0
        self.tension_value.setText(f"{value}%")
        if self.engine:
            self.engine.set_tension(self.config.tension)
    
    def _on_expr_changed(self, value: int):
        """Handle expressiveness slider change."""
        self.config.expressiveness = value / 100.0
        self.expr_value.setText(f"{value}%")
        if self.engine:
            self.engine.set_expressiveness(self.config.expressiveness)
    
    def _on_chord_changed(self, chord: Chord):
        """Handle chord change callback from engine."""
        root_name = NOTE_NAMES[chord.root % 12]
        quality_name = chord.quality.value.replace("_", " ").title()
        self.chord_label.setText(f"{root_name} {quality_name}")
    
    def _update_display(self):
        """Update display periodically."""
        # Could add beat visualization, note activity, etc.
        pass
    
    def closeEvent(self, event):
        """Handle window close."""
        self._stop()
        if self.engine:
            self.engine = None
        self.update_timer.stop()
        super().closeEvent(event)
