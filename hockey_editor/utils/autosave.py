"""
Autosave and Recovery System - сохранение проекта каждые 5 минут + восстановление при краше.
"""

import os
import json
from pathlib import Path
from datetime import datetime
from PySide6.QtCore import QTimer, QObject, Signal
from typing import Optional
from ..core.project_manager import ProjectManager


class AutosaveManager(QObject):
    """Менеджер автосохранения с поддержкой восстановления."""
    
    autosave_triggered = Signal()  # Сигнал перед сохранением
    autosave_completed = Signal(bool, str)  # (success, message)
    recovery_available = Signal(str)  # path to recovery file
    
    AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000  # 5 минут
    RECOVERY_DIR = Path.home() / ".hockey_editor" / "recovery"
    RECOVERY_MANIFEST = RECOVERY_DIR / "manifest.json"
    
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.autosave_enabled = True
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self._on_autosave_tick)
        self.last_autosave_path: Optional[str] = None
        
        # Создать директорию восстановления
        self.RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
        
        # Загрузить настройки автосохранения
        from ..utils.settings_manager import get_settings_manager
        settings = get_settings_manager()
        self.autosave_interval = settings.load_autosave_interval()

    def start(self):
        """Запустить автосохранение."""
        if self.autosave_enabled:
            self.autosave_timer.start(self.AUTOSAVE_INTERVAL_MS)

    def stop(self):
        """Остановить автосохранение."""
        self.autosave_timer.stop()

    def _on_autosave_tick(self):
        """Таймер автосохранения."""
        if self.controller.processor.video_path:
            self.perform_autosave()

    def perform_autosave(self) -> bool:
        """Выполнить автосохранение."""
        try:
            self.autosave_triggered.emit()
            
            # Создать имя файла восстановления
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            recovery_path = self.RECOVERY_DIR / f"project_{timestamp}.hep"
            
            # Сохранить проект
            success = self.controller.save_project(str(recovery_path))
            
            if success:
                self.last_autosave_path = str(recovery_path)
                self._update_recovery_manifest(str(recovery_path))
                self.autosave_completed.emit(True, f"Autosaved at {datetime.now().strftime('%H:%M:%S')}")
                return True
            else:
                self.autosave_completed.emit(False, "Autosave failed")
                return False
        except Exception as e:
            self.autosave_completed.emit(False, f"Autosave error: {str(e)}")
            return False

    def _update_recovery_manifest(self, project_path: str):
        """Обновить manifest файл восстановления."""
        try:
            manifest = {"recovery_files": [], "last_modified": datetime.now().isoformat()}
            
            # Загрузить старый manifest если существует
            if self.RECOVERY_MANIFEST.exists():
                with open(self.RECOVERY_MANIFEST, 'r') as f:
                    manifest = json.load(f)
            
            # Добавить новый файл
            manifest["recovery_files"].append({
                "path": project_path,
                "timestamp": datetime.now().isoformat(),
                "size": os.path.getsize(project_path)
            })
            
            # Сохранить обновленный manifest (максимум 10 файлов)
            if len(manifest["recovery_files"]) > 10:
                old_file = manifest["recovery_files"].pop(0)
                try:
                    Path(old_file["path"]).unlink()  # Удалить старый файл
                except:
                    pass
            
            manifest["last_modified"] = datetime.now().isoformat()
            
            with open(self.RECOVERY_MANIFEST, 'w') as f:
                json.dump(manifest, f, indent=2)
        except Exception as e:
            print(f"Error updating recovery manifest: {e}")

    @staticmethod
    def check_recovery() -> Optional[str]:
        """Проверить наличие файлов восстановления."""
        manifest_path = AutosaveManager.RECOVERY_DIR / "manifest.json"
        
        if not manifest_path.exists():
            return None
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            recovery_files = manifest.get("recovery_files", [])
            if recovery_files:
                # Вернуть самый новый файл восстановления
                latest = recovery_files[-1]
                path = latest.get("path")
                if path and Path(path).exists():
                    return path
        except Exception as e:
            print(f"Error checking recovery: {e}")
        
        return None

    @staticmethod
    def clear_recovery():
        """Очистить файлы восстановления."""
        try:
            manifest_path = AutosaveManager.RECOVERY_DIR / "manifest.json"
            
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                # Удалить все файлы восстановления
                for recovery_file in manifest.get("recovery_files", []):
                    try:
                        Path(recovery_file.get("path")).unlink()
                    except:
                        pass
                
                # Удалить manifest
                manifest_path.unlink()
        except Exception as e:
            print(f"Error clearing recovery: {e}")

    @staticmethod
    def set_autosave_interval(seconds: int):
        """Установить интервал автосохранения."""
        from ..utils.settings_manager import get_settings_manager
        settings = get_settings_manager()
        settings.save_autosave_interval(seconds)
