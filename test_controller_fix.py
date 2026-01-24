#!/usr/bin/env python3
"""
Тест для проверки, что timeline_controller.py больше не вызывает update_segment.
"""

import sys
sys.path.insert(0, 'hockey_editor')
sys.path.insert(0, 'src')

# Проверяем код timeline_controller.py
with open('src/controllers/timeline_controller.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ищем вызовы update_segment(
if 'update_segment(' in content:
    print("ERROR: update_segment() calls still exist in timeline_controller.py")
    # Найдем строки
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'update_segment(' in line:
            print(f"Line {i}: {line.strip()}")
else:
    print("OK: No update_segment() calls found in timeline_controller.py")

# Ищем вызовы remove_segment
if 'remove_segment' in content:
    print("ERROR: remove_segment calls still exist in timeline_controller.py")
    lines = content.split('\n')
    for i, line in enumerate(lines, 1):
        if 'remove_segment' in line:
            print(f"Line {i}: {line.strip()}")
else:
    print("OK: No remove_segment calls found in timeline_controller.py")

# Ищем markers_changed.emit()
if 'markers_changed.emit()' in content:
    print("OK: markers_changed.emit() calls found")
else:
    print("ERROR: No markers_changed.emit() calls found")

print("Controller test completed")