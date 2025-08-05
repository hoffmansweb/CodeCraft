"""
ESPHome Component Model
Represents an ESPHome component with its configuration variables.
"""

from typing import List, Optional, Dict, Any
import uuid
from .config_variable import ConfigVariable

class ESPHomeComponent:
    """Represents an ESPHome component (e.g., 'switch', 'sensor.dht')."""
    
    def __init__(self, name: str, component_type: str, description: str = "",
                 platforms: Optional[List[str]] = None, 
                 config_vars: Optional[List[ConfigVariable]] = None, 
                 url: Optional[str] = None):
        self.name = name
        self.component_type = component_type
        self.description = description
        self.platforms = platforms if platforms is not None else []
        self.config_vars = config_vars if config_vars is not None else []
        self.url = url
        self.instance_id = str(uuid.uuid4())  # Unique ID for each instance
        self.x_position = 0
        self.y_position = 0
        self.width = 200
        self.height = 150
        
    def add_config_var(self, config_var: ConfigVariable):
        """Add a configuration variable to this component."""
        self.config_vars.append(config_var)
    
    def get_config_var(self, name: str) -> Optional[ConfigVariable]:
        """Get a configuration variable by name."""
        for var in self.config_vars:
            if var.name == name:
                return var
        return None
    
    def set_config_value(self, var_name: str, value: Any) -> bool:
        """Set a configuration variable value."""
        var = self.get_config_var(var_name)
        if var:
            return var.set_value(value)
        return False
    
    def is_valid_configuration(self) -> tuple[bool, List[str]]:
        """Check if all required configuration variables are set."""
        errors = []
        for var in self.config_vars:
            if not var.is_valid():
                errors.append(f"Required variable '{var.name}' is not set")
        return len(errors) == 0, errors
    
    def get_yaml_config(self, indent: int = 0) -> str:
        """Generate YAML configuration for this component."""
        indent_str = "  " * indent
        lines = []
        
        # Component header
        if self.component_type == self.name:
            lines.append(f"{indent_str}{self.component_type}:")
        else:
            lines.append(f"{indent_str}{self.component_type}:")
            lines.append(f"{indent_str}  - platform: {self.name}")
        
        # Add configuration variables
        has_config = False
        for var in self.config_vars:
            value = var.to_yaml_value()
            if value is not None:
                if not has_config and self.component_type != self.name:
                    # First config var after platform
                    lines.append(f"{indent_str}    {var.name}: {value}")
                else:
                    if self.component_type == self.name:
                        lines.append(f"{indent_str}  {var.name}: {value}")
                    else:
                        lines.append(f"{indent_str}    {var.name}: {value}")
                has_config = True
        
        return "\n".join(lines)
    
    def set_position(self, x: int, y: int):
        """Set the position of this component on the canvas."""
        self.x_position = x
        self.y_position = y
    
    def set_size(self, width: int, height: int):
        """Set the size of this component on the canvas."""
        self.width = width
        self.height = height
    
    def contains_point(self, x: int, y: int) -> bool:
        """Check if a point is within this component's bounds."""
        return (self.x_position <= x <= self.x_position + self.width and
                self.y_position <= y <= self.y_position + self.height)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "component_type": self.component_type,
            "description": self.description,
            "platforms": self.platforms,
            "config_vars": [var.to_dict() for var in self.config_vars],
            "url": self.url,
            "instance_id": self.instance_id,
            "x_position": self.x_position,
            "y_position": self.y_position,
            "width": self.width,
            "height": self.height
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ESPHomeComponent':
        """Create instance from dictionary."""
        config_vars = [ConfigVariable.from_dict(var_data) 
                       for var_data in data.get('config_vars', [])]
        
        component = cls(
            name=data['name'],
            component_type=data['component_type'],
            description=data.get('description', ''),
            platforms=data.get('platforms', []),
            config_vars=config_vars,
            url=data.get('url')
        )
        
        component.instance_id = data.get('instance_id', str(uuid.uuid4()))
        component.x_position = data.get('x_position', 0)
        component.y_position = data.get('y_position', 0)
        component.width = data.get('width', 200)
        component.height = data.get('height', 150)
        
        return component
    
    def clone(self) -> 'ESPHomeComponent':
        """Create a copy of this component with a new instance ID."""
        clone_data = self.to_dict()
        clone_data['instance_id'] = str(uuid.uuid4())
        return ESPHomeComponent.from_dict(clone_data)
    
    def __str__(self) -> str:
        return f"ESPHomeComponent({self.component_type}.{self.name})"
    
    def __repr__(self) -> str:
        return self.__str__()
