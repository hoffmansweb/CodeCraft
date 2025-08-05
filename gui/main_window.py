"""
Main Window for ESPHome Component Manager
Central GUI application window with all major functionality.
"""

import logging
import os
from typing import List, Optional
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTextEdit, QTreeWidget, QTreeWidgetItem, QLabel, QMessageBox,
    QProgressBar, QTabWidget, QFormLayout, QLineEdit, QScrollArea,
    QInputDialog, QStatusBar, QToolBar, QSplitter, QFrame,
    QGroupBox, QComboBox, QSpinBox, QCheckBox, QFileDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QIcon, QFont

from database import DatabaseManager
from scraper import ESPHomeScraper, ScrapingThread
from models.component import ESPHomeComponent
from models.config_variable import ConfigVariable
from utils.yaml_generator import YAMLGenerator
from utils.validation import ConfigValidator
from gui.component_canvas import ComponentCanvas
from gui.component_dialog import ComponentConfigDialog
from gui.yaml_editor import YAMLEditor

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.db_manager = DatabaseManager()
        self.scraper = ESPHomeScraper(self.db_manager)
        self.yaml_generator = YAMLGenerator()
        self.validator = ConfigValidator()
        
        # Initialize UI components
        self.component_tree = None
        self.canvas = None
        self.log_display = None
        self.progress_bar = None
        self.status_label = None
        self.yaml_editor = None
        
        # State variables
        self.current_project_id = None
        self.current_project_name = "Untitled Project"
        self.is_scraping = False
        self.scraping_thread = None
        
        self.setup_ui()
        self.setup_connections()
        self.load_initial_data()
        
        self.logger.info("Main window initialized")
    
    def setup_ui(self):
        """Set up the user interface."""
        self.setWindowTitle("ESPHome Component Manager")
        self.setGeometry(100, 100, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel (components and controls)
        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)
        
        # Right panel (canvas and editor)
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        
        # Set splitter sizes
        main_splitter.setSizes([350, 1050])
        
        # Create menu bar and toolbars
        self.create_menu_bar()
        self.create_toolbar()
        self.create_status_bar()
    
    def create_left_panel(self) -> QWidget:
        """Create the left panel with component tree and controls."""
        panel = QFrame()
        panel.setFrameStyle(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(panel)
        
        # Scraping controls
        scraping_group = QGroupBox("Component Scraping")
        scraping_layout = QVBoxLayout(scraping_group)
        
        # Scraping buttons
        button_layout = QHBoxLayout()
        self.scrape_btn = QPushButton("Start Scraping")
        self.scrape_btn.clicked.connect(self.start_scraping)
        self.cancel_scrape_btn = QPushButton("Cancel")
        self.cancel_scrape_btn.clicked.connect(self.cancel_scraping)
        self.cancel_scrape_btn.setEnabled(False)
        
        button_layout.addWidget(self.scrape_btn)
        button_layout.addWidget(self.cancel_scrape_btn)
        scraping_layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        scraping_layout.addWidget(self.progress_bar)
        
        layout.addWidget(scraping_group)
        
        # Component search
        search_group = QGroupBox("Component Search")
        search_layout = QVBoxLayout(search_group)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search components...")
        self.search_input.textChanged.connect(self.filter_components)
        search_layout.addWidget(self.search_input)
        
        self.component_type_filter = QComboBox()
        self.component_type_filter.addItem("All Types")
        self.component_type_filter.currentTextChanged.connect(self.filter_components)
        search_layout.addWidget(QLabel("Filter by Type:"))
        search_layout.addWidget(self.component_type_filter)
        
        layout.addWidget(search_group)
        
        # Component tree
        components_group = QGroupBox("Available Components")
        components_layout = QVBoxLayout(components_group)
        
        self.component_tree = QTreeWidget()
        self.component_tree.setHeaderLabel("Components")
        self.component_tree.itemDoubleClicked.connect(self.add_component_to_canvas)
        components_layout.addWidget(self.component_tree)
        
        # Component info
        self.component_info = QTextEdit()
        self.component_info.setMaximumHeight(100)
        self.component_info.setPlaceholderText("Select a component to view details...")
        components_layout.addWidget(self.component_info)
        self.component_tree.itemSelectionChanged.connect(self.show_component_info)
        
        layout.addWidget(components_group)
        
        # Log display
        log_group = QGroupBox("Activity Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_display = QTextEdit()
        self.log_display.setMaximumHeight(150)
        self.log_display.setReadOnly(True)
        log_layout.addWidget(self.log_display)
        
        log_button_layout = QHBoxLayout()
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        export_log_btn = QPushButton("Export Log")
        export_log_btn.clicked.connect(self.export_log)
        log_button_layout.addWidget(clear_log_btn)
        log_button_layout.addWidget(export_log_btn)
        log_layout.addLayout(log_button_layout)
        
        layout.addWidget(log_group)
        
        return panel
    
    def create_right_panel(self) -> QWidget:
        """Create the right panel with canvas and YAML editor."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget for canvas and YAML editor
        self.tab_widget = QTabWidget()
        
        # Canvas tab
        canvas_widget = QWidget()
        canvas_layout = QVBoxLayout(canvas_widget)
        
        # Canvas controls
        canvas_controls = QHBoxLayout()
        
        self.project_name_input = QLineEdit(self.current_project_name)
        self.project_name_input.textChanged.connect(self.update_project_name)
        canvas_controls.addWidget(QLabel("Project:"))
        canvas_controls.addWidget(self.project_name_input)
        
        canvas_controls.addStretch()
        
        save_project_btn = QPushButton("Save Project")
        save_project_btn.clicked.connect(self.save_project)
        load_project_btn = QPushButton("Load Project")
        load_project_btn.clicked.connect(self.load_project)
        clear_canvas_btn = QPushButton("Clear Canvas")
        clear_canvas_btn.clicked.connect(self.clear_canvas)
        
        canvas_controls.addWidget(save_project_btn)
        canvas_controls.addWidget(load_project_btn)
        canvas_controls.addWidget(clear_canvas_btn)
        
        canvas_layout.addLayout(canvas_controls)
        
        # Component canvas
        self.canvas = ComponentCanvas()
        self.canvas.component_selected.connect(self.on_canvas_component_selected)
        self.canvas.component_double_clicked.connect(self.configure_canvas_component)
        canvas_layout.addWidget(self.canvas)
        
        self.tab_widget.addTab(canvas_widget, "Design Canvas")
        
        # YAML editor tab
        self.yaml_editor = YAMLEditor()
        self.tab_widget.addTab(self.yaml_editor, "YAML Configuration")
        
        layout.addWidget(self.tab_widget)
        
        # Generate YAML button
        generate_layout = QHBoxLayout()
        generate_layout.addStretch()
        
        generate_yaml_btn = QPushButton("Generate YAML")
        generate_yaml_btn.clicked.connect(self.generate_yaml_config)
        generate_layout.addWidget(generate_yaml_btn)
        
        save_yaml_btn = QPushButton("Save YAML")
        save_yaml_btn.clicked.connect(self.save_yaml_config)
        generate_layout.addWidget(save_yaml_btn)
        
        layout.addLayout(generate_layout)
        
        return panel
    
    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Project', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open Project', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.load_project)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save Project', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_yaml_action = QAction('Export YAML', self)
        export_yaml_action.triggered.connect(self.export_yaml)
        file_menu.addAction(export_yaml_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        scrape_action = QAction('Start Scraping', self)
        scrape_action.triggered.connect(self.start_scraping)
        tools_menu.addAction(scrape_action)
        
        refresh_action = QAction('Refresh Components', self)
        refresh_action.triggered.connect(self.load_components)
        tools_menu.addAction(refresh_action)
        
        tools_menu.addSeparator()
        
        reset_db_action = QAction('Reset Database', self)
        reset_db_action.triggered.connect(self.reset_database)
        tools_menu.addAction(reset_db_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        # Add common actions to toolbar
        toolbar.addAction(QAction('New', self, triggered=self.new_project))
        toolbar.addAction(QAction('Save', self, triggered=self.save_project))
        toolbar.addSeparator()
        toolbar.addAction(QAction('Scrape', self, triggered=self.start_scraping))
        toolbar.addAction(QAction('Generate YAML', self, triggered=self.generate_yaml_config))
    
    def create_status_bar(self):
        """Create the application status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Add permanent widgets to status bar
        self.component_count_label = QLabel("Components: 0")
        self.status_bar.addPermanentWidget(self.component_count_label)
    
    def setup_connections(self):
        """Set up signal-slot connections."""
        # Scraper signals
        self.scraper.log_message.connect(self.add_log_message)
        self.scraper.status_update.connect(self.update_status)
        self.scraper.progress_update.connect(self.update_progress)
        self.scraper.component_found.connect(self.on_component_found)
        self.scraper.scraping_finished.connect(self.on_scraping_finished)
        self.scraper.scraping_error.connect(self.on_scraping_error)
    
    def load_initial_data(self):
        """Load initial data when the application starts."""
        self.load_components()
        self.update_status("Ready")
    
    def load_components(self):
        """Load components from database and populate the tree."""
        try:
            components = self.db_manager.load_all_components()
            self.populate_component_tree(components)
            self.update_component_count(len(components))
            self.add_log_message(f"Loaded {len(components)} components from database")
        except Exception as e:
            self.logger.error(f"Error loading components: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load components: {e}")
    
    def populate_component_tree(self, components: dict):
        """Populate the component tree widget."""
        self.component_tree.clear()
        component_types = {}
        
        # Group components by type
        for key, component in components.items():
            comp_type = component.component_type
            if comp_type not in component_types:
                component_types[comp_type] = []
            component_types[comp_type].append(component)
        
        # Update filter dropdown
        self.component_type_filter.clear()
        self.component_type_filter.addItem("All Types")
        for comp_type in sorted(component_types.keys()):
            self.component_type_filter.addItem(comp_type)
        
        # Add items to tree
        for comp_type in sorted(component_types.keys()):
            type_item = QTreeWidgetItem(self.component_tree, [comp_type])
            type_item.setData(0, Qt.ItemDataRole.UserRole, "type")
            
            for component in sorted(component_types[comp_type], key=lambda c: c.name):
                comp_item = QTreeWidgetItem(type_item, [component.name])
                comp_item.setData(0, Qt.ItemDataRole.UserRole, component)
        
        self.component_tree.expandAll()
    
    def filter_components(self):
        """Filter components based on search text and type filter."""
        search_text = self.search_input.text().lower()
        type_filter = self.component_type_filter.currentText()
        
        # Iterate through all items and show/hide based on filters
        for i in range(self.component_tree.topLevelItemCount()):
            type_item = self.component_tree.topLevelItem(i)
            type_name = type_item.text(0)
            
            # Check type filter
            type_matches = (type_filter == "All Types" or type_filter == type_name)
            
            visible_children = 0
            for j in range(type_item.childCount()):
                child_item = type_item.child(j)
                component = child_item.data(0, Qt.ItemDataRole.UserRole)
                
                if isinstance(component, ESPHomeComponent):
                    # Check search filter
                    name_matches = search_text in component.name.lower()
                    desc_matches = search_text in component.description.lower()
                    
                    child_visible = type_matches and (not search_text or name_matches or desc_matches)
                    child_item.setHidden(not child_visible)
                    
                    if child_visible:
                        visible_children += 1
            
            # Hide type item if no children are visible
            type_item.setHidden(visible_children == 0)
    
    def show_component_info(self):
        """Show information about the selected component."""
        current_item = self.component_tree.currentItem()
        if not current_item:
            self.component_info.clear()
            return
        
        component = current_item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(component, ESPHomeComponent):
            info = f"<b>{component.name}</b><br>"
            info += f"Type: {component.component_type}<br>"
            if component.platforms:
                info += f"Platforms: {', '.join(component.platforms)}<br>"
            info += f"<br>{component.description}"
            if component.config_vars:
                info += f"<br><br>Configuration variables: {len(component.config_vars)}"
            self.component_info.setHtml(info)
        else:
            self.component_info.clear()
    
    def add_component_to_canvas(self, item: QTreeWidgetItem):
        """Add a component to the design canvas."""
        component = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(component, ESPHomeComponent):
            # Clone the component to create a new instance
            new_component = component.clone()
            self.canvas.add_component(new_component)
            self.add_log_message(f"Added component '{component.name}' to canvas")
    
    def on_canvas_component_selected(self, component: ESPHomeComponent):
        """Handle component selection on canvas."""
        if component:
            self.add_log_message(f"Selected component: {component.name}")
    
    def configure_canvas_component(self, component: ESPHomeComponent):
        """Open configuration dialog for a canvas component."""
        dialog = ComponentConfigDialog(component, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.canvas.update()
            self.add_log_message(f"Configured component: {component.name}")
    
    def start_scraping(self):
        """Start the web scraping process."""
        if self.is_scraping:
            return
        
        # Get maximum components to scrape
        max_components, ok = QInputDialog.getInt(
            self, "Scraping Options", 
            "Maximum components to scrape:", 50, 1, 500
        )
        if not ok:
            return
        
        self.is_scraping = True
        self.scrape_btn.setEnabled(False)
        self.cancel_scrape_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Start scraping in a separate thread
        self.scraping_thread = ScrapingThread(self.scraper, max_components)
        self.scraping_thread.start()
        
        self.add_log_message(f"Started scraping up to {max_components} components")
    
    def cancel_scraping(self):
        """Cancel the scraping process."""
        if self.scraping_thread and self.scraping_thread.isRunning():
            self.scraper.cancel_scraping()
            self.add_log_message("Canceling scraping...")
    
    def on_component_found(self, name: str, component: ESPHomeComponent):
        """Handle when a new component is found during scraping."""
        self.add_log_message(f"Found component: {name}")
    
    def on_scraping_finished(self):
        """Handle scraping completion."""
        self.is_scraping = False
        self.scrape_btn.setEnabled(True)
        self.cancel_scrape_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        self.add_log_message("Scraping completed successfully")
        self.load_components()  # Refresh the component tree
        
        if self.scraping_thread:
            self.scraping_thread.wait()
            self.scraping_thread = None
    
    def on_scraping_error(self, error: str):
        """Handle scraping errors."""
        self.is_scraping = False
        self.scrape_btn.setEnabled(True)
        self.cancel_scrape_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        
        self.add_log_message(f"Scraping error: {error}")
        QMessageBox.critical(self, "Scraping Error", f"An error occurred during scraping:\n{error}")
        
        if self.scraping_thread:
            self.scraping_thread.wait()
            self.scraping_thread = None
    
    def update_progress(self, current: int, total: int, message: str):
        """Update the progress bar."""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.update_status(message)
    
    def update_status(self, message: str):
        """Update the status bar message."""
        self.status_label.setText(message)
    
    def update_component_count(self, count: int):
        """Update the component count in the status bar."""
        self.component_count_label.setText(f"Components: {count}")
    
    def add_log_message(self, message: str):
        """Add a message to the log display."""
        self.log_display.append(f"[{self.get_timestamp()}] {message}")
        self.db_manager.log_message("INFO", message, "MainWindow")
    
    def get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def clear_log(self):
        """Clear the log display."""
        self.log_display.clear()
        self.add_log_message("Log cleared")
    
    def export_log(self):
        """Export log to a file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", "esphome_manager.log", "Log files (*.log);;All files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(self.log_display.toPlainText())
                self.add_log_message(f"Log exported to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export log: {e}")
    
    def new_project(self):
        """Create a new project."""
        if self.canvas.has_components():
            reply = QMessageBox.question(
                self, "New Project",
                "Current project has unsaved changes. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        self.clear_canvas()
        self.current_project_id = None
        self.current_project_name = "Untitled Project"
        self.project_name_input.setText(self.current_project_name)
        self.add_log_message("New project created")
    
    def save_project(self):
        """Save the current project."""
        if not self.current_project_id:
            import uuid
            self.current_project_id = str(uuid.uuid4())
        
        components = self.canvas.get_all_components()
        if self.db_manager.save_project(
            self.current_project_id, 
            self.current_project_name, 
            "ESPHome project", 
            components
        ):
            self.add_log_message(f"Project '{self.current_project_name}' saved")
        else:
            QMessageBox.critical(self, "Save Error", "Failed to save project")
    
    def load_project(self):
        """Load a project from database."""
        # For now, just implement a simple input dialog
        # In a full implementation, you'd want a project selection dialog
        project_id, ok = QInputDialog.getText(
            self, "Load Project", "Enter project ID:"
        )
        if ok and project_id:
            result = self.db_manager.load_project(project_id)
            if result:
                name, description, components = result
                self.clear_canvas()
                for component in components:
                    self.canvas.add_component(component)
                self.current_project_id = project_id
                self.current_project_name = name
                self.project_name_input.setText(name)
                self.add_log_message(f"Loaded project: {name}")
            else:
                QMessageBox.warning(self, "Load Error", "Project not found")
    
    def update_project_name(self, name: str):
        """Update the current project name."""
        self.current_project_name = name
    
    def clear_canvas(self):
        """Clear all components from the canvas."""
        self.canvas.clear_all_components()
        self.add_log_message("Canvas cleared")
    
    def generate_yaml_config(self):
        """Generate YAML configuration from canvas components."""
        components = self.canvas.get_all_components()
        if not components:
            QMessageBox.information(self, "No Components", "Add components to the canvas first")
            return
        
        yaml_config = self.yaml_generator.generate_esphome_config(
            components, self.current_project_name.lower().replace(' ', '_')
        )
        
        self.yaml_editor.set_content(yaml_config)
        self.tab_widget.setCurrentIndex(1)  # Switch to YAML tab
        self.add_log_message("YAML configuration generated")
    
    def save_yaml_config(self):
        """Save the current YAML configuration."""
        yaml_content = self.yaml_editor.get_content()
        if not yaml_content.strip():
            QMessageBox.information(self, "No Content", "Generate YAML configuration first")
            return
        
        config_name, ok = QInputDialog.getText(
            self, "Save YAML", "Configuration name:", text=f"{self.current_project_name}_config"
        )
        if ok and config_name:
            import uuid
            config_id = str(uuid.uuid4())
            if self.db_manager.save_yaml_config(config_id, config_name, yaml_content):
                self.add_log_message(f"YAML configuration '{config_name}' saved")
            else:
                QMessageBox.critical(self, "Save Error", "Failed to save YAML configuration")
    
    def export_yaml(self):
        """Export YAML configuration to file."""
        yaml_content = self.yaml_editor.get_content()
        if not yaml_content.strip():
            QMessageBox.information(self, "No Content", "Generate YAML configuration first")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export YAML", f"{self.current_project_name}.yaml", 
            "YAML files (*.yaml *.yml);;All files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write(yaml_content)
                self.add_log_message(f"YAML exported to: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export YAML: {e}")
    
    def reset_database(self):
        """Reset the entire database."""
        reply = QMessageBox.question(
            self, "Reset Database",
            "This will delete all components and configurations. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.reset_database()
                self.load_components()
                self.add_log_message("Database reset successfully")
            except Exception as e:
                QMessageBox.critical(self, "Reset Error", f"Failed to reset database: {e}")
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self, "About ESPHome Component Manager",
            "ESPHome Component Manager v1.0\n\n"
            "A comprehensive tool for managing ESPHome components\n"
            "with visual design capabilities and YAML generation.\n\n"
            "Built with PyQt6 and Python."
        )
    
    def closeEvent(self, event):
        """Handle application close event."""
        if self.is_scraping and self.scraping_thread:
            reply = QMessageBox.question(
                self, "Exit Application",
                "Scraping is in progress. Exit anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            # Cancel scraping
            self.scraper.cancel_scraping()
            if self.scraping_thread.isRunning():
                self.scraping_thread.wait(3000)  # Wait up to 3 seconds
        
        self.logger.info("Application closing")
        event.accept()
