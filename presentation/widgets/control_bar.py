from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QSpacerItem,
    QSizePolicy, QStyle,
)


class ControlBar(QWidget):
    play_toggled = pyqtSignal(bool)
    stop_triggered = pyqtSignal()
    seek_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_playing = False
        self._total_frames = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self._play_btn = QPushButton()
        self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self._play_btn.setFixedSize(36, 32)
        self._play_btn.setToolTip("Play / Pausa")
        self._play_btn.clicked.connect(self._toggle_play)

        self._stop_btn = QPushButton()
        self._stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self._stop_btn.setFixedSize(36, 32)
        self._stop_btn.setToolTip("Detener")
        self._stop_btn.clicked.connect(self._on_stop)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(0)
        self._slider.setValue(0)
        self._slider.sliderMoved.connect(self._on_seek)

        self._position_label = QLabel("00:00 / 00:00")
        self._position_label.setFixedWidth(140)
        self._position_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self._play_btn)
        layout.addWidget(self._stop_btn)
        layout.addWidget(self._slider, 1)
        layout.addWidget(self._position_label)

        self.setEnabled(False)

    def _toggle_play(self):
        self._is_playing = not self._is_playing
        icon = (QStyle.StandardPixmap.SP_MediaPause if self._is_playing
                else QStyle.StandardPixmap.SP_MediaPlay)
        self._play_btn.setIcon(self.style().standardIcon(icon))
        self.play_toggled.emit(self._is_playing)

    def _on_stop(self):
        self._is_playing = False
        self._play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.stop_triggered.emit()

    def _on_seek(self, position: int):
        self.seek_requested.emit(position)

    def set_playing(self, playing: bool):
        self._is_playing = playing
        icon = (QStyle.StandardPixmap.SP_MediaPause if playing
                else QStyle.StandardPixmap.SP_MediaPlay)
        self._play_btn.setIcon(self.style().standardIcon(icon))

    def set_total_frames(self, total: int, fps: float):
        self._total_frames = total
        self._slider.setMaximum(max(0, total - 1))

    def update_position(self, frame_idx: int, fps: float):
        self._slider.blockSignals(True)
        self._slider.setValue(frame_idx)
        self._slider.blockSignals(False)

        current_s = frame_idx / fps if fps > 0 else 0
        total_s = self._total_frames / fps if fps > 0 else 0
        self._position_label.setText(
            f"{self._format_time(current_s)} / {self._format_time(total_s)}"
        )

    def enable(self, enabled: bool):
        self.setEnabled(enabled)

    @staticmethod
    def _format_time(seconds: float) -> str:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"
