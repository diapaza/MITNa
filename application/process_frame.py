from __future__ import annotations

import time
import cv2
import numpy as np
from typing import Optional

from domain.entities import (
    TrackedVehicle, Detection, Speed, VehicleStatus, AlertType,
    PerspectiveCalibration, BBox,
)
from application.ports import IDetector, ITracker
from application.calibrator import CalibrationService
from application.parking_analyzer import ParkingAnalyzer
from domain.value_objects import ProcessingResult, FrameData


class ProcessFrameUseCase:
    def __init__(
        self,
        detector: IDetector,
        tracker: ITracker,
        calibrator: CalibrationService,
        parking_analyzer: ParkingAnalyzer,
        speed_limit_kmh: float = 50.0,
        smoothing_window: int = 8,
    ):
        self._detector = detector
        self._tracker = tracker
        self._calibrator = calibrator
        self._parking_analyzer = parking_analyzer
        self._speed_limit_kmh = speed_limit_kmh
        self._smoothing_window = smoothing_window
        self._fps = 30.0
        self._export_buffer: list = []
        self._total_vehicles_seen: set[int] = set()
        self._heatmap_positions: list[tuple[float, float]] = []
        self._hourly_vehicles: dict[int, set[int]] = {}
        self._frame_size: tuple[int, int] = (640, 480)

    @property
    def calibrator(self) -> CalibrationService:
        return self._calibrator

    def update_settings(self, speed_limit: float, smoothing_window: int):
        self._speed_limit_kmh = speed_limit
        self._smoothing_window = smoothing_window

    def process(self, frame: object, frame_idx: int, timestamp_s: float,
                conf_threshold: float, iou_threshold: float) -> ProcessingResult:
        detections = self._detector.detect(frame, conf_threshold, iou_threshold)
        vehicles = self._tracker.update(detections, frame, frame_idx)
        self._total_vehicles_seen.update(v.track_id for v in vehicles)

        if hasattr(frame, 'shape'):
            self._frame_size = (frame.shape[1], frame.shape[0])

        calibration: PerspectiveCalibration | None = self._calibrator.calibration

        for v in vehicles:
            status = self._parking_analyzer.analyze(v)
            v.status = status

            if calibration and len(v.positions_buffer) >= 3:
                self._compute_speed(v, calibration)

            if v.speed.is_over_limit:
                v.alert = AlertType.OVERSPEED
            else:
                v.alert = AlertType.NONE

            self._export_buffer.append({
                "timestamp": timestamp_s,
                "track_id": v.track_id,
                "class_name": v.class_name,
                "speed_kmh": round(v.speed.value_kmh, 2),
                "is_over_limit": v.speed.is_over_limit,
                "is_parked": v.status == VehicleStatus.PARKED,
                "bbox_center_x": round(v.bbox.centroid.x, 1),
                "bbox_center_y": round(v.bbox.centroid.y, 1),
                "frame_idx": frame_idx,
            })

            bc = v.bbox.bottom_center
            self._heatmap_positions.append((bc.x, bc.y))
            hour_bucket = int(timestamp_s // 3600)
            if hour_bucket not in self._hourly_vehicles:
                self._hourly_vehicles[hour_bucket] = set()
            self._hourly_vehicles[hour_bucket].add(v.track_id)

        active = [v for v in vehicles if v.is_active]
        parked = sum(1 for v in active if v.status == VehicleStatus.PARKED)
        speeding = sum(1 for v in active if v.alert == AlertType.OVERSPEED)
        speeds = [v.speed.value_kmh for v in active if v.speed.value_kmh > 0 and v.status != VehicleStatus.PARKED]

        stats = {
            "total_detections": len(self._total_vehicles_seen),
            "active_vehicles": len(active),
            "parked_vehicles": parked,
            "speeding_vehicles": speeding,
            "avg_speed": round(np.mean(speeds), 1) if speeds else 0.0,
            "max_speed": round(max(speeds), 1) if speeds else 0.0,
        }

        return ProcessingResult(
            frame=frame,
            vehicles=active,
            stats=stats,
            calibration_active=calibration is not None,
            fps_current=self._fps,
        )

    def _compute_speed(self, vehicle: TrackedVehicle, calibration: PerspectiveCalibration):
        positions = list(vehicle.positions_buffer)
        if len(positions) < self._smoothing_window:
            return

        recent = positions[-self._smoothing_window:]
        displacements = []
        for i in range(1, len(recent)):
            d = recent[i - 1].distance_to(recent[i])
            displacements.append(d)

        avg_disp_px = np.mean(displacements)
        vehicle_y = vehicle.bbox.bottom_center.y
        disp_m = calibration.pixels_to_meters(avg_disp_px, vehicle_y)
        speed_ms = disp_m * self._fps
        vehicle.speed = Speed.from_m_s(speed_ms, self._speed_limit_kmh)

    def set_fps(self, fps: float):
        self._fps = max(1.0, fps)

    def get_and_clear_export(self) -> list:
        data = list(self._export_buffer)
        self._export_buffer.clear()
        return data

    def get_heatmap(self, width: int | None = None, height: int | None = None) -> np.ndarray:
        if not self._heatmap_positions:
            return np.zeros((height or 480, width or 640, 3), dtype=np.uint8)

        w = width or self._frame_size[0]
        h = height or self._frame_size[1]
        xs = np.array([p[0] for p in self._heatmap_positions])
        ys = np.array([p[1] for p in self._heatmap_positions])

        heatmap, _, _ = np.histogram2d(
            ys, xs, bins=[h, w],
            range=[[0, h], [0, w]],
        )
        heatmap = cv2.GaussianBlur(heatmap.astype(np.float32), (0, 0), sigmaX=15)
        heatmap = heatmap / (heatmap.max() + 1e-8)
        heatmap = (heatmap * 255).astype(np.uint8)
        colored = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(colored, 0.6, np.zeros_like(colored), 0.4, 0)
        return overlay

    def get_hourly_counts(self) -> dict[int, int]:
        return {h: len(ids) for h, ids in sorted(self._hourly_vehicles.items())}

    def reset(self):
        self._tracker.reset()

    def clear_data(self):
        self._tracker.reset()
        self._export_buffer.clear()
        self._total_vehicles_seen.clear()
        self._heatmap_positions.clear()
        self._hourly_vehicles.clear()
