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

### 5. Context Class Diagram (`context_class_diagram.puml`)
**Purpose**: High-level system architecture overview
- **Components**: MainWindow, VideoController, VideoProcessor, ProjectManager
- **Focus**: Main system components and their high-level relationships
- **Scope**: Core system architecture without implementation details

### 6. Extended State Machine Diagram (`extended_state_machine_diagram.puml`)
**Purpose**: Comprehensive state modeling for markers and video playback
- **States**: Video playback (Stopped/Playing/Paused/Frame-by-frame)
- **States**: Marker lifecycle (Created/Visible/Selected/Edited/Deleted)
- **Coordination**: Interplay between video states and marker operations

### 7. Activity Diagram (`activity_diagram.puml`)
**Purpose**: Business process modeling for event marking workflow
- **Process**: Complete event marking scenario during video playback
- **Modes**: Dynamic and Fixed Length recording modes
- **Signals**: Qt signal emissions and UI updates

### 8. Package Diagram (`package_diagram.puml`)
**Purpose**: 4-layer architectural structure representation
- **Layers**: Presentation, Application Logic, Domain Logic, Data Model
- **Dependencies**: Layer interaction patterns and direction
- **Principles**: Separation of concerns and architectural guidelines

### 9. Deployment Diagram (`deployment_diagram.puml`)
**Purpose**: System deployment and runtime environment
- **Target**: Desktop application deployment on Windows/Linux/macOS
- **Components**: Application modules and external dependencies
- **Requirements**: System requirements and deployment options

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
- `diagrams_description.md` - Comprehensive diagram explanations

## Detailed Documentation

For comprehensive descriptions of all diagrams, including explanations of elements, relationships, and business logic, see **[diagrams_description.md](diagrams_description.md)**.

This document provides:
- Detailed explanation of each diagram's purpose and scope
- Description of all elements, actors, and components
- Analysis of relationships and interactions
- Business logic explanations and workflows
- Technical implementation details
- Architectural principles and patterns

## Maintenance Guidelines

- **Keep diagrams in sync**: Update diagrams when architecture changes
- **Use consistent naming**: Follow existing naming conventions
- **Document changes**: Update this README and `diagrams_description.md` when adding new diagrams
- **Version control**: Commit diagram changes with related code changes

## Benefits of Formal UML Diagrams

✅ **Visual understanding**: Complex relationships are easier to grasp visually
✅ **Architecture documentation**: Formal representation of system design
✅ **Communication**: Better discussion tool for development teams
✅ **Onboarding**: Faster understanding for new developers
✅ **Maintenance**: Clearer view of dependencies and responsibilities
