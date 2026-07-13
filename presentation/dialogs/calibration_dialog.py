from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QBrush, QFont
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDoubleSpinBox, QWidget, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox,
)

from domain.entities import Point2D


class CalibrationDialog(QDialog):
    calibration_complete = pyqtSignal(list)

    def __init__(self, frame: np.ndarray, parent=None):
        super().__init__(parent)
        self._frame = frame.copy()
        self._click_points: list[Point2D] = []
        self._saved_lines: list[tuple[Point2D, Point2D, float]] = []
        self.setWindowTitle("Calibraci\u00f3n - L\u00edneas de Referencia")
        self.setModal(True)
        self.setMinimumSize(1000, 700)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        instructions = QLabel(
            "1. Haz clic en 2 puntos sobre la imagen para crear una l\u00ednea de referencia.\n"
            "2. Ingresa la distancia real en metros y presiona 'Agregar l\u00ednea'.\n"
            "3. Repite para m\u00e1s l\u00edneas a diferentes profundidades (opcional).\n"
            "4. Presiona 'Finalizar calibraci\u00f3n' cuando hayas terminado."
        )
        instructions.setStyleSheet("color: #ffab00; font-size: 12px; padding: 6px;")
        layout.addWidget(instructions)

        mid_layout = QHBoxLayout()
        mid_layout.setSpacing(8)

        self._image_widget = CalibrationImageWidget(self._frame, self)
        self._image_widget.point_clicked.connect(self._on_point_clicked)
        mid_layout.addWidget(self._image_widget, 3)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        # Current line group
        current_group = QGroupBox("L\u00ednea actual")
        current_form = QVBoxLayout(current_group)
        current_form.setSpacing(6)

        self._p1_label = QLabel("Punto 1: --")
        self._p1_label.setStyleSheet("font-size: 12px;")
        self._p2_label = QLabel("Punto 2: --")
        self._p2_label.setStyleSheet("font-size: 12px;")
        self._distance_label = QLabel("Distancia px: --")
        self._distance_label.setStyleSheet("font-size: 12px;")

        dist_row = QHBoxLayout()
        dist_row.setSpacing(6)
        dist_label = QLabel("Distancia real:")
        dist_label.setStyleSheet("font-size: 12px;")
        self._distance_input = QDoubleSpinBox()
        self._distance_input.setRange(0.1, 1000.0)
        self._distance_input.setValue(3.5)
        self._distance_input.setSuffix(" m")
        self._distance_input.setDecimals(2)
        self._distance_input.setSingleStep(0.5)
        dist_row.addWidget(dist_label)
        dist_row.addWidget(self._distance_input)

        self._add_btn = QPushButton("+ Agregar l\u00ednea")
        self._add_btn.setObjectName("successButton")
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add_line)

        self._clear_btn = QPushButton("Limpiar puntos")
        self._clear_btn.clicked.connect(self._on_clear_current)

        current_form.addWidget(self._p1_label)
        current_form.addWidget(self._p2_label)
        current_form.addWidget(self._distance_label)
        current_form.addLayout(dist_row)
        current_form.addWidget(self._add_btn)
        current_form.addWidget(self._clear_btn)
        right_panel.addWidget(current_group)

        # Saved lines table
        saved_group = QGroupBox("L\u00edneas guardadas")
        saved_layout = QVBoxLayout(saved_group)
        saved_layout.setSpacing(4)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["#", "Y (px)", "Dist px", "px/m"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setMaximumHeight(150)

        self._remove_last_btn = QPushButton("Eliminar \u00faltima")
        self._remove_last_btn.setEnabled(False)
        self._remove_last_btn.clicked.connect(self._on_remove_last)

        saved_layout.addWidget(self._table)
        saved_layout.addWidget(self._remove_last_btn)
        right_panel.addWidget(saved_group)

        # Finish / Cancel
        right_panel.addStretch()
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self._finish_btn = QPushButton("Finalizar calibraci\u00f3n")
        self._finish_btn.setObjectName("successButton")
        self._finish_btn.setEnabled(False)
        self._finish_btn.clicked.connect(self._on_finish)
        self._cancel_btn = QPushButton("Cancelar")
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._finish_btn)
        btn_row.addWidget(self._cancel_btn)
        right_panel.addLayout(btn_row)

        mid_layout.addLayout(right_panel, 1)
        layout.addLayout(mid_layout, 1)

    def _on_point_clicked(self, point: Point2D):
        self._click_points.append(point)
        self._image_widget.set_current_points(self._click_points)

        if len(self._click_points) == 1:
            self._p1_label.setText(f"Punto 1: ({point.x:.1f}, {point.y:.1f})")
        elif len(self._click_points) == 2:
            p1, p2 = self._click_points
            self._p1_label.setText(f"P1: ({p1.x:.1f}, {p1.y:.1f})")
            self._p2_label.setText(f"P2: ({p2.x:.1f}, {p2.y:.1f})")
            dist_px = p1.distance_to(p2)
            self._distance_label.setText(f"Distancia px: {dist_px:.1f}")
            self._add_btn.setEnabled(True)
            self._image_widget.set_preview_distance(dist_px)

    def _on_add_line(self):
        if len(self._click_points) < 2:
            return
        p1, p2 = self._click_points
        dist_m = self._distance_input.value()
        self._saved_lines.append((p1, p2, dist_m))
        self._update_table()
        self._on_clear_current()
        self._finish_btn.setEnabled(True)
        self._remove_last_btn.setEnabled(True)
        self._image_widget.set_saved_lines(self._saved_lines)

    def _on_clear_current(self):
        self._click_points.clear()
        self._image_widget.set_current_points([])
        self._image_widget.set_preview_distance(0)
        self._p1_label.setText("Punto 1: --")
        self._p2_label.setText("Punto 2: --")
        self._distance_label.setText("Distancia px: --")
        self._add_btn.setEnabled(False)

    def _on_remove_last(self):
        if self._saved_lines:
            self._saved_lines.pop()
            self._update_table()
            self._image_widget.set_saved_lines(self._saved_lines)
            self._remove_last_btn.setEnabled(len(self._saved_lines) > 0)
            self._finish_btn.setEnabled(len(self._saved_lines) > 0)

    def _update_table(self):
        self._table.setRowCount(len(self._saved_lines))
        for i, (p1, p2, dist_m) in enumerate(self._saved_lines):
            mid_y = (p1.y + p2.y) / 2.0
            px_dist = p1.distance_to(p2)
            scale = px_dist / dist_m
            self._table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self._table.setItem(i, 1, QTableWidgetItem(f"{mid_y:.0f}"))
            self._table.setItem(i, 2, QTableWidgetItem(f"{px_dist:.1f}"))
            self._table.setItem(i, 3, QTableWidgetItem(f"{scale:.1f}"))
        self._table.resizeColumnsToContents()

    def _on_finish(self):
        if not self._saved_lines:
            QMessageBox.warning(self, "Atenci\u00f3n",
                                "Debes agregar al menos una l\u00ednea de referencia.")
            return
        self.calibration_complete.emit(self._saved_lines)
        self.accept()


class CalibrationImageWidget(QWidget):
    point_clicked = pyqtSignal(Point2D)

    COLORS = [
        QColor("#ff6d00"), QColor("#2979ff"), QColor("#00e676"),
        QColor("#d500f9"), QColor("#ff1744"),
    ]

    def __init__(self, frame: np.ndarray, parent=None):
        super().__init__(parent)
        self._frame = frame
        self._saved_lines: list[tuple[Point2D, Point2D, float]] = []
        self._current_points: list[Point2D] = []
        self._preview_dist: float = 0
        self._scale = 1.0
        self.setMinimumSize(540, 480)
        self.setMouseTracking(True)

    def set_current_points(self, points: list[Point2D]):
        self._current_points = points
        self.update()

    def set_saved_lines(self, lines: list[tuple[Point2D, Point2D, float]]):
        self._saved_lines = lines
        self.update()

    def set_preview_distance(self, dist_px: float):
        self._preview_dist = dist_px
        self.update()

    def mousePressEvent(self, event):
        if len(self._current_points) >= 2:
            return
        img_x = event.position().x() / self._scale
        img_y = event.position().y() / self._scale
        self.point_clicked.emit(Point2D(img_x, img_y))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        h, w = self._frame.shape[:2]
        vw = self.width()
        vh = self.height()

        frame_rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        qimg = QImage(frame_rgb.data, w, h, frame_rgb.strides[0],
                       QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg).scaled(
            vw, vh, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation)
        painter.drawPixmap(0, 0, pixmap)
        self._scale = pixmap.width() / w if w > 0 else 1.0

        # Draw saved lines (permanently)
        for idx, (p1, p2, dist_m) in enumerate(self._saved_lines):
            color = self.COLORS[idx % len(self.COLORS)]
            self._draw_line(painter, p1, p2, dist_m, color, idx, alpha=180)

        # Draw current working points
        pts = self._current_points
        for i, pt in enumerate(pts):
            dx = pt.x * self._scale
            dy = pt.y * self._scale
            color = QColor("#ffffff")
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(QColor("#ff6d00")))
            r = 8
            painter.drawEllipse(int(dx) - r, int(dy) - r, r * 2, r * 2)
            painter.setPen(QPen(QColor("#ffffff")))
            font = painter.font()
            font.setPointSize(11)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(int(dx) + 14, int(dy) + 6, f"P{i + 1}")

        if len(pts) == 2:
            p1, p2 = pts
            dx1, dy1 = p1.x * self._scale, p1.y * self._scale
            dx2, dy2 = p2.x * self._scale, p2.y * self._scale
            painter.setPen(QPen(QColor("#ffab00"), 2, Qt.PenStyle.DashLine))
            painter.drawLine(int(dx1), int(dy1), int(dx2), int(dy2))

            if self._preview_dist > 0:
                mid_x = (dx1 + dx2) / 2
                mid_y = (dy1 + dy2) / 2
                text = f"{self._preview_dist:.0f} px"
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(0, 0, 0, 180))
                fm = painter.fontMetrics()
                tw = fm.horizontalAdvance(text) + 10
                painter.drawRoundedRect(int(mid_x - tw / 2),
                                        int(mid_y - 18), int(tw), 24, 4, 4)
                painter.setPen(QPen(QColor("#ffab00")))
                painter.drawText(int(mid_x - tw / 2), int(mid_y - 18),
                                 int(tw), 24, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_line(self, painter, p1, p2, dist_m, color, idx, alpha=255):
        dx1, dy1 = p1.x * self._scale, p1.y * self._scale
        dx2, dy2 = p2.x * self._scale, p2.y * self._scale

        c = QColor(color)
        c.setAlpha(alpha)
        painter.setPen(QPen(c, 2, Qt.PenStyle.DashLine))
        painter.drawLine(int(dx1), int(dy1), int(dx2), int(dy2))

        # Draw endpoints
        for (dx, dy) in [(dx1, dy1), (dx2, dy2)]:
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.setBrush(QBrush(c))
            r = 6
            painter.drawEllipse(int(dx) - r, int(dy) - r, r * 2, r * 2)

        # Draw label
        mid_x = (dx1 + dx2) / 2
        mid_y = (dy1 + dy2) / 2
        text = f"L{idx + 1}: {dist_m:.1f}m"
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 180))
        fm = painter.fontMetrics()
        tw = fm.horizontalAdvance(text) + 10
        painter.drawRoundedRect(int(mid_x - tw / 2), int(mid_y - 20),
                                int(tw), 26, 4, 4)
        painter.setPen(QPen(QColor("#ffffff")))
        font = painter.font()
        font.setPointSize(10)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(int(mid_x - tw / 2), int(mid_y - 20),
                         int(tw), 26, Qt.AlignmentFlag.AlignCenter, text)
