from __future__ import annotations

import cv2
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QScrollArea,
)


class HeatmapDialog(QDialog):
    def __init__(self, heatmap_image: np.ndarray, parent=None):
        super().__init__(parent)
        self._image = heatmap_image
        self.setWindowTitle("Mapa de Calor - Tr\u00e1fico")
        self.setMinimumSize(800, 650)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Zonas de mayor concentraci\u00f3n de veh\u00edculos")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background-color: #1a1a2e; border: none;")

        h, w = self._image.shape[:2]
        max_display = 900
        if w > max_display:
            scale = max_display / w
            new_w = max_display
            new_h = int(h * scale)
            display_img = cv2.resize(self._image, (new_w, new_h))
        else:
            display_img = self._image

        frame_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        qimg = QImage(frame_rgb.data, frame_rgb.shape[1], frame_rgb.shape[0],
                       frame_rgb.strides[0], QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        self._image_label = QLabel()
        self._image_label.setPixmap(pixmap)
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self._image_label)
        layout.addWidget(scroll, 1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        save_btn = QPushButton("Guardar como PNG...")
        save_btn.setObjectName("successButton")
        save_btn.clicked.connect(self._on_save)

        close_btn = QPushButton("Cerrar")
        close_btn.clicked.connect(self.accept)

        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar mapa de calor", "heatmap.png",
            "PNG Images (*.png);;All Files (*.*)"
        )
        if path:
            try:
                cv2.imwrite(path, self._image)
                QMessageBox.information(self, "Guardado",
                                        f"Mapa de calor guardado en:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")
