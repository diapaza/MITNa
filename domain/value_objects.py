from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class FrameData:
    frame: object
    frame_idx: int
    timestamp_s: float
    fps: float


@dataclass
class ProcessingResult:
    frame: object
    vehicles: list
    stats: dict
    calibration_active: bool
    fps_current: float


@dataclass
class ExportRecord:
    timestamp_s: float
    track_id: int
    class_name: str
    speed_kmh: float
    is_over_limit: bool
    is_parked: bool
    bbox_center_x: float
    bbox_center_y: float
    frame_idx: int
