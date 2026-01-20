!/usr/bin/env python3
"""
Комплексный тест сохранения и загрузки проектов в формате .hep
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Добавляем src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from services.serialization.project_io import ProjectIO
from models.domain.project import Project
from models.domain.marker import Marker


def test_project_save_load_basic():
    """Тест базового сохранения и загрузки проекта."""
    print("🧪 Тестирование базового сохранения/загрузки проекта...")

    # Создаем тестовый проект
    project = Project(
        name="Test Project",
        video_path="/fake/video.mp4",
        fps=29.97
    )

    # Добавляем маркеры
    project.markers.append(Marker(
        start_frame=0,
        end_frame=30,
        event_name="Attack",
        note="First attack"
    ))
    project.markers.append(Marker(
        start_frame=60,
        end_frame=90,
        event_name="Defense",
        note="Strong defense"
    ))

    # Сохраняем проект
    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "test_project.hep"

        success = ProjectIO.save_project(project, str(project_path))
        assert success, "Сохранение проекта должно быть успешным"
        assert project_path.exists(), "Файл проекта должен существовать"

        # Проверяем, что это ZIP файл
        import zipfile
        assert zipfile.is_zipfile(project_path), "Файл должен быть ZIP архивом"

        # Загружаем проект
        loaded_project = ProjectIO.load_project(str(project_path))
        assert loaded_project is not None, "Загрузка проекта должна быть успешной"

        # Проверяем данные
        assert loaded_project.name == project.name
        assert loaded_project.video_path == project.video_path
        assert loaded_project.fps == project.fps
        assert len(loaded_project.markers) == len(project.markers)

        # Проверяем маркеры
        for original, loaded in zip(project.markers, loaded_project.markers):
            assert loaded.start_frame == original.start_frame
            assert loaded.end_frame == original.end_frame
            assert loaded.event_name == original.event_name
            assert loaded.note == original.note

    print("✅ Базовое сохранение/загрузка работает корректно")


def test_project_save_load_empty():
    """Тест сохранения и загрузки пустого проекта."""
    print("\n🧪 Тестирование пустого проекта...")

    # Создаем пустой проект
    project = Project(name="Empty Project")

    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "empty_project.hep"

        # Сохраняем и загружаем
        success = ProjectIO.save_project(project, str(project_path))
        assert success, "Сохранение пустого проекта должно быть успешным"

        loaded_project = ProjectIO.load_project(str(project_path))
        assert loaded_project is not None
        assert loaded_project.name == project.name
        assert len(loaded_project.markers) == 0

    print("✅ Пустой проект сохраняется/загружается корректно")


def test_project_save_load_complex():
    """Тест сохранения и загрузки проекта с множеством маркеров."""
    print("\n🧪 Тестирование проекта с множеством маркеров...")

    project = Project(
        name="Complex Project",
        video_path="/videos/complex.mp4",
        fps=25.0
    )

    # Добавляем много маркеров разных типов
    events = ["Attack", "Defense", "Goal", "Penalty", "Timeout", "CustomEvent"]
    for i in range(50):
        project.markers.append(Marker(
            start_frame=i * 100,
            end_frame=i * 100 + 50,
            event_name=events[i % len(events)],
            note=f"Marker {i}"
        ))

    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "complex_project.hep"

        # Сохраняем
        success = ProjectIO.save_project(project, str(project_path))
        assert success, "Сохранение сложного проекта должно быть успешным"

        # Проверяем размер файла (должен быть разумным для ZIP с данными)
        file_size = project_path.stat().st_size
        assert file_size > 500, f"Файл слишком маленький: {file_size} bytes"

        # Загружаем
        loaded_project = ProjectIO.load_project(str(project_path))
        assert loaded_project is not None
        assert len(loaded_project.markers) == 50

        # Проверяем все маркеры
        for i, (original, loaded) in enumerate(zip(project.markers, loaded_project.markers)):
            assert loaded.start_frame == original.start_frame, f"Marker {i} start_frame mismatch"
            assert loaded.end_frame == original.end_frame, f"Marker {i} end_frame mismatch"
            assert loaded.event_name == original.event_name, f"Marker {i} event_name mismatch"
            assert loaded.note == original.note, f"Marker {i} note mismatch"

    print("✅ Сложный проект с множеством маркеров работает корректно")


def test_project_file_extension():
    """Тест автоматического добавления расширения .hep."""
    print("\n🧪 Тестирование автоматического добавления расширения .hep...")

    project = Project(name="Extension Test")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Сохраняем без расширения
        project_path_no_ext = Path(temp_dir) / "test_project"
        success = ProjectIO.save_project(project, str(project_path_no_ext))
        assert success

        # Файл должен быть создан с расширением .hep
        expected_path = project_path_no_ext.with_suffix(".hep")
        assert expected_path.exists(), "Файл должен быть создан с расширением .hep"
        assert not project_path_no_ext.exists(), "Файл без расширения не должен существовать"

        # Загружаем по правильному пути с расширением
        loaded_project = ProjectIO.load_project(str(expected_path))
        assert loaded_project is not None, "Должен загрузить проект по правильному пути"

    print("✅ Автоматическое добавление расширения работает")


def test_project_error_handling():
    """Тест обработки ошибок."""
    print("\n🧪 Тестирование обработки ошибок...")

    project = Project(name="Error Test")

    # Тест загрузки несуществующего файла
    loaded_project = ProjectIO.load_project("/nonexistent/file.hep")
    assert loaded_project is None, "Загрузка несуществующего файла должна вернуть None"

    # Тест сохранения в недоступную директорию
    success = ProjectIO.save_project(project, "/root/forbidden/project.hep")
    # На Windows это может быть успешным, поэтому просто проверяем, что функция не крашится

    print("✅ Обработка ошибок работает корректно")


def test_project_metadata():
    """Тест сохранения метаданных проекта."""
    print("\n🧪 Тестирование метаданных проекта...")

    import time
    from datetime import datetime

    project = Project(
        name="Metadata Test",
        video_path="/test/video.mp4",
        fps=24.0
    )

    # Запоминаем время создания
    created_time = project.created_at

    with tempfile.TemporaryDirectory() as temp_dir:
        project_path = Path(temp_dir) / "metadata_test.hep"

        # Небольшая задержка
        time.sleep(0.01)

        # Сохраняем
        success = ProjectIO.save_project(project, str(project_path))
        assert success

        # Загружаем
        loaded_project = ProjectIO.load_project(str(project_path))
        assert loaded_project is not None

        # Проверяем метаданные
        assert loaded_project.name == project.name
        assert loaded_project.video_path == project.video_path
        assert loaded_project.fps == project.fps
        assert loaded_project.version == project.version
        assert loaded_project.created_at == created_time  # Время создания должно сохраниться
        # modified_at должен быть обновлен при сохранении
        assert loaded_project.modified_at != created_time

    print("✅ Метаданные проекта сохраняются корректно")


def test_project_round_trip():
    """Тест полного цикла сохранение->загрузка->сохранение."""
    print("\n🧪 Тестирование полного цикла...")

    # Создаем проект
    project = Project(
        name="Round Trip Test",
        video_path="/round/trip/video.mp4",
        fps=30.0
    )

    # Добавляем маркеры
    for i in range(10):
        project.markers.append(Marker(
            start_frame=i * 60,
            end_frame=i * 60 + 30,
            event_name=f"Event{i}",
            note=f"Note {i}"
        ))

    with tempfile.TemporaryDirectory() as temp_dir:
        path1 = Path(temp_dir) / "round_trip_1.hep"
        path2 = Path(temp_dir) / "round_trip_2.hep"

        # Первый цикл: сохранить -> загрузить
        success1 = ProjectIO.save_project(project, str(path1))
        assert success1

        loaded1 = ProjectIO.load_project(str(path1))
        assert loaded1 is not None

        # Второй цикл: сохранить загруженный проект -> загрузить снова
        success2 = ProjectIO.save_project(loaded1, str(path2))
        assert success2

        loaded2 = ProjectIO.load_project(str(path2))
        assert loaded2 is not None

        # Сравниваем оригинал и финальный результат
        assert loaded2.name == project.name
        assert loaded2.video_path == project.video_path
        assert loaded2.fps == project.fps
        assert len(loaded2.markers) == len(project.markers)

        for orig, final in zip(project.markers, loaded2.markers):
            assert final.start_frame == orig.start_frame
            assert final.end_frame == orig.end_frame
            assert final.event_name == orig.event_name
            assert final.note == orig.note

    print("✅ Полный цикл сохранение->загрузка работает корректно")


def cleanup_test_files():
    """Очистка тестовых файлов."""
    # Ничего не делаем, так как используем TemporaryDirectory
    pass


if __name__ == "__main__":
    print("🚀 Запуск комплексного тестирования сохранения проектов в формате .hep...\n")

    try:
        test_project_save_load_basic()
        test_project_save_load_empty()
        test_project_save_load_complex()
        test_project_file_extension()
        test_project_error_handling()
        test_project_metadata()
        test_project_round_trip()

        print("\n🎉 Все тесты сохранения/загрузки проектов пройдены успешно!")
        print("✅ Система сохранения в формате .hep работает корректно.")

    except Exception as e:
        print(f"\n❌ Тест провален: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        cleanup_test_files()
