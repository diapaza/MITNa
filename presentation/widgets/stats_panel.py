from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QGroupBox, QGridLayout, QFrame,
    QSizePolicy,
)


class StatsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(260)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        title = QLabel("ESTAD\u00cdSTICAS")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        # General stats
        general_group = QGroupBox("General")
        general_grid = QGridLayout(general_group)
        general_grid.setSpacing(8)

        self._total_label = self._make_stat_value("0")
        self._active_label = self._make_stat_value("0")
        self._parked_label = self._make_stat_value("0")

        general_grid.addWidget(self._make_stat_title("Tot. Detectados"), 0, 0)
        general_grid.addWidget(self._total_label, 0, 1)
        general_grid.addWidget(self._make_stat_title("Activos"), 1, 0)
        general_grid.addWidget(self._active_label, 1, 1)
        general_grid.addWidget(self._make_stat_title("Estacionados"), 2, 0)
        general_grid.addWidget(self._parked_label, 2, 1)

        layout.addWidget(general_group)

        # Speed stats
        speed_group = QGroupBox("Velocidad")
        speed_grid = QGridLayout(speed_group)
        speed_grid.setSpacing(8)

        self._avg_speed_label = self._make_stat_value("--")
        self._max_speed_label = self._make_stat_value("--")
        self._speeding_label = self._make_stat_value("0")
        self._speeding_label.setObjectName("dangerLabel")

        speed_grid.addWidget(self._make_stat_title("Promedio"), 0, 0)
        speed_grid.addWidget(self._avg_speed_label, 0, 1)
        speed_grid.addWidget(self._make_stat_title("M\u00e1xima"), 1, 0)
        speed_grid.addWidget(self._max_speed_label, 1, 1)
        speed_grid.addWidget(self._make_stat_title("Excesos"), 2, 0)
        speed_grid.addWidget(self._speeding_label, 2, 1)

        layout.addWidget(speed_group)

        # Calibration info
        calib_group = QGroupBox("Calibraci\u00f3n")
        calib_layout = QVBoxLayout(calib_group)

        self._calib_status = QLabel("No calibrado")
        self._calib_status.setStyleSheet("color: #ffab00; font-weight: 600;")
        self._calib_scale = QLabel("")
        self._calib_scale.setStyleSheet("color: #888; font-size: 11px;")

        calib_layout.addWidget(self._calib_status)
        calib_layout.addWidget(self._calib_scale)

        layout.addWidget(calib_group)

        layout.addStretch(1)

    def update_stats(self, stats: dict, calibration_active: bool, scale: float = 0):
        self._total_label.setText(str(stats.get("total_detections", 0)))
        self._active_label.setText(str(stats.get("active_vehicles", 0)))
        self._parked_label.setText(str(stats.get("parked_vehicles", 0)))
        self._avg_speed_label.setText(f'{stats.get("avg_speed", 0):.1f} km/h')
        self._max_speed_label.setText(f'{stats.get("max_speed", 0):.1f} km/h')

        speeding = stats.get("speeding_vehicles", 0)
        self._speeding_label.setText(str(speeding))
        if speeding > 0:
            self._speeding_label.setStyleSheet("color: #ff1744; font-weight: 700; font-size: 22px;")
        else:
            self._speeding_label.setStyleSheet("color: #4fc3f7; font-weight: 700; font-size: 22px;")

        if calibration_active:
            self._calib_status.setText("Calibrado")
            self._calib_status.setStyleSheet("color: #00e676; font-weight: 600;")
            self._calib_scale.setText(f"Escala: {scale:.2f} px/m" if scale > 0 else "")
        else:
            self._calib_status.setText("No calibrado")
            self._calib_status.setStyleSheet("color: #ffab00; font-weight: 600;")
            self._calib_scale.setText("")

    def _make_stat_value(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("statValue")
        label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return label

    def _make_stat_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("statLabel")
        return label
