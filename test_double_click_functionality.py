#!/usr/bin/env python3
"""
Test script to verify double-click functionality on timeline segments.
This script tests the signal chain from SegmentGraphicsItem to the segment editor.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from models.domain.marker import Marker
from models.domain.project import Project
from controllers.timeline_controller import TimelineController
from views.widgets.timeline import TimelineWidget, SegmentGraphicsItem, TimelineGraphicsScene
from services.history.history_manager import HistoryManager
from models.config.app_settings import AppSettings

class MockMainWindow:
    """Mock main window for testing"""
    def __init__(self):
        self.segment_editor_opened = False
        self.last_marker_idx = None

    def open_segment_editor(self, marker_idx):
        """Mock method to track segment editor opening"""
        self.segment_editor_opened = True
        self.last_marker_idx = marker_idx
        print(f"Segment editor opened for marker index: {marker_idx}")

def run_tests():
    """Run all tests using a single QApplication instance"""
    print("Running double-click functionality tests...\n")

    # Create a single QApplication instance
    app = QApplication([])

    # Test 1: Signal chain test
    print("Testing double-click signal chain...")
    test1_result = False

    try:
        # Create test data
        project = Project("Test Project")
        history_manager = HistoryManager()
        settings = AppSettings()

        # Create a test marker
        test_marker = Marker(start_frame=100, end_frame=200, event_name="TestEvent", note="Test note")
        project.add_marker(test_marker, 0)

        # Create mock main window
        mock_window = MockMainWindow()

        # Create timeline widget and controller
        timeline_widget = TimelineWidget()
        controller = TimelineController(
            project=project,
            timeline_widget=timeline_widget,
            segment_list_widget=None,
            history_manager=history_manager,
            settings=settings
        )

        # Set main window reference
        controller.set_main_window(mock_window)

        # Create a segment graphics item
        scene = timeline_widget.scene
        segment_item = SegmentGraphicsItem(test_marker, scene)

        # Test the signal emission
        print("Emitting segment_double_clicked signal...")
        scene.segment_double_clicked.emit(test_marker)

        # Check if the signal was processed correctly
        if mock_window.segment_editor_opened:
            print("✓ SUCCESS: Segment editor was opened")
            print(f"✓ SUCCESS: Correct marker index {mock_window.last_marker_idx} was passed")
            test1_result = True
        else:
            print("✗ FAILED: Segment editor was not opened")
            test1_result = False

    except Exception as e:
        print(f"✗ FAILED: Test 1 failed with exception: {e}")
        test1_result = False

    # Test 2: Mouse event test
    print("\nTesting mouse double-click event handling...")
    test2_result = False

    try:
        # Create test data
        project = Project("Test Project")
        history_manager = HistoryManager()
        settings = AppSettings()

        # Create a test marker
        test_marker = Marker(start_frame=100, end_frame=200, event_name="TestEvent", note="Test note")
        project.add_marker(test_marker, 0)

        # Create mock main window
        mock_window = MockMainWindow()

        # Create timeline widget and controller
        timeline_widget = TimelineWidget()
        controller = TimelineController(
            project=project,
            timeline_widget=timeline_widget,
            segment_list_widget=None,
            history_manager=history_manager,
            settings=settings
        )

        # Set main window reference
        controller.set_main_window(mock_window)

        # Create a segment graphics item
        scene = timeline_widget.scene
        segment_item = SegmentGraphicsItem(test_marker, scene)

        # Simulate a mouse double-click event
        from PySide6.QtGui import QMouseEvent
        from PySide6.QtCore import QPointF

        # Create a mock mouse event
        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )

        print("Simulating mouse double-click event...")
        segment_item.mouseDoubleClickEvent(mouse_event)

        # Check if the signal was processed correctly
        if mock_window.segment_editor_opened:
            print("✓ SUCCESS: Mouse double-click event triggered segment editor")
            print(f"✓ SUCCESS: Correct marker index {mock_window.last_marker_idx} was passed")
            test2_result = True
        else:
            print("✗ FAILED: Mouse double-click event did not trigger segment editor")
            test2_result = False

    except Exception as e:
        print(f"✗ FAILED: Test 2 failed with exception: {e}")
        test2_result = False

    # Summary
    print("\n" + "="*50)
    print("TEST RESULTS:")
    print(f"Signal Chain Test: {'PASSED' if test1_result else 'FAILED'}")
    print(f"Mouse Event Test: {'PASSED' if test2_result else 'FAILED'}")

    if test1_result and test2_result:
        print("\n🎉 ALL TESTS PASSED! Double-click functionality is working correctly.")
        return True
    else:
        print("\n❌ SOME TESTS FAILED! Please check the implementation.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)