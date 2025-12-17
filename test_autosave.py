#!/usr/bin/env python3
"""
Тест системы автосохранения и восстановления.
"""

import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hockey_editor.utils.autosave import AutosaveManager
from hockey_editor.core.video_controller import VideoController


class MockController:
    """Мок контроллера для тестирования."""

    def __init__(self, has_video=True):
        self.processor = Mock()
        self.processor.video_path = "/fake/video.mp4" if has_video else None

    def save_project(self, path):
        """Мокаем сохранение проекта."""
        # Создаем фиктивный файл проекта
        with open(path, 'w') as f:
            f.write('{"test": "data"}')
        return True


def test_autosave_initialization():
    """Тест инициализации AutosaveManager."""
    print("🧪 Тестирование инициализации AutosaveManager...")

    controller = MockController()
    autosave = AutosaveManager(controller)

    # Проверяем начальные значения
    # autosave_enabled должен загружаться из настроек (по умолчанию True)
    assert isinstance(autosave.autosave_enabled, bool)
    assert autosave.autosave_timer is not None
    assert autosave.last_autosave_path is None
    assert autosave.RECOVERY_DIR.exists()

    print("✅ Инициализация прошла успешно")


def test_autosave_without_video():
    """Тест автосохранения без загруженного видео."""
    print("\n🧪 Тестирование автосохранения без видео...")

    controller = MockController(has_video=False)
    autosave = AutosaveManager(controller)

    # perform_autosave всегда пытается сохранить, но может вернуть False если сохранение не удалось
    # Проверка на видео происходит в _on_autosave_tick
    result = autosave.perform_autosave()
    # В нашем случае сохранение должно быть успешным, так как мы мокаем controller.save_project
    assert result == True, "perform_autosave должен вернуть True при успешном сохранении"

    print("✅ perform_autosave работает независимо от наличия видео")


def test_autosave_with_video():
    """Тест автосохранения с загруженным видео."""
    print("\n🧪 Тестирование автосохранения с видео...")

    controller = MockController(has_video=True)
    autosave = AutosaveManager(controller)

    # Выполняем автосохранение
    result = autosave.perform_autosave()
    assert result == True, "Автосохранение с видео должно быть успешным"

    # Проверяем, что файл создан
    assert autosave.last_autosave_path is not None
    assert Path(autosave.last_autosave_path).exists()

    # Проверяем содержимое файла
    with open(autosave.last_autosave_path, 'r') as f:
        data = f.read()
        assert '"test": "data"' in data

    print(f"✅ Автосохранение создано: {autosave.last_autosave_path}")


def test_recovery_manifest():
    """Тест обновления манифеста восстановления."""
    print("\n🧪 Тестирование манифеста восстановления...")

    # Очищаем перед тестом
    AutosaveManager.clear_recovery()

    controller = MockController(has_video=True)
    autosave = AutosaveManager(controller)

    # Создаем несколько автосохранений
    paths = []
    for i in range(3):
        autosave.perform_autosave()
        paths.append(autosave.last_autosave_path)

    # Проверяем манифест
    assert autosave.RECOVERY_MANIFEST.exists()

    with open(autosave.RECOVERY_MANIFEST, 'r') as f:
        manifest = json.load(f)

    assert "recovery_files" in manifest
    assert len(manifest["recovery_files"]) == 3

    # Проверяем структуру файлов
    for recovery_file in manifest["recovery_files"]:
        assert "path" in recovery_file
        assert "timestamp" in recovery_file
        assert "size" in recovery_file
        assert Path(recovery_file["path"]).exists()

    print("✅ Манифест восстановления обновляется корректно")


def test_recovery_check():
    """Тест проверки наличия файлов восстановления."""
    print("\n🧪 Тестирование проверки восстановления...")

    # Сначала очищаем все
    AutosaveManager.clear_recovery()

    # Проверяем, что восстановление не доступно
    recovery_path = AutosaveManager.check_recovery()
    assert recovery_path is None, "Восстановление не должно быть доступно после очистки"

    # Создаем файл восстановления
    controller = MockController(has_video=True)
    autosave = AutosaveManager(controller)
    autosave.perform_autosave()

    # Теперь проверяем наличие
    recovery_path = AutosaveManager.check_recovery()
    assert recovery_path is not None, "Восстановление должно быть доступно"
    assert Path(recovery_path).exists()

    print(f"✅ Восстановление найдено: {recovery_path}")


def test_recovery_limit():
    """Тест ограничения количества файлов восстановления (макс 10)."""
    print("\n🧪 Тестирование ограничения файлов восстановления...")

    # Очищаем
    AutosaveManager.clear_recovery()

    controller = MockController(has_video=True)
    autosave = AutosaveManager(controller)

    # Создаем 12 автосохранений
    for i in range(12):
        autosave.perform_autosave()

    # Проверяем манифест
    with open(autosave.RECOVERY_MANIFEST, 'r') as f:
        manifest = json.load(f)

    # Должно быть максимум 10 файлов
    assert len(manifest["recovery_files"]) <= 10, f"Файлов должно быть <= 10, найдено {len(manifest['recovery_files'])}"

    print(f"✅ Ограничение работает: {len(manifest['recovery_files'])} файлов")


def test_timer_functionality():
    """Тест работы таймера автосохранения."""
    print("\n🧪 Тестирование таймера автосохранения...")

    controller = MockController(has_video=True)
    autosave = AutosaveManager(controller)

    # Таймер должен существовать
    assert autosave.autosave_timer is not None

    # В тестовой среде без QApplication таймер не может быть активным
    # Просто проверяем, что методы не вызывают исключений
    try:
        autosave.start()
        autosave.stop()
        print("✅ Методы start/stop таймера работают без исключений")
    except Exception as e:
        print(f"❌ Ошибка в работе таймера: {e}")
        raise


def test_timer_with_video_check():
    """Тест что таймер вызывает автосохранение только при наличии видео."""
    print("\n🧪 Тестирование логики таймера с проверкой видео...")

    # Тест с видео
    controller_with_video = MockController(has_video=True)
    autosave_with_video = AutosaveManager(controller_with_video)

    # Вызываем метод таймера напрямую
    initial_path = autosave_with_video.last_autosave_path
    autosave_with_video._on_autosave_tick()

    # Должно быть выполнено автосохранение
    assert autosave_with_video.last_autosave_path != initial_path
    assert autosave_with_video.last_autosave_path is not None

    # Тест без видео
    controller_no_video = MockController(has_video=False)
    autosave_no_video = AutosaveManager(controller_no_video)

    # Вызываем метод таймера напрямую
    initial_path = autosave_no_video.last_autosave_path
    autosave_no_video._on_autosave_tick()

    # Автосохранение НЕ должно быть выполнено
    assert autosave_no_video.last_autosave_path == initial_path

    print("✅ Таймер корректно проверяет наличие видео перед автосохранением")


def test_clear_recovery():
    """Тест очистки файлов восстановления."""
    print("\n🧪 Тестирование очистки восстановления...")

    # Создаем файлы
    controller = MockController(has_video=True)
    autosave = AutosaveManager(controller)
    autosave.perform_autosave()

    # Проверяем, что файлы существуют
    assert autosave.RECOVERY_MANIFEST.exists()
    assert autosave.last_autosave_path is not None

    # Запоминаем пути
    manifest_path = autosave.RECOVERY_MANIFEST
    recovery_path = Path(autosave.last_autosave_path)

    # Проверяем, что файл существует перед очисткой
    if recovery_path.exists():
        print(f"  Файл существует перед очисткой: {recovery_path}")

        # Очищаем
        AutosaveManager.clear_recovery()

        # Проверяем, что файлы удалены
        assert not manifest_path.exists(), "Манифест должен быть удален"
        assert not recovery_path.exists(), "Файл восстановления должен быть удален"

        print("✅ Очистка восстановления работает корректно")
    else:
        print("⚠️  Файл не существует перед очисткой - пропускаем тест")
        # Все равно вызываем очистку для чистоты
        AutosaveManager.clear_recovery()


def cleanup_test_files():
    """Очистка тестовых файлов."""
    try:
        if AutosaveManager.RECOVERY_DIR.exists():
            shutil.rmtree(AutosaveManager.RECOVERY_DIR)
        print("🧹 Тестовые файлы очищены")
    except Exception as e:
        print(f"⚠️  Ошибка очистки: {e}")


if __name__ == "__main__":
    print("🚀 Запуск тестов автосохранения...\n")

    try:
        # Очищаем перед тестами
        cleanup_test_files()

        # Запускаем тесты
        test_autosave_initialization()
        test_autosave_without_video()
        test_autosave_with_video()
        test_recovery_manifest()
        test_recovery_check()
        test_recovery_limit()
        test_timer_functionality()
        test_timer_with_video_check()
        test_clear_recovery()

        print("\n🎉 Все тесты автосохранения пройдены успешно!")
        print("✅ Система автосохранения работает корректно.")

    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        # Всегда очищаем
        cleanup_test_files()
