# src/services/autosave/autosave_service.py
"""
Auto-save service — периодическое автосохранение проекта.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List

from PySide6.QtCore import QObject, QTimer, Signal


class AutoSaveService(QObject):
    """
    Автосохранение проекта по таймеру.

    - Настраиваемый интервал (по умолчанию 5 минут)
    - Хранит N последних авто-копий (ротация)
    - Не сохраняет, если проект не менялся (dirty flag)
    - Уведомление через сигналы
    """

    auto_saved = Signal(str)         # путь к сохранённому файлу
    auto_save_failed = Signal(str)   # описание ошибки

    DEFAULT_INTERVAL_MS = 5 * 60 * 1000   # 5 минут
    DEFAULT_MAX_BACKUPS = 5
    AUTOSAVE_DIR = ".autosave"

    def __init__(
        self,
        save_callback: Optional[Callable[[], bool]] = None,
        project_dir: Optional[str] = None,
        interval_ms: int = DEFAULT_INTERVAL_MS,
        max_backups: int = DEFAULT_MAX_BACKUPS,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self._save_callback = save_callback
        self._project_dir = project_dir or "."
        self._interval_ms = interval_ms
        self._max_backups = max_backups
        self._enabled = True
        self._dirty = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timer)

    # ─── Properties ──────────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value
        if not value:
            self.stop()

    @property
    def interval_ms(self) -> int:
        return self._interval_ms

    @interval_ms.setter
    def interval_ms(self, value: int) -> None:
        self._interval_ms = max(30_000, value)  # минимум 30 сек
        if self._timer.isActive():
            self._timer.setInterval(self._interval_ms)

    @property
    def project_dir(self) -> str:
        return self._project_dir

    @project_dir.setter
    def project_dir(self, value: str) -> None:
        self._project_dir = value

    # ─── Public API ──────────────────────────────────────────────────────

    def set_save_callback(self, callback: Callable[[], bool]) -> None:
        self._save_callback = callback

    def mark_dirty(self) -> None:
        """Пометить проект как изменённый."""
        self._dirty = True

    def mark_clean(self) -> None:
        """Пометить проект как сохранённый."""
        self._dirty = False

    def start(self) -> None:
        if not self._enabled:
            return
        self._timer.start(self._interval_ms)

    def stop(self) -> None:
        self._timer.stop()

    def save_now(self) -> bool:
        """Немедленное авто-сохранение."""
        return self._do_autosave()

    def get_autosave_files(self) -> List[Path]:
        """Список файлов авто-сохранения, от новых к старым."""
        autosave_dir = Path(self._project_dir) / self.AUTOSAVE_DIR
        if not autosave_dir.exists():
            return []
        return sorted(autosave_dir.glob("autosave_*.json"), reverse=True)

    def restore_latest(self) -> Optional[Path]:
        """Путь к самому свежему авто-сохранению, или None."""
        files = self.get_autosave_files()
        return files[0] if files else None

    def cleanup(self) -> None:
        """Удалить все файлы авто-сохранения."""
        autosave_dir = Path(self._project_dir) / self.AUTOSAVE_DIR
        if autosave_dir.exists():
            shutil.rmtree(autosave_dir, ignore_errors=True)

    # ─── Internals ───────────────────────────────────────────────────────

    def _on_timer(self) -> None:
        if not self._dirty:
            return
        self._do_autosave()

    def _do_autosave(self) -> bool:
        """Выполнить автосохранение."""
        if not self._save_callback:
            return False

        try:
            success = self._save_callback()
            if not success:
                # Callback вернул False — тихий пропуск.
                # Это НЕ ошибка: например, проект ещё не имеет file_path.
                # НЕ эмитим auto_save_failed, просто пропускаем.
                return False

            self._dirty = False
            self.auto_saved.emit("")
            return True

        except Exception as e:
            # Только реальные исключения показываем как ошибку
            self.auto_save_failed.emit(str(e))
            return False

    def _rotate_backups(self, autosave_dir: Path) -> None:
        files = sorted(autosave_dir.glob("autosave_*.json"), reverse=True)
        while len(files) > self._max_backups:
            old_file = files.pop()
            try:
                old_file.unlink()
            except OSError:
                pass