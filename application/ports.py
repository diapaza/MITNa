from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from domain.entities import Detection, TrackedVehicle


class IVideoSource(ABC):
    @abstractmethod
    def open(self, path: str) -> None: ...

    @abstractmethod
    def read(self) -> tuple[bool, object, int, float]: ...

    @abstractmethod
    def release(self) -> None: ...

    @abstractmethod
    def get_fps(self) -> float: ...

    @abstractmethod
    def get_total_frames(self) -> int: ...

    @abstractmethod
    def get_frame_count(self) -> int: ...

    @abstractmethod
    def set_frame(self, frame_idx: int) -> bool: ...

    @abstractmethod
    def is_opened(self) -> bool: ...

    @property
    @abstractmethod
    def source_path(self) -> Optional[str]: ...


class IDetector(ABC):
    @abstractmethod
    def load_model(self, model_path: str) -> None: ...

    @abstractmethod
    def detect(self, frame: object, conf_threshold: float, iou_threshold: float) -> list[Detection]: ...

    @abstractmethod
    def get_model_info(self) -> dict: ...


class ITracker(ABC):
    @abstractmethod
    def update(self, detections: list[Detection], frame: object, frame_idx: int) -> list[TrackedVehicle]: ...

    @abstractmethod
    def reset(self) -> None: ...

    @abstractmethod
    def get_active_tracks(self) -> list[TrackedVehicle]: ...
