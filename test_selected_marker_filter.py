#!/usr/bin/env python3
"""
Test script for selected marker filter functionality.

This script tests the new feature where clicking on a segment
shows only that segment while hiding others.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models.domain.marker import Marker
from models.domain.project import Project
from models.config.app_settings import AppSettings
from services.history import HistoryManager
from views.widgets.segment_list import SegmentListWidget
from views.widgets.timeline_scene import TimelineWidget
from controllers.timeline_controller import TimelineController
from services.events.custom_event_manager import get_custom_event_manager


def test_selected_marker_filter():
    """Test the selected marker filter functionality."""
    print("Testing Selected Marker Filter Functionality")
    print("=" * 50)
    
    # Create test project with markers
    project = Project(name="Test Project")
    
    # Create test markers
    marker1 = Marker(id=1, start_frame=100, end_frame=200, event_name="Гол", note="Первый гол")
    marker2 = Marker(id=2, start_frame=300, end_frame=400, event_name="Удаление", note="Штраф")
    marker3 = Marker(id=3, start_frame=500, end_frame=600, event_name="Бросок в створ", note="Отличный бросок")
    
    project.add_marker(marker1, 0)
    project.add_marker(marker2, 1)
    project.add_marker(marker3, 2)
    
    print(f"Created project with {len(project.markers)} markers")
    
    # Create timeline controller
    controller = TimelineController(
        project=project,
        timeline_widget=None,
        segment_list_widget=None,
        history_manager=HistoryManager(),
        settings=AppSettings()
    )
    
    print(f"Initial filter mode: {controller.filter_mode}")
    print(f"Initial selected marker ID: {controller.selected_marker_id}")
    
    # Test 1: Get all markers initially
    print("\nTest 1: Get all markers initially")
    filtered_markers = controller.get_filtered_markers()
    print(f"Filtered markers count: {len(filtered_markers)}")
    assert len(filtered_markers) == 3, "Should show all 3 markers initially"
    print("✓ PASS")
    
    # Test 2: Select first marker (index 0)
    print("\nTest 2: Select first marker (index 0)")
    controller.toggle_selected_mode(0)
    print(f"Filter mode after selection: {controller.filter_mode}")
    print(f"Selected marker ID: {controller.selected_marker_id}")
    
    filtered_markers = controller.get_filtered_markers()
    print(f"Filtered markers count: {len(filtered_markers)}")
    assert len(filtered_markers) == 1, "Should show only 1 marker after selection"
    assert filtered_markers[0].id == 1, "Should show marker with ID 1"
    print("✓ PASS")
    
    # Test 3: Select second marker (index 1)
    print("\nTest 3: Select second marker (index 1)")
    controller.toggle_selected_mode(1)
    print(f"Filter mode after selection: {controller.filter_mode}")
    print(f"Selected marker ID: {controller.selected_marker_id}")
    
    filtered_markers = controller.get_filtered_markers()
    print(f"Filtered markers count: {len(filtered_markers)}")
    assert len(filtered_markers) == 1, "Should show only 1 marker after selection"
    assert filtered_markers[0].id == 2, "Should show marker with ID 2"
    print("✓ PASS")
    
    # Test 4: Toggle back to show all markers
    print("\nTest 4: Toggle back to show all markers")
    controller.toggle_selected_mode(1)  # Click same marker again
    print(f"Filter mode after toggle: {controller.filter_mode}")
    print(f"Selected marker ID: {controller.selected_marker_id}")
    
    filtered_markers = controller.get_filtered_markers()
    print(f"Filtered markers count: {len(filtered_markers)}")
    assert len(filtered_markers) == 3, "Should show all 3 markers after toggle"
    print("✓ PASS")
    
    # Test 5: Select third marker (index 2)
    print("\nTest 5: Select third marker (index 2)")
    controller.toggle_selected_mode(2)
    print(f"Filter mode after selection: {controller.filter_mode}")
    print(f"Selected marker ID: {controller.selected_marker_id}")
    
    filtered_markers = controller.get_filtered_markers()
    print(f"Filtered markers count: {len(filtered_markers)}")
    assert len(filtered_markers) == 1, "Should show only 1 marker after selection"
    assert filtered_markers[0].id == 3, "Should show marker with ID 3"
    print("✓ PASS")
    
    print("\n" + "=" * 50)
    print("🎉 ALL TESTS PASSED!")
    print("Selected marker filter functionality is working correctly.")
    print("\nHow it works:")
    print("1. Click on any segment on the timeline")
    print("2. Only that segment will be visible")
    print("3. Click on the same segment again to show all segments")
    print("4. Click on another segment to show only that one")


if __name__ == "__main__":
    test_selected_marker_filter()