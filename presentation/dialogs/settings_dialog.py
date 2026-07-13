from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QDoubleSpinBox, QSpinBox, QLineEdit, QComboBox, QPushButton,
    QTabWidget, QWidget, QGroupBox, QCheckBox, QFileDialog,
)

KNOWN_MODELS: list[str] = [
    "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt",
    "yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt", "yolo11x.pt",
]


class SettingsDialog(QDialog):
    settings_applied = pyqtSignal(dict)

    def __init__(self, current_settings: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuraci\u00f3n")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._settings = dict(current_settings)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_speed_tab(), "Velocidad")
        tabs.addTab(self._build_parking_tab(), "Estacionados")
        tabs.addTab(self._build_display_tab(), "Visualizaci\u00f3n")
        layout.addWidget(tabs)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        apply_btn = QPushButton("Aplicar")
        apply_btn.setObjectName("successButton")
        apply_btn.clicked.connect(self._on_apply)
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)

        self._model_combo = QComboBox()
        self._model_combo.setEditable(False)
        current = self._settings.get("model_path", "yolov8n.pt")
        self._model_combo.addItems(KNOWN_MODELS)
        self._model_combo.addItem("Otro...")
        idx = self._model_combo.findText(current)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setCurrentIndex(0)
        self._model_custom_path = current if idx < 0 and current not in KNOWN_MODELS else ""
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        form.addRow("Modelo YOLO:", self._model_combo)

        self._conf_threshold = QDoubleSpinBox()
        self._conf_threshold.setRange(0.01, 1.0)
        self._conf_threshold.setSingleStep(0.05)
        self._conf_threshold.setDecimals(2)
        self._conf_threshold.setValue(self._settings.get("confidence_threshold", 0.5))
        form.addRow("Confianza m\u00edn:", self._conf_threshold)

        self._iou_threshold = QDoubleSpinBox()
        self._iou_threshold.setRange(0.01, 1.0)
        self._iou_threshold.setSingleStep(0.05)
        self._iou_threshold.setDecimals(2)
        self._iou_threshold.setValue(self._settings.get("iou_threshold", 0.45))
        form.addRow("IoU NMS:", self._iou_threshold)

        self._calibration_frame = QSpinBox()
        self._calibration_frame.setRange(1, 100)
        self._calibration_frame.setValue(self._settings.get("calibration_frame", 5))
        form.addRow("Frame de calibraci\u00f3n:", self._calibration_frame)

        return tab

    def _build_speed_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)

        self._speed_limit = QDoubleSpinBox()
        self._speed_limit.setRange(1, 200)
        self._speed_limit.setSuffix(" km/h")
        self._speed_limit.setValue(self._settings.get("speed_limit_kmh", 50.0))
        form.addRow("L\u00edmite velocidad:", self._speed_limit)

        self._smoothing = QSpinBox()
        self._smoothing.setRange(2, 30)
        self._smoothing.setValue(self._settings.get("speed_smoothing_window", 8))
        form.addRow("Ventana suavizado (frames):", self._smoothing)

        self._track_max_lost = QSpinBox()
        self._track_max_lost.setRange(1, 60)
        self._track_max_lost.setValue(self._settings.get("track_max_lost", 15))
        form.addRow("Frames perdidos antes de eliminar:", self._track_max_lost)

        return tab

    def _build_parking_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)

        self._parking_px = QDoubleSpinBox()
        self._parking_px.setRange(0.1, 50.0)
        self._parking_px.setDecimals(1)
        self._parking_px.setSuffix(" px")
        self._parking_px.setValue(self._settings.get("parking_px_threshold", 3.0))
        form.addRow("Umbral estacionado (px):", self._parking_px)

        self._parking_frames = QSpinBox()
        self._parking_frames.setRange(5, 120)
        self._parking_frames.setValue(self._settings.get("parking_frames", 30))
        form.addRow("Frames para confirmar estacionado:", self._parking_frames)

        return tab

    def _build_display_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(10)

        self._show_fps = QCheckBox()
        self._show_fps.setChecked(self._settings.get("show_fps", True))
        form.addRow("Mostrar FPS:", self._show_fps)

        return tab

    def _on_model_changed(self, text: str):
        if text == "Otro...":
            path, _ = QFileDialog.getOpenFileName(
                self, "Seleccionar modelo YOLO",
                "", "Modelos (*.pt);;All Files (*.*)"
            )
            if path:
                self._model_custom_path = path
                self._model_combo.blockSignals(True)
                self._model_combo.setCurrentIndex(self._model_combo.count() - 1)
                self._model_combo.setItemText(self._model_combo.count() - 1, path)
                self._model_combo.blockSignals(False)
            else:
                prev = self._settings.get("model_path", "yolov8n.pt")
                self._model_combo.blockSignals(True)
                idx = self._model_combo.findText(prev)
                self._model_combo.setCurrentIndex(idx if idx >= 0 else 0)
                self._model_combo.blockSignals(False)

    def _get_model_path(self) -> str:
        text = self._model_combo.currentText()
        if self._model_combo.currentIndex() == self._model_combo.count() - 1:
            return self._model_custom_path if self._model_custom_path else ""
        return text

    def _on_apply(self):
        self._settings.update({
            "model_path": self._get_model_path(),
            "confidence_threshold": self._conf_threshold.value(),
            "iou_threshold": self._iou_threshold.value(),
            "calibration_frame": self._calibration_frame.value(),
            "speed_limit_kmh": self._speed_limit.value(),
            "speed_smoothing_window": self._smoothing.value(),
            "track_max_lost": self._track_max_lost.value(),
            "parking_px_threshold": self._parking_px.value(),
            "parking_frames": self._parking_frames.value(),
            "show_fps": self._show_fps.isChecked(),
        })
        self.settings_applied.emit(self._settings)
        self.accept()
