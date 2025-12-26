#!/usr/bin/env python3
"""
Test script for views package functionality.
Tests imports and basic functionality of all views components.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test all imports work correctly."""
    print("Testing imports...")

    try:
        # Test main views package
        import src.views
        print("✓ src.views imported")

        # Test widgets
        from src.views.widgets import (
            DrawingOverlay, DrawingTool,
            EventCardDelegate,
            PlayerControls,
            SegmentListWidget,
            EventShortcutListWidget,
            TimelineWidget
        )
        print("✓ All widgets imported")

        # Test windows
        from src.views.windows import (
            MainWindow,
            PreviewWindow,
            InstanceEditWindow,
            ExportDialog,
            SettingsDialog
        )
        print("✓ All windows imported")

        # Test dialogs
        from src.views.dialogs import (
            CustomEventDialog,
            CustomEventManagerDialog
        )
        print("✓ All dialogs imported")

        # Test services
        from src.services.events.custom_event_type import CustomEventType
        from src.services.events.custom_event_manager import CustomEventManager, get_custom_event_manager
        print("✓ Events service imported")

        # Test models
        from src.models.ui.event_list_model import MarkersListModel
        print("✓ UI models imported")

        return True

    except ImportError as e:
        print(f"✗ Import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality of key components."""
    print("\nTesting basic functionality...")

    try:
        # Test CustomEventType
        from src.services.events.custom_event_type import CustomEventType
        event = CustomEventType(name="Test", color="#FF0000", shortcut="T")
        assert event.name == "Test"
        assert event.get_qcolor().name() == "#ff0000"
        print("✓ CustomEventType works")

        # Test MarkersListModel
        from src.models.ui.event_list_model import MarkersListModel
        from src.models.domain.marker import Marker

        model = MarkersListModel()
        marker = Marker(event_name="Test", start_frame=0, end_frame=30)
        model.set_markers([marker])
        assert model.rowCount() == 1
        print("✓ MarkersListModel works")

        # Test event manager
        from src.services.events.custom_event_manager import get_custom_event_manager
        manager = get_custom_event_manager()
        events = manager.get_all_events()
        assert len(events) > 0
        print("✓ CustomEventManager works")

        return True

    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

def test_widget_creation():
    """Test widget creation without GUI."""
    print("\nTesting widget creation...")

    try:
        # Set up minimal Qt environment
        from PySide6.QtWidgets import QApplication
        import sys

        # Create QApplication if it doesn't exist
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        # Test widget imports and basic instantiation
        from src.views.widgets import EventShortcutListWidget, PlayerControls

        # Test EventShortcutListWidget
        widget = EventShortcutListWidget()
        assert widget is not None
        widget.deleteLater()
        print("✓ EventShortcutListWidget created")

        # Test PlayerControls
        controls = PlayerControls()
        assert controls is not None
        controls.deleteLater()
        print("✓ PlayerControls created")

        return True

    except Exception as e:
        print(f"✗ Widget creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Testing Views Package ===\n")

    results = []

    # Test imports
    results.append(("Imports", test_imports()))

    # Test basic functionality
    results.append(("Basic Functionality", test_basic_functionality()))

    # Test widget creation
    results.append(("Widget Creation", test_widget_creation()))

    # Summary
    print("\n=== Test Results ===")
    all_passed = True
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
        all_passed = all_passed and passed

    if all_passed:
        print("\n🎉 All tests passed! Views package is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
