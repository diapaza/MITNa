from __future__ import annotations

import os
import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox,
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import matplotlib
matplotlib.use("QtAgg")


class HourlyChartDialog(QDialog):
    def __init__(self, hourly_counts: dict[int, int], parent=None):
        super().__init__(parent)
        self._counts = hourly_counts
        self.setWindowTitle("Tr\u00e1fico por Hora")
        self.setMinimumSize(800, 500)
        self.setModal(True)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("Cantidad de veh\u00edculos por hora transcurrida de video")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self._figure = Figure(figsize=(9, 4.5), dpi=100)
        self._figure.patch.set_facecolor("#1a1a2e")
        self._canvas = FigureCanvasQTAgg(self._figure)
        layout.addWidget(self._canvas, 1)

        self._draw_chart()

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

    def _draw_chart(self):
        self._figure.clear()
        ax = self._figure.add_subplot(111)
        ax.set_facecolor("#16213e")

        hours = list(range(24))
        counts = [self._counts.get(h, 0) for h in hours]

        colors = []
        max_c = max(counts) if counts else 1
        for c in counts:
            intensity = c / max_c if max_c > 0 else 0
            r = int(30 + 200 * intensity)
            g = int(30 + 150 * (1 - intensity * 0.7))
            b = int(30 + 100 * (1 - intensity))
            colors.append(f"#{r:02x}{g:02x}{b:02x}")

        bars = ax.bar(hours, counts, color=colors, edgecolor="#4fc3f7", linewidth=0.5)

        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_c * 0.01,
                        str(count), ha="center", va="bottom", fontsize=8,
                        color="#e0e0e0")

        ax.set_xlabel("Hora transcurrida del video", color="#888", fontsize=11)
        ax.set_ylabel("Veh\u00edculos detectados", color="#888", fontsize=11)
        ax.set_title("Distribuci\u00f3n de tr\u00e1fico por hora", color="#e0e0e0",
                     fontsize=13, fontweight="bold", pad=12)
        ax.set_xticks(hours)
        ax.set_xticklabels([str(h) for h in hours], color="#888", fontsize=8)
        ax.tick_params(axis="y", colors="#888")
        ax.spines["bottom"].set_color("#0f3460")
        ax.spines["left"].set_color("#0f3460")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlim(-0.5, 23.5)

        total = sum(counts)
        ax.text(0.98, 0.95, f"Total: {total} veh\u00edculos",
                transform=ax.transAxes, ha="right", va="top",
                color="#4fc3f7", fontsize=11, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#0f3460",
                          edgecolor="#4fc3f7", alpha=0.8))

        self._figure.tight_layout()
        self._canvas.draw()

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar gr\u00e1fico", "trafico_por_hora.png",
            "PNG Images (*.png);;All Files (*.*)"
        )
        if path:
            try:
                self._figure.savefig(path, dpi=150, bbox_inches="tight",
                                     facecolor="#1a1a2e", edgecolor="none")
                QMessageBox.information(self, "Guardado",
                                        f"Gr\u00e1fico guardado en:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")
