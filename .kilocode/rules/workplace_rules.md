# workplace_rules.md

## Project Context
You are working on https://github.com/mijeha4/hockey_editor — desktop app for hockey coaches to tag events in match videos.

Core stack: Python 3, PySide6 (Qt6), OpenCV, NumPy, Pandas, Pillow, MoviePy, ReportLab

Main value: ultra-fast event marking via hotkeys + instant visual feedback on timeline + easy clip export

Primary user: hockey coach — needs speed, reliability, intuitive UI (like Hudl, Sportscode, LongoMatch)

## Mandatory Coding Rules
- All new classes/functions: full type hints + detailed Google-style docstrings
- Hotkeys: centralize in one place (utils/hotkeys.py or similar) — never hardcode Qt.Key_XXX in multiple files
- Video operations: minimize frame decoding — use caching, seek wisely, prefer QMediaPlayer where possible
- Timeline rendering: optimize paintEvent — avoid heavy computations inside it
- When editing events: ensure changes reflect instantly on MainWindow timeline and markers table via signals/slots
- UI/UX priority: maximize video preview area, make inspector compact, add presentation mode (hide panels on F11/p)
- Colors & styles: use consistent palette (team colors, event types), dark theme default
- Export: prefer relative paths, add progress bar for long exports

## Behavior Rules
- When adding features: ask "Is this MVP-critical or can postpone?"
- For bugs: first analyze signals/slots, then propose minimal patch
- Always suggest QSplitter for resizable panels (video | sidebar | timeline)
- Presentation mode: suggest hotkey to toggle full-video view (hide sidebar/inspector, large controls overlay)

## Testing & Validation
- After UI/layout changes: remind to test on different resolutions (laptop + external monitor/projector)
- Suggest logging key actions: logger.info(f"Event {id} saved: {start}–{end}")
