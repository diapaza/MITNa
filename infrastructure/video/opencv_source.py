from __future__ import annotations

import cv2
import numpy as np
from typing import Optional

from application.ports import IVideoSource


class OpenCVVideoSource(IVideoSource):
    def __init__(self):
        self._cap: Optional[cv2.VideoCapture] = None
        self._fps: float = 30.0
        self._total_frames: int = 0
        self._frame_count: int = 0
        self._path: Optional[str] = None

    def open(self, path: str) -> None:
        self.release()
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise RuntimeError(f"No se pudo abrir el video: {path}")
        self._fps = self._cap.get(cv2.CAP_PROP_FPS)
        self._total_frames = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self._frame_count = 0
        self._path = path

    def read(self) -> tuple[bool, Optional[np.ndarray], int, float]:
        if self._cap is None:
            return False, None, 0, 0.0
        ret, frame = self._cap.read()
        if ret:
            self._frame_count += 1
            timestamp = self._frame_count / self._fps
            return True, frame, self._frame_count, timestamp
        return False, None, self._frame_count, self._frame_count / self._fps

    def release(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._frame_count = 0
        self._path = None

    def get_fps(self) -> float:
        return self._fps

    def get_total_frames(self) -> int:
        return self._total_frames

    def get_frame_count(self) -> int:
        return self._frame_count

    def set_frame(self, frame_idx: int) -> bool:
        if self._cap is None:
            return False
        idx = max(0, min(frame_idx, self._total_frames - 1))
        ok = self._cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        if ok:
            self._frame_count = idx
        return ok

    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def source_path(self) -> Optional[str]:
        return self._path

    def read_specific_frame(self, frame_idx: int) -> Optional[np.ndarray]:
        if self._cap is None:
            return None
        old_pos = self._cap.get(cv2.CAP_PROP_POS_FRAMES)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self._cap.read()
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, old_pos)
        return frame if ret else None
