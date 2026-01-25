"""
Dialog for managing custom event types with add/edit/delete functionality.
"""

from typing import Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QInputDialog, QColorDialog, QFormLayout,
    QLineEdit, QLabel, QGroupBox
)
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtCore import Qt

from hockey_editor.utils.custom_events import CustomEventManager, CustomEventType, get_custom_event_manager


class CustomEventDialog(QDialog):
    """Dialog for adding/editing custom event types."""

    def __init__(self, parent=None, event: Optional[CustomEventType] = None):
        """Initialize event dialog.
        
        Args:
            parent: Parent widget
            event: If provided, dialog is in edit mode for this event
        """
        super().__init__(parent)
        self._event = event  # Исправлено имя атрибута
        self.is_edit_mode = event is not None
        self.selected_color = QColor(event.color) if event else QColor('#CCCCCC')
        
        self.setWindowTitle('Edit Event Type' if self.is_edit_mode else 'Add Event Type')
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self._create_ui()
        self._load_data()
    
    def _create_ui(self) -> None:
        """Create dialog UI."""
        layout = QVBoxLayout()
        
        # Form layout for fields
        form = QFormLayout()
        
        # Name field
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('e.g., Attack, Goal, Penalty')
        form.addRow('Event Name:', self.name_input)
        
        # Description field
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText('e.g., Offensive play')
        form.addRow('Description:', self.desc_input)
        
        # Shortcut field
        self.shortcut_input = QLineEdit()
        self.shortcut_input.setPlaceholderText('e.g., A, Ctrl+X, Shift+1')
        form.addRow('Shortcut:', self.shortcut_input)
        
        layout.addLayout(form)
        
        # Color picker
        color_group = QGroupBox('Color')
        color_layout = QHBoxLayout()
        
        self.color_label = QLabel()
        self.color_label.setFixedSize(40, 40)
        self.color_label.setStyleSheet('border: 1px solid #333;')
        self._update_color_label()
        
        color_btn = QPushButton('Choose Color...')
        color_btn.clicked.connect(self._on_choose_color)
        
        color_layout.addWidget(self.color_label)
        color_layout.addWidget(color_btn)
        color_layout.addStretch()
        color_group.setLayout(color_layout)
        
        layout.addWidget(color_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton('OK')
        ok_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton('Cancel')
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_data(self) -> None:
        """Load existing event data if in edit mode."""
        if self.is_edit_mode and self._event:
            self.name_input.setText(self._event.name)
            self.desc_input.setText(self._event.description)
            self.shortcut_input.setText(self._event.shortcut)
            self.selected_color = QColor(self._event.color)
            self._update_color_label()
            # Disable name editing in edit mode
            self.name_input.setReadOnly(True)
    
    def _on_choose_color(self) -> None:
        """Open color picker dialog."""
        color = QColorDialog.getColor(self.selected_color, self, 'Choose Event Color')
        if color.isValid():
            self.selected_color = color
            self._update_color_label()
    
    def _update_color_label(self) -> None:
        """Update color preview label."""
        self.color_label.setStyleSheet(
            f'background-color: {self.selected_color.name()}; border: 1px solid #333;'
        )
    
    def get_event(self) -> CustomEventType:
        """Get the resulting event object."""
        return CustomEventType(
            name=self.name_input.text().strip(),
            color=self.selected_color.name(),
            shortcut=self.shortcut_input.text().strip(),
            description=self.desc_input.text().strip()
        )


class CustomEventManagerDialog(QDialog):
    """Main dialog for managing all custom event types."""
    
    def __init__(self, parent=None):
        """Initialize manager dialog."""
        super().__init__(parent)
        self.manager: CustomEventManager = get_custom_event_manager()
        
        self.setWindowTitle('Manage Event Types')
        self.setModal(True)
        self.setMinimumSize(500, 400)
        
        self._create_ui()
        self._refresh_list()
    
    def _create_ui(self) -> None:
        """Create dialog UI."""
        layout = QVBoxLayout()
        
        # Event list
        list_label = QLabel('Event Types:')
        layout.addWidget(list_label)
        
        self.event_list = QListWidget()
        self.event_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.event_list.itemDoubleClicked.connect(self._on_edit_event)
        layout.addWidget(self.event_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton('➕ Add Event')
        self.add_btn.clicked.connect(self._on_add_event)
        button_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton('✏️ Edit')
        self.edit_btn.clicked.connect(self._on_edit_event)
        self.edit_btn.setEnabled(False)
        button_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton('🗑️ Delete')
        self.delete_btn.clicked.connect(self._on_delete_event)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)
        
        button_layout.addStretch()
        
        reset_btn = QPushButton('↺ Reset to Defaults')
        reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(reset_btn)
        
        layout.addLayout(button_layout)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        
        close_btn = QPushButton('Close')
        close_btn.clicked.connect(self.accept)
        
        dialog_buttons.addStretch()
        dialog_buttons.addWidget(close_btn)
        
        layout.addLayout(dialog_buttons)
        
        self.setLayout(layout)
    
    def _refresh_list(self) -> None:
        """Refresh event list display."""
        self.event_list.clear()
        
        for event in self.manager.get_all_events():
            # Create list item with color preview and name
            item = QListWidgetItem()
            
            # Create colored pixmap
            pixmap = QPixmap(20, 20)
            pixmap.fill(event.get_qcolor())
            icon = QIcon(pixmap)
            
            # Format display text
            text = f"{event.name}"
            if event.shortcut:
                text += f" [{event.shortcut}]"
            if event.description:
                text += f" - {event.description}"
            
            item.setIcon(icon)
            item.setText(text)
            item.setData(Qt.UserRole, event.name)  # Store event name for lookup
            
            self.event_list.addItem(item)
    
    def _on_selection_changed(self) -> None:
        """Handle event selection change."""
        selected = self.event_list.selectedItems()
        has_selection = len(selected) > 0
        
        self.edit_btn.setEnabled(has_selection)
        
        # Can only delete non-default events
        if has_selection:
            event_name = selected[0].data(Qt.UserRole)
            event = self.manager.get_event(event_name)
            
            # Проверка на None
            if event is None:
                self.delete_btn.setEnabled(False)
                return
            
            is_default = event.name in {e.name for e in self.manager.DEFAULT_EVENTS}
            self.delete_btn.setEnabled(has_selection and not is_default)
        else:
            self.delete_btn.setEnabled(False)
    
    def _on_add_event(self) -> None:
        """Handle add event button."""
        dialog = CustomEventDialog(self)
        if dialog.exec() == QDialog.Accepted:
            event = dialog.get_event()
            # Validate
            if not event.name:
                QMessageBox.warning(self, 'Invalid', 'Event name cannot be empty')
                return

            if not self.manager.add_event(event):
                QMessageBox.warning(self, 'Error', f'Event "{event.name}" already exists or has invalid color')
                return

            self._refresh_list()
            QMessageBox.information(self, 'Success', f'Event "{event.name}" added')
    
    def _on_edit_event(self) -> None:
        """Handle edit event button."""
        selected = self.event_list.selectedItems()
        if not selected:
            return
        
        event_name = selected[0].data(Qt.UserRole)
        event = self.manager.get_event(event_name)
        if not event:
            return
        
        dialog = CustomEventDialog(self, event)
        if dialog.exec() == QDialog.Accepted:
            new_event = dialog.get_event()
            if not self.manager.update_event(event_name, new_event):
                QMessageBox.warning(self, 'Error', f'Failed to update event')
                return
            
            self._refresh_list()
            QMessageBox.information(self, 'Success', 'Event updated')
    
    def _on_delete_event(self) -> None:
        """Handle delete event button."""
        selected = self.event_list.selectedItems()
        if not selected:
            return
        
        event_name = selected[0].data(Qt.UserRole)
        
        reply = QMessageBox.question(
            self,
            'Confirm Delete',
            f'Delete event "{event_name}"?\n\nThis cannot be undone.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.manager.delete_event(event_name):
                self._refresh_list()
                QMessageBox.information(self, 'Success', f'Event "{event_name}" deleted')
            else:
                QMessageBox.warning(self, 'Error', f'Cannot delete default event "{event_name}"')
    
    def _on_reset(self) -> None:
        """Handle reset to defaults button."""
        reply = QMessageBox.question(
            self,
            'Confirm Reset',
            'Reset all events to defaults?\n\nThis will remove all custom events.',
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.manager.reset_to_defaults()
            self._refresh_list()
            QMessageBox.information(self, 'Success', 'Events reset to defaults')
