from __future__ import annotations

import os
import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QFileDialog, QMessageBox, QStatusBar, QMenu, QLabel,
)

from presentation.widgets.video_display import VideoDisplay
from presentation.widgets.control_bar import ControlBar
from presentation.widgets.stats_panel import StatsPanel
from presentation.dialogs.calibration_dialog import CalibrationDialog
from presentation.dialogs.settings_dialog import SettingsDialog
from presentation.dialogs.heatmap_dialog import HeatmapDialog
from presentation.dialogs.hourly_chart_dialog import HourlyChartDialog
from presentation.viewmodel import MainViewModel
from domain.entities import Point2D, PerspectiveCalibration


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._viewmodel = MainViewModel(self)
        self._current_frame: np.ndarray | None = None
        self._is_calibrating = False
        self._setup_ui()
        self._connect_signals()
        self._apply_theme()

    def _setup_ui(self):
        self.setWindowTitle("Traffic Speed Tracker v1.0")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)

        self._setup_menu()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        self._video_display = VideoDisplay()
        left_layout.addWidget(self._video_display, 1)

        self._control_bar = ControlBar()
        left_layout.addWidget(self._control_bar)

        splitter.addWidget(left_widget)

        self._stats_panel = StatsPanel()
        splitter.addWidget(self._stats_panel)
        splitter.setSizes([900, 260])

        main_layout.addWidget(splitter, 1)

        self._status_label = QLabel("Listo")
        self.statusBar().addWidget(self._status_label)

    def _setup_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&Archivo")

        open_action = QAction("Abrir Video...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open_video)
        file_menu.addAction(open_action)

        export_action = QAction("Exportar CSV...", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._on_export_csv)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Salir", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("&Herramientas")

        calibrate_action = QAction("Calibrar...", self)
        calibrate_action.setShortcut(QKeySequence("Ctrl+K"))
        calibrate_action.triggered.connect(self._on_calibrate)
        tools_menu.addAction(calibrate_action)

        settings_action = QAction("Configuraci\u00f3n...", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._on_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        heatmap_action = QAction("Mapa de calor...", self)
        heatmap_action.setShortcut(QKeySequence("Ctrl+H"))
        heatmap_action.triggered.connect(self._on_heatmap)
        tools_menu.addAction(heatmap_action)

        chart_action = QAction("Gr\u00e1fico por hora...", self)
        chart_action.setShortcut(QKeySequence("Ctrl+G"))
        chart_action.triggered.connect(self._on_hourly_chart)
        tools_menu.addAction(chart_action)

        # Help menu
        help_menu = menubar.addMenu("&Ayuda")

        about_action = QAction("Acerca de...", self)
        about_action.triggered.connect(self._on_about)
        help_menu.addAction(about_action)

    def _connect_signals(self):
        self._viewmodel.frame_ready.connect(self._on_frame_ready)
        self._viewmodel.stats_updated.connect(self._stats_panel.update_stats)
        self._viewmodel.calibration_frame_ready.connect(self._on_calibration_frame_ready)
        self._viewmodel.status_message.connect(self._status_label.setText)
        self._viewmodel.video_loaded.connect(self._on_video_loaded)
        self._viewmodel.export_ready.connect(self._on_export_ready)
        self._viewmodel.processing_stopped.connect(self._on_processing_stopped)

        self._video_display.calibration_requested.connect(self._on_video_calibration_click)
        self._control_bar.play_toggled.connect(self._on_play_toggle)
        self._control_bar.stop_triggered.connect(self._on_stop)
        self._control_bar.seek_requested.connect(self._viewmodel.seek_to)

    def _apply_theme(self):
        theme_path = os.path.join(
            os.path.dirname(__file__), "resources", "theme.qss"
        )
        if os.path.exists(theme_path):
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    # --- Slots ---

    def _on_open_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Video",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*.*)"
        )
        if path:
            self._viewmodel.open_video(path)

    def _on_calibrate(self):
        if self._current_frame is not None:
            self._open_calibration_dialog(self._current_frame)

    def _on_settings(self):
        dialog = SettingsDialog(self._viewmodel.settings, self)
        dialog.settings_applied.connect(self._viewmodel.update_settings)
        dialog.exec()

    def _on_play_toggle(self, playing: bool):
        if playing:
            self._viewmodel.start_processing()
        else:
            self._viewmodel.pause_processing()

    def _on_stop(self):
        self._viewmodel.stop_processing()
        self._control_bar.set_playing(False)

    def _on_export_csv(self):
        if not self._viewmodel.is_calibrated:
            QMessageBox.warning(self, "Atenci\u00f3n",
                                "Debes calibrar antes de exportar datos.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "datos_vehiculos.csv",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        if path:
            self._viewmodel.export_csv(path)

    def _on_heatmap(self):
        if self._current_frame is None:
            QMessageBox.warning(self, "Atenci\u00f3n",
                                "Debes cargar un video primero.")
            return
        heatmap = self._viewmodel.get_heatmap()
        if heatmap is None or heatmap.size == 0 or heatmap.max() == 0:
            QMessageBox.information(self, "Mapa de calor",
                                    "No hay datos suficientes para generar el mapa de calor.")
            return
        dialog = HeatmapDialog(heatmap, self)
        dialog.exec()

    def _on_hourly_chart(self):
        counts = self._viewmodel.get_hourly_counts()
        if not counts:
            QMessageBox.information(self, "Gr\u00e1fico por hora",
                                    "No hay datos para generar el gr\u00e1fico.")
            return
        dialog = HourlyChartDialog(counts, self)
        dialog.exec()

    def _on_about(self):
        QMessageBox.about(
            self, "Acerca de Traffic Speed Tracker",
            "Traffic Speed Tracker v1.0\n\n"
            "Sistema de detecci\u00f3n y seguimiento de veh\u00edculos\n"
            "con c\u00e1lculo de velocidad en tiempo real.\n\n"
            "Tecnolog\u00edas: YOLOv8 + ByteTrack + PyQt6\n"
            "Arquitectura: Clean Architecture\n\n"
            "Proyecto Integrador - Visi\u00f3n Artificial"
        )

    def _on_frame_ready(self, frame, vehicles, fps, frame_idx):
        if frame is not None:
            self._current_frame = frame
            self._video_display.set_frame(frame)
            self._video_display.update_overlay(
                vehicles,
                self._viewmodel._calibrator.calibration,
                fps or 0,
                empty=(len(vehicles) == 0),
            )
            if fps:
                self._control_bar.update_position(frame_idx, fps)

    def _on_calibration_frame_ready(self, frame: np.ndarray, frame_idx: int):
        self._current_frame = frame
        self._video_display.set_frame(frame)
        self._video_display.update_overlay([], None, 0, empty=True)
        self._open_calibration_dialog(frame)

    def _on_video_loaded(self, total_frames: int, fps: float):
        self._control_bar.enable(True)
        self._control_bar.set_total_frames(total_frames, fps)
        self._control_bar.update_position(0, fps)

    def _on_export_ready(self, filepath: str):
        QMessageBox.information(
            self, "Exportaci\u00f3n completada",
            f"Datos exportados exitosamente a:\n{filepath}"
        )

    def _on_processing_stopped(self):
        self._control_bar.set_playing(False)
        self._video_display.update_overlay([], None, 0, empty=True)

    def _open_calibration_dialog(self, frame: np.ndarray):
        dialog = CalibrationDialog(frame, self)
        dialog.calibration_complete.connect(self._on_calibration_complete)
        dialog.exec()

    def _on_calibration_complete(self, lines: list):
        self._viewmodel.set_calibration(lines)
        self._video_display.enter_calibration_mode(False)

    def _on_video_calibration_click(self, frame: object, click_count: int):
        pass

    def closeEvent(self, event):
        self._viewmodel.cleanup()
        event.accept()
