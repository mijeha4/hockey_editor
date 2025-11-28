# Hockey Editor Pro - UML Diagrams

This directory contains formal UML diagrams for the Hockey Editor Pro application, created based on the textual architecture descriptions and actual codebase implementation.

## Available Diagrams

### 1. State Machine Diagram (`state_machine_diagram.puml`)
**Purpose**: Shows the event creation workflow state transitions
- **States**: IDLE → RECORDING → RECORDED
- **Based on**: `EventCreationController` implementation
- **Key transitions**: Hotkey presses, timer events, cancellation

### 2. Class Diagram (`class_diagram.puml`)
**Purpose**: Shows the core architecture and class relationships
- **Packages**: Core, UI, Models, Utils
- **Key classes**: VideoController, MainWindow, Marker, SettingsManager
- **Relationships**: Dependencies, associations, method calls

### 3. Component Diagram (`component_diagram.puml`)
**Purpose**: Shows system-level component interactions
- **Components**: Core modules, UI modules, external dependencies
- **Communication**: Direct calls, Qt signals/slots, data flow
- **External deps**: OpenCV, PySide6, FFmpeg, MPV

### 4. Use Case Diagram (`use_case_diagram.puml`)
**Purpose**: Shows user interactions and workflows
- **Actor**: Hockey Coach/Analyst
- **Use cases**: Event marking, timeline review, export, project management
- **Relationships**: Include/extend relationships showing dependencies

## File Format

All diagrams are created using **PlantUML** syntax (.puml files):
- **Version controllable**: Text-based format that works with Git
- **Editable**: Can be modified as code evolves
- **Portable**: Can be rendered to PNG, SVG, PDF, etc.

## How to View Diagrams

### Option 1: Online PlantUML Server
1. Copy the content of any `.puml` file
2. Paste into [PlantUML Online Server](https://www.plantuml.com/plantuml/uml/)
3. View the rendered diagram

### Option 2: VS Code Extension
1. Install "PlantUML" extension in VS Code
2. Open any `.puml` file
3. Use `Alt+D` to preview diagram

### Option 3: Command Line
```bash
# Install plantuml
# Then convert to PNG
plantuml state_machine_diagram.puml
```

## How to Edit Diagrams

1. **Update source code**: When the codebase changes, update the corresponding diagram
2. **Add new diagrams**: Create new `.puml` files for additional views
3. **Validate changes**: Render diagrams to ensure they remain readable

## Integration with Documentation

These diagrams complement the textual descriptions in:
- `README_PROFESSIONAL.md` - Architecture overview
- `README.md` - High-level descriptions
- Source code comments - Implementation details

## Maintenance Guidelines

- **Keep diagrams in sync**: Update diagrams when architecture changes
- **Use consistent naming**: Follow existing naming conventions
- **Document changes**: Update this README when adding new diagrams
- **Version control**: Commit diagram changes with related code changes

## Benefits of Formal UML Diagrams

✅ **Visual understanding**: Complex relationships are easier to grasp visually
✅ **Architecture documentation**: Formal representation of system design
✅ **Communication**: Better discussion tool for development teams
✅ **Onboarding**: Faster understanding for new developers
✅ **Maintenance**: Clearer view of dependencies and responsibilities
