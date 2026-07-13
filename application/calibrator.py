from __future__ import annotations
from typing import Optional

from domain.entities import PerspectiveCalibration, CalibrationPoint, Point2D


class CalibrationService:
    def __init__(self):
        self._raw_points: list[tuple[Point2D, Point2D, float]] = []
        self._calibration: Optional[PerspectiveCalibration] = None

    def reset(self):
        self._raw_points.clear()
        self._calibration = None

    def add_reference(self, p1: Point2D, p2: Point2D, real_distance_m: float) -> int:
        if real_distance_m <= 0:
            raise ValueError("La distancia real debe ser mayor a 0")
        px_dist = p1.distance_to(p2)
        if px_dist <= 0:
            raise ValueError("Los puntos de referencia no pueden coincidir")
        self._raw_points.append((p1, p2, real_distance_m))
        return len(self._raw_points)

    def compute_calibration(self) -> PerspectiveCalibration:
        if not self._raw_points:
            raise ValueError("Debe haber al menos una línea de referencia")
        points = []
        for p1, p2, dist_m in self._raw_points:
            px_dist = p1.distance_to(p2)
            mid_y = (p1.y + p2.y) / 2.0
            scale = px_dist / dist_m
            points.append(CalibrationPoint(y_coord=mid_y, scale_px_per_m=scale))
        self._calibration = PerspectiveCalibration(
            points=points, raw_lines=list(self._raw_points)
        )
        return self._calibration

    def remove_last(self) -> None:
        if self._raw_points:
            self._raw_points.pop()
        self._calibration = None

    @property
    def reference_count(self) -> int:
        return len(self._raw_points)

    @property
    def calibration(self) -> Optional[PerspectiveCalibration]:
        return self._calibration

    @property
    def is_calibrated(self) -> bool:
        return self._calibration is not None
