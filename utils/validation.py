"""
Validation utilities for ESPHome configurations.
"""

import re
import logging
from typing import Any, List, Dict, Optional, Tuple

class ConfigValidator:
    """Validates ESPHome configuration values and structures."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Common validation patterns
        self.patterns = {
            'identifier': re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$'),
            'pin_number': re.compile(r'^(GPIO)?(\d+)$', re.IGNORECASE),
            'i2c_address': re.compile(r'^0x[0-9A-Fa-f]{2}$'),
            'frequency': re.compile(r'^\d+(\.\d+)?(Hz|KHz|MHz)$', re.IGNORECASE),
            'time_duration': re.compile(r'^\d+(\.\d+)?(ms|s|min|h)$', re.IGNORECASE),
            'percentage': re.compile(r'^\d+(\.\d+)?%$'),
            'temperature': re.compile(r'^-?\d+(\.\d+)?°?[CFK]?$'),
            'ip_address': re.compile(r'^(\d{1,3}\.){3}\d{1,3}$')
        }
    
    def validate_identifier(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate an ESPHome identifier."""
        if not value:
            return False, "Identifier cannot be empty"
        
        if not self.patterns['identifier'].match(value):
            return False, "Identifier must start with a letter and contain only letters, numbers, and underscores"
        
        if len(value) > 63:
            return False, "Identifier must be 63 characters or less"
        
        # Check against reserved keywords
        reserved_keywords = [
            'true', 'false', 'null', 'yes', 'no', 'on', 'off',
            'esphome', 'wifi', 'api', 'ota', 'logger', 'web_server'
        ]
        
        if value.lower() in reserved_keywords:
            return False, f"'{value}' is a reserved keyword"
        
        return True, None
    
    def validate_pin_number(self, value: Any, platform: str = "ESP32") -> Tuple[bool, Optional[str]]:
        """Validate a GPIO pin number."""
        if isinstance(value, str):
            match = self.patterns['pin_number'].match(value)
            if match:
                pin_num = int(match.group(2))
            else:
                return False, "Invalid pin format. Use 'GPIO<number>' or just '<number>'"
        elif isinstance(value, int):
            pin_num = value
        else:
            return False, "Pin must be a number or GPIO string"
        
        # Platform-specific pin validation
        if platform.upper() == "ESP32":
            valid_pins = list(range(0, 40))  # GPIO 0-39
            # Remove some problematic pins
            invalid_pins = [6, 7, 8, 9, 10, 11]  # Flash pins
            valid_pins = [p for p in valid_pins if p not in invalid_pins]
        elif platform.upper() == "ESP8266":
            valid_pins = [0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16]
        else:
            # Generic validation
            valid_pins = list(range(0, 50))
        
        if pin_num not in valid_pins:
            return False, f"Pin {pin_num} is not valid for {platform}"
        
        return True, None
    
    def validate_i2c_address(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate an I2C address."""
        if isinstance(value, str):
            if not self.patterns['i2c_address'].match(value):
                return False, "I2C address must be in format '0xNN' (e.g., '0x48')"
            addr = int(value, 16)
        elif isinstance(value, int):
            if not (0x00 <= value <= 0xFF):
                return False, "I2C address must be between 0x00 and 0xFF"
            addr = value
        else:
            return False, "I2C address must be a hex string or integer"
        
        # Check for reserved addresses
        reserved_addresses = [0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07,
                             0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F]
        
        if addr in reserved_addresses:
            return False, f"Address 0x{addr:02X} is reserved"
        
        return True, None
    
    def validate_frequency(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate a frequency value."""
        if not self.patterns['frequency'].match(value):
            return False, "Frequency must include units (Hz, KHz, MHz)"
        
        # Extract numeric part and unit
        match = re.match(r'^(\d+(?:\.\d+)?)([A-Za-z]+)$', value)
        if match:
            num_part = float(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to Hz for range checking
            multipliers = {'hz': 1, 'khz': 1000, 'mhz': 1000000}
            if unit in multipliers:
                freq_hz = num_part * multipliers[unit]
                if freq_hz <= 0:
                    return False, "Frequency must be positive"
                if freq_hz > 1e9:  # 1 GHz limit
                    return False, "Frequency is too high (max 1 GHz)"
            else:
                return False, "Unit must be Hz, KHz, or MHz"
        
        return True, None
    
    def validate_time_duration(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate a time duration value."""
        if not self.patterns['time_duration'].match(value):
            return False, "Time duration must include units (ms, s, min, h)"
        
        # Extract numeric part and unit
        match = re.match(r'^(\d+(?:\.\d+)?)([A-Za-z]+)$', value)
        if match:
            num_part = float(match.group(1))
            unit = match.group(2).lower()
            
            # Convert to milliseconds for range checking
            multipliers = {'ms': 1, 's': 1000, 'min': 60000, 'h': 3600000}
            if unit in multipliers:
                duration_ms = num_part * multipliers[unit]
                if duration_ms <= 0:
                    return False, "Duration must be positive"
                if duration_ms > 86400000:  # 24 hours limit
                    return False, "Duration is too long (max 24 hours)"
            else:
                return False, "Unit must be ms, s, min, or h"
        
        return True, None
    
    def validate_percentage(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate a percentage value."""
        if isinstance(value, str):
            if value.endswith('%'):
                try:
                    num_value = float(value[:-1])
                except ValueError:
                    return False, "Invalid percentage format"
            else:
                return False, "Percentage must end with '%'"
        elif isinstance(value, (int, float)):
            num_value = float(value)
        else:
            return False, "Percentage must be a number or string with '%'"
        
        if not (0 <= num_value <= 100):
            return False, "Percentage must be between 0 and 100"
        
        return True, None
    
    def validate_ip_address(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate an IP address."""
        if not self.patterns['ip_address'].match(value):
            return False, "Invalid IP address format"
        
        octets = value.split('.')
        for octet in octets:
            try:
                num = int(octet)
                if not (0 <= num <= 255):
                    return False, "IP address octets must be between 0 and 255"
            except ValueError:
                return False, "IP address octets must be numbers"
        
        return True, None
    
    def validate_by_type(self, value: Any, data_type: str, context: Dict[str, Any] = None) -> Tuple[bool, Optional[str]]:
        """Validate a value based on its data type."""
        if context is None:
            context = {}
        
        # Handle None values
        if value is None:
            return True, None
        
        # Convert value to string for pattern matching
        str_value = str(value)
        
        # Type-specific validation
        if data_type == 'identifier':
            return self.validate_identifier(str_value)
        elif data_type == 'pin':
            platform = context.get('platform', 'ESP32')
            return self.validate_pin_number(value, platform)
        elif data_type == 'i2c_address':
            return self.validate_i2c_address(value)
        elif data_type == 'frequency':
            return self.validate_frequency(str_value)
        elif data_type == 'time':
            return self.validate_time_duration(str_value)
        elif data_type == 'percentage':
            return self.validate_percentage(value)
        elif data_type == 'ip_address':
            return self.validate_ip_address(str_value)
        elif data_type == 'int':
            try:
                int(value)
                return True, None
            except (ValueError, TypeError):
                return False, "Value must be an integer"
        elif data_type == 'float':
            try:
                float(value)
                return True, None
            except (ValueError, TypeError):
                return False, "Value must be a number"
        elif data_type == 'bool':
            if isinstance(value, bool):
                return True, None
            if isinstance(value, str):
                if value.lower() in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                    return True, None
            return False, "Value must be a boolean (true/false)"
        elif data_type == 'string':
            # Basic string validation
            if len(str_value) > 1000:
                return False, "String is too long (max 1000 characters)"
            return True, None
        else:
            # Unknown type, assume valid
            return True, None
    
    def validate_component_config(self, component) -> Tuple[bool, List[str]]:
        """Validate all configuration variables for a component."""
        errors = []
        
        for var in component.config_vars:
            if var.is_required and var.get_effective_value() is None:
                errors.append(f"Required variable '{var.name}' is not set")
                continue
            
            value = var.get_effective_value()
            if value is not None:
                is_valid, error = self.validate_by_type(value, var.data_type)
                if not is_valid:
                    errors.append(f"Variable '{var.name}': {error}")
        
        return len(errors) == 0, errors
