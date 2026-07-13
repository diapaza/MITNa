from __future__ import annotations

import numpy as np

from domain.entities import TrackedVehicle, VehicleStatus


class ParkingAnalyzer:
    def __init__(self, px_threshold: float = 3.0, confirm_frames: int = 30):
        self.px_threshold = px_threshold
        self.confirm_frames = confirm_frames

    def analyze(self, vehicle: TrackedVehicle) -> VehicleStatus:
        if len(vehicle.positions_buffer) < self.confirm_frames:
            return vehicle.status

        positions = list(vehicle.positions_buffer)
        recent = positions[-self.confirm_frames:]
        xs = [p.x for p in recent]
        ys = [p.y for p in recent]

        std_x = np.std(xs)
        std_y = np.std(ys)
        total_std = (std_x ** 2 + std_y ** 2) ** 0.5

        if total_std < self.px_threshold:
            vehicle.parked_confirmed_counter += 1
        else:
            vehicle.parked_confirmed_counter = max(0, vehicle.parked_confirmed_counter - 1)

        if vehicle.parked_confirmed_counter >= 10:
            return VehicleStatus.PARKED
        elif total_std > self.px_threshold * 3:
            return VehicleStatus.MOVING

        return vehicle.status
