from __future__ import annotations

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QFontMetrics
from PyQt6.QtWidgets import QWidget

from domain.entities import (
    TrackedVehicle, VehicleStatus, AlertType,
    PerspectiveCalibration, CalibrationPoint, Point2D,
)


class OverlayPainter:
    COLORS = {
        "default": QColor("#00e676"),
        "parked": QColor("#888888"),
        "overspeed": QColor("#ff1744"),
        "reference_line": QColor("#ffab00"),
        "reference_point": QColor("#ff6d00"),
        "text_bg": QColor(0, 0, 0, 180),
    }

    def __init__(self):
        self._font = QFont("Segoe UI", 11, QFont.Weight.Bold)
        self._small_font = QFont("Segoe UI", 9)

    REF_COLORS = [
        QColor("#ffab00"), QColor("#2979ff"), QColor("#00e676"),
        QColor("#d500f9"), QColor("#ff1744"),
    ]

    def paint(self, painter: QPainter, widget: QWidget, vehicles: list[TrackedVehicle],
              calibration: PerspectiveCalibration | None, scale_x: float, scale_y: float):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for vehicle in vehicles:
            self._draw_vehicle(painter, vehicle, scale_x, scale_y)

        if calibration:
            self._draw_reference_lines(painter, calibration, scale_x, scale_y)

    def _draw_vehicle(self, painter: QPainter, vehicle: TrackedVehicle,
                      scale_x: float, scale_y: float):
        bbox = vehicle.bbox
        x1 = bbox.x1 * scale_x
        y1 = bbox.y1 * scale_y
        x2 = bbox.x2 * scale_x
        y2 = bbox.y2 * scale_y

        color = self._get_color(vehicle)
        alpha = 80 if vehicle.status == VehicleStatus.PARKED else 50
        border_width = 3 if vehicle.alert == AlertType.OVERSPEED else 2

        painter.setPen(QPen(color, border_width))
        painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), alpha)))
        painter.drawRoundedRect(QRectF(x1, y1, x2 - x1, y2 - y1), 4, 4)

        if vehicle.status == VehicleStatus.PARKED:
            self._draw_parked_label(painter, x1, y1, x2, color)
        else:
            self._draw_speed_label(painter, vehicle, x1, y1, x2, color)

        self._draw_track_id(painter, vehicle.track_id, x1, y1)

    def _get_color(self, vehicle: TrackedVehicle) -> QColor:
        if vehicle.alert == AlertType.OVERSPEED:
            return self.COLORS["overspeed"]
        if vehicle.status == VehicleStatus.PARKED:
            return self.COLORS["parked"]
        return self.COLORS["default"]

    def _draw_speed_label(self, painter: QPainter, vehicle: TrackedVehicle,
                          x1: float, y1: float, x2: float, color: QColor):
        speed_text = f"{vehicle.speed.value_kmh:.1f} km/h"
        painter.setFont(self._font)
        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(speed_text) + 12
        text_h = fm.height() + 4
        label_x = x1
        label_y = y1 - text_h - 4 if y1 - text_h > 0 else y1 + 4

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.COLORS["text_bg"])
        painter.drawRoundedRect(QRectF(label_x, label_y, text_w, text_h), 3, 3)

        painter.setPen(QPen(color if vehicle.alert != AlertType.OVERSPEED else self.COLORS["overspeed"]))
        painter.drawText(QRectF(label_x + 6, label_y, text_w - 12, text_h),
                         Qt.AlignmentFlag.AlignVCenter, speed_text)

    def _draw_parked_label(self, painter: QPainter, x1: float, y1: float,
                           x2: float, color: QColor):
        text = "PARKED"
        painter.setFont(self._small_font)
        fm = QFontMetrics(self._small_font)
        text_w = fm.horizontalAdvance(text) + 10
        text_h = fm.height() + 2
        label_x = x2 - text_w - 4
        label_y = y1 - text_h - 4 if y1 - text_h > 0 else y1 + 4

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.COLORS["text_bg"])
        painter.drawRoundedRect(QRectF(label_x, label_y, text_w, text_h), 3, 3)

        painter.setPen(QPen(color))
        painter.drawText(QRectF(label_x + 5, label_y, text_w - 10, text_h),
                         Qt.AlignmentFlag.AlignVCenter, text)

    def _draw_track_id(self, painter: QPainter, track_id: int, x1: float, y1: float):
        text = f"#{track_id}"
        painter.setFont(self._small_font)
        fm = QFontMetrics(self._small_font)
        text_w = fm.horizontalAdvance(text) + 8
        text_h = fm.height() + 2

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.COLORS["text_bg"])
        painter.drawRoundedRect(QRectF(x1 + 4, y1 + 4, text_w, text_h), 3, 3)

        painter.setPen(QPen(QColor("#ffffff")))
        painter.drawText(QRectF(x1 + 8, y1 + 4, text_w - 8, text_h),
                         Qt.AlignmentFlag.AlignVCenter, text)

    def _draw_reference_lines(self, painter: QPainter, calibration: PerspectiveCalibration,
                              scale_x: float, scale_y: float):
        for idx, (p1, p2, dist_m) in enumerate(calibration.raw_lines):
            color = self.REF_COLORS[idx % len(self.REF_COLORS)]
            p1x = p1.x * scale_x
            p1y = p1.y * scale_y
            p2x = p2.x * scale_x
            p2y = p2.y * scale_y

            painter.setPen(QPen(color, 2, Qt.PenStyle.DashLine))
            painter.drawLine(int(p1x), int(p1y), int(p2x), int(p2y))

            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("#ffffff"), 2))
            r = 6
            painter.drawEllipse(int(p1x) - r, int(p1y) - r, r * 2, r * 2)
            painter.drawEllipse(int(p2x) - r, int(p2y) - r, r * 2, r * 2)

            mid_x = (p1x + p2x) / 2
            mid_y = (p1y + p2y) / 2
            text = f"L{idx + 1}: {dist_m:.1f}m"
            painter.setFont(self._small_font)
            fm = QFontMetrics(self._small_font)
            text_w = fm.horizontalAdvance(text) + 10

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.COLORS["text_bg"])
            painter.drawRoundedRect(QRectF(mid_x - text_w / 2, mid_y - 16, text_w, 22), 4, 4)

            painter.setPen(QPen(color))
            painter.drawText(QRectF(mid_x - text_w / 2, mid_y - 16, text_w, 22),
                             Qt.AlignmentFlag.AlignCenter, text)
