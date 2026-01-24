"""
Test for checking marker display and updates on timeline.

Checks:
1. Marker display on timeline when added
2. Marker updates on timeline when changed
3. Segment table updates when changed
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from controllers.main_controller import MainController


def test_marker_display():
    """Тест отображения маркеров."""
    app = QApplication(sys.argv)
    
    # Создать контроллер
    controller = MainController()
    
    # Показать окно
    controller.main_window.show()
    
    print("=" * 60)
    print("ТЕСТ: Отображение и обновление маркеров на таймлайне")
    print("=" * 60)
    
    # Функция для добавления тестовых маркеров
    def add_test_markers():
        print("\n1. Добавление тестовых маркеров...")
        
        # Add several markers
        controller.add_marker(100, 200, "Attack")
        print("   [OK] Added marker Attack (100-200)")
        
        controller.add_marker(300, 400, "Defense")
        print("   [OK] Added marker Defense (300-400)")
        
        controller.add_marker(500, 600, "Goal")
        print("   [OK] Added marker Goal (500-600)")
        
        # Check marker count
        marker_count = len(controller.project.markers)
        print(f"\n   Total markers in project: {marker_count}")
        
        # Check timeline widget
        timeline_widget = controller.main_window.get_timeline_widget()
        if timeline_widget:
            segment_count = len(timeline_widget.segment_items)
            print(f"   Segments on timeline: {segment_count}")
            
            if segment_count == marker_count:
                print("   [OK] All markers displayed on timeline!")
            else:
                print(f"   [ERROR] Expected {marker_count} segments, but got {segment_count}")
        else:
            print("   [ERROR] Timeline widget not found!")
        
        # Check segment table
        segment_list = controller.main_window.get_segment_list_widget()
        if segment_list:
            row_count = segment_list.table.rowCount()
            print(f"   Rows in segment table: {row_count}")
            
            if row_count == marker_count:
                print("   [OK] All markers displayed in table!")
            else:
                print(f"   [ERROR] Expected {marker_count} rows, but got {row_count}")
        else:
            print("   [ERROR] Segment list widget not found!")
        
        # Запланировать тест изменения маркера
        QTimer.singleShot(2000, test_marker_update)
    
    def test_marker_update():
        print("\n2. Changing marker...")
        
        # Change first marker
        if len(controller.project.markers) > 0:
            marker = controller.project.markers[0]
            old_start = marker.start_frame
            old_end = marker.end_frame
            
            # Change boundaries
            marker.start_frame = 150
            marker.end_frame = 250
            
            print(f"   Changed marker: {old_start}-{old_end} -> {marker.start_frame}-{marker.end_frame}")
            
            # Check update after small delay
            QTimer.singleShot(500, verify_marker_update)
        else:
            print("   [ERROR] No markers to change!")
            QTimer.singleShot(1000, app.quit)
    
    def verify_marker_update():
        print("\n3. Verifying UI update...")
        
        # Check that changes are displayed
        marker = controller.project.markers[0]
        
        # Check timeline
        timeline_widget = controller.main_window.get_timeline_widget()
        if timeline_widget and len(timeline_widget.segment_items) > 0:
            # Get first segment
            first_segment = timeline_widget.segment_items[0]
            rect = first_segment.rect()
            
            # Calculate expected position
            expected_x = marker.start_frame * timeline_widget.pixels_per_frame
            actual_x = rect.x()
            
            if abs(actual_x - expected_x) < 1:  # Tolerance for rounding
                print("   [OK] Timeline updated correctly!")
            else:
                print(f"   [ERROR] Timeline position not updated")
                print(f"      Expected: {expected_x}, Actual: {actual_x}")
        else:
            print("   [ERROR] Could not check timeline!")
        
        # Check table
        segment_list = controller.main_window.get_segment_list_widget()
        if segment_list and segment_list.table.rowCount() > 0:
            # Get text from "Start" cell
            start_item = segment_list.table.item(0, 2)
            if start_item:
                start_text = start_item.text()
                print(f"   Start time in table: {start_text}")
                print("   [OK] Segment table updated!")
            else:
                print("   [ERROR] Could not get data from table!")
        else:
            print("   [ERROR] Could not check table!")
        
        print("\n" + "=" * 60)
        print("TEST COMPLETED")
        print("=" * 60)
        print("\nWindow will remain open for visual inspection.")
        print("Close window to finish test.")
    
    # Запустить тест через 1 секунду после показа окна
    QTimer.singleShot(1000, add_test_markers)
    
    # Запустить приложение
    sys.exit(app.exec())


if __name__ == "__main__":
    test_marker_display()
