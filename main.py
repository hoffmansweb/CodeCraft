#!/usr/bin/env python3
"""
ESPHome Component Manager - Main Entry Point
A comprehensive desktop application for managing ESPHome components with visual design capabilities.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon

from gui.main_window import MainWindow

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('esphome_manager.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    """Main application entry point."""
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Create QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("ESPHome Component Manager")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ESPHome Tools")
    
    # Set application properties
    app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, False)
    
    # Load stylesheet
    try:
        with open('resources/styles.qss', 'r') as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        logger.warning("Stylesheet file not found, using default styling")
    
    try:
        # Create and show main window
        main_window = MainWindow()
        main_window.show()
        
        logger.info("ESPHome Component Manager started successfully")
        
        # Start the event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.exception("Fatal error occurred")
        QMessageBox.critical(
            None,
            "Fatal Error",
            f"A fatal error occurred:\n{str(e)}\n\nThe application will now exit."
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
