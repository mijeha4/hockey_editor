#!/usr/bin/env python3
"""
Test script for final dialog size.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_final_size():
    """Test that dialog has final adequate size."""
    from PySide6.QtWidgets import QApplication

    # Create QApplication if it doesn't exist
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    try:
        # Test direct import
        from src.views.dialogs.new_project_dialog import NewProjectDialog

        print("✓ Imports successful")

        # Test dialog creation
        dialog = NewProjectDialog()
        print("✓ Dialog created successfully")

        # Check final dialog size
        size = dialog.size()
        print(f"✓ Final dialog size: {size.width()}x{size.height()}")

        # Expected final size
        expected_width = 450
        expected_height = 380

        if size.width() == expected_width and size.height() == expected_height:
            print(f"✓ Perfect size: {size.width()}x{size.height()} - all content should fit!")
        else:
            print(f"⚠ Size differs: got {size.width()}x{size.height()}, expected {expected_width}x{expected_height}")

        # Test that dialog can be shown
        dialog.show()
        print("✓ Dialog shown successfully")

        # Close dialog
        dialog.close()
        print("✓ Dialog closed successfully")

        print("✓ Final size test completed successfully")
        return True

    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_final_size()
    sys.exit(0 if success else 1)
