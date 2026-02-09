#!/usr/bin/env python3
"""
Test script to verify that shortcut rebind fix works correctly.
This test simulates changing a shortcut and verifies that the old shortcut no longer works.
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
        self.setWindowTitle("Shortcut Test")
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
        """Run the shortcut rebind test."""
        print("=== Testing Shortcut Rebind Fix ===")
        
        # Get event manager
        event_manager = get_custom_event_manager()
        
        # Find an event with 'G' shortcut (Goal)
        goal_event = None
        for event in event_manager.get_all_events():
            if event.shortcut.upper() == 'G':
                goal_event = event
                break
                
        if not goal_event:
            print("ERROR: No event with 'G' shortcut found")
            return False
            
        print(f"Found event: {goal_event.name} with shortcut: {goal_event.shortcut}")
        
        # Test 1: Verify 'G' works initially
        print("\nTest 1: Testing initial 'G' shortcut")
        self.test_results.clear()
        self.simulate_key_press('G')
        initial_results = len(self.test_results)
        print(f"Results after 'G' press: {self.test_results}")
        
        if initial_results == 0:
            print("ERROR: 'G' shortcut didn't work initially")
            return False
            
        # Test 2: Change shortcut from 'G' to 'Y' (free key)
        print(f"\nTest 2: Changing shortcut from 'G' to 'Y' for event '{goal_event.name}'")
        
        # Update shortcut in event
        goal_event.shortcut = 'Y'
        success = event_manager.update_event(goal_event.name, goal_event)
        if not success:
            print("ERROR: Failed to update event shortcut")
            return False
            
        print(f"Updated event shortcut to: {goal_event.shortcut}")
        
        # Wait for controller to process changes
        time.sleep(0.5)
        QApplication.processEvents()
        
        # Test 3: Verify 'G' no longer works
        print("\nTest 3: Testing that 'G' no longer works")
        self.test_results.clear()
        self.simulate_key_press('G')
        g_results = len(self.test_results)
        print(f"Results after 'G' press: {self.test_results}")
        
        if g_results > 0:
            print("ERROR: 'G' shortcut still works after rebind!")
            return False
            
        # Test 4: Verify 'Y' now works
        print("\nTest 4: Testing that 'Y' now works")
        self.test_results.clear()
        self.simulate_key_press('Y')
        y_results = len(self.test_results)
        print(f"Results after 'Y' press: {self.test_results}")
        
        if y_results == 0:
            print("ERROR: 'Y' shortcut doesn't work after rebind!")
            return False
            
        print("\n=== Test Results ===")
        print("✓ 'G' worked initially")
        print("✓ 'G' no longer works after rebind")
        print("✓ 'Y' works after rebind")
        print("✓ Shortcut rebind fix is working correctly!")
        
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