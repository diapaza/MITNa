from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
from enum import Enum, auto
from typing import Optional


class VehicleStatus(Enum):
    ENTERING = auto()
    MOVING = auto()
    PARKED = auto()
    LEAVING = auto()


class AlertType(Enum):
    NONE = auto()
    OVERSPEED = auto()


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def distance_to(self, other: Point2D) -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5


@dataclass
class BBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def centroid(self) -> Point2D:
        return Point2D((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def bottom_center(self) -> Point2D:
        return Point2D((self.x1 + self.x2) / 2, self.y2)

    def area(self) -> float:
        return self.width * self.height

    def iou(self, other: BBox) -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        inter = iw * ih
        union = self.area() + other.area() - inter
        return inter / union if union > 0 else 0.0

    def to_ltrb(self) -> tuple[float, float, float, float]:
        return (self.x1, self.y1, self.x2, self.y2)


@dataclass
class Detection:
    bbox: BBox
    confidence: float
    class_id: int
    class_name: str

    @property
    def is_vehicle(self) -> bool:
        return self.class_name in VEHICLE_CLASSES


VEHICLE_CLASSES: set[str] = {"car", "truck", "bus", "motorcycle", "bicycle"}


@dataclass
class Speed:
    value_m_s: float = 0.0
    value_kmh: float = 0.0
    is_over_limit: bool = False
    limit_kmh: float = 50.0

    @classmethod
    def from_m_s(cls, value: float, limit: float = 50.0) -> Speed:
        kmh = value * 3.6
        return cls(value_m_s=value, value_kmh=kmh, is_over_limit=kmh >= limit, limit_kmh=limit)

    @classmethod
    def from_kmh(cls, value: float, limit: float = 50.0) -> Speed:
        ms = value / 3.6
        return cls(value_m_s=ms, value_kmh=value, is_over_limit=value >= limit, limit_kmh=limit)


@dataclass
class CalibrationPoint:
    y_coord: float
    scale_px_per_m: float


@dataclass
class PerspectiveCalibration:
    points: list[CalibrationPoint]
    raw_lines: list[tuple[Point2D, Point2D, float]] = field(default_factory=list)

    def scale_at(self, y: float) -> float:
        if not self.points:
            return 0.0
        sorted_pts = sorted(self.points, key=lambda p: p.y_coord)
        if len(sorted_pts) == 1:
            return sorted_pts[0].scale_px_per_m
        if y <= sorted_pts[0].y_coord:
            return sorted_pts[0].scale_px_per_m
        if y >= sorted_pts[-1].y_coord:
            return sorted_pts[-1].scale_px_per_m
        for i in range(len(sorted_pts) - 1):
            if sorted_pts[i].y_coord <= y <= sorted_pts[i + 1].y_coord:
                t = ((y - sorted_pts[i].y_coord)
                     / (sorted_pts[i + 1].y_coord - sorted_pts[i].y_coord))
                return (sorted_pts[i].scale_px_per_m
                        + t * (sorted_pts[i + 1].scale_px_per_m - sorted_pts[i].scale_px_per_m))
        return sorted_pts[-1].scale_px_per_m

    def pixels_to_meters(self, px: float, y: float) -> float:
        return px / self.scale_at(y)


@dataclass
class TrackedVehicle:
    track_id: int
    bbox: BBox
    class_name: str
    confidence: float
    status: VehicleStatus = VehicleStatus.ENTERING
    speed: Speed = field(default_factory=Speed)
    alert: AlertType = AlertType.NONE
    positions_buffer: deque = field(default_factory=lambda: deque(maxlen=60))
    last_seen_frame: int = 0
    frames_since_last_seen: int = 0
    is_active: bool = True
    parked_confirmed_counter: int = 0
    entry_time: float = 0.0

    def update_position(self, bbox: BBox, frame_idx: int):
        self.bbox = bbox
        self.positions_buffer.append(bbox.bottom_center)
        self.last_seen_frame = frame_idx
        self.frames_since_last_seen = 0

    def mark_missing(self):
        self.frames_since_last_seen += 1
        if self.frames_since_last_seen > 30:
            self.is_active = False
            self.status = VehicleStatus.LEAVING
