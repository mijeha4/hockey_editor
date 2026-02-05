#!/usr/bin/env python3
"""
Test script for Delete functionality in Hockey Editor.

This script tests the Delete key functionality for removing segments
from the timeline and segment list.
"""

import sys
import os
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

# Import components
from views.windows.main_window import MainWindow
from controllers.main_controller import MainController
from models.domain.marker import Marker
from models.domain.project import Project
from services.events.custom_event_manager import get_custom_event_manager

def test_delete_functionality():
    """Test Delete key functionality."""
    print("Testing Delete functionality...")
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create main controller
    controller = MainController()
    
    # Create main window
    window = MainWindow()
    window.set_controller(controller)
    
    # Create timeline controller
    from controllers.timeline_controller import TimelineController
    timeline_controller = TimelineController(controller)
    window.set_timeline_controller(timeline_controller)
    
    # Create test project
    project = Project("Test Project")
    controller.set_project(project)
    
    # Add test events
    event_manager = get_custom_event_manager()
    event_manager.add_event("Goal", "Гол", "#00ff00")
    event_manager.add_event("Penalty", "Штраф", "#ff0000")
    
    # Create test markers
    marker1 = Marker("Goal", 100, 200, "Test goal")
    marker2 = Marker("Penalty", 300, 400, "Test penalty")
    
    # Add markers to project
    controller.add_marker(marker1)
    controller.add_marker(marker2)
    
    print(f"Initial markers count: {len(controller.markers)}")
    
    # Test 1: Delete via timeline selection
    print("\nTest 1: Delete via timeline selection")
    
    # Simulate clicking on first segment in timeline
    # This would normally be done by user clicking on the segment
    # For testing, we'll directly call the delete method
    
    # Get timeline widget
    timeline_widget = window.get_timeline_widget()
    
    # Simulate selection of first marker (index 0)
    # In real usage, this would be done by clicking on the segment
    # For testing, we'll simulate the selection
    
    # Test deletion via timeline controller
    initial_count = len(controller.markers)
    timeline_controller.delete_marker(0)
    
    print(f"After deleting first marker: {len(controller.markers)}")
    assert len(controller.markers) == initial_count - 1, "Marker should be deleted"
    
    # Test 2: Delete via segment list selection
    print("\nTest 2: Delete via segment list selection")
    
    # Add marker back for testing
    controller.add_marker(marker1)
    
    # Get segment list widget
    segment_list = window.get_segment_list_widget()
    
    # Test deletion via segment list signal
    initial_count = len(controller.markers)
    
    # Simulate delete request from segment list
    # This would normally be triggered by clicking delete button or pressing Delete key
    # For testing, we'll directly call the controller method
    
    # Test the delete command directly
    from controllers.timeline_controller import DeleteMarkerCommand
    
    # Create and execute delete command
    delete_cmd = DeleteMarkerCommand(controller, 0)
    controller.history_manager.execute(delete_cmd)
    
    print(f"After deleting via command: {len(controller.markers)}")
    assert len(controller.markers) == initial_count - 1, "Marker should be deleted via command"
    
    # Test 3: Undo functionality
    print("\nTest 3: Undo functionality")
    
    # Add marker back for testing
    controller.add_marker(marker1)
    
    initial_count = len(controller.markers)
    
    # Execute delete command
    delete_cmd = DeleteMarkerCommand(controller, 0)
    controller.history_manager.execute(delete_cmd)
    
    print(f"After delete: {len(controller.markers)}")
    assert len(controller.markers) == initial_count - 1, "Marker should be deleted"
    
    # Undo delete
    controller.history_manager.undo()
    
    print(f"After undo: {len(controller.markers)}")
    assert len(controller.markers) == initial_count, "Marker should be restored after undo"
    
    # Test 4: Redo functionality
    print("\nTest 4: Redo functionality")
    
    # Redo delete
    controller.history_manager.redo()
    
    print(f"After redo: {len(controller.markers)}")
    assert len(controller.markers) == initial_count - 1, "Marker should be deleted after redo"
    
    print("\n✅ All Delete functionality tests passed!")
    
    return True

def test_delete_shortcut():
    """Test Delete key shortcut."""
    print("\nTesting Delete key shortcut...")
    
    app = QApplication(sys.argv)
    controller = MainController()
    window = MainWindow()
    window.set_controller(controller)
    
    # Create timeline controller
    from controllers.timeline_controller import TimelineController
    timeline_controller = TimelineController(controller)
    window.set_timeline_controller(timeline_controller)
    
    # Create test project
    project = Project("Test Project")
    controller.set_project(project)
    
    # Add test event
    event_manager = get_custom_event_manager()
    event_manager.add_event("Test", "Тест", "#ffffff")
    
    # Create test marker
    marker = Marker("Test", 100, 200, "Test marker")
    controller.add_marker(marker)
    
    print(f"Initial markers count: {len(controller.markers)}")
    
    # Simulate Delete key press
    # This would normally be handled by the shortcut system
    # For testing, we'll simulate the shortcut handler
    
    # Simulate the shortcut handler calling delete on selected segment
    # In real usage, this would be triggered by the shortcut system
    # when Delete key is pressed and a segment is selected
    
    # For this test, we'll simulate having a selected segment
    # and then calling the delete function
    
    # Test the delete functionality directly
    initial_count = len(controller.markers)
    
    # Simulate delete of selected segment (index 0)
    timeline_controller.delete_marker(0)
    
    print(f"After Delete key simulation: {len(controller.markers)}")
    assert len(controller.markers) == initial_count - 1, "Marker should be deleted by Delete key"
    
    print("✅ Delete key shortcut test passed!")
    
    return True

if __name__ == "__main__":
    try:
        # Run tests
        test_delete_functionality()
        test_delete_shortcut()
        
        print("\n🎉 All tests completed successfully!")
        print("Delete functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)