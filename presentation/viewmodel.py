from __future__ import annotations

import csv
import os
import time
import numpy as np
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from domain.entities import TrackedVehicle, PerspectiveCalibration, Point2D, Speed
from application.process_frame import ProcessFrameUseCase
from application.calibrator import CalibrationService
from application.parking_analyzer import ParkingAnalyzer
from infrastructure.video.opencv_source import OpenCVVideoSource
from infrastructure.detection.yolo_detector import YOLODetector
from infrastructure.tracking.bytetrack_impl import ByteTrack
from infrastructure.config.yaml_repo import ConfigRepository


class MainViewModel(QObject):
    frame_ready = pyqtSignal(object, list, float, int)
    stats_updated = pyqtSignal(dict, bool, float)
    calibration_frame_ready = pyqtSignal(object, int)
    status_message = pyqtSignal(str)
    video_loaded = pyqtSignal(int, float)
    export_ready = pyqtSignal(str)
    processing_stopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._config = ConfigRepository()
        self._video_source = OpenCVVideoSource()
        self._detector = YOLODetector()
        self._tracker = ByteTrack()
        self._calibrator = CalibrationService()
        self._parking_analyzer = ParkingAnalyzer()
        self._process_use_case = ProcessFrameUseCase(
            detector=self._detector,
            tracker=self._tracker,
            calibrator=self._calibrator,
            parking_analyzer=self._parking_analyzer,
        )

        self._settings = {}
        self._is_playing = False
        self._is_paused = False
        self._frame_count = 0
        self._fps_timer = time.time()
        self._fps_counter = 0
        self._current_fps = 0.0
        self._processing_timer = QTimer(self)
        self._processing_timer.timeout.connect(self._process_next_frame)

        self._load_config()

    def _load_config(self):
        self._settings = self._config.load_defaults()
        self._config.load_custom()
        for k, v in self._config.all.items():
            self._settings[k] = v
        self._apply_settings()

    def _apply_settings(self):
        self._process_use_case.update_settings(
            speed_limit=self._settings.get("speed_limit_kmh", 50.0),
            smoothing_window=self._settings.get("speed_smoothing_window", 8),
        )
        self._parking_analyzer.px_threshold = self._settings.get("parking_px_threshold", 3.0)
        self._parking_analyzer.confirm_frames = self._settings.get("parking_frames", 30)
        self._tracker._track_max_lost = self._settings.get("track_max_lost", 15)

        self._load_model_from_settings()

    def _load_model_from_settings(self):
        model_path = self._settings.get("model_path", "yolov8n.pt")
        current_path = self._detector.model_path

        if self._detector.model_loaded and model_path == current_path:
            return

        self.status_message.emit(f"Cargando modelo {model_path}...")
        try:
            self._detector.load_model(model_path)
            self.status_message.emit(f"Modelo cargado: {model_path}")
        except FileNotFoundError as e:
            self.status_message.emit(str(e))
        except ConnectionError:
            self.status_message.emit(
                f"Error de conexión al descargar '{model_path}'. "
                "Verifica tu conexión a internet."
            )
        except Exception as e:
            self.status_message.emit(f"Error cargando modelo '{model_path}': {e}")

    @property
    def settings(self) -> dict:
        return dict(self._settings)

    def update_settings(self, new_settings: dict):
        self._settings.update(new_settings)
        self._config.save(new_settings)
        self._apply_settings()

    @property
    def is_calibrated(self) -> bool:
        return self._calibrator.is_calibrated

    def open_video(self, path: str):
        try:
            self.stop_processing()
            self._process_use_case.clear_data()
            self._calibrator.reset()
            self._video_source.open(path)
            total_frames = self._video_source.get_total_frames()
            fps = self._video_source.get_fps()
            self.video_loaded.emit(total_frames, fps)
            self._process_use_case.set_fps(fps)
            self._frame_count = 0
            self.status_message.emit(f"Video cargado: {os.path.basename(path)}")

            # Go to calibration frame
            calib_frame = self._settings.get("calibration_frame", 5)
            calib_frame = min(calib_frame, total_frames - 1)
            self._video_source.set_frame(calib_frame)
            ret, frame, idx, ts = self._video_source.read()
            if ret and frame is not None:
                self.calibration_frame_ready.emit(frame, calib_frame)
                self.frame_ready.emit(frame, [], 0.0, calib_frame)
        except Exception as e:
            self.status_message.emit(f"Error abriendo video: {e}")

    def start_processing(self):
        if not self._video_source.is_opened():
            return
        if not self._calibrator.is_calibrated:
            self.status_message.emit("Debes calibrar primero (Tools \u2192 Calibrar)")
            return
        self._is_playing = True
        self._is_paused = False
        self._fps_counter = 0
        self._fps_timer = time.time()
        # Reopen video to start from beginning
        if self._video_source.source_path:
            self._video_source.set_frame(0)
        self._processing_timer.start(0)

    def pause_processing(self):
        self._is_paused = not self._is_paused

    def stop_processing(self):
        self._is_playing = False
        self._is_paused = False
        self._processing_timer.stop()
        self._process_use_case.reset()
        self._video_source.set_frame(0)
        self.frame_ready.emit(None, [], 0.0, 0)
        self.processing_stopped.emit()

    def request_calibration(self, frame: np.ndarray):
        self._calibrator.reset()

    def set_calibration(self, lines: list[tuple[Point2D, Point2D, float]]):
        try:
            self._calibrator.reset()
            for p1, p2, dist_m in lines:
                self._calibrator.add_reference(p1, p2, dist_m)
            calib = self._calibrator.compute_calibration()
            n = len(lines)
            scales = [f"{calib.scale_at(p.y):.1f}" for p in [lines[0][0], lines[-1][0]]]
            scale_text = f"{scales[0]} a {scales[1]} px/m" if n > 1 else f"{scales[0]} px/m"
            self.status_message.emit(
                f"Calibraci\u00f3n: {n} l\u00ednea(s), escala {scale_text}"
            )
            self.stats_updated.emit({}, True, calib.scale_at(lines[0][0].y))
        except ValueError as e:
            self.status_message.emit(f"Error de calibraci\u00f3n: {e}")

    def seek_to(self, frame_idx: int):
        if self._video_source.is_opened():
            self._video_source.set_frame(frame_idx)

    def _process_next_frame(self):
        if not self._is_playing or self._is_paused or not self._video_source.is_opened():
            return

        ret, frame, idx, ts = self._video_source.read()
        if not ret or frame is None:
            self.stop_processing()
            self.status_message.emit("Fin del video")
            return

        # FPS calculation
        self._fps_counter += 1
        elapsed = time.time() - self._fps_timer
        if elapsed >= 0.5:
            self._current_fps = self._fps_counter / elapsed
            self._fps_counter = 0
            self._fps_timer = time.time()
            self._process_use_case.set_fps(self._current_fps)

        # Process frame
        result = self._process_use_case.process(
            frame, idx, ts,
            conf_threshold=self._settings.get("confidence_threshold", 0.5),
            iou_threshold=self._settings.get("iou_threshold", 0.45),
        )

        calib = self._calibrator.calibration
        scale = calib.scale_at(calib.points[0].y_coord) if calib and calib.points else 0.0
        self.frame_ready.emit(result.frame, result.vehicles, result.fps_current, idx)
        self.stats_updated.emit(result.stats, result.calibration_active, scale)

        # Determine delay based on target FPS
        target_fps = self._video_source.get_fps()
        delay = max(1, int(1000 / max(target_fps, 1)))
        self._processing_timer.setInterval(delay)

    def export_csv(self, filepath: str):
        data = self._process_use_case.get_and_clear_export()
        if not data:
            self.status_message.emit("No hay datos para exportar")
            return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "timestamp", "track_id", "class_name", "speed_kmh",
                    "is_over_limit", "is_parked", "bbox_center_x",
                    "bbox_center_y", "frame_idx",
                ])
                writer.writeheader()
                writer.writerows(data)
            self.export_ready.emit(filepath)
            self.status_message.emit(f"Datos exportados: {os.path.basename(filepath)}")
        except Exception as e:
            self.status_message.emit(f"Error exportando CSV: {e}")

    def get_heatmap(self) -> np.ndarray | None:
        return self._process_use_case.get_heatmap()

    def get_hourly_counts(self) -> dict[int, int]:
        return self._process_use_case.get_hourly_counts()

    def cleanup(self):
        self.stop_processing()
        self._video_source.release()
