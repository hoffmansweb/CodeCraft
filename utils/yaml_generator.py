"""
YAML Configuration Generator
Generates ESPHome YAML configurations from component instances.
"""

import yaml
from typing import List, Dict, Any, Optional
from io import StringIO
import logging
from datetime import datetime

from models.component import ESPHomeComponent

class YAMLGenerator:
    """Generates ESPHome YAML configurations from component instances."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_esphome_config(self, components: List[ESPHomeComponent], 
                               device_name: str = "my_device",
                               platform: str = "ESP32",
                               board: str = "nodemcu-32s") -> str:
        """Generate a complete ESPHome YAML configuration."""
        
        config = {
            'esphome': {
                'name': device_name,
                'platform': platform,
                'board': board
            },
            'wifi': {
                'ssid': '!secret wifi_ssid',
                'password': '!secret wifi_password'
            },
            'logger': {},
            'api': {
                'password': '!secret api_password'
            },
            'ota': {
                'password': '!secret ota_password'
            }
        }
        
        # Group components by type
        component_groups = {}
        for component in components:
            if component.component_type not in component_groups:
                component_groups[component.component_type] = []
            component_groups[component.component_type].append(component)
        
        # Add components to config
        for component_type, comps in component_groups.items():
            if component_type not in config:
                config[component_type] = []
            
            for component in comps:
                comp_config = self._generate_component_config(component)
                if comp_config:
                    if isinstance(config[component_type], list):
                        config[component_type].append(comp_config)
                    else:
                        # Handle single-value components
                        config[component_type] = comp_config
        
        # Convert to YAML string
        return self._dict_to_yaml(config)
    
    def _generate_component_config(self, component: ESPHomeComponent) -> Optional[Dict[str, Any]]:
        """Generate configuration dictionary for a single component."""
        config = {}
        
        # Add platform if component name differs from type
        if component.name != component.component_type:
            config['platform'] = component.name
        
        # Add configured variables
        for var in component.config_vars:
            value = var.get_effective_value()
            if value is not None:
                config[var.name] = value
        
        # Add default ID if not specified
        if 'id' not in config:
            safe_name = component.name.lower().replace(' ', '_').replace('-', '_')
            config['id'] = f"{safe_name}_{component.instance_id[:8]}"
        
        return config if config else None
    
    def _dict_to_yaml(self, data: Dict[str, Any]) -> str:
        """Convert dictionary to YAML string with proper formatting."""
        try:
            # Use StringIO to capture YAML output
            stream = StringIO()
            
            # Custom YAML representer for better formatting
            def represent_none(self, data):
                return self.represent_scalar('tag:yaml.org,2002:null', '')
            
            yaml.add_representer(type(None), represent_none)
            
            # Generate YAML with custom settings
            yaml.dump(
                data,
                stream,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
                indent=2,
                width=120
            )
            
            yaml_content = stream.getvalue()
            
            # Add header comment
            header = f"""# ESPHome Configuration
# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# ESPHome Component Manager

"""
            
            return header + yaml_content
            
        except Exception as e:
            self.logger.error(f"Error generating YAML: {e}")
            return f"# Error generating YAML configuration: {e}\n"
    
    def validate_yaml(self, yaml_content: str) -> tuple[bool, Optional[str]]:
        """Validate YAML syntax."""
        try:
            yaml.safe_load(yaml_content)
            return True, None
        except yaml.YAMLError as e:
            return False, str(e)
    
    def generate_secrets_template(self) -> str:
        """Generate a secrets.yaml template file."""
        secrets_template = """# ESPHome Secrets Template
# Copy this file to secrets.yaml and fill in your actual values

# WiFi Configuration
wifi_ssid: "Your_WiFi_Network_Name"
wifi_password: "your_wifi_password"

# API Configuration
api_password: "your_api_password"

# OTA Configuration
ota_password: "your_ota_password"

# Additional secrets can be added here
# mqtt_username: "your_mqtt_username"
# mqtt_password: "your_mqtt_password"
"""
        return secrets_template
    
    def extract_component_yaml(self, component: ESPHomeComponent) -> str:
        """Generate YAML for a single component."""
        comp_config = self._generate_component_config(component)
        if not comp_config:
            return f"# No configuration available for {component.name}\n"
        
        # Create a minimal structure for this component
        config_dict = {component.component_type: [comp_config]}
        
        return self._dict_to_yaml(config_dict)
    
    def merge_yaml_configs(self, yaml_configs: List[str]) -> str:
        """Merge multiple YAML configuration strings."""
        merged_config = {}
        
        try:
            for yaml_config in yaml_configs:
                if yaml_config.strip():
                    config = yaml.safe_load(yaml_config)
                    if config:
                        self._deep_merge(merged_config, config)
            
            return self._dict_to_yaml(merged_config)
            
        except Exception as e:
            self.logger.error(f"Error merging YAML configs: {e}")
            return f"# Error merging YAML configurations: {e}\n"
    
    def _deep_merge(self, base_dict: Dict[str, Any], merge_dict: Dict[str, Any]):
        """Deep merge two dictionaries."""
        for key, value in merge_dict.items():
            if key in base_dict:
                if isinstance(base_dict[key], dict) and isinstance(value, dict):
                    self._deep_merge(base_dict[key], value)
                elif isinstance(base_dict[key], list) and isinstance(value, list):
                    base_dict[key].extend(value)
                else:
                    base_dict[key] = value
            else:
                base_dict[key] = value
