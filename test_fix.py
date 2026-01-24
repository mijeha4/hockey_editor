#!/usr/bin/env python3
"""
Простой тест для проверки исправления AttributeError.
"""

import sys
sys.path.insert(0, 'hockey_editor')
sys.path.insert(0, 'src')

# Проверяем, что TimelineWidget имеет нужные методы
try:
    from hockey_editor.ui.timeline_graphics import TimelineWidget
    print("TimelineWidget imported successfully")

    # Проверяем, что метода update_segment нет (как и должно быть)
    if hasattr(TimelineWidget, 'update_segment'):
        print("ERROR: update_segment method still exists!")
    else:
        print("OK: update_segment method removed")

    # Проверяем, что rebuild есть
    if hasattr(TimelineWidget, 'scene') and hasattr(TimelineWidget.scene, 'rebuild'):
        print("OK: rebuild method exists")
    else:
        print("ERROR: rebuild method not found")

except ImportError as e:
    print(f"Import error: {e}")

print("Test completed")