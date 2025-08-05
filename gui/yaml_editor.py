"""
YAML Editor Widget
Advanced YAML editor with syntax highlighting, validation, and ESPHome-specific features.
"""

import logging
import yaml
from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton,
    QLabel, QMessageBox, QSplitter, QTreeWidget, QTreeWidgetItem,
    QGroupBox, QCheckBox, QComboBox, QSpinBox, QFormLayout,
    QFrame, QScrollArea, QTabWidget, QFileDialog, QLineEdit,
    QToolBar, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QRegularExpression
from PyQt6.QtGui import (
    QFont, QFontMetrics, QPalette, QColor, QTextCharFormat,
    QSyntaxHighlighter, QTextDocument, QAction, QKeySequence
)

from utils.validation import ConfigValidator

class YAMLSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for YAML files."""
    
    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self.setup_highlighting_rules()
    
    def setup_highlighting_rules(self):
        """Set up syntax highlighting rules for YAML."""
        self.highlighting_rules = []
        
        # YAML key format
        key_format = QTextCharFormat()
        key_format.setForeground(QColor(0, 0, 139))  # Dark blue
        key_format.setFontWeight(QFont.Weight.Bold)
        key_pattern = QRegularExpression(r"^[^\s#][^:]*(?=:)")
        self.highlighting_rules.append((key_pattern, key_format))
        
        # String values (quoted)
        string_format = QTextCharFormat()
        string_format.setForeground(QColor(0, 128, 0))  # Green
        string_pattern = QRegularExpression(r'"[^"]*"')
        self.highlighting_rules.append((string_pattern, string_format))
        
        single_string_pattern = QRegularExpression(r"'[^']*'")
        self.highlighting_rules.append((single_string_pattern, string_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor(255, 140, 0))  # Orange
        number_pattern = QRegularExpression(r"\b\d+\.?\d*\b")
        self.highlighting_rules.append((number_pattern, number_format))
        
        # Boolean values
        bool_format = QTextCharFormat()
        bool_format.setForeground(QColor(128, 0, 128))  # Purple
        bool_pattern = QRegularExpression(r"\b(true|false|yes|no|on|off)\b")
        self.highlighting_rules.append((bool_pattern, bool_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor(128, 128, 128))  # Gray
        comment_format.setFontItalic(True)
        comment_pattern = QRegularExpression(r"#.*")
        self.highlighting_rules.append((comment_pattern, comment_format))
        
        # YAML special characters
        special_format = QTextCharFormat()
        special_format.setForeground(QColor(255, 0, 0))  # Red
        special_pattern = QRegularExpression(r"[:\[\]{}|>-]")
        self.highlighting_rules.append((special_pattern, special_format))
        
        # ESPHome specific keywords
        esphome_format = QTextCharFormat()
        esphome_format.setForeground(QColor(0, 0, 255))  # Blue
        esphome_format.setFontWeight(QFont.Weight.Bold)
        esphome_keywords = [
            "esphome", "wifi", "api", "ota", "logger", "web_server",
            "sensor", "binary_sensor", "switch", "light", "climate",
            "cover", "fan", "text_sensor", "number", "select", "button"
        ]
        esphome_pattern = QRegularExpression(f"\\b({'|'.join(esphome_keywords)})\\b")
        self.highlighting_rules.append((esphome_pattern, esphome_format))
    
    def highlightBlock(self, text: str):
        """Apply syntax highlighting to a block of text."""
        for pattern, format_obj in self.highlighting_rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format_obj)

class YAMLValidationWidget(QWidget):
    """Widget to display YAML validation results."""
    
    def __init__(self):
        super().__init__()
        self.validator = ConfigValidator()
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the validation display UI."""
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("No validation performed")
        self.status_label.setStyleSheet("padding: 5px; border: 1px solid #ccc;")
        layout.addWidget(self.status_label)
        
        # Error details
        self.error_text = QTextEdit()
        self.error_text.setMaximumHeight(100)
        self.error_text.setReadOnly(True)
        self.error_text.hide()
        layout.addWidget(self.error_text)
    
    def update_validation(self, yaml_content: str):
        """Update validation display with YAML content."""
        try:
            # Parse YAML
            parsed = yaml.safe_load(yaml_content)
            if parsed is None:
                self.show_warning("YAML is empty")
                return
            
            # Basic structure validation
            errors = []
            warnings = []
            
            # Check for required ESPHome sections
            required_sections = ['esphome']
            for section in required_sections:
                if section not in parsed:
                    errors.append(f"Missing required section: {section}")
            
            # Validate esphome section
            if 'esphome' in parsed:
                esphome_config = parsed['esphome']
                if not isinstance(esphome_config, dict):
                    errors.append("esphome section must be a dictionary")
                else:
                    required_esphome_keys = ['name', 'platform', 'board']
                    for key in required_esphome_keys:
                        if key not in esphome_config:
                            warnings.append(f"Missing recommended esphome key: {key}")
            
            # Show results
            if errors:
                self.show_error(f"Validation errors:\n" + "\n".join(errors))
            elif warnings:
                self.show_warning(f"Validation warnings:\n" + "\n".join(warnings))
            else:
                self.show_success("YAML is valid")
            
        except yaml.YAMLError as e:
            self.show_error(f"YAML syntax error:\n{str(e)}")
        except Exception as e:
            self.show_error(f"Validation error:\n{str(e)}")
    
    def show_success(self, message: str):
        """Show success status."""
        self.status_label.setText(f"✓ {message}")
        self.status_label.setStyleSheet("padding: 5px; border: 1px solid #4CAF50; background-color: #E8F5E8; color: #2E7D32;")
        self.error_text.hide()
    
    def show_warning(self, message: str):
        """Show warning status."""
        self.status_label.setText(f"⚠ Warning")
        self.status_label.setStyleSheet("padding: 5px; border: 1px solid #FF9800; background-color: #FFF3E0; color: #E65100;")
        self.error_text.setPlainText(message)
        self.error_text.show()
    
    def show_error(self, message: str):
        """Show error status."""
        self.status_label.setText(f"✗ Validation Error")
        self.status_label.setStyleSheet("padding: 5px; border: 1px solid #F44336; background-color: #FFEBEE; color: #C62828;")
        self.error_text.setPlainText(message)
        self.error_text.show()

class YAMLEditor(QWidget):
    """Advanced YAML editor widget with syntax highlighting and validation."""
    
    content_changed = pyqtSignal()
    validation_updated = pyqtSignal(bool)  # is_valid
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.auto_validate = True
        self.validation_timer = QTimer()
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self.validate_content)
        
        self.setup_ui()
        self.setup_connections()
    
    def setup_ui(self):
        """Set up the editor UI."""
        layout = QVBoxLayout(self)
        
        # Create text editor first (needed for toolbar connections)
        self.text_edit = QTextEdit()
        self.setup_editor()
        
        # Toolbar
        self.create_toolbar(layout)
        
        # Main content area
        splitter = QSplitter(Qt.Orientation.Vertical)
        layout.addWidget(splitter)
        
        # Editor area
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        
        # Add the already created text editor
        editor_layout.addWidget(self.text_edit)
        
        splitter.addWidget(editor_widget)
        
        # Validation area
        validation_group = QGroupBox("Validation")
        validation_layout = QVBoxLayout(validation_group)
        
        self.validation_widget = YAMLValidationWidget()
        validation_layout.addWidget(self.validation_widget)
        
        splitter.addWidget(validation_group)
        
        # Set splitter sizes
        splitter.setSizes([400, 150])
        
        # Status bar
        self.status_bar = QStatusBar()
        layout.addWidget(self.status_bar)
        
        self.update_status("Ready")
    
    def create_toolbar(self, layout: QVBoxLayout):
        """Create the editor toolbar."""
        toolbar = QToolBar()
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        # File operations
        new_action = QAction("New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Edit operations
        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.text_edit.undo)
        toolbar.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.text_edit.redo)
        toolbar.addAction(redo_action)
        
        toolbar.addSeparator()
        
        # Validation
        validate_action = QAction("Validate", self)
        validate_action.triggered.connect(self.validate_content)
        toolbar.addAction(validate_action)
        
        # Auto-validate checkbox
        self.auto_validate_cb = QCheckBox("Auto-validate")
        self.auto_validate_cb.setChecked(self.auto_validate)
        self.auto_validate_cb.toggled.connect(self.toggle_auto_validate)
        toolbar.addWidget(self.auto_validate_cb)
        
        toolbar.addSeparator()
        
        # Format operations
        format_action = QAction("Format", self)
        format_action.triggered.connect(self.format_yaml)
        toolbar.addAction(format_action)
        
        layout.addWidget(toolbar)
    
    def setup_editor(self):
        """Set up the text editor with syntax highlighting."""
        # Font
        font = QFont("Consolas", 10)
        if not font.exactMatch():
            font = QFont("Courier New", 10)
        self.text_edit.setFont(font)
        
        # Tab settings
        tab_width = 2
        metrics = QFontMetrics(font)
        self.text_edit.setTabStopDistance(tab_width * metrics.horizontalAdvance(' '))
        
        # Syntax highlighting
        self.highlighter = YAMLSyntaxHighlighter(self.text_edit.document())
        
        # Editor settings
        self.text_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.text_edit.setAcceptRichText(False)
        
        # Default content
        self.text_edit.setPlainText(self.get_default_yaml())
    
    def setup_connections(self):
        """Set up signal connections."""
        self.text_edit.textChanged.connect(self.on_text_changed)
    
    def get_default_yaml(self) -> str:
        """Get default YAML template."""
        return """# ESPHome Configuration
esphome:
  name: my_device
  platform: ESP32
  board: nodemcu-32s

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password

logger:

api:
  password: !secret api_password

ota:
  password: !secret ota_password

# Add your components below
"""
    
    def on_text_changed(self):
        """Handle text changes."""
        self.content_changed.emit()
        
        if self.auto_validate:
            # Restart validation timer
            self.validation_timer.stop()
            self.validation_timer.start(1000)  # Validate after 1 second of no changes
        
        self.update_status("Modified")
    
    def toggle_auto_validate(self, enabled: bool):
        """Toggle auto-validation."""
        self.auto_validate = enabled
        if enabled:
            self.validate_content()
    
    def validate_content(self):
        """Validate the current YAML content."""
        content = self.text_edit.toPlainText()
        if content.strip():
            self.validation_widget.update_validation(content)
            self.update_status("Validated")
        else:
            self.validation_widget.show_warning("YAML content is empty")
    
    def format_yaml(self):
        """Format the current YAML content."""
        try:
            content = self.text_edit.toPlainText()
            if not content.strip():
                return
            
            # Parse and reformat
            parsed = yaml.safe_load(content)
            if parsed is not None:
                formatted = yaml.dump(
                    parsed,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                    width=120
                )
                
                # Preserve cursor position approximately
                cursor = self.text_edit.textCursor()
                position = cursor.position()
                
                self.text_edit.setPlainText(formatted)
                
                # Restore cursor position
                cursor.setPosition(min(position, len(formatted)))
                self.text_edit.setTextCursor(cursor)
                
                self.update_status("Formatted")
            
        except yaml.YAMLError as e:
            QMessageBox.warning(self, "Format Error", f"Cannot format invalid YAML:\n{str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "Format Error", f"Error formatting YAML:\n{str(e)}")
    
    def new_file(self):
        """Create a new YAML file."""
        if self.text_edit.document().isModified():
            reply = QMessageBox.question(
                self, "New File",
                "Current content has unsaved changes. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.text_edit.setPlainText(self.get_default_yaml())
        self.text_edit.document().setModified(False)
        self.update_status("New file")
    
    def open_file(self):
        """Open a YAML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open YAML File", "",
            "YAML files (*.yaml *.yml);;All files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                self.text_edit.setPlainText(content)
                self.text_edit.document().setModified(False)
                self.update_status(f"Opened: {file_path}")
                
                if self.auto_validate:
                    self.validate_content()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Open Error",
                    f"Failed to open file:\n{str(e)}"
                )
    
    def save_file(self):
        """Save the current content to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save YAML File", "config.yaml",
            "YAML files (*.yaml *.yml);;All files (*)"
        )
        
        if file_path:
            try:
                content = self.text_edit.toPlainText()
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.text_edit.document().setModified(False)
                self.update_status(f"Saved: {file_path}")
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Save Error",
                    f"Failed to save file:\n{str(e)}"
                )
    
    def set_content(self, content: str):
        """Set the editor content."""
        self.text_edit.setPlainText(content)
        self.text_edit.document().setModified(False)
        
        if self.auto_validate:
            self.validate_content()
    
    def get_content(self) -> str:
        """Get the current editor content."""
        return self.text_edit.toPlainText()
    
    def is_modified(self) -> bool:
        """Check if the content has been modified."""
        return self.text_edit.document().isModified()
    
    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_bar.showMessage(message)
        
        # Add document info
        content = self.text_edit.toPlainText()
        lines = content.count('\n') + 1 if content else 0
        chars = len(content)
        
        self.status_bar.showMessage(f"{message} | Lines: {lines} | Characters: {chars}")
    
    def find_and_replace(self):
        """Show find and replace dialog."""
        # This could be implemented as a separate dialog
        # For now, we'll use the built-in find functionality
        pass
    
    def insert_template(self, template_name: str):
        """Insert a predefined template."""
        templates = {
            'sensor': """sensor:
  - platform: dht
    pin: GPIO2
    temperature:
      name: "Temperature"
    humidity:
      name: "Humidity"
    update_interval: 60s
""",
            'switch': """switch:
  - platform: gpio
    pin: GPIO4
    name: "Relay Switch"
""",
            'light': """light:
  - platform: binary
    name: "LED Light"
    output: light_output

output:
  - platform: gpio
    id: light_output
    pin: GPIO5
""",
            'binary_sensor': """binary_sensor:
  - platform: gpio
    pin:
      number: GPIO0
      mode: INPUT_PULLUP
      inverted: True
    name: "Button"
"""
        }
        
        if template_name in templates:
            cursor = self.text_edit.textCursor()
            cursor.insertText(templates[template_name])
            
            if self.auto_validate:
                self.validate_content()
