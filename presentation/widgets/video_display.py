from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtWidgets import QWidget, QSizePolicy

from domain.entities import TrackedVehicle, PerspectiveCalibration
from presentation.widgets.overlay_painter import OverlayPainter


class VideoDisplay(QWidget):
    calibration_requested = pyqtSignal(object, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frame: np.ndarray | None = None
        self._vehicles: list[TrackedVehicle] = []
        self._calibration: PerspectiveCalibration | None = None
        self._painter = OverlayPainter()
        self._fps_display: float = 0.0
        self._show_fps: bool = True
        self._scale: float = 1.0
        self._calibration_mode: bool = False
        self._click_points: list = []
        self._empty_overlay = True

        self.setMinimumSize(640, 480)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

    def set_frame(self, frame: np.ndarray | None):
        self._frame = frame
        self.update()

    def update_overlay(self, vehicles: list[TrackedVehicle], calibration: PerspectiveCalibration | None,
                       fps: float, empty: bool = False):
        self._vehicles = vehicles
        self._calibration = calibration
        self._fps_display = fps
        self._empty_overlay = empty
        self.update()

    def enter_calibration_mode(self, active: bool):
        self._calibration_mode = active
        self._click_points.clear()
        self.update()

    @property
    def calibration_mode(self) -> bool:
        return self._calibration_mode

    def mousePressEvent(self, event):
        if self._calibration_mode and self._frame is not None:
            img_x = event.position().x() / self._scale
            img_y = event.position().y() / self._scale
            self._click_points.append((img_x, img_y))
            self.calibration_requested.emit(self._frame, len(self._click_points))
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if self._frame is not None:
            h, w = self._frame.shape[:2]
            vw = self.width()
            vh = self.height()
            frame_rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
            qimg = QImage(frame_rgb.data, w, h, frame_rgb.strides[0], QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qimg).scaled(vw, vh, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(0, 0, pixmap)
            self._scale = pixmap.width() / w if w > 0 else 1.0

            if not self._empty_overlay:
                self._painter.paint(painter, self, self._vehicles, self._calibration,
                                    self._scale, self._scale)

            if self._calibration_mode and self._click_points:
                self._draw_calibration_points(painter)

            self._draw_fps(painter)
        else:
            painter.fillRect(self.rect(), QColor("#1a1a2e"))
            painter.setPen(QPen(QColor("#888888")))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Arrastra un video o ve a File → Open Video")

    def _draw_calibration_points(self, painter: QPainter):
        if not self._frame:
            return

        for i, (px, py) in enumerate(self._click_points):
            dx = px * self._scale
            dy = py * self._scale
            color = QColor("#ff6d00") if i == 0 else QColor("#ffab00")
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QBrush(color))
            r = 8
            painter.drawEllipse(int(dx) - r, int(dy) - r, r * 2, r * 2)

            painter.setFont(self._painter._font)
            painter.setPen(QPen(QColor("#ffffff")))
            painter.drawText(int(dx) + 14, int(dy) + 6, f"P{i + 1}")

        if len(self._click_points) == 2:
            px1, py1 = self._click_points[0]
            px2, py2 = self._click_points[1]
            dx1, dy1 = px1 * self._scale, py1 * self._scale
            dx2, dy2 = px2 * self._scale, py2 * self._scale
            painter.setPen(QPen(QColor("#ffab00"), 2, Qt.PenStyle.DashLine))
            painter.drawLine(int(dx1), int(dy1), int(dx2), int(dy2))

    def _draw_fps(self, painter: QPainter):
        if self._show_fps and self._fps_display > 0:
            text = f"{self._fps_display:.1f} FPS"
            painter.setPen(QPen(QColor("#4fc3f7")))
            painter.setFont(self._painter._small_font)
            painter.drawText(self.width() - 120, 24, text)
