#!/usr/bin/env python3
"""
Architecture Integrity Check
Sanity check script to verify all modules can be imported successfully
"""

import sys
import os
import traceback

# Добавить src в путь для импортов
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


def test_imports():
    """Test all critical imports."""
    try:
        # Test Models
        from models.domain import Marker, Project, EventType
        from models.config import AppSettings
        print("✅ Models imported successfully")

        # Test Services
        from services.video_engine import VideoService
        from services.history import Command, HistoryManager
        from services.serialization import ProjectIO
        print("✅ Services imported successfully")

        # Test Views
        from views.widgets import PlayerControls
        from views.widgets import SegmentListWidget
        from views.windows import MainWindow
        print("✅ Views imported successfully")

        # Test Controllers
        from controllers import PlaybackController, TimelineController, ProjectController, MainController
        print("✅ Controllers imported successfully")

        # Test Main Controller instantiation
        main_controller = MainController()
        print("✅ MainController instantiated successfully")

        return True

    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run the integrity check."""
    print("🔍 Running Architecture Integrity Check...")
    print("=" * 50)

    success = test_imports()

    print("=" * 50)
    if success:
        print("✅ Architecture integrity check passed. All modules imported successfully.")
        print("\n🚀 Ready to run: python main.py")
    else:
        print("❌ Architecture integrity check failed. Please fix the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
