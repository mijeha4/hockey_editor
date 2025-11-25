# Hockey Editor Pro - Professional Video Analysis Tool

## Overview

Hockey Editor Pro is a professional-grade video analysis tool designed for hockey teams, coaches, and analysts. It enables frame-by-frame annotation of game footage with support for multiple event types (Attack, Defense, Shift).

### Features ✨

- **🎥 Professional Video Player**: Play/pause, seek, speed control with real-time frame display
- **📍 Event Markers**: Mark Attack (A), Defense (D), and Shift (S) events with frame precision
- **📊 Interactive Timeline**: QGraphicsView-based timeline with drag/resize segments, zoom, pan
- **👁️ Segment Preview**: Review all marked segments with filtering and playback
- **💾 Project System**: Save/load projects (.hep format - ZIP with metadata)
- **↩️ Undo/Redo**: Full undo/redo stack (Ctrl+Z / Ctrl+Shift+Z)
- **🔄 Autosave & Recovery**: Automatic saving every 5 minutes with crash recovery
- **📤 Export**: Export segments in multiple formats with quality control
- **⌨️ Customizable Hotkeys**: Global hotkeys with dynamic rebinding (no restart needed)
- **🎨 Dark UI**: Professional dark theme with tooltips and keyboard shortcuts

## Installation

### Requirements
- Python 3.8+
- PySide6
- OpenCV (cv2)
- FFmpeg (for export)

### Setup

```bash
# Clone repository
git clone https://github.com/mijeha4/hockey_editor.git
cd hockey_editor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python -m hockey_editor.main
```

## Usage

### Basic Workflow

1. **Open Video**: File → Open Project or drag-drop video file
2. **Mark Events**: 
   - Press **A** for Attack event at current frame
   - Press **D** for Defense event
   - Press **S** for Shift event
   - Or click corresponding buttons
3. **Review Timeline**: See all marked events on the interactive timeline
4. **Edit Segments**: Double-click segment on timeline or in list to edit
5. **Preview**: Click "Preview" button to review all segments with filtering
6. **Export**: Click "Export" to save segments to video file

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **A** | Add Attack event |
| **D** | Add Defense event |
| **S** | Add Shift event |
| **Space** | Play/Pause |
| **Ctrl+O** | Open video |
| **Ctrl+N** | New project |
| **Ctrl+S** | Save project |
| **Ctrl+Z** | Undo |
| **Ctrl+Shift+Z** | Redo |
| **Ctrl+E** | Export segments |
| **Ctrl+,** | Settings |
| **Escape** | Cancel recording |

### Project Files (.hep)

Hockey Editor projects are saved as `.hep` files (ZIP format) containing:
- `project.json` - Metadata and all markers with timestamps
- Compatible with version 1.0+

## Architecture

### Core Components

- **VideoProcessor** (`hockey_editor/core/video_processor.py`)
  - Handles video I/O using OpenCV
  - Manages frame seeking and playback

- **VideoController** (`hockey_editor/core/video_controller.py`)
  - Central command hub for all video operations
  - Manages markers, playback, recording states
  - Integrates settings, undo/redo, and project management

- **ProjectManager** (`hockey_editor/core/project_manager.py`)
  - Save/load .hep project files
  - Maintains recent projects list
  - ZIP-based serialization

- **SettingsManager** (`hockey_editor/utils/settings_manager.py`)
  - QSettings wrapper for persistent configuration
  - Stores: hotkeys, UI geometry, autosave settings, recent projects
  - Platform-native (Windows Registry, Linux ~/.config)

- **ShortcutManager** (`hockey_editor/utils/shortcut_manager.py`)
  - Dynamic hotkey binding using QShortcut
  - Supports runtime rebinding without restart
  - Global scope (works across all UI widgets)

- **UndoRedoManager** (`hockey_editor/utils/undo_redo.py`)
  - QUndoStack-based command pattern
  - Commands: AddMarker, DeleteMarker, ModifyMarker, ClearMarkers
  - Full undo/redo history

- **AutosaveManager** (`hockey_editor/utils/autosave.py`)
  - QTimer-based autosave every 5 minutes
  - Crash recovery with manifest tracking
  - Up to 10 recovery snapshots

### UI Components

- **MainWindow** (`hockey_editor/ui/main_window.py`)
  - Main application window
  - File menu with New/Open/Save/Recent Projects
  - Event buttons (A/D/S), undo/redo, preview, settings, export

- **TimelineGraphicsView** (`hockey_editor/ui/timeline_graphics.py`)
  - Professional QGraphicsView-based timeline
  - Interactive segments: drag/resize, double-click to edit
  - Zoom (Ctrl+Wheel) and pan support
  - Time grid with adjustable scale

- **PreviewWindow** (`hockey_editor/ui/preview_window.py`)
  - Segment playback window (separate from main)
  - Segment list with type coloring
  - Filtering (A/D/S checkboxes)
  - Auto-advance to next segment
  - Edit/delete buttons

- **EditSegmentDialog** (`hockey_editor/ui/edit_segment_dialog.py`)
  - Frame-accurate segment editing
  - Start/end frame spinboxes with MM:SS.FF format
  - Duration display in frames and time
  - Note field for annotations
  - Dark stylesheet

- **ExportDialog** (`hockey_editor/ui/export_dialog.py`)
  - Multi-threaded export with progress bar
  - Codec selection (h264/h265/mpeg4)
  - Quality control (CRF slider)
  - Format selection (MP4/MOV/MKV)
  - Cancellation support

## Configuration

### Hotkeys

Change hotkeys in Settings dialog:
- Settings → Hotkeys tab
- Select event type
- Enter desired hotkey (e.g., "X", "Ctrl+A", "Shift+1")
- Save - changes apply immediately

### Autosave

Configure in Settings:
- Autosave interval (default: 5 minutes)
- Enable/disable autosave
- Manual save via Ctrl+S or File → Save

### Recording Mode

- **Dynamic**: Two keystrokes = start/end (or one keystroke with timeout)
- **Fixed Length**: One keystroke = fixed-duration segment

## Troubleshooting

### Video Not Playing
- Ensure FFmpeg is installed: `ffmpeg -version`
- Supported formats: MP4, AVI, MOV, MKV, FLV, WMV
- Check file permissions

### Projects Won't Open
- Ensure .hep file is valid (ZIP format)
- Check if video file path is accessible
- Use recovery: watch for crash recovery dialog on startup

### Hotkeys Not Working
- Check Settings dialog - hotkeys may be remapped
- Ensure no conflicting shortcuts
- Try restarting if shortcuts unresponsive

### Autosave Issues
- Check directory permissions: `~/.hockey_editor/recovery/`
- If crash recovery stuck: manually delete `manifest.json`

## Development

### Project Structure

```
hockey_editor/
├── __init__.py
├── main.py                 # Application entry point
├── core/
│   ├── video_processor.py  # OpenCV video I/O
│   ├── video_controller.py # Main controller
│   ├── project_manager.py  # Project serialization
│   └── exporter.py         # Video export
├── ui/
│   ├── main_window.py      # Main UI window
│   ├── timeline_graphics.py # QGraphicsView timeline
│   ├── preview_window.py   # Segment preview
│   ├── edit_segment_dialog.py
│   ├── export_dialog.py
│   ├── settings_dialog.py
│   └── ...
├── models/
│   ├── marker.py           # Event marker model
│   └── recording_mode.py
├── utils/
│   ├── settings_manager.py # QSettings wrapper
│   ├── shortcut_manager.py # QShortcut manager
│   ├── undo_redo.py        # QUndoStack commands
│   ├── autosave.py         # Autosave manager
│   ├── time_utils.py
│   └── ...
└── assets/
    └── icons/              # Application icons
```

### Building from Source

```bash
# Development setup
pip install -e ".[dev]"

# Run tests
pytest

# Build installer
pyinstaller hockey_editor.spec
```

## API Documentation

### VideoController

Main interface for video operations:

```python
from hockey_editor.core.video_controller import VideoController

controller = VideoController()

# Load video
controller.load_video("game.mp4")

# Get properties
fps = controller.get_fps()
total_frames = controller.get_total_frames()

# Playback
controller.play()
controller.pause()
controller.seek_frame(100)

# Markers
controller.on_hotkey_pressed(EventType.ATTACK)
controller.delete_marker(0)
marker = controller.markers[0]

# Projects
controller.save_project("game.hep")
controller.load_project("saved.hep")

# Undo/Redo
controller.undo()
controller.redo()

# Properties
print(controller.markers)  # List[Marker]
```

### Marker Model

```python
from hockey_editor.models.marker import Marker, EventType

marker = Marker(
    type=EventType.ATTACK,
    start_frame=100,
    end_frame=150,
    note="Quick counterattack"
)

print(f"{marker.type.name} ({marker.start_frame}-{marker.end_frame})")
```

### Settings Manager

```python
from hockey_editor.utils.settings_manager import get_settings_manager

settings = get_settings_manager()

# Hotkeys
settings.save_hotkeys({'ATTACK': 'A', 'DEFENSE': 'D', 'SHIFT': 'S'})
hotkeys = settings.load_hotkeys()

# Recording settings
settings.save_recording_mode("dynamic")
settings.save_fixed_duration(60)

# Colors
settings.save_event_colors({'ATTACK': '#ff0000', 'DEFENSE': '#0000ff'})

# Recent projects
recent = settings.load_recent_projects()
```

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## Support

- 📧 Email: support@hockeyeditor.dev
- 🐛 Issues: GitHub Issues
- 💬 Discussions: GitHub Discussions

## Roadmap

### v1.1
- [ ] Telestration/drawing overlay
- [ ] Batch segment export
- [ ] Analytics dashboard
- [ ] Custom event types (user-defined)

### v1.2
- [ ] Multi-video timeline
- [ ] Real-time transcoding
- [ ] Cloud project sync
- [ ] AI-assisted event detection

### v2.0
- [ ] Plugin system
- [ ] Network streaming
- [ ] iOS/Android companion app
- [ ] REST API server

## Acknowledgments

Built with:
- **PySide6** - Qt for Python
- **OpenCV** - Video processing
- **FFmpeg** - Codec support

Inspired by:
- SportCode
- Hudl
- LongoMatch

---

**Hockey Editor Pro v1.0** - Professional Video Analysis Tool
Made with ❤️ for hockey teams and analysts worldwide

