"""
ESPHome Component Scraper
Advanced web scraping functionality for ESPHome component documentation.
"""

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import re
import time
import logging
from typing import List, Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from PyQt6.QtCore import QObject, QThread, pyqtSignal
import trafilatura

from models.component import ESPHomeComponent
from models.config_variable import ConfigVariable
from database import DatabaseManager

class ESPHomeScraper(QObject):
    """
    Scrapes ESPHome component information from the official documentation.
    Enhanced with robust error handling and comprehensive parsing using trafilatura.
    """
    
    # Signals for GUI communication
    log_message = pyqtSignal(str)
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int, int, str)
    component_found = pyqtSignal(str, ESPHomeComponent)
    scraping_finished = pyqtSignal()
    scraping_error = pyqtSignal(str)
    
    BASE_URL = "https://esphome.io"
    COMPONENTS_URL = f"{BASE_URL}/components/"
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__()
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self._is_canceled = False
        self.components_data = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def cancel_scraping(self):
        """Cancel the scraping operation."""
        self._is_canceled = True
        self.log_message.emit("Scraping cancellation requested.")
    
    def _fetch_page(self, url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
        """Fetch a web page and return BeautifulSoup object."""
        try:
            self.logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            return soup
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            self.log_message.emit(f"Error fetching {url}: {e}")
            return None
    
    def _extract_clean_content(self, url: str) -> Optional[str]:
        """Extract clean text content from a webpage using trafilatura."""
        try:
            downloaded = trafilatura.fetch_url(url)
            if downloaded:
                text = trafilatura.extract(downloaded)
                return text
            return None
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _extract_component_links(self, soup: BeautifulSoup) -> List[tuple[str, str]]:
        """Extract component links from the main components page."""
        component_links = []
        
        try:
            # Look for component links in various potential locations
            # Method 1: Links in main content area
            content_area = soup.find('div', class_='rst-content')
            if content_area:
                links = content_area.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if href.startswith('/components/') and href.count('/') >= 2:
                        full_url = urljoin(self.BASE_URL, href)
                        link_text = link.get_text(strip=True)
                        if link_text and not link_text.startswith('#'):
                            component_links.append((link_text, full_url))
            
            # Method 2: Look for toctree or component listings
            toctree = soup.find('div', class_='toctree-wrapper')
            if toctree:
                links = toctree.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if '/components/' in href:
                        full_url = urljoin(self.BASE_URL, href)
                        link_text = link.get_text(strip=True)
                        if link_text and not link_text.startswith('#'):
                            component_links.append((link_text, full_url))
            
            # Method 3: Look for navigation menus
            nav_menus = soup.find_all(['nav', 'ul'], class_=re.compile(r'nav|menu|toc'))
            for menu in nav_menus:
                links = menu.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if '/components/' in href and href.count('/') >= 2:
                        full_url = urljoin(self.BASE_URL, href)
                        link_text = link.get_text(strip=True)
                        if link_text and not link_text.startswith('#'):
                            component_links.append((link_text, full_url))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_links = []
            for name, url in component_links:
                if url not in seen:
                    seen.add(url)
                    unique_links.append((name, url))
            
            self.logger.info(f"Found {len(unique_links)} unique component links")
            
        except Exception as e:
            self.logger.error(f"Error extracting component links: {e}")
        
        return unique_links
    
    def _parse_config_variables_from_content(self, content: str) -> List[ConfigVariable]:
        """Parse configuration variables from clean text content."""
        config_vars = []
        
        if not content:
            return config_vars
        
        try:
            # Look for configuration sections in the text
            lines = content.split('\n')
            in_config_section = False
            current_var = None
            
            for line in lines:
                line = line.strip()
                
                # Detect configuration sections
                if re.search(r'configuration|config|options|parameters', line, re.IGNORECASE):
                    in_config_section = True
                    continue
                
                # Look for variable definitions (key: description pattern)
                var_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*)\s*[:]\s*(.+)', line)
                if var_match and in_config_section:
                    var_name = var_match.group(1)
                    description = var_match.group(2)
                    
                    # Determine data type from description
                    data_type = 'string'
                    is_required = False
                    
                    desc_lower = description.lower()
                    if any(word in desc_lower for word in ['required', 'must', 'mandatory']):
                        is_required = True
                    
                    if any(word in desc_lower for word in ['integer', 'number', 'pin', 'gpio']):
                        data_type = 'int'
                    elif any(word in desc_lower for word in ['float', 'decimal', 'temperature', 'voltage']):
                        data_type = 'float'
                    elif any(word in desc_lower for word in ['boolean', 'bool', 'true', 'false', 'enable']):
                        data_type = 'bool'
                    elif any(word in desc_lower for word in ['time', 'duration', 'interval']):
                        data_type = 'time'
                    elif any(word in desc_lower for word in ['frequency', 'hz']):
                        data_type = 'frequency'
                    elif any(word in desc_lower for word in ['percentage', '%']):
                        data_type = 'percentage'
                    
                    config_var = ConfigVariable(var_name, description, data_type, is_required)
                    config_vars.append(config_var)
                
                # Look for common ESPHome configuration patterns
                elif re.match(r'^(id|name|pin|platform|update_interval|accuracy_decimals):', line):
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        var_name = parts[0].strip()
                        description = f"Configuration for {var_name}"
                        
                        # Determine type based on common patterns
                        data_type = 'string'
                        is_required = var_name in ['name', 'platform']
                        
                        if var_name in ['pin', 'accuracy_decimals']:
                            data_type = 'int'
                        elif var_name == 'update_interval':
                            data_type = 'time'
                        elif var_name in ['id', 'name']:
                            data_type = 'identifier'
                        
                        config_var = ConfigVariable(var_name, description, data_type, is_required)
                        if not any(cv.name == var_name for cv in config_vars):
                            config_vars.append(config_var)
            
        except Exception as e:
            self.logger.error(f"Error parsing config variables from content: {e}")
        
        return config_vars
    
    def _parse_config_variables(self, soup: BeautifulSoup) -> List[ConfigVariable]:
        """Parse configuration variables from a component page using multiple methods."""
        config_vars = []
        
        try:
            # Method 1: Look for configuration sections in HTML
            config_sections = soup.find_all(['div', 'section'], 
                                          text=re.compile(r'configuration|config', re.I))
            
            for section in config_sections:
                parent = section.parent if section.parent else section
                
                # Look for tables
                tables = parent.find_all('table')
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows[1:]:  # Skip header row
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 2:
                            var_name = cells[0].get_text(strip=True)
                            description = cells[1].get_text(strip=True)
                            
                            # Extract type and required info
                            data_type = 'string'
                            is_required = False
                            default_value = None
                            
                            if len(cells) > 2:
                                type_cell = cells[2].get_text(strip=True)
                                if 'int' in type_cell.lower():
                                    data_type = 'int'
                                elif 'float' in type_cell.lower():
                                    data_type = 'float'
                                elif 'bool' in type_cell.lower():
                                    data_type = 'bool'
                                
                                is_required = 'required' in type_cell.lower()
                            
                            if var_name and not var_name.startswith('*'):
                                config_var = ConfigVariable(
                                    var_name, description, data_type, is_required, default_value
                                )
                                config_vars.append(config_var)
                
                # Look for definition lists
                dl_elements = parent.find_all('dl')
                for dl in dl_elements:
                    dt_elements = dl.find_all('dt')
                    dd_elements = dl.find_all('dd')
                    
                    for dt, dd in zip(dt_elements, dd_elements):
                        var_name = dt.get_text(strip=True)
                        description = dd.get_text(strip=True)
                        
                        # Basic type inference
                        data_type = self._infer_data_type(var_name, description)
                        is_required = 'required' in description.lower()
                        
                        if var_name and re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name):
                            config_var = ConfigVariable(
                                var_name, description, data_type, is_required
                            )
                            config_vars.append(config_var)
            
            # Method 2: Look for code blocks with YAML examples
            code_blocks = soup.find_all(['pre', 'code'])
            for block in code_blocks:
                code_text = block.get_text()
                yaml_vars = self._extract_vars_from_yaml(code_text)
                for var in yaml_vars:
                    if not any(cv.name == var.name for cv in config_vars):
                        config_vars.append(var)
            
        except Exception as e:
            self.logger.error(f"Error parsing config variables: {e}")
        
        return config_vars
    
    def _infer_data_type(self, var_name: str, description: str) -> str:
        """Infer data type from variable name and description."""
        var_name_lower = var_name.lower()
        desc_lower = description.lower()
        
        # Pin-related variables
        if 'pin' in var_name_lower or 'gpio' in var_name_lower:
            return 'pin'
        
        # Time-related variables
        if any(word in var_name_lower for word in ['interval', 'timeout', 'delay', 'duration']):
            return 'time'
        
        # Frequency variables
        if 'frequency' in var_name_lower or 'freq' in var_name_lower:
            return 'frequency'
        
        # Boolean variables
        if any(word in var_name_lower for word in ['enable', 'invert', 'inverted']):
            return 'bool'
        
        # Numeric variables
        if any(word in var_name_lower for word in ['count', 'number', 'decimals', 'threshold']):
            return 'int'
        
        # Float variables
        if any(word in var_name_lower for word in ['temperature', 'voltage', 'current', 'power']):
            return 'float'
        
        # Identifier variables
        if var_name_lower in ['id', 'name']:
            return 'identifier'
        
        # Check description for type hints
        if any(word in desc_lower for word in ['integer', 'number']):
            return 'int'
        elif any(word in desc_lower for word in ['float', 'decimal']):
            return 'float'
        elif any(word in desc_lower for word in ['boolean', 'bool', 'true', 'false']):
            return 'bool'
        elif any(word in desc_lower for word in ['time', 'duration', 'ms', 'seconds']):
            return 'time'
        elif any(word in desc_lower for word in ['frequency', 'hz']):
            return 'frequency'
        elif any(word in desc_lower for word in ['percentage', '%']):
            return 'percentage'
        
        return 'string'
    
    def _extract_vars_from_yaml(self, yaml_text: str) -> List[ConfigVariable]:
        """Extract configuration variables from YAML code examples."""
        vars_list = []
        
        try:
            lines = yaml_text.split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    var_name = line.split(':')[0].strip()
                    
                    # Skip non-identifier names
                    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var_name):
                        continue
                    
                    # Skip common YAML structure keywords
                    if var_name in ['esphome', 'wifi', 'api', 'ota', 'logger', 'web_server']:
                        continue
                    
                    # Extract value for type inference
                    value_part = line.split(':', 1)[1].strip() if ':' in line else ''
                    data_type = self._infer_type_from_value(value_part)
                    
                    config_var = ConfigVariable(
                        var_name, 
                        f"Configuration parameter for {var_name}", 
                        data_type, 
                        False
                    )
                    vars_list.append(config_var)
        
        except Exception as e:
            self.logger.error(f"Error extracting variables from YAML: {e}")
        
        return vars_list
    
    def _infer_type_from_value(self, value: str) -> str:
        """Infer data type from a YAML value."""
        value = value.strip().strip('"\'')
        
        if not value or value in ['null', '~']:
            return 'string'
        
        # Boolean values
        if value.lower() in ['true', 'false', 'yes', 'no', 'on', 'off']:
            return 'bool'
        
        # Numeric values
        try:
            if '.' in value:
                float(value)
                return 'float'
            else:
                int(value)
                return 'int'
        except ValueError:
            pass
        
        # Time duration pattern
        if re.match(r'^\d+(\.\d+)?(ms|s|min|h)$', value):
            return 'time'
        
        # Frequency pattern
        if re.match(r'^\d+(\.\d+)?(Hz|KHz|MHz)$', value):
            return 'frequency'
        
        # GPIO pin pattern
        if re.match(r'^GPIO\d+$', value) or re.match(r'^\d+$', value):
            return 'pin'
        
        return 'string'
    
    def _extract_platforms(self, soup: BeautifulSoup, clean_content: str = None) -> List[str]:
        """Extract supported platforms from component page."""
        platforms = []
        
        try:
            # Method 1: Look in HTML
            text_content = soup.get_text().lower()
            
            # Common ESP platforms
            platform_keywords = ['esp32', 'esp8266', 'esp32s2', 'esp32s3', 'esp32c3', 'rp2040']
            
            for platform in platform_keywords:
                if platform in text_content:
                    platforms.append(platform.upper())
            
            # Method 2: Look in clean content if available
            if clean_content:
                content_lower = clean_content.lower()
                for platform in platform_keywords:
                    if platform in content_lower and platform.upper() not in platforms:
                        platforms.append(platform.upper())
            
            # Method 3: Look for specific platform sections
            platform_sections = soup.find_all(text=re.compile(r'platform|supported', re.I))
            for section in platform_sections:
                parent = section.parent if section.parent else section
                parent_text = parent.get_text().lower()
                for platform in platform_keywords:
                    if platform in parent_text and platform.upper() not in platforms:
                        platforms.append(platform.upper())
            
        except Exception as e:
            self.logger.error(f"Error extracting platforms: {e}")
        
        return platforms
    
    def scrape_component_page(self, url: str) -> Optional[ESPHomeComponent]:
        """Scrape a single component page for detailed information."""
        try:
            # Fetch HTML content
            soup = self._fetch_page(url)
            if not soup:
                return None
            
            # Extract clean text content using trafilatura
            clean_content = self._extract_clean_content(url)
            
            # Extract component name from page title or URL
            title_tag = soup.find('h1')
            component_name = title_tag.get_text(strip=True) if title_tag else "Unknown"
            
            # Clean up component name
            component_name = re.sub(r'\s*component\s*$', '', component_name, flags=re.IGNORECASE)
            component_name = component_name.strip()
            
            # Extract component type from URL path
            url_path = urlparse(url).path
            path_parts = [part for part in url_path.split('/') if part]
            component_type = path_parts[-2] if len(path_parts) >= 2 else "component"
            
            # Extract description
            description = ""
            if clean_content:
                # Use first paragraph from clean content
                paragraphs = clean_content.split('\n\n')
                for para in paragraphs:
                    if len(para.strip()) > 20 and not para.strip().startswith('#'):
                        description = para.strip()[:300] + "..."
                        break
            
            if not description:
                # Fallback to HTML extraction
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    description = meta_desc.get('content', '')
                else:
                    first_p = soup.find('p')
                    if first_p:
                        description = first_p.get_text(strip=True)[:200] + "..."
            
            # Extract configuration variables using multiple methods
            config_vars = self._parse_config_variables(soup)
            
            # Parse additional variables from clean content
            if clean_content:
                content_vars = self._parse_config_variables_from_content(clean_content)
                for var in content_vars:
                    if not any(cv.name == var.name for cv in config_vars):
                        config_vars.append(var)
            
            # Extract supported platforms
            platforms = self._extract_platforms(soup, clean_content)
            
            component = ESPHomeComponent(
                name=component_name,
                component_type=component_type,
                description=description,
                platforms=platforms,
                config_vars=config_vars,
                url=url
            )
            
            self.logger.info(f"Successfully scraped component: {component_name} ({len(config_vars)} config vars)")
            return component
            
        except Exception as e:
            self.logger.error(f"Error scraping component page {url}: {e}")
            self.log_message.emit(f"Error scraping {url}: {e}")
            return None
    
    def run_scraping(self, max_components: int = 100):
        """Main scraping method that orchestrates the entire process."""
        try:
            self._is_canceled = False
            self.status_update.emit("Starting scraping process...")
            self.log_message.emit("Beginning ESPHome components scraping")
            
            # Fetch main components page
            self.status_update.emit("Fetching main components page...")
            soup = self._fetch_page(self.COMPONENTS_URL)
            if not soup:
                self.scraping_error.emit("Failed to fetch main components page")
                return
            
            # Extract component links
            self.status_update.emit("Extracting component links...")
            component_links = self._extract_component_links(soup)
            
            if not component_links:
                # Fallback: try to find links in the entire page
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link.get('href', '')
                    if '/components/' in href and href.count('/') >= 2:
                        full_url = urljoin(self.BASE_URL, href)
                        link_text = link.get_text(strip=True)
                        if link_text and not link_text.startswith('#'):
                            component_links.append((link_text, full_url))
                
                # Remove duplicates
                component_links = list(set(component_links))
            
            if not component_links:
                self.scraping_error.emit("No component links found")
                return
            
            # Limit the number of components to scrape
            component_links = component_links[:max_components]
            total_components = len(component_links)
            
            self.log_message.emit(f"Found {total_components} components to scrape")
            
            # Scrape each component
            scraped_count = 0
            failed_count = 0
            
            for i, (name, url) in enumerate(component_links):
                if self._is_canceled:
                    self.log_message.emit("Scraping canceled by user")
                    break
                
                self.progress_update.emit(i + 1, total_components, f"Scraping {name}...")
                self.status_update.emit(f"Scraping component {i + 1}/{total_components}: {name}")
                
                component = self.scrape_component_page(url)
                if component:
                    # Save to database
                    if self.db_manager.save_component(component):
                        self.component_found.emit(name, component)
                        scraped_count += 1
                    
                    # Add to local cache
                    self.components_data[f"{component.component_type}.{component.name}"] = component
                else:
                    failed_count += 1
                
                # Delay between requests to be respectful
                if i < len(component_links) - 1:  # Don't delay after the last request
                    time.sleep(2)  # Increased delay to be more respectful
            
            if not self._is_canceled:
                self.status_update.emit(f"Scraping completed. Found {scraped_count} components, {failed_count} failed.")
                self.log_message.emit(f"Scraping completed successfully. Scraped {scraped_count} components, {failed_count} failed.")
                self.scraping_finished.emit()
            
        except Exception as e:
            self.logger.exception("Fatal error during scraping")
            self.scraping_error.emit(f"Fatal error during scraping: {str(e)}")
    
    def get_component_count(self) -> int:
        """Get the total number of components in the local cache."""
        return len(self.components_data)
    
    def get_component_by_key(self, key: str) -> Optional[ESPHomeComponent]:
        """Get a component by its key from the local cache."""
        return self.components_data.get(key)

class ScrapingThread(QThread):
    """Thread for running scraping operations without blocking the GUI."""
    
    def __init__(self, scraper: ESPHomeScraper, max_components: int = 100):
        super().__init__()
        self.scraper = scraper
        self.max_components = max_components
    
    def run(self):
        """Run the scraping process in a separate thread."""
        self.scraper.run_scraping(self.max_components)
