from PySide6.QtWidgets import QWidget, QPushButton, QGridLayout, QHBoxLayout, QVBoxLayout, QLabel, QSlider
from PySide6.QtCore import Qt, QSize
from .models import Layout, KeyDef
from .midi_io import MidiOut
from .scale import quantize

def velocity_curve(v_in: int, curve: str) -> int:
    v = max(1, min(127, v_in))
    if curve == "soft":
        return int((v / 127) ** 0.7 * 127)
    if curve == "hard":
        return int((v / 127) ** 1.5 * 127)
    return v

class KeyboardWidget(QWidget):
    def __init__(self, layout_model: Layout, midi_out: MidiOut, title: str = ""):
        super().__init__()
        self.layout_model = layout_model
        self.midi = midi_out
        self.octave_offset = 0
        self.sustain = False
        self.vel_curve = "linear"
        self.active_notes: set[tuple[int,int]] = set()
        self.setWindowTitle(title or layout_model.name)
        root = QVBoxLayout(self)

        header = QHBoxLayout()
        self.oct_label = QLabel("Octave: 0")
        self.sus_label = QLabel("Sustain: Off")
        self.vel_label = QLabel("Vel curve: linear")
        header.addWidget(self.oct_label)
        header.addWidget(self.sus_label)
        header.addWidget(self.vel_label)
        header.addStretch()
        self.vel_slider = QSlider(Qt.Horizontal)
        self.vel_slider.setMinimum(20)
        self.vel_slider.setMaximum(127)
        self.vel_slider.setValue(100)
        header.addWidget(QLabel("Vel"))
        header.addWidget(self.vel_slider)
        root.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(self.layout_model.gap)
        grid.setVerticalSpacing(self.layout_model.gap)
        row_idx = 0
        for r in self.layout_model.rows:
            col = 0
            for key in r.keys:
                btn = QPushButton(key.label)
                w = max(1, key.width)
                h = max(1, key.height)
                btn.setMinimumSize(QSize(44 * w, 44 * h))
                if key.color:
                    btn.setStyleSheet(f"background-color: {key.color};")
                btn.pressed.connect(lambda k=key: self.on_key_press(k))
                btn.released.connect(lambda k=key: self.on_key_release(k))
                grid.addWidget(btn, row_idx, col, h, w)
                col += w
            row_idx += 1
        root.addLayout(grid)

        tips = QLabel("Shortcuts: Z/X octave down/up, S toggle sustain, 1/2/3 velocity curve, Q quantize toggle, Esc all notes off")
        tips.setStyleSheet("color: gray;")
        root.addWidget(tips)

    def effective_note(self, base_note: int) -> int:
        n = base_note + 12 * (self.layout_model.base_octave + self.octave_offset)
        n = max(0, min(127, n))
        n = quantize(n, self.layout_model.quantize_scale or "chromatic", self.layout_model.custom_scale)
        return n

    def on_key_press(self, key: KeyDef):
        note = self.effective_note(key.note)
        vel = velocity_curve(int(self.vel_slider.value() * (key.velocity / 127)), self.vel_curve)
        self.midi.note_on(note, vel, key.channel)
        self.active_notes.add((note, key.channel))

    def on_key_release(self, key: KeyDef):
        note = self.effective_note(key.note)
        if self.sustain:
            return
        self.midi.note_off(note, key.channel)
        self.active_notes.discard((note, key.channel))

    def keyPressEvent(self, event):
        k = event.key()
        if k == Qt.Key_Z:
            self.octave_offset -= 1
            self.oct_label.setText(f"Octave: {self.octave_offset}")
        elif k == Qt.Key_X:
            self.octave_offset += 1
            self.oct_label.setText(f"Octave: {self.octave_offset}")
        elif k == Qt.Key_S:
            self.sustain = not self.sustain
            self.sus_label.setText(f"Sustain: {'On' if self.sustain else 'Off'}")
            if not self.sustain:
                self.all_notes_off()
        elif k == Qt.Key_1:
            self.vel_curve = "linear"; self.vel_label.setText("Vel curve: linear")
        elif k == Qt.Key_2:
            self.vel_curve = "soft"; self.vel_label.setText("Vel curve: soft")
        elif k == Qt.Key_3:
            self.vel_curve = "hard"; self.vel_label.setText("Vel curve: hard")
        elif k == Qt.Key_Q:
            q = self.layout_model.quantize_scale or "chromatic"
            self.layout_model.quantize_scale = "chromatic" if q != "chromatic" else "major"
        elif k == Qt.Key_Escape:
            self.all_notes_off()

    def all_notes_off(self):
        for note, ch in list(self.active_notes):
            self.midi.note_off(note, ch)
        self.active_notes.clear()
