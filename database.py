"""
Database Manager for ESPHome Component Manager
Handles all SQLite database operations for components, configurations, and logs.
"""

import sqlite3
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import json

from models.component import ESPHomeComponent
from models.config_variable import ConfigVariable

class DatabaseManager:
    """Manages all database operations for the ESPHome Component Manager."""
    
    def __init__(self, db_name: str = "esphome_components.db"):
        self.db_name = db_name
        self.logger = logging.getLogger(__name__)
        self._init_db()
    
    def _init_db(self):
        """Initialize the SQLite database and create tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Components table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS components (
                        component_key TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        component_type TEXT NOT NULL,
                        description TEXT,
                        platforms TEXT, -- JSON array
                        url TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Configuration variables table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS config_variables (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        component_key TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        data_type TEXT DEFAULT 'string',
                        is_required INTEGER DEFAULT 0, -- 0 for False, 1 for True
                        default_value TEXT,
                        FOREIGN KEY (component_key) REFERENCES components (component_key) ON DELETE CASCADE
                    )
                ''')
                
                # Application logs table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        level TEXT NOT NULL DEFAULT 'INFO',
                        message TEXT NOT NULL,
                        module TEXT
                    )
                ''')
                
                # YAML configurations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS yaml_configs (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        config_data TEXT NOT NULL,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Project configurations table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS projects (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        description TEXT,
                        components_data TEXT, -- JSON array of component instances
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def _generate_component_key(self, component: ESPHomeComponent) -> str:
        """Generate a unique key for a component."""
        return f"{component.component_type}.{component.name.lower().replace(' ', '_').replace('.', '_')}"
    
    def save_component(self, component: ESPHomeComponent) -> bool:
        """Save or update a component and its variables to the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                component_key = self._generate_component_key(component)
                platforms_json = json.dumps(component.platforms)
                
                # Insert or update component
                cursor.execute('''
                    INSERT OR REPLACE INTO components 
                    (component_key, name, component_type, description, platforms, url, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (component_key, component.name, component.component_type, 
                      component.description, platforms_json, component.url, 
                      datetime.now().isoformat()))
                
                # Delete existing config variables
                cursor.execute("DELETE FROM config_variables WHERE component_key = ?", (component_key,))
                
                # Insert new config variables
                for var in component.config_vars:
                    cursor.execute('''
                        INSERT INTO config_variables 
                        (component_key, name, description, data_type, is_required, default_value)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (component_key, var.name, var.description, var.data_type, 
                          int(var.is_required), json.dumps(var.default_value) if var.default_value is not None else None))
                
                conn.commit()
                self.logger.info(f"Saved component '{component.name}' to database")
                return True
                
        except sqlite3.Error as e:
            self.logger.error(f"Error saving component '{component.name}': {e}")
            return False
    
    def load_component(self, component_key: str) -> Optional[ESPHomeComponent]:
        """Load a specific component from the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Load component data
                cursor.execute('''
                    SELECT name, component_type, description, platforms, url 
                    FROM components WHERE component_key = ?
                ''', (component_key,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                name, component_type, description, platforms_json, url = row
                platforms = json.loads(platforms_json) if platforms_json else []
                
                # Load config variables
                cursor.execute('''
                    SELECT name, description, data_type, is_required, default_value 
                    FROM config_variables WHERE component_key = ? ORDER BY name
                ''', (component_key,))
                
                config_vars = []
                for var_row in cursor.fetchall():
                    var_name, var_desc, var_data_type, var_is_required, var_default_value = var_row
                    default_value = json.loads(var_default_value) if var_default_value else None
                    config_vars.append(ConfigVariable(
                        var_name, var_desc, var_data_type, 
                        bool(var_is_required), default_value
                    ))
                
                component = ESPHomeComponent(
                    name, component_type, description, platforms, config_vars, url
                )
                
                return component
                
        except sqlite3.Error as e:
            self.logger.error(f"Error loading component '{component_key}': {e}")
            return None
    
    def load_all_components(self) -> Dict[str, ESPHomeComponent]:
        """Load all components from the database."""
        components = {}
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT component_key, name, component_type, description, platforms, url 
                    FROM components ORDER BY component_type, name
                ''')
                
                for row in cursor.fetchall():
                    component_key, name, component_type, description, platforms_json, url = row
                    platforms = json.loads(platforms_json) if platforms_json else []
                    
                    # Load config variables for this component
                    cursor.execute('''
                        SELECT name, description, data_type, is_required, default_value 
                        FROM config_variables WHERE component_key = ? ORDER BY name
                    ''', (component_key,))
                    
                    config_vars = []
                    for var_row in cursor.fetchall():
                        var_name, var_desc, var_data_type, var_is_required, var_default_value = var_row
                        default_value = json.loads(var_default_value) if var_default_value else None
                        config_vars.append(ConfigVariable(
                            var_name, var_desc, var_data_type, 
                            bool(var_is_required), default_value
                        ))
                    
                    component = ESPHomeComponent(
                        name, component_type, description, platforms, config_vars, url
                    )
                    components[component_key] = component
                
                self.logger.info(f"Loaded {len(components)} components from database")
                
        except sqlite3.Error as e:
            self.logger.error(f"Error loading components: {e}")
        
        return components
    
    def search_components(self, query: str, component_type: Optional[str] = None) -> List[ESPHomeComponent]:
        """Search components by name, description, or type."""
        components = []
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                sql = '''
                    SELECT component_key FROM components 
                    WHERE (name LIKE ? OR description LIKE ? OR component_type LIKE ?)
                '''
                params = [f"%{query}%", f"%{query}%", f"%{query}%"]
                
                if component_type:
                    sql += " AND component_type = ?"
                    params.append(component_type)
                
                sql += " ORDER BY component_type, name"
                
                cursor.execute(sql, params)
                
                for (component_key,) in cursor.fetchall():
                    component = self.load_component(component_key)
                    if component:
                        components.append(component)
                
        except sqlite3.Error as e:
            self.logger.error(f"Error searching components: {e}")
        
        return components
    
    def save_yaml_config(self, config_id: str, name: str, yaml_data: str) -> bool:
        """Save a YAML configuration to the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO yaml_configs (id, name, config_data, updated_at)
                    VALUES (?, ?, ?, ?)
                ''', (config_id, name, yaml_data, datetime.now().isoformat()))
                conn.commit()
                self.logger.info(f"YAML configuration '{name}' saved")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving YAML configuration: {e}")
            return False
    
    def load_yaml_config(self, config_id: str) -> Optional[tuple[str, str]]:
        """Load a YAML configuration from the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, config_data FROM yaml_configs WHERE id = ?", 
                    (config_id,)
                )
                result = cursor.fetchone()
                return result if result else None
        except sqlite3.Error as e:
            self.logger.error(f"Error loading YAML configuration: {e}")
            return None
    
    def list_yaml_configs(self) -> List[tuple[str, str, str]]:
        """List all YAML configurations."""
        configs = []
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, name, updated_at FROM yaml_configs ORDER BY updated_at DESC"
                )
                configs = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error listing YAML configurations: {e}")
        return configs
    
    def save_project(self, project_id: str, name: str, description: str, 
                     components: List[ESPHomeComponent]) -> bool:
        """Save a project configuration."""
        try:
            components_data = json.dumps([comp.to_dict() for comp in components])
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO projects (id, name, description, components_data, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (project_id, name, description, components_data, datetime.now().isoformat()))
                conn.commit()
                self.logger.info(f"Project '{name}' saved")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error saving project: {e}")
            return False
    
    def load_project(self, project_id: str) -> Optional[tuple[str, str, List[ESPHomeComponent]]]:
        """Load a project configuration."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name, description, components_data FROM projects WHERE id = ?", 
                    (project_id,)
                )
                result = cursor.fetchone()
                if result:
                    name, description, components_json = result
                    components_data = json.loads(components_json)
                    components = [ESPHomeComponent.from_dict(comp_data) for comp_data in components_data]
                    return name, description, components
                return None
        except sqlite3.Error as e:
            self.logger.error(f"Error loading project: {e}")
            return None
    
    def log_message(self, level: str, message: str, module: Optional[str] = None):
        """Log a message to the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO logs (timestamp, level, message, module)
                    VALUES (?, ?, ?, ?)
                ''', (datetime.now().isoformat(), level, message, module))
                conn.commit()
        except sqlite3.Error as e:
            # Don't log database errors to avoid recursion
            print(f"Error saving log to database: {e}")
    
    def get_logs(self, limit: int = 1000) -> List[tuple]:
        """Retrieve recent logs from the database."""
        logs = []
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT timestamp, level, message, module 
                    FROM logs ORDER BY timestamp DESC LIMIT ?
                ''', (limit,))
                logs = cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Error retrieving logs: {e}")
        return logs
    
    def clear_logs(self) -> bool:
        """Clear all logs from the database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM logs")
                conn.commit()
                self.logger.info("Logs cleared from database")
                return True
        except sqlite3.Error as e:
            self.logger.error(f"Error clearing logs: {e}")
            return False
    
    def reset_database(self):
        """Reset the entire database."""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("DROP TABLE IF EXISTS components")
                cursor.execute("DROP TABLE IF EXISTS config_variables")
                cursor.execute("DROP TABLE IF EXISTS yaml_configs")
                cursor.execute("DROP TABLE IF EXISTS projects")
                cursor.execute("DROP TABLE IF EXISTS logs")
                conn.commit()
            self.logger.info("Database reset successfully")
            self._init_db()
        except sqlite3.Error as e:
            self.logger.error(f"Error resetting database: {e}")
            raise
