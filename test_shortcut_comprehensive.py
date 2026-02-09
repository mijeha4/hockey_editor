#!/usr/bin/env python3
"""
Comprehensive test script to verify that shortcut rebind fix works correctly.
This test covers both normal rebind and conflict resolution scenarios.
"""

import sys
import os
import time
from PySide6.QtWidgets import QApplication, QWidget, QMessageBox
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
        self.setWindowTitle("Comprehensive Shortcut Test")
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
        
    def restore_default_shortcuts(self):
        """Restore default shortcuts for testing."""
        event_manager = get_custom_event_manager()
        events = event_manager.get_all_events()
        
        # Restore some default shortcuts for testing
        for event in events:
            if event.name == "Goal":
                event.shortcut = "G"
            elif event.name == "Shot on Goal":
                event.shortcut = "H"
            elif event.name == "Takeaway":
                event.shortcut = "A"
            elif event.name == "Turnover":
                event.shortcut = "T"
            elif event.name == "Zone Entry":
                event.shortcut = "Z"
            elif event.name == "Zone Exit":
                event.shortcut = "X"
            elif event.name == "Dump In":
                event.shortcut = "D"
            elif event.name == "Faceoff Win":
                event.shortcut = "F"
            elif event.name == "Faceoff Loss":
                event.shortcut = "L"
            elif event.name == "Missed Shot":
                event.shortcut = "M"
            elif event.name == "Blocked Shot":
                event.shortcut = "C"
            elif event.name == "Defensive Block":
                event.shortcut = "K"
            elif event.name == "Penalty":
                event.shortcut = "P"
                
            event_manager.update_event(event.name, event)
            
        # Wait for controller to process changes
        time.sleep(0.5)
        QApplication.processEvents()
        print("Default shortcuts restored")
        
    def run_test(self):
        """Run comprehensive shortcut tests."""
        print("=== Comprehensive Shortcut Rebind Test ===")
        
        # Restore default shortcuts first
        self.restore_default_shortcuts()
        
        # Test 1: Normal rebind (G -> Y)
        print("\n--- Test 1: Normal Rebind (G -> Y) ---")
        if not self.test_normal_rebind():
            return False
            
        # Test 2: Conflict resolution (Y -> H, where H is used by Shot on Goal)
        print("\n--- Test 2: Conflict Resolution (Y -> H) ---")
        if not self.test_conflict_resolution():
            return False
            
        print("\n=== ALL TESTS PASSED ===")
        print("✓ Shortcut rebind fix is working correctly!")
        print("✓ Old shortcuts are properly cleaned up")
        print("✓ New shortcuts work as expected")
        print("✓ Conflict resolution works properly")
        
        return True
        
    def test_normal_rebind(self):
        """Test normal shortcut rebind without conflicts."""
        event_manager = get_custom_event_manager()
        goal_event = None
        
        # Find Goal event
        for event in event_manager.get_all_events():
            if event.name == "Goal":
                goal_event = event
                break
                
        if not goal_event or goal_event.shortcut != "G":
            print("ERROR: Goal event not found or shortcut not 'G'")
            return False
            
        print(f"Found event: {goal_event.name} with shortcut: {goal_event.shortcut}")
        
        # Test initial 'G' works
        print("Testing initial 'G' shortcut...")
        self.test_results.clear()
        self.simulate_key_press('G')
        if len(self.test_results) != 1 or self.test_results[0] != 'G':
            print("ERROR: 'G' shortcut didn't work initially")
            return False
            
        # Change 'G' to 'Y'
        print("Changing 'G' to 'Y'...")
        goal_event.shortcut = 'Y'
        success = event_manager.update_event(goal_event.name, goal_event)
        if not success:
            print("ERROR: Failed to update event shortcut")
            return False
            
        # Wait for changes
        time.sleep(0.5)
        QApplication.processEvents()
        
        # Test 'G' no longer works, 'Y' works
        print("Testing after rebind...")
        self.test_results.clear()
        self.simulate_key_press('G')  # Should not work
        self.simulate_key_press('Y')  # Should work
        if len(self.test_results) != 1 or self.test_results[0] != 'Y':
            print("ERROR: Rebind failed - expected only 'Y' to work")
            return False
            
        print("✓ Normal rebind test passed")
        return True
        
    def test_conflict_resolution(self):
        """Test shortcut rebind with conflict resolution."""
        event_manager = get_custom_event_manager()
        goal_event = None
        shot_event = None
        
        # Find Goal and Shot on Goal events
        for event in event_manager.get_all_events():
            if event.name == "Goal":
                goal_event = event
            elif event.name == "Shot on Goal":
                shot_event = event
                
        if not goal_event or not shot_event:
            print("ERROR: Required events not found")
            return False
            
        # Ensure Goal has 'Y' and Shot on Goal has 'H'
        if goal_event.shortcut != 'Y' or shot_event.shortcut != 'H':
            print("ERROR: Events don't have expected shortcuts")
            return False
            
        print(f"Found events: {goal_event.name} (Y), {shot_event.name} (H)")
        
        # Test initial shortcuts work
        print("Testing initial shortcuts...")
        self.test_results.clear()
        self.simulate_key_press('Y')  # Goal
        self.simulate_key_press('H')  # Shot on Goal
        if len(self.test_results) != 2:
            print("ERROR: Both shortcuts didn't work initially")
            return False
            
        # Change Goal from 'Y' to 'H' (creating conflict)
        print("Changing Goal from 'Y' to 'H' (creating conflict)...")
        goal_event.shortcut = 'H'
        success = event_manager.update_event(goal_event.name, goal_event)
        if not success:
            print("ERROR: Failed to update event shortcut")
            return False
            
        # Wait for changes
        time.sleep(0.5)
        QApplication.processEvents()
        
        # Test conflict resolution: 'Y' should not work, 'H' should work for Goal
        print("Testing conflict resolution...")
        self.test_results.clear()
        self.simulate_key_press('Y')  # Should not work (Goal moved to H)
        self.simulate_key_press('H')  # Should work for Goal (Shot on Goal lost H)
        if len(self.test_results) != 1 or self.test_results[0] != 'H':
            print("ERROR: Conflict resolution failed")
            return False
            
        print("✓ Conflict resolution test passed")
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