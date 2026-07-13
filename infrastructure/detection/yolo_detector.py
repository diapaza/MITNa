from __future__ import annotations

import os
from typing import Optional
import numpy as np
from ultralytics import YOLO

from domain.entities import Detection, BBox, VEHICLE_CLASSES
from application.ports import IDetector


KNOWN_MODELS: list[str] = [
    "yolov8n.pt", "yolov8s.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt",
    "yolo11n.pt", "yolo11s.pt", "yolo11m.pt", "yolo11l.pt", "yolo11x.pt",
]


class YOLODetector(IDetector):
    def __init__(self, model_path: str = "yolov8n.pt"):
        self._model: Optional[YOLO] = None
        self._model_path = model_path
        self._class_names: dict[int, str] = {}
        self._loaded = False

    @property
    def model_path(self) -> str:
        return self._model_path

    @property
    def model_loaded(self) -> bool:
        return self._loaded

    def unload(self) -> None:
        self._model = None
        self._class_names = {}
        self._loaded = False

    def load_model(self, model_path: str) -> None:
        self.unload()
        if not model_path:
            raise ValueError("La ruta del modelo no puede estar vacía")

        exists = os.path.isfile(model_path)
        is_known = model_path in KNOWN_MODELS

        if not exists:
            if is_known:
                print(f"[YOLO] Modelo '{model_path}' no encontrado localmente. "
                      f"Ultralytics lo descargará automáticamente.")
            else:
                raise FileNotFoundError(
                    f"Modelo '{model_path}' no encontrado. "
                    f"Los nombres válidos son: {', '.join(KNOWN_MODELS)}. "
                    "Para un archivo personalizado, usa 'Otro...' y selecciona el archivo .pt."
                )

        self._model = YOLO(model_path)
        self._model_path = model_path
        self._class_names = self._model.names if hasattr(self._model, 'names') else {}
        self._loaded = True

    def detect(self, frame: np.ndarray, conf_threshold: float = 0.5,
               iou_threshold: float = 0.45) -> list[Detection]:
        if not self._loaded or self._model is None:
            return []

        results = self._model(frame, conf=conf_threshold, iou=iou_threshold, verbose=False)
        detections: list[Detection] = []

        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            for i in range(len(boxes)):
                xyxy = boxes.xyxy[i].cpu().numpy()
                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = self._class_names.get(cls_id, "unknown")

                if cls_name not in VEHICLE_CLASSES:
                    continue

                bbox = BBox(
                    x1=float(xyxy[0]),
                    y1=float(xyxy[1]),
                    x2=float(xyxy[2]),
                    y2=float(xyxy[3]),
                )
                detections.append(Detection(
                    bbox=bbox,
                    confidence=conf,
                    class_id=cls_id,
                    class_name=cls_name,
                ))

        return detections

    def get_model_info(self) -> dict:
        return {
            "model_path": self._model_path,
            "loaded": self._loaded,
            "classes": len(self._class_names),
        }
