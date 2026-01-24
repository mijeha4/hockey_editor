#!/usr/bin/env python3
"""
Test script for reactive timeline functionality.

Tests the dynamic redrawing of timeline segments after changes in the editor.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PySide6.QtCore import Qt
from models.domain.observable_project import ObservableProject
from models.domain.observable_marker import ObservableMarker
from controllers.timeline_controller import TimelineController
from views.widgets.timeline import TimelineWidget
from views.widgets.segment_list import SegmentListWidget
from services.history import HistoryManager
from models.config.app_settings import AppSettings


class TestReactiveTimeline(QMainWindow):
    """Test window for reactive timeline functionality."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Reactive Timeline Test")
        self.setGeometry(100, 100, 1200, 600)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create test components
        self.create_test_components(layout)
        
        # Initialize test data
        self.setup_test_data()
        
        # Connect signals
        self.connect_signals()
    
    def create_test_components(self, layout):
        """Create test UI components."""
        # Status label
        self.status_label = QLabel("Status: Ready")
        layout.addWidget(self.status_label)
        
        # Timeline widget
        self.timeline_widget = TimelineWidget()
        self.timeline_widget.set_total_frames(3000)  # 100 seconds at 30fps
        self.timeline_widget.set_fps(30.0)
        layout.addWidget(self.timeline_widget)
        
        # Segment list widget
        self.segment_list_widget = SegmentListWidget()
        layout.addWidget(self.segment_list_widget)
        
        # Test buttons
        button_layout = QVBoxLayout()
        
        self.btn_add_marker = QPushButton("Add Test Marker")
        self.btn_modify_marker = QPushButton("Modify First Marker")
        self.btn_delete_marker = QPushButton("Delete First Marker")
        self.btn_clear_all = QPushButton("Clear All Markers")
        
        button_layout.addWidget(self.btn_add_marker)
        button_layout.addWidget(self.btn_modify_marker)
        button_layout.addWidget(self.btn_delete_marker)
        button_layout.addWidget(self.btn_clear_all)
        
        layout.addLayout(button_layout)
    
    def setup_test_data(self):
        """Setup test data and controllers."""
        # Create observable project
        self.observable_project = ObservableProject("Test Project")
        
        # Create controllers
        self.history_manager = HistoryManager()
        self.settings = AppSettings()
        
        self.timeline_controller = TimelineController(
            self.observable_project.to_project(),  # Regular project for compatibility
            self.timeline_widget,
            self.segment_list_widget,
            self.history_manager,
            self.settings
        )
        
        # Set up reactive project
        self.timeline_controller.set_observable_project(self.observable_project)
        
        # Add initial test markers
        self.add_test_marker("Attack", 100, 200, "Test attack sequence")
        self.add_test_marker("Defense", 300, 400, "Test defense sequence")
        self.add_test_marker("Change", 500, 600, "Test player change")
    
    def connect_signals(self):
        """Connect test signals."""
        self.btn_add_marker.clicked.connect(self.on_add_marker)
        self.btn_modify_marker.clicked.connect(self.on_modify_marker)
        self.btn_delete_marker.clicked.connect(self.on_delete_marker)
        self.btn_clear_all.clicked.connect(self.on_clear_all)
        
        # Connect timeline controller signals
        self.timeline_controller.markers_changed.connect(self.on_markers_changed)
    
    def add_test_marker(self, event_name, start_frame, end_frame, note):
        """Add a test marker to the project."""
        marker = ObservableMarker(start_frame, end_frame, event_name, note)
        self.observable_project.add_marker(marker)
        
        # Also add to timeline controller for compatibility
        self.timeline_controller.add_observable_marker(start_frame, end_frame, event_name, note)
    
    def on_add_marker(self):
        """Handle add marker button."""
        try:
            # Add a new marker
            start_frame = 700 + len(self.observable_project.markers) * 100
            end_frame = start_frame + 100
            self.add_test_marker("Test", start_frame, end_frame, f"Auto-generated marker {len(self.observable_project.markers)}")
            
            self.status_label.setText(f"Added marker: Test {start_frame}-{end_frame}")
        except Exception as e:
            self.status_label.setText(f"Error adding marker: {e}")
    
    def on_modify_marker(self):
        """Handle modify marker button."""
        try:
            if len(self.observable_project.markers) > 0:
                marker = self.observable_project.markers[0]
                # Modify the first marker
                new_start = marker.start_frame + 50
                new_end = marker.end_frame + 50
                new_event = "Modified"
                new_note = "Modified by test"
                
                self.timeline_controller.modify_observable_marker(0, new_start, new_end, new_event, new_note)
                
                self.status_label.setText(f"Modified marker 0: {new_event} {new_start}-{new_end}")
            else:
                self.status_label.setText("No markers to modify")
        except Exception as e:
            self.status_label.setText(f"Error modifying marker: {e}")
    
    def on_delete_marker(self):
        """Handle delete marker button."""
        try:
            if len(self.observable_project.markers) > 0:
                marker = self.observable_project.markers[0]
                self.observable_project.remove_marker(marker)
                
                self.status_label.setText(f"Deleted marker: {marker.event_name}")
            else:
                self.status_label.setText("No markers to delete")
        except Exception as e:
            self.status_label.setText(f"Error deleting marker: {e}")
    
    def on_clear_all(self):
        """Handle clear all markers button."""
        try:
            self.observable_project.clear_markers()
            self.status_label.setText("Cleared all markers")
        except Exception as e:
            self.status_label.setText(f"Error clearing markers: {e}")
    
    def on_markers_changed(self):
        """Handle markers changed signal."""
        count = len(self.observable_project.markers)
        self.status_label.setText(f"Markers updated: {count} markers visible")


def main():
    """Main test function."""
    app = QApplication(sys.argv)
    
    # Create and show test window
    test_window = TestReactiveTimeline()
    test_window.show()
    
    print("Reactive Timeline Test started")
    print("Test buttons:")
    print("- Add Test Marker: Adds a new marker to the timeline")
    print("- Modify First Marker: Modifies the first marker's properties")
    print("- Delete First Marker: Removes the first marker")
    print("- Clear All Markers: Removes all markers")
    print("\nWatch the timeline update dynamically as you click buttons!")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()