#!/usr/bin/env python3
"""
Simple import test for the new MarkerSegmentTimelineWidget.
"""

import sys
sys.path.insert(0, 'src')

try:
    from views.widgets.marker_segment_timeline import MarkerSegmentTimelineWidget
    from views.windows.main_window import MainWindow
    from models.domain.marker import Marker
    print("All imports successful!")
    print("MarkerSegmentTimelineWidget imported")
    print("MainWindow imported with new timeline widget")
    print("Marker model imported")
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)