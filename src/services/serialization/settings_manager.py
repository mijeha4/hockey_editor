"""
Settings Manager - loads/saves app settings to JSON.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Any

from models.config.app_settings import AppSettings

_settings_manager: Optional["SettingsManager"] = None


def get_settings_manager() -> "SettingsManager":
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


class SettingsManager:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path

    def _load_raw(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except Exception as e:
            print(f"Error loading settings: {e}")
            return {}

    def _save_raw(self, data: Dict[str, Any]) -> bool:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def load_settings(self) -> Optional[AppSettings]:
        raw = self._load_raw()
        if not raw:
            return None
        try:
            return AppSettings.from_dict(raw)
        except Exception as e:
            print(f"Error parsing settings: {e}")
            return None

    def save_settings(self, settings: AppSettings) -> bool:
        try:
            return self._save_raw(settings.to_dict())
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def export_settings(self, settings: AppSettings, file_path: str) -> bool:
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False

    def import_settings(self, file_path: str) -> Optional[AppSettings]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            return AppSettings.from_dict(data)
        except Exception as e:
            print(f"Error importing settings: {e}")
            return None

    # ─── Custom events persistence ─────────────────────────────────────────

    def load_custom_events(self) -> List[Dict]:
        raw = self._load_raw()
        events = raw.get("custom_events", [])
        return events if isinstance(events, list) else []

    def save_custom_events(self, events_data: List[Dict]) -> None:
        raw = self._load_raw()
        raw["custom_events"] = events_data
        self._save_raw(raw)