"""
Simple test to verify that segments appear immediately on the timeline after creation.
This test focuses on the core functionality without complex event management.
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

def test_simple_timeline_fix():
    """Test that segments appear immediately on timeline after creation."""

    print("=== Starting Simple Timeline Fix Test ===")

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

    print(f"Initial markers count: {len(project.markers)}")

    # Test: Add a marker and verify it appears immediately
    print("\n--- Test: Adding marker via controller ---")

    # Add a marker via controller method (simulates hotkey press)
    timeline_controller.add_marker(100, 200, "Goal", "Test marker")

    # Wait a bit for Qt signals to process
    QTimer.singleShot(100, lambda: verify_marker_appearance(timeline_widget, project, "Simple Test"))

    # Run the application event loop for a short time to process signals
    print("\n--- Processing Qt events ---")
    QTimer.singleShot(300, app.quit)

    app.exec()

    print("\n=== Test completed ===")

def verify_marker_appearance(timeline_widget, project, test_name):
    """Verify that markers appear correctly on the timeline."""
    print(f"{test_name}: Verifying marker appearance...")

    # Check if the project has the expected number of markers
    actual_count = len(project.markers)
    print(f"{test_name}: Project markers count: {actual_count} (expected: 1)")

    if actual_count != 1:
        print(f"{test_name}: ERROR - Marker count mismatch!")
        return False

    # Check if the timeline scene has the expected number of segment items
    if hasattr(timeline_widget, 'scene') and timeline_widget.scene:
        segment_items = []
        for item in timeline_widget.scene.items():
            if hasattr(item, 'marker') and isinstance(item.marker, Marker):
                segment_items.append(item)

        scene_segment_count = len(segment_items)
        print(f"{test_name}: Timeline scene segment count: {scene_segment_count} (expected: 1)")

        if scene_segment_count != 1:
            print(f"{test_name}: ERROR - Timeline segment count mismatch!")
            return False

        # Verify that the marker from project is represented in the timeline
        project_marker = project.markers[0]
        scene_marker = segment_items[0].marker

        print(f"{test_name}: Project marker: {project_marker.start_frame}-{project_marker.end_frame} ({project_marker.event_name})")
        print(f"{test_name}: Scene marker: {scene_marker.start_frame}-{scene_marker.end_frame} ({scene_marker.event_name})")

        if (project_marker.start_frame == scene_marker.start_frame and
            project_marker.end_frame == scene_marker.end_frame and
            project_marker.event_name == scene_marker.event_name):
            print(f"{test_name}: SUCCESS - Marker appears correctly on timeline!")
            return True
        else:
            print(f"{test_name}: ERROR - Marker data mismatch between project and timeline!")
            return False
    else:
        print(f"{test_name}: ERROR - Timeline scene not available!")
        return False

if __name__ == "__main__":
    test_simple_timeline_fix()