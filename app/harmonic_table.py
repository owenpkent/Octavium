from typing import Tuple
from types import SimpleNamespace
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QSize, QPoint
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPen, QBrush

from .midi_io import MidiOut


class HexButton(QPushButton):
    """Custom painted hexagonal button in the app's blue theme."""
    def __init__(self, label: str, size_px: int, parent=None):
        super().__init__(label, parent)
        # Non-latching (momentary) behavior; visuals rely on isDown()
        self.setCheckable(False)
        self._size = int(size_px)
        self.setCursor(Qt.PointingHandCursor)
        self.setFlat(True)
        # Remove native styling; we paint everything
        self.setStyleSheet("QPushButton { background: transparent; border: none; }")
        # Flat-top hex proper aspect ratio: H = sqrt(3)/2 * W
        self._height = int(self._size * 0.8660254)
        self.setFixedSize(self._size, self._height)

    def _hex_path(self) -> QPainterPath:
        # Use the actual widget width/height so the path matches the visual size
        W = float(self.width())
        H = float(self.height())
        # Flat-top hex exact vertices using full widget rect (no extra margin)
        m = 0.0
        w = W - 2 * m
        h = H - 2 * m
        x0 = m
        x1 = m + 0.25 * w
        x2 = m + 0.75 * w
        x3 = m + w
        y0 = m
        y1 = m + 0.5 * h
        y2 = m + h
        pts = [
            QPoint(int(x3), int(y1)),  # right
            QPoint(int(x2), int(y2)),  # bottom-right
            QPoint(int(x1), int(y2)),  # bottom-left
            QPoint(int(x0), int(y1)),  # left
            QPoint(int(x1), int(y0)),  # top-left
            QPoint(int(x2), int(y0)),  # top-right
        ]
        
        path = QPainterPath()
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        path.closeSubpath()
        return path

    def paintEvent(self, ev):  # type: ignore[override]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        path = self._hex_path()
        # Background (pressed only; no latch)
        if self.isDown():
            fill = QColor('#2f82e6')
            text = QColor('white')
            border = QColor('#61b3ff')
        else:
            fill = QColor('#1b1f24')
            text = QColor('#cfe7ff')
            border = QColor('#3b4148')
        p.fillPath(path, QBrush(fill))
        pen = QPen(border)
        pen.setWidth(1)
        p.setPen(pen)
        p.drawPath(path)
        # Label
        p.setPen(text)
        p.drawText(self.rect(), Qt.AlignCenter, self.text())
        p.end()


class HarmonicTableWidget(QWidget):
    """Isomorphic Harmonic Table layout with a hex-style staggered grid of buttons.

    Mapping (typical Harmonic Table):
    - Horizontal step (E direction): +7 semitones (perfect fifth)
    - One axial step in the other basis (combines up-left/up-right): +3 semitones (minor third)

    We render a rectangular footprint using a flat-top hex grid with odd-q offset
    (columns are vertically offset by half a hex). This produces a tidy rectangle
    while preserving isomorphic harmonic adjacency.
    """
    def __init__(self, midi_out: MidiOut, scale: float = 1.0,
                 rows: int = 6, cols: int = 12,
                 base_note: int = 36,  # C2 lower starting octave
                 step_x: int = 7, step_y: int = 3):
        super().__init__()
        self.midi: MidiOut = midi_out
        self.port_name: str = ""
        try:
            self.ui_scale = float(scale) if float(scale) > 0 else 1.0
        except Exception:
            self.ui_scale = 1.0
        self.midi_channel: int = 0
        self.rows = int(rows)
        self.cols = int(cols)
        self.base_note = int(base_note)
        self.step_x = int(step_x)
        self.step_y = int(step_y)
        self.layout_model = SimpleNamespace(name="Harmonic Table", columns=self.cols)
        self.setWindowTitle("Harmonic Table")
        try:
            self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        except Exception:
            pass

        root = QVBoxLayout(self)
        root.setContentsMargins(int(10 * self.ui_scale), int(8 * self.ui_scale), int(10 * self.ui_scale), int(10 * self.ui_scale))
        root.setSpacing(int(8 * self.ui_scale))

        # Absolute-positioned honeycomb using axial coordinates (flat-top)
        self.buttons: list[list[QPushButton]] = []
        self.notes: list[list[int | None]] = []
        self._recompute_grid()

        grid = QWidget(self)
        grid.setObjectName("harmonic_grid")
        root.addWidget(grid, 0)

        # Geometry: flat-top hexes with odd-q vertical offset (rectangular footprint)
        size_px = int(60 * self.ui_scale)  # hex width = 2 * radius
        s = size_px / 2.0                   # radius
        import math
        H = int(round(math.sqrt(3.0) * s))  # hex height (center-to-center vertically per row)
        margin = int(12 * self.ui_scale)

        # Precompute grid size for sizeHint and widget size (odd-q offset rectangle)
        max_q = self.cols - 1
        max_r = self.rows - 1
        cx_max = s * 1.5 * max_q
        # With odd-q offset, tallest column gets an extra H/2
        cy_max = H * max_r + (H / 2 if self.cols > 1 else 0)
        grid_w = int(math.ceil(cx_max + size_px / 2.0)) + margin * 2
        grid_h = int(math.ceil(cy_max + H / 2.0)) + margin * 2
        grid.setFixedSize(grid_w, grid_h)

        for r in range(self.rows):
            row_btns: list[QPushButton] = []
            row_notes: list[int] = []
            for q in range(self.cols):
                note = self.notes[r][q]
                row_notes.append(note)
                label = self._note_name(note) if (note is not None and 0 <= note <= 127) else ""
                b = HexButton(label, size_px, grid)
                # centers (flat-top, odd-q offset rectangle)
                cx = s * 1.5 * q
                cy = H * r + (H / 2 if (q % 2) == 1 else 0)
                # top-left position
                x = int(round(cx - size_px / 2.0)) + margin
                y = int(round(cy - H / 2.0)) + margin
                b.move(x, y)
                if note is not None and 0 <= note <= 127:
                    b.pressed.connect(lambda r=r, q=q: self._on_btn(r, q, True))
                    b.released.connect(lambda r=r, q=q: self._on_btn(r, q, False))
                    b.setEnabled(True)
                else:
                    b.setEnabled(False)
                row_btns.append(b)
            self.buttons.append(row_btns)
            self.notes.append(row_notes)
        self.setLayout(root)

    def sizeHint(self) -> QSize:  # type: ignore[override]
        try:
            size_px = int(60 * self.ui_scale)
            s = size_px / 2.0
            import math
            H = int(round(math.sqrt(3.0) * s))
            max_q = self.cols - 1
            max_r = self.rows - 1
            cx_max = s * 1.5 * max_q
            cy_max = H * max_r + (H / 2 if self.cols > 1 else 0)
            margin = int(12 * self.ui_scale)
            w = int(math.ceil(cx_max + size_px / 2.0)) + margin * 2
            h = int(math.ceil(cy_max + H / 2.0)) + margin * 2
            return QSize(w, h)
        except Exception:
            return QSize(900, 420)

    # Mapping helpers
    def _recompute_grid(self):
        # Map notes using axial coordinates derived from flat-top odd-q offset
        # Base is placed at bottom-left cell (row = rows-1, col = 0)
        rows, cols = self.rows, self.cols
        notes: list[list[int | None]] = [[None for _ in range(cols)] for __ in range(rows)]
        if rows == 0 or cols == 0:
            self.notes = notes
            return
        base = int(self.base_note)
        step_q = int(self.step_x)  # per +q (east)
        step_r = int(self.step_y)  # per +r (south-east in axial for flat-top)
        last_row = rows - 1
        for r in range(rows):
            for q in range(cols):
                # Convert from offset (row=r, col=q) to axial r': r_ax = r - floor(q/2)
                r_ax = r - (q // 2)
                # Reference bottom-left axial r for base (col=0): r_base_ax = last_row
                dq = q  # since base col is 0
                dr = r_ax - last_row
                n = base + step_q * dq + step_r * dr
                notes[r][q] = n
        self.notes = notes

    @staticmethod
    def _note_name(n: int) -> str:
        names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        if n < 0:
            n = 0
        if n > 127:
            n = 127
        octave = (n // 12) - 1
        return f"{names[n % 12]}{octave}"

    # MIDI handlers
    def _on_btn(self, r: int, c: int, pressed: bool):
        try:
            note = int(self.notes[r][c])
        except Exception:
            return
        if pressed:
            try:
                self.midi.note_on(note, 100, self.midi_channel)
            except Exception:
                pass
        else:
            try:
                self.midi.note_off(note, self.midi_channel)
            except Exception:
                pass

    # External API parity
    def set_channel(self, channel_1_based: int):
        try:
            self.midi_channel = max(1, min(16, int(channel_1_based))) - 1
        except Exception:
            self.midi_channel = 0

    def set_midi_out(self, midi: MidiOut, port_name: str = ""):
        try:
            self.midi = midi
        except Exception:
            pass
        try:
            self.port_name = str(port_name)
        except Exception:
            self.port_name = ""

    # Config
    def get_mapping(self) -> Tuple[int, int, int]:
        return int(self.base_note), int(self.step_x), int(self.step_y)

    def set_mapping(self, base_note: int, step_x: int, step_y: int):
        try:
            self.base_note = int(base_note)
            self.step_x = int(step_x)
            self.step_y = int(step_y)
            # Recompute labels/notes
            self._recompute_grid()
            for r in range(self.rows):
                for c in range(self.cols):
                    n = self.notes[r][c]
                    try:
                        if n is not None and 0 <= n <= 127:
                            self.buttons[r][c].setText(self._note_name(int(n)))
                            self.buttons[r][c].setEnabled(True)
                        else:
                            self.buttons[r][c].setText("")
                            self.buttons[r][c].setEnabled(False)
                    except Exception:
                        pass
        except Exception:
            pass
