"""
Configuration management for Amazon Scraper.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager for the Amazon scraper."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Path to config.yaml file. If None, looks for config.yaml in current directory.
        """
        # Load environment variables
        load_dotenv()
        
        # Set default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        default_config = {
            "scraper": {
                "rate_limit": {
                    "delay_between_requests": 2.0,
                    "max_requests_per_minute": 30,
                    "random_delay_range": [0.5, 1.5]
                },
                "browser": {
                    "headless": True,
                    "viewport": {"width": 1920, "height": 1080},
                    "user_agent": "auto",
                    "timeout": 30000
                },
                "retry": {
                    "max_retries": 3,
                    "retry_delay": 5.0,
                    "exponential_backoff": True
                }
            },
            "proxy": {
                "enabled": False,
                "rotation": True,
                "timeout": 10.0,
                "proxies": []
            },
            "storage": {
                "output_format": "csv",
                "output_directory": "data",
                "database": {
                    "enabled": False,
                    "type": "sqlite",
                    "connection_string": "sqlite:///amazon_products.db"
                }
            },
            "amazon": {
                "base_url": "https://www.amazon.com",
                "domains": [
                    "amazon.com",
                    "amazon.co.uk",
                    "amazon.de",
                    "amazon.fr",
                    "amazon.it",
                    "amazon.es"
                ]
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f) or {}
                # Merge user config with defaults
                return self._merge_configs(default_config, user_config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_path}: {e}")
                print("Using default configuration.")
        
        return default_config
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge user config with default config."""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'scraper.rate_limit.delay')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable with fallback to config.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or config value
        """
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        return self.get(key.lower(), default)
    
    @property
    def scraper_config(self) -> Dict[str, Any]:
        """Get scraper configuration."""
        return self.get("scraper", {})
    
    @property
    def proxy_config(self) -> Dict[str, Any]:
        """Get proxy configuration."""
        return self.get("proxy", {})
    
    @property
    def storage_config(self) -> Dict[str, Any]:
        """Get storage configuration."""
        return self.get("storage", {})
    
    @property
    def amazon_config(self) -> Dict[str, Any]:
        """Get Amazon-specific configuration."""
        return self.get("amazon", {})
    
    def save_config(self, path: Optional[str] = None) -> None:
        """
        Save current configuration to YAML file.
        
        Args:
            path: Path to save config. If None, uses current config_path.
        """
        save_path = Path(path) if path else self.config_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)
    
    def update_config(self, updates: Dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of configuration updates
        """
        self._config = self._merge_configs(self._config, updates)

