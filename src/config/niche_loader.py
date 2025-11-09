"""Niche configuration loader for YAML files."""

import os
import yaml
import hashlib
from typing import Dict, List, Optional, Any
from pathlib import Path
from src.config.settings import settings


class NicheConfig:
    """Represents a loaded niche configuration."""

    def __init__(self, config_dict: Dict[str, Any], file_path: str):
        self.config_dict = config_dict
        self.file_path = file_path

        # Basic info
        self.name: str = config_dict.get("name", "")
        self.display_name: str = config_dict.get("display_name", self.name)
        self.description: str = config_dict.get("description", "")

        # Keywords and topics
        self.keywords: List[str] = config_dict.get("keywords", [])
        self.seed_topics: List[str] = config_dict.get("seed_topics", [])

        # Sources
        sources = config_dict.get("sources", {})
        self.google_trends = sources.get("google_trends", {})
        self.reddit = sources.get("reddit", {})

        # Thresholds
        thresholds = config_dict.get("thresholds", {})
        self.min_search_volume: int = thresholds.get("min_search_volume", 1000)
        self.max_competition: float = thresholds.get("max_competition", 0.7)
        self.min_opportunity_score: float = thresholds.get("min_opportunity_score", 60.0)
        self.min_trend_score: float = thresholds.get("min_trend_score", 40.0)

        # Formats
        formats = config_dict.get("formats", {})
        self.preferred_formats: List[str] = formats.get("preferred", [])
        self.excluded_formats: List[str] = formats.get("excluded", [])

        # Regional
        regional = config_dict.get("regional", {})
        self.target_regions: List[str] = regional.get("target_regions", ["US"])
        self.target_languages: List[str] = regional.get("target_languages", ["en"])

        # Custom settings
        self.custom: Dict[str, Any] = config_dict.get("custom", {})

    def get_config_hash(self) -> str:
        """Generate SHA-256 hash of configuration."""
        config_str = yaml.dump(self.config_dict, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "niche_name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "keywords": self.keywords,
            "seed_topics": self.seed_topics,
            "google_trends_enabled": self.google_trends.get("enabled", True),
            "google_trends_weight": self.google_trends.get("weight", 0.5),
            "reddit_enabled": self.reddit.get("enabled", True),
            "reddit_weight": self.reddit.get("weight", 0.5),
            "reddit_subreddits": self.reddit.get("subreddits", []),
            "min_search_volume": self.min_search_volume,
            "max_competition": self.max_competition,
            "min_opportunity_score": self.min_opportunity_score,
            "preferred_formats": self.preferred_formats,
            "excluded_formats": self.excluded_formats,
            "target_regions": self.target_regions,
            "target_languages": self.target_languages,
            "custom_settings": self.custom,
            "config_file_path": self.file_path,
            "config_hash": self.get_config_hash(),
            "is_active": True,
        }


class NicheLoader:
    """Loads and manages niche configurations from YAML files."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the niche loader.

        Args:
            config_dir: Directory containing niche YAML files.
                       Defaults to settings.CONFIG_DIR
        """
        self.config_dir = Path(config_dir or settings.CONFIG_DIR)
        self.configs: Dict[str, NicheConfig] = {}
        self.load_all()

    def load_all(self) -> None:
        """Load all YAML configuration files from the config directory."""
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Config directory not found: {self.config_dir}")

        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                config = self.load_config(yaml_file)
                self.configs[config.name] = config
            except Exception as e:
                print(f"Error loading config {yaml_file}: {e}")

    def load_config(self, file_path: Path) -> NicheConfig:
        """
        Load a single YAML configuration file.

        Args:
            file_path: Path to the YAML file

        Returns:
            NicheConfig object

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        with open(file_path, "r") as f:
            config_dict = yaml.safe_load(f)

        return NicheConfig(config_dict, str(file_path))

    def get_config(self, niche_name: str) -> Optional[NicheConfig]:
        """
        Get a specific niche configuration.

        Args:
            niche_name: Name of the niche (e.g., "ai_tech")

        Returns:
            NicheConfig object or None if not found
        """
        return self.configs.get(niche_name)

    def list_niches(self) -> List[str]:
        """Get list of all available niche names."""
        return list(self.configs.keys())

    def get_default_config(self) -> NicheConfig:
        """
        Get the default niche configuration.

        Returns:
            NicheConfig for the default niche

        Raises:
            ValueError: If default niche not found
        """
        default_config = self.get_config(settings.DEFAULT_NICHE)
        if not default_config:
            raise ValueError(f"Default niche '{settings.DEFAULT_NICHE}' not found")
        return default_config

    def reload(self) -> None:
        """Reload all configurations from disk."""
        self.configs.clear()
        self.load_all()


# Global niche loader instance
niche_loader = NicheLoader()
