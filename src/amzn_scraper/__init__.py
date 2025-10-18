"""
Amazon Scraper Package

A Python package for scraping Amazon product data using Playwright.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .scraper import AmazonScraper
from .parser import ProductParser
from .storage import DataStorage
from .config import Config
from .market_research import MarketResearch

__all__ = ["AmazonScraper", "ProductParser", "DataStorage", "Config", "MarketResearch"]
