#!/usr/bin/env python3
"""
Test script to verify that shortcut conflict resolution works correctly.
This test simulates changing a shortcut when there's a conflict and verifies proper handling.
"""

import sys
import os
import time
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer, QObject, Signal
from PySide6.QtGui import QKeySequence

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from controllers.shortcut_controller import ShortcutController
from services.events.custom_event_manager import get_custom_event_manager


class TestWidget(QWidget):
    """Test widget for shortcut testing."""
    shortcut_pressed = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Shortcut Conflict Test")
        self.resize(400, 300)
        self.shortcut_controller = None
        self.test_results = []
        
    def setup_controller(self):
        """Setup shortcut controller for testing."""
        self.shortcut_controller = ShortcutController(self)
        self.shortcut_controller.shortcut_pressed.connect(self.on_shortcut_pressed)
        
        # Connect to our signal for testing
        self.shortcut_pressed.connect(self.record_shortcut)
        
    def record_shortcut(self, key: str):
        """Record shortcut press for testing."""
        self.test_results.append(key)
        print(f"RECORDED: Shortcut '{key}' was pressed")
        
    def on_shortcut_pressed(self, key: str):
        """Handle shortcut press from controller."""
        self.shortcut_pressed.emit(key)
        
    def simulate_key_press(self, key: str):
        """Simulate key press for testing."""
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtCore import Qt
        
        # Create key press event
        key_event = QKeyEvent(QKeyEvent.KeyPress, getattr(Qt.Key, f"Key_{key}"), Qt.NoModifier, key)
        QApplication.postEvent(self, key_event)
        QApplication.processEvents()
        time.sleep(0.1)  # Small delay to ensure processing
        
    def run_test(self):
        """Run the shortcut conflict resolution test."""
        print("=== Testing Shortcut Conflict Resolution ===")
        
        # Get event manager
        event_manager = get_custom_event_manager()
        
        # Find events with 'G' and 'H' shortcuts
        goal_event = None
        shot_event = None
        
        for event in event_manager.get_all_events():
            if event.shortcut.upper() == 'G':
                goal_event = event
            elif event.shortcut.upper() == 'H':
                shot_event = event
                
        if not goal_event or not shot_event:
            print("ERROR: Required events with 'G' and 'H' shortcuts not found")
            return False
            
        print(f"Found events: {goal_event.name} (G), {shot_event.name} (H)")
        
        # Test 1: Verify both shortcuts work initially
        print("\nTest 1: Testing initial shortcuts")
        self.test_results.clear()
        self.simulate_key_press('G')
        self.simulate_key_press('H')
        initial_results = len(self.test_results)
        print(f"Results after 'G' and 'H' press: {self.test_results}")
        
        if initial_results != 2:
            print("ERROR: Both shortcuts didn't work initially")
            return False
            
        # Test 2: Change 'G' to 'H' (creating conflict)
        print(f"\nTest 2: Changing '{goal_event.name}' shortcut from 'G' to 'H' (creating conflict)")
        goal_event.shortcut = 'H'
        success = event_manager.update_event(goal_event.name, goal_event)
        if not success:
            print("ERROR: Failed to update event shortcut")
            return False
            
        print(f"Updated {goal_event.name} shortcut to: {goal_event.shortcut}")
        
        # Wait for controller to process changes
        time.sleep(0.5)
        QApplication.processEvents()
        
        # Test 3: Verify 'G' no longer works, 'H' works for new event
        print("\nTest 3: Testing after conflict resolution")
        self.test_results.clear()
        self.simulate_key_press('G')  # Should not work
        self.simulate_key_press('H')  # Should work for new event
        conflict_results = len(self.test_results)
        print(f"Results after 'G' and 'H' press: {self.test_results}")
        
        if conflict_results != 1:
            print("ERROR: Conflict resolution failed - expected 1 result")
            return False
            
        if 'G' in self.test_results:
            print("ERROR: 'G' still works after rebind")
            return False
            
        if 'H' not in self.test_results:
            print("ERROR: 'H' doesn't work after rebind")
            return False
            
        print("\n=== Test Results ===")
        print("✓ Both shortcuts worked initially")
        print("✓ 'G' no longer works after rebind")
        print("✓ 'H' works for new event after conflict resolution")
        print("✓ Shortcut conflict resolution is working correctly!")
        
        return True


def main():
    """Main test function."""
    app = QApplication(sys.argv)
    widget = TestWidget()
    widget.setup_controller()
    widget.show()
    
    # Run test after widget is shown
    QTimer.singleShot(100, widget.run_test)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()