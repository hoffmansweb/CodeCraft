"""
Configuration Variable Model
Represents a configuration variable for an ESPHome component.
"""

from typing import Any, Optional, Dict
import json

class ConfigVariable:
    """Represents a configuration variable for an ESPHome component."""
    
    def __init__(self, name: str, description: str, data_type: str, 
                 is_required: bool = False, default_value: Any = None):
        self.name = name
        self.description = description
        self.data_type = data_type
        self.is_required = is_required
        self.default_value = default_value
        self.current_value = None  # To store user-configured value
        
    def set_value(self, value: Any) -> bool:
        """Set the current value with basic validation."""
        try:
            if value is None and self.is_required:
                return False
            
            # Basic type validation
            if value is not None:
                if self.data_type == 'int' and not isinstance(value, int):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        return False
                elif self.data_type == 'float' and not isinstance(value, (int, float)):
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        return False
                elif self.data_type == 'bool' and not isinstance(value, bool):
                    if isinstance(value, str):
                        value = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        value = bool(value)
            
            self.current_value = value
            return True
        except Exception:
            return False
    
    def get_effective_value(self) -> Any:
        """Get the effective value (current or default)."""
        if self.current_value is not None:
            return self.current_value
        return self.default_value
    
    def is_valid(self) -> bool:
        """Check if the current configuration is valid."""
        effective_value = self.get_effective_value()
        if self.is_required and effective_value is None:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "data_type": self.data_type,
            "is_required": self.is_required,
            "default_value": self.default_value,
            "current_value": self.current_value
        }
    
    def to_yaml_value(self) -> Any:
        """Get value formatted for YAML output."""
        value = self.get_effective_value()
        if value is None:
            return None
        
        # Handle special YAML formatting
        if self.data_type == 'string' and isinstance(value, str):
            # Check if string needs quoting
            if any(char in value for char in [':', '[', ']', '{', '}', '|', '>', '#']):
                return f'"{value}"'
        
        return value
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigVariable':
        """Create instance from dictionary."""
        instance = cls(
            name=data['name'],
            description=data.get('description', ''),
            data_type=data.get('data_type', 'string'),
            is_required=data.get('is_required', False),
            default_value=data.get('default_value')
        )
        instance.current_value = data.get('current_value')
        return instance
    
    def __str__(self) -> str:
        return f"ConfigVariable({self.name}, {self.data_type}, required={self.is_required})"
    
    def __repr__(self) -> str:
        return self.__str__()
