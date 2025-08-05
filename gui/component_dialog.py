"""
Component Configuration Dialog
Dialog for configuring ESPHome component variables and settings.
"""

import logging
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, 
    QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox, QPushButton, QDialogButtonBox, QGroupBox,
    QScrollArea, QWidget, QMessageBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from models.component import ESPHomeComponent
from models.config_variable import ConfigVariable
from utils.validation import ConfigValidator

class ConfigVariableWidget(QWidget):
    """Widget for editing a single configuration variable."""
    
    value_changed = pyqtSignal(str, object)  # variable_name, new_value
    
    def __init__(self, config_var: ConfigVariable, parent=None):
        super().__init__(parent)
        self.config_var = config_var
        self.validator = ConfigValidator()
        self.setup_ui()
        self.load_current_value()
    
    def setup_ui(self):
        """Set up the UI for this configuration variable."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        
        # Variable name label
        name_label = QLabel(self.config_var.name)
        name_label.setMinimumWidth(120)
        if self.config_var.is_required:
            name_label.setText(f"{self.config_var.name} *")
            font = name_label.font()
            font.setBold(True)
            name_label.setFont(font)
        layout.addWidget(name_label)
        
        # Create appropriate input widget based on data type
        self.input_widget = self.create_input_widget()
        layout.addWidget(self.input_widget, 1)
        
        # Validation indicator
        self.validation_label = QLabel()
        self.validation_label.setFixedWidth(20)
        layout.addWidget(self.validation_label)
        
        # Help button/tooltip
        if self.config_var.description:
            self.setToolTip(self.config_var.description)
    
    def create_input_widget(self) -> QWidget:
        """Create the appropriate input widget for the variable type."""
        data_type = self.config_var.data_type.lower()
        
        if data_type == 'bool' or data_type == 'boolean':
            widget = QCheckBox()
            widget.stateChanged.connect(self.on_bool_changed)
            return widget
        
        elif data_type == 'int' or data_type == 'integer':
            widget = QSpinBox()
            widget.setRange(-999999, 999999)
            widget.valueChanged.connect(self.on_int_changed)
            return widget
        
        elif data_type == 'float' or data_type == 'double':
            widget = QDoubleSpinBox()
            widget.setRange(-999999.0, 999999.0)
            widget.setDecimals(3)
            widget.valueChanged.connect(self.on_float_changed)
            return widget
        
        elif data_type in ['choice', 'select', 'enum']:
            widget = QComboBox()
            widget.setEditable(True)
            # Add common choices based on variable name
            self.add_common_choices(widget)
            widget.currentTextChanged.connect(self.on_text_changed)
            return widget
        
        elif data_type in ['text', 'multiline']:
            widget = QTextEdit()
            widget.setMaximumHeight(60)
            widget.textChanged.connect(self.on_multiline_changed)
            return widget
        
        else:  # Default to string/text input
            widget = QLineEdit()
            widget.textChanged.connect(self.on_text_changed)
            return widget
    
    def add_common_choices(self, combo: QComboBox):
        """Add common choices to combo box based on variable name."""
        var_name = self.config_var.name.lower()
        
        if 'pin' in var_name:
            # GPIO pins for ESP32/ESP8266
            pins = ['GPIO0', 'GPIO1', 'GPIO2', 'GPIO3', 'GPIO4', 'GPIO5',
                   'GPIO12', 'GPIO13', 'GPIO14', 'GPIO15', 'GPIO16', 'GPIO17']
            combo.addItems(pins)
        elif 'platform' in var_name:
            platforms = ['ESP32', 'ESP8266', 'ESP32-S2', 'ESP32-S3', 'ESP32-C3']
            combo.addItems(platforms)
        elif 'unit' in var_name:
            units = ['°C', '°F', '%', 'V', 'A', 'W', 'Hz', 'ms', 's']
            combo.addItems(units)
        elif var_name in ['accuracy_decimals', 'decimals']:
            combo.addItems(['0', '1', '2', '3', '4'])
    
    def load_current_value(self):
        """Load the current value into the input widget."""
        current_value = self.config_var.get_effective_value()
        
        if isinstance(self.input_widget, QCheckBox):
            self.input_widget.setChecked(bool(current_value) if current_value is not None else False)
        elif isinstance(self.input_widget, QSpinBox):
            self.input_widget.setValue(int(current_value) if current_value is not None else 0)
        elif isinstance(self.input_widget, QDoubleSpinBox):
            self.input_widget.setValue(float(current_value) if current_value is not None else 0.0)
        elif isinstance(self.input_widget, QComboBox):
            if current_value is not None:
                self.input_widget.setCurrentText(str(current_value))
        elif isinstance(self.input_widget, QTextEdit):
            self.input_widget.setPlainText(str(current_value) if current_value is not None else '')
        elif isinstance(self.input_widget, QLineEdit):
            self.input_widget.setText(str(current_value) if current_value is not None else '')
    
    def get_current_value(self) -> Any:
        """Get the current value from the input widget."""
        if isinstance(self.input_widget, QCheckBox):
            return self.input_widget.isChecked()
        elif isinstance(self.input_widget, QSpinBox):
            return self.input_widget.value()
        elif isinstance(self.input_widget, QDoubleSpinBox):
            return self.input_widget.value()
        elif isinstance(self.input_widget, QComboBox):
            text = self.input_widget.currentText()
            return text if text else None
        elif isinstance(self.input_widget, QTextEdit):
            text = self.input_widget.toPlainText()
            return text if text else None
        elif isinstance(self.input_widget, QLineEdit):
            text = self.input_widget.text()
            return text if text else None
        return None
    
    def validate_current_value(self) -> tuple[bool, Optional[str]]:
        """Validate the current value."""
        current_value = self.get_current_value()
        
        # Check if required value is missing
        if self.config_var.is_required and (current_value is None or current_value == ''):
            return False, "Required field cannot be empty"
        
        # Skip validation for empty optional fields
        if current_value is None or current_value == '':
            return True, None
        
        # Use validator to check the value
        return self.validator.validate_by_type(current_value, self.config_var.data_type)
    
    def update_validation_display(self):
        """Update the validation indicator."""
        is_valid, error_msg = self.validate_current_value()
        
        if is_valid:
            self.validation_label.setText("✓")
            self.validation_label.setStyleSheet("color: green; font-weight: bold;")
            self.validation_label.setToolTip("Valid")
        else:
            self.validation_label.setText("✗")
            self.validation_label.setStyleSheet("color: red; font-weight: bold;")
            self.validation_label.setToolTip(error_msg or "Invalid value")
    
    def on_bool_changed(self, state):
        """Handle boolean value change."""
        value = state == Qt.CheckState.Checked.value
        self.config_var.set_value(value)
        self.value_changed.emit(self.config_var.name, value)
        self.update_validation_display()
    
    def on_int_changed(self, value):
        """Handle integer value change."""
        self.config_var.set_value(value)
        self.value_changed.emit(self.config_var.name, value)
        self.update_validation_display()
    
    def on_float_changed(self, value):
        """Handle float value change."""
        self.config_var.set_value(value)
        self.value_changed.emit(self.config_var.name, value)
        self.update_validation_display()
    
    def on_text_changed(self, text):
        """Handle text value change."""
        value = text if text else None
        self.config_var.set_value(value)
        self.value_changed.emit(self.config_var.name, value)
        self.update_validation_display()
    
    def on_multiline_changed(self):
        """Handle multiline text change."""
        text = self.input_widget.toPlainText()
        value = text if text else None
        self.config_var.set_value(value)
        self.value_changed.emit(self.config_var.name, value)
        self.update_validation_display()

class ComponentConfigDialog(QDialog):
    """Dialog for configuring an ESPHome component."""
    
    def __init__(self, component: ESPHomeComponent, parent=None):
        super().__init__(parent)
        self.component = component
        self.logger = logging.getLogger(__name__)
        self.config_widgets: Dict[str, ConfigVariableWidget] = {}
        self.setup_ui()
        self.load_component_data()
    
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Configure {self.component.name}")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Component info header
        self.create_header(layout)
        
        # Tab widget for different configuration sections
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Configuration tab
        self.config_tab = self.create_config_tab()
        self.tab_widget.addTab(self.config_tab, "Configuration")
        
        # Properties tab
        self.properties_tab = self.create_properties_tab()
        self.tab_widget.addTab(self.properties_tab, "Properties")
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Apply
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply_changes)
        layout.addWidget(button_box)
        
        self.button_box = button_box
    
    def create_header(self, layout: QVBoxLayout):
        """Create the component information header."""
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        header_layout = QVBoxLayout(header_frame)
        
        # Component name
        name_label = QLabel(self.component.name)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        name_label.setFont(font)
        header_layout.addWidget(name_label)
        
        # Component type and description
        type_label = QLabel(f"Type: {self.component.component_type}")
        header_layout.addWidget(type_label)
        
        if self.component.description:
            desc_label = QLabel(self.component.description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; font-style: italic;")
            header_layout.addWidget(desc_label)
        
        # Platforms
        if self.component.platforms:
            platforms_label = QLabel(f"Platforms: {', '.join(self.component.platforms)}")
            header_layout.addWidget(platforms_label)
        
        layout.addWidget(header_frame)
    
    def create_config_tab(self) -> QWidget:
        """Create the configuration variables tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        if not self.component.config_vars:
            # No configuration variables
            no_config_label = QLabel("This component has no configuration variables.")
            no_config_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_config_label.setStyleSheet("color: #666; font-style: italic; padding: 20px;")
            layout.addWidget(no_config_label)
            return tab
        
        # Create scroll area for config variables
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Group variables by category (required vs optional)
        required_vars = [var for var in self.component.config_vars if var.is_required]
        optional_vars = [var for var in self.component.config_vars if not var.is_required]
        
        # Required variables section
        if required_vars:
            required_group = QGroupBox("Required Configuration")
            required_layout = QVBoxLayout(required_group)
            
            for var in required_vars:
                widget = ConfigVariableWidget(var)
                widget.value_changed.connect(self.on_variable_changed)
                self.config_widgets[var.name] = widget
                required_layout.addWidget(widget)
            
            scroll_layout.addWidget(required_group)
        
        # Optional variables section
        if optional_vars:
            optional_group = QGroupBox("Optional Configuration")
            optional_layout = QVBoxLayout(optional_group)
            
            for var in optional_vars:
                widget = ConfigVariableWidget(var)
                widget.value_changed.connect(self.on_variable_changed)
                self.config_widgets[var.name] = widget
                optional_layout.addWidget(widget)
            
            scroll_layout.addWidget(optional_group)
        
        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_widget)
        layout.addWidget(scroll_area)
        
        return tab
    
    def create_properties_tab(self) -> QWidget:
        """Create the component properties tab."""
        tab = QWidget()
        layout = QFormLayout(tab)
        
        # Component instance ID
        self.instance_id_edit = QLineEdit(self.component.instance_id)
        self.instance_id_edit.setReadOnly(True)
        layout.addRow("Instance ID:", self.instance_id_edit)
        
        # Position
        self.x_spin = QSpinBox()
        self.x_spin.setRange(0, 9999)
        self.x_spin.setValue(self.component.x_position)
        layout.addRow("X Position:", self.x_spin)
        
        self.y_spin = QSpinBox()
        self.y_spin.setRange(0, 9999)
        self.y_spin.setValue(self.component.y_position)
        layout.addRow("Y Position:", self.y_spin)
        
        # Size
        self.width_spin = QSpinBox()
        self.width_spin.setRange(50, 500)
        self.width_spin.setValue(self.component.width)
        layout.addRow("Width:", self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 500)
        self.height_spin.setValue(self.component.height)
        layout.addRow("Height:", self.height_spin)
        
        # URL (if available)
        if self.component.url:
            url_edit = QLineEdit(self.component.url)
            url_edit.setReadOnly(True)
            layout.addRow("Documentation:", url_edit)
        
        return tab
    
    def load_component_data(self):
        """Load current component data into the dialog."""
        # Update validation display for all config widgets
        for widget in self.config_widgets.values():
            widget.update_validation_display()
    
    def on_variable_changed(self, var_name: str, value: Any):
        """Handle configuration variable changes."""
        self.logger.debug(f"Variable changed: {var_name} = {value}")
        
        # Update validation for all widgets (in case of dependencies)
        for widget in self.config_widgets.values():
            widget.update_validation_display()
        
        # Update OK button state based on validation
        self.update_ok_button_state()
    
    def update_ok_button_state(self):
        """Enable/disable OK button based on validation state."""
        all_valid = True
        
        for widget in self.config_widgets.values():
            is_valid, _ = widget.validate_current_value()
            if not is_valid:
                all_valid = False
                break
        
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(all_valid)
        
        if not all_valid:
            ok_button.setToolTip("Fix validation errors before proceeding")
        else:
            ok_button.setToolTip("")
    
    def apply_changes(self):
        """Apply changes without closing the dialog."""
        if self.validate_all_inputs():
            self.save_changes()
            QMessageBox.information(self, "Changes Applied", "Configuration changes have been applied.")
    
    def validate_all_inputs(self) -> bool:
        """Validate all configuration inputs."""
        errors = []
        
        for var_name, widget in self.config_widgets.items():
            is_valid, error_msg = widget.validate_current_value()
            if not is_valid:
                errors.append(f"{var_name}: {error_msg}")
        
        if errors:
            error_text = "Validation errors:\n\n" + "\n".join(errors)
            QMessageBox.warning(self, "Validation Errors", error_text)
            return False
        
        return True
    
    def save_changes(self):
        """Save all changes to the component."""
        # Save configuration variables
        for var_name, widget in self.config_widgets.items():
            current_value = widget.get_current_value()
            var = self.component.get_config_var(var_name)
            if var:
                var.set_value(current_value)
        
        # Save properties
        self.component.set_position(self.x_spin.value(), self.y_spin.value())
        self.component.set_size(self.width_spin.value(), self.height_spin.value())
        
        self.logger.info(f"Saved configuration for component: {self.component.name}")
    
    def accept(self):
        """Accept the dialog and save changes."""
        if self.validate_all_inputs():
            self.save_changes()
            super().accept()
    
    def reject(self):
        """Reject the dialog without saving changes."""
        # Ask for confirmation if there are unsaved changes
        reply = QMessageBox.question(
            self, "Discard Changes",
            "Discard all changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            super().reject()
