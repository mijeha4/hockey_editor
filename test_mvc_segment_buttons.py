#!/usr/bin/env python3
"""
Test script for MVC project segment buttons.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from views.widgets.segment_list import SegmentListWidget
from models.domain.marker import Marker
from services.events import get_custom_event_manager


class TestMVCSegmentButtons(QWidget):
    """Test widget for MVC segment buttons."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Тест MVC кнопок сегментов")
        self.setGeometry(100, 100, 600, 400)
        
        layout = QVBoxLayout(self)
        
        # Create test label
        label = QLabel("Если кнопки работают, вы увидите сообщения ниже при нажатии:")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Create segment list widget
        self.segment_widget = SegmentListWidget()
        layout.addWidget(self.segment_widget)
        
        # Connect signals to test handlers
        self.segment_widget.segment_edit_requested.connect(self._on_edit_requested)
        self.segment_widget.segment_delete_requested.connect(self._on_delete_requested)
        self.segment_widget.segment_jump_requested.connect(self._on_jump_requested)
        
        # Create test segments
        self._create_test_segments()
        
    def _create_test_segments(self):
        """Create test segments for the widget."""
        # Initialize custom event manager
        event_manager = get_custom_event_manager()
        
        # Create test markers
        marker1 = Marker(
            event_name="shot",
            start_frame=100,
            end_frame=150
        )
        
        marker2 = Marker(
            event_name="goal",
            start_frame=200,
            end_frame=250
        )
        
        # Set FPS
        self.segment_widget.set_fps(30.0)
        
        # Set segments
        segments = [(0, marker1), (1, marker2)]
        self.segment_widget.set_segments(segments)
        
    def _on_edit_requested(self, marker_idx):
        """Handle edit button click."""
        print(f"✓ MVC Кнопка Редактировать нажата для сегмента {marker_idx}")
        
    def _on_delete_requested(self, marker_idx):
        """Handle delete button click."""
        print(f"✓ MVC Кнопка Удалить нажата для сегмента {marker_idx}")
        
    def _on_jump_requested(self, marker_idx):
        """Handle jump button click."""
        print(f"✓ MVC Кнопка Перейти нажата для сегмента {marker_idx}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    test_widget = TestMVCSegmentButtons()
    test_widget.show()
    sys.exit(app.exec())
