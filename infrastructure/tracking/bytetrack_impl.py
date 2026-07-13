from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment
from collections import defaultdict
from typing import Optional

from domain.entities import Detection, TrackedVehicle, BBox, VehicleStatus
from application.ports import ITracker


class ByteTrack(ITracker):
    def __init__(self, track_max_lost: int = 15, track_high_conf: float = 0.5,
                 match_threshold: float = 0.5):
        self._track_max_lost = track_max_lost
        self._track_high_conf = track_high_conf
        self._match_threshold = match_threshold
        self._next_id: int = 1
        self._tracks: dict[int, TrackedVehicle] = {}
        self._recent_matches: list = []

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1
        self._recent_matches = []

    def update(self, detections: list[Detection], frame: object, frame_idx: int) -> list[TrackedVehicle]:
        high_dets = [d for d in detections if d.confidence >= self._track_high_conf]
        low_dets = [d for d in detections if d.confidence < self._track_high_conf]

        # First association: high-confidence detections with existing tracks
        tracked_indices = list(self._tracks.keys())
        if tracked_indices and high_dets:
            self._associate(tracked_indices, high_dets, frame_idx)

        # Second association: remaining tracks with low-confidence detections
        remaining_tracks = [tid for tid in self._tracks
                            if self._tracks[tid].is_active
                            and self._tracks[tid].frames_since_last_seen > 0]
        unmatched_low = []
        if remaining_tracks and low_dets:
            unmatched_low = self._second_associate(remaining_tracks, low_dets, frame_idx)

        # Remove tracks lost for too long
        self._cleanup_tracks(frame_idx)

        # Create new tracks from unmatched high detections
        matched_high = set()
        for tid, det in self._recent_matches:
            matched_high.add(id(det))
        for det in high_dets:
            if id(det) not in matched_high:
                self._create_track(det, frame_idx)

        # Try unmatched low detections
        for det in unmatched_low:
            if id(det) not in matched_high:
                self._create_track(det, frame_idx)

        return list(self._tracks.values())

    def _associate(self, track_ids: list[int], detections: list[Detection],
                   frame_idx: int) -> None:
        if not track_ids or not detections:
            self._recent_matches = []
            return

        iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)
        for ti, tid in enumerate(track_ids):
            track = self._tracks[tid]
            for di, det in enumerate(detections):
                iou_matrix[ti, di] = track.bbox.iou(det.bbox)

        track_indices, det_indices = linear_sum_assignment(-iou_matrix)
        self._recent_matches = []

        for ti, di in zip(track_indices, det_indices):
            iou = iou_matrix[ti, di]
            if iou >= self._match_threshold:
                tid = track_ids[ti]
                det = detections[di]
                self._tracks[tid].update_position(det.bbox, frame_idx)
                self._tracks[tid].confidence = det.confidence
                self._tracks[tid].class_name = det.class_name
                self._recent_matches.append((tid, det))

    def _second_associate(self, track_ids: list[int], detections: list[Detection],
                          frame_idx: int) -> list[Detection]:
        if not track_ids or not detections:
            return detections

        iou_matrix = np.zeros((len(track_ids), len(detections)), dtype=np.float32)
        for ti, tid in enumerate(track_ids):
            track = self._tracks[tid]
            for di, det in enumerate(detections):
                iou_matrix[ti, di] = track.bbox.iou(det.bbox)

        track_indices, det_indices = linear_sum_assignment(-iou_matrix)
        unmatched_dets = list(range(len(detections)))

        for ti, di in zip(track_indices, det_indices):
            iou = iou_matrix[ti, di]
            if iou >= 0.5:
                tid = track_ids[ti]
                det = detections[di]
                self._tracks[tid].update_position(det.bbox, frame_idx)
                self._tracks[tid].confidence = det.confidence
                if di in unmatched_dets:
                    unmatched_dets.remove(di)

        return [detections[i] for i in unmatched_dets]

    def _create_track(self, detection: Detection, frame_idx: int) -> TrackedVehicle:
        vehicle = TrackedVehicle(
            track_id=self._next_id,
            bbox=detection.bbox,
            class_name=detection.class_name,
            confidence=detection.confidence,
            status=VehicleStatus.ENTERING,
            last_seen_frame=frame_idx,
        )
        self._tracks[self._next_id] = vehicle
        self._next_id += 1
        return vehicle

    def _cleanup_tracks(self, frame_idx: int) -> None:
        to_remove = []
        for tid, track in self._tracks.items():
            if track.is_active:
                if track.last_seen_frame < frame_idx:
                    track.mark_missing()
                if not track.is_active:
                    to_remove.append(tid)

        for tid in to_remove:
            del self._tracks[tid]

    def get_active_tracks(self) -> list[TrackedVehicle]:
        return [v for v in self._tracks.values() if v.is_active]
