#!/usr/bin/env python3
"""
Test script for MarkerSegmentTimelineWidget.

Creates a simple window to display the timeline widget with sample markers and segments.
"""

import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

# Add src to path for imports
sys.path.insert(0, 'src')

from models.domain.marker import Marker
from views.widgets.marker_segment_timeline import MarkerSegmentTimelineWidget


class TestWindow(QMainWindow):
    """Test window for the timeline widget."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Marker Segment Timeline Test")
        self.setGeometry(100, 100, 1200, 400)

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Create layout
        layout = QVBoxLayout(central_widget)

        # Create timeline widget
        self.timeline = MarkerSegmentTimelineWidget()
        layout.addWidget(self.timeline)

        # Set up timeline
        self.timeline.set_fps(30.0)
        self.timeline.set_total_frames(3000)  # 100 seconds at 30fps

        # Create sample markers and segments
        self.create_sample_data()

        # Set playhead
        self.timeline.draw_playhead(450)  # At 15 seconds

    def create_sample_data(self):
        """Create sample markers and segments for testing."""
        markers = []

        # Point markers (start_frame == end_frame)
        markers.append(Marker(100, 100, "Goal"))  # Frame 100
        markers.append(Marker(200, 200, "Shot on Goal"))  # Frame 200
        markers.append(Marker(350, 350, "Penalty"))  # Frame 350
        markers.append(Marker(500, 500, "Faceoff Win"))  # Frame 500

        # Segment markers (intervals)
        markers.append(Marker(600, 750, "Zone Entry"))  # 5 seconds
        markers.append(Marker(800, 950, "Dump In"))  # 5 seconds
        markers.append(Marker(1000, 1150, "Turnover"))  # 5 seconds
        markers.append(Marker(1200, 1300, "Defensive Block"))  # 3.33 seconds

        # Set markers and segments
        self.timeline.set_markers_and_segments(markers)


def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)

    # Create and show test window
    window = TestWindow()
    window.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()