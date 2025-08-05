# Overview

The ESPHome Component Manager is a comprehensive desktop application built with PyQt6 that provides a visual interface for managing ESPHome components. The application enables users to scrape component documentation from the ESPHome website, configure components through a drag-and-drop canvas interface, and generate complete YAML configurations for ESP32/ESP8266 devices. It combines web scraping capabilities with an intuitive visual design system for IoT device configuration management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture

The application uses PyQt6 as the primary GUI framework with a modular design pattern. The main components include:

- **Main Window (`MainWindow`)**: Central hub that orchestrates all application functionality and manages the overall user interface
- **Component Canvas (`ComponentCanvas`)**: Visual drag-and-drop interface for designing ESPHome configurations with graphical component representation
- **Component Dialog (`ComponentConfigDialog`)**: Modal dialogs for configuring individual component variables and settings
- **YAML Editor (`YAMLEditor`)**: Advanced text editor with syntax highlighting and validation for direct YAML editing

The GUI architecture follows a signal-slot communication pattern typical in Qt applications, enabling loose coupling between components and responsive user interactions.

## Backend Architecture

The backend is structured around several key architectural patterns:

- **Database Layer (`DatabaseManager`)**: SQLite-based persistence layer for storing component metadata, configuration variables, and application state
- **Data Models**: Clear separation of concerns with dedicated model classes (`ESPHomeComponent`, `ConfigVariable`) representing core business entities
- **Web Scraping Engine (`ESPHomeScraper`)**: Asynchronous web scraping system using requests and BeautifulSoup with trafilatura for robust content extraction
- **Utility Services**: Modular utility classes for validation (`ConfigValidator`) and YAML generation (`YAMLGenerator`)

The architecture emphasizes modularity and separation of concerns, with each component having clearly defined responsibilities.

## Data Storage Solutions

The application uses SQLite as the primary database solution for several reasons:

- **Embedded Database**: No external database server required, simplifying deployment and setup
- **Local Data**: All component metadata and configurations stored locally for offline access
- **Schema Design**: Normalized schema with separate tables for components and configuration variables
- **Transaction Support**: ACID compliance for reliable data operations

The database schema supports component metadata, configuration variables, and maintains relationships between components and their configurable parameters.

## Configuration Management

The system implements a comprehensive configuration management approach:

- **Visual Configuration**: Drag-and-drop interface for intuitive component placement and connection
- **Form-based Configuration**: Dedicated dialogs for detailed parameter configuration with type-specific input widgets
- **YAML Generation**: Automatic conversion from visual configurations to ESPHome-compatible YAML
- **Validation Layer**: Multi-level validation ensuring configuration correctness before YAML generation

## Threading and Asynchronous Operations

The application uses Qt's threading model for non-blocking operations:

- **Scraping Operations**: Web scraping runs in separate threads to prevent UI freezing
- **Signal-Slot Communication**: Thread-safe communication between background operations and UI updates
- **Progress Tracking**: Real-time progress updates during long-running operations

# External Dependencies

## Core GUI Framework
- **PyQt6**: Complete desktop application framework providing widgets, threading, and cross-platform compatibility

## Web Scraping and HTTP
- **requests**: HTTP library for making web requests to ESPHome documentation
- **BeautifulSoup4**: HTML parsing and DOM navigation for extracting component information
- **trafilatura**: Advanced content extraction for robust text mining from web pages

## Data Processing and Storage
- **SQLite3**: Built-in Python database interface for local data persistence
- **PyYAML**: YAML parsing and generation for configuration file handling
- **json**: Built-in JSON processing for data serialization

## System and Utilities
- **logging**: Built-in Python logging system for application monitoring and debugging
- **datetime**: Time and date handling for timestamps and scheduling
- **uuid**: Unique identifier generation for component instances
- **re**: Regular expressions for pattern matching and validation
- **typing**: Type hints for better code documentation and IDE support

## Optional Integrations
The application is designed to scrape data from the official ESPHome documentation website (https://esphome.io) but can operate independently with locally stored component data. The scraping functionality is optional and the application can function entirely offline once components are cached locally.