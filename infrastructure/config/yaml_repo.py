from __future__ import annotations

import os
import yaml
from typing import Any


DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "default.yaml")
CUSTOM_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config", "custom.yaml")


class ConfigRepository:
    def __init__(self):
        self._data: dict[str, Any] = {}

    def load_defaults(self) -> dict[str, Any]:
        path = os.path.abspath(DEFAULT_CONFIG_PATH)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self._data = yaml.safe_load(f) or {}
        return dict(self._data)

    def load_custom(self) -> dict[str, Any]:
        path = os.path.abspath(CUSTOM_CONFIG_PATH)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                custom = yaml.safe_load(f) or {}
                self._data.update(custom)
        return dict(self._data)

    def save(self, data: dict[str, Any]) -> None:
        self._data.update(data)
        path = os.path.abspath(CUSTOM_CONFIG_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, default_flow_style=False, allow_unicode=True)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    @property
    def all(self) -> dict[str, Any]:
        return dict(self._data)
