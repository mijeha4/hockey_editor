"""
Test to verify that segments appear immediately on the timeline after creation.
This test simulates the issue described in the task and verifies the fix.
"""

import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from models.domain.project import Project
from models.domain.marker import Marker
from controllers.timeline_controller import TimelineController
from views.widgets.timeline import TimelineWidget
from views.widgets.segment_list import SegmentListWidget
from services.history.history_manager import HistoryManager
from models.config.app_settings import AppSettings
from services.events.custom_event_manager import get_custom_event_manager

def test_segment_immediate_appearance():
    """Test that segments appear immediately on timeline after creation."""

    print("=== Starting Timeline Fix Verification Test ===")

    # Create Qt application
    app = QApplication(sys.argv)

    # Initialize required components
    project = Project("TestProject")
    timeline_widget = TimelineWidget()
    segment_list_widget = SegmentListWidget()
    history_manager = HistoryManager()
    settings = AppSettings()

    # Create timeline controller
    timeline_controller = TimelineController(
        project=project,
        timeline_widget=timeline_widget,
        segment_list_widget=segment_list_widget,
        history_manager=history_manager,
        settings=settings
    )

    # Set up initial data
    timeline_controller.set_total_frames(1000)
    timeline_controller.set_fps(30.0)

    # Initialize event manager with some events
    event_manager = get_custom_event_manager()
    from services.events.custom_event_type import CustomEventType
    test_event = CustomEventType(name="TestEvent", color="#FF0000", shortcut="T", description="Test event")
    event_manager.add_event(test_event)

    print(f"Initial markers count: {len(project.markers)}")

    # Test 1: Add a marker and verify it appears immediately
    print("\n--- Test 1: Adding first marker ---")

    # Add a marker directly to test the signal flow
    marker1 = Marker(start_frame=100, end_frame=200, event_name="TestEvent", note="First test marker")
    project.add_marker(marker1, 0)

    # Wait a bit for Qt signals to process
    QTimer.singleShot(100, lambda: verify_marker_appearance(timeline_widget, project, 1, "Test 1"))

    # Test 2: Add another marker
    print("\n--- Test 2: Adding second marker ---")

    marker2 = Marker(start_frame=300, end_frame=400, event_name="TestEvent", note="Second test marker")
    project.add_marker(marker2, 1)

    # Wait a bit for Qt signals to process
    QTimer.singleShot(200, lambda: verify_marker_appearance(timeline_widget, project, 2, "Test 2"))

    # Test 3: Add marker via controller method (simulates hotkey press)
    print("\n--- Test 3: Adding marker via controller ---")

    timeline_controller.add_marker(500, 600, "TestEvent", "Controller test")

    # Wait a bit for Qt signals to process
    QTimer.singleShot(300, lambda: verify_marker_appearance(timeline_widget, project, 3, "Test 3"))

    # Run the application event loop for a short time to process signals
    print("\n--- Processing Qt events ---")
    QTimer.singleShot(500, app.quit)

    app.exec()

    print("\n=== Test completed ===")

def verify_marker_appearance(timeline_widget, project, expected_count, test_name):
    """Verify that markers appear correctly on the timeline."""
    print(f"{test_name}: Verifying marker appearance...")

    # Check if the project has the expected number of markers
    actual_count = len(project.markers)
    print(f"{test_name}: Project markers count: {actual_count} (expected: {expected_count})")

    if actual_count != expected_count:
        print(f"{test_name}: ERROR - Marker count mismatch!")
        return False

    # Check if the timeline scene has the expected number of segment items
    if hasattr(timeline_widget, 'scene') and timeline_widget.scene:
        segment_items = []
        for item in timeline_widget.scene.items():
            if hasattr(item, 'marker') and isinstance(item.marker, Marker):
                segment_items.append(item)

        scene_segment_count = len(segment_items)
        print(f"{test_name}: Timeline scene segment count: {scene_segment_count} (expected: {expected_count})")

        if scene_segment_count != expected_count:
            print(f"{test_name}: ERROR - Timeline segment count mismatch!")
            return False

        # Verify that all markers from project are represented in the timeline
        project_marker_ids = [(m.start_frame, m.end_frame, m.event_name) for m in project.markers]
        scene_marker_ids = [(item.marker.start_frame, item.marker.end_frame, item.marker.event_name) for item in segment_items]

        print(f"{test_name}: Project markers: {project_marker_ids}")
        print(f"{test_name}: Scene segments: {scene_marker_ids}")

        if set(project_marker_ids) != set(scene_marker_ids):
            print(f"{test_name}: ERROR - Marker data mismatch between project and timeline!")
            return False

        print(f"{test_name}: SUCCESS - All markers appear correctly on timeline!")
        return True
    else:
        print(f"{test_name}: ERROR - Timeline scene not available!")
        return False

if __name__ == "__main__":
    test_segment_immediate_appearance()