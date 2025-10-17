"""
Test suite for Amazon Scraper.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from amzn_scraper.scraper import AmazonScraper
from amzn_scraper.parser import ProductParser
from amzn_scraper.storage import DataStorage
from amzn_scraper.config import Config


class TestConfig:
    """Test configuration management."""
    
    def test_config_initialization(self):
        """Test config initialization with defaults."""
        config = Config()
        assert config.get("scraper.rate_limit.delay_between_requests") == 2.0
        assert config.get("scraper.browser.headless") is True
        assert config.get("storage.output_format") == "csv"
    
    def test_config_get_nested(self):
        """Test getting nested configuration values."""
        config = Config()
        rate_config = config.get("scraper.rate_limit")
        assert isinstance(rate_config, dict)
        assert "delay_between_requests" in rate_config
    
    def test_config_get_default(self):
        """Test getting default values for missing keys."""
        config = Config()
        assert config.get("nonexistent.key", "default") == "default"


class TestProductParser:
    """Test product parsing functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.parser = ProductParser()
    
    def test_extract_asin_from_url(self):
        """Test ASIN extraction from various URL formats."""
        test_urls = [
            "https://www.amazon.com/dp/B08N5WRWNW",
            "https://www.amazon.com/product/B08N5WRWNW",
            "https://www.amazon.com/gp/product/B08N5WRWNW",
            "https://www.amazon.com/some-page?ASIN=B08N5WRWNW"
        ]
        
        for url in test_urls:
            asin = self.parser._extract_asin(url)
            assert asin == "B08N5WRWNW"
    
    def test_extract_asin_invalid_url(self):
        """Test ASIN extraction from invalid URL."""
        invalid_url = "https://www.amazon.com/search?q=test"
        asin = self.parser._extract_asin(invalid_url)
        assert asin is None
    
    def test_parse_product_page_empty_html(self):
        """Test parsing empty HTML."""
        result = self.parser.parse_product_page("", "https://example.com")
        assert result is not None
        assert result["url"] == "https://example.com"
        assert result["asin"] is None


class TestDataStorage:
    """Test data storage functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.test_data_dir = Path("test_data")
        self.test_data_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        if self.test_data_dir.exists():
            shutil.rmtree(self.test_data_dir)
    
    def test_csv_storage(self):
        """Test CSV storage functionality."""
        storage = DataStorage(
            output_format="csv",
            output_directory=str(self.test_data_dir)
        )
        
        test_products = [
            {
                "asin": "B08N5WRWNW",
                "title": "Test Product",
                "price": "$29.99",
                "rating": 4.5,
                "url": "https://amazon.com/dp/B08N5WRWNW"
            }
        ]
        
        success = storage.save_products(test_products)
        assert success is True
        
        # Check if file was created
        csv_files = list(self.test_data_dir.glob("*.csv"))
        assert len(csv_files) > 0
    
    def test_json_storage(self):
        """Test JSON storage functionality."""
        storage = DataStorage(
            output_format="json",
            output_directory=str(self.test_data_dir)
        )
        
        test_products = [
            {
                "asin": "B08N5WRWNW",
                "title": "Test Product",
                "price": "$29.99",
                "rating": 4.5,
                "url": "https://amazon.com/dp/B08N5WRWNW"
            }
        ]
        
        success = storage.save_products(test_products)
        assert success is True
        
        # Check if file was created
        json_files = list(self.test_data_dir.glob("*.json"))
        assert len(json_files) > 0
    
    def test_storage_stats(self):
        """Test storage statistics."""
        storage = DataStorage(
            output_format="csv",
            output_directory=str(self.test_data_dir)
        )
        
        stats = storage.get_stats()
        assert "storage_type" in stats
        assert stats["storage_type"] == "csv"


@pytest.mark.asyncio
class TestAmazonScraper:
    """Test Amazon scraper functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        # Use test configuration
        self.config._config["scraper"]["browser"]["headless"] = True
        self.config._config["scraper"]["rate_limit"]["delay_between_requests"] = 0.1
    
    @pytest.mark.asyncio
    async def test_scraper_initialization(self):
        """Test scraper initialization."""
        scraper = AmazonScraper(self.config)
        assert scraper.config is not None
        assert scraper.parser is not None
        assert scraper.storage is not None
    
    @pytest.mark.asyncio
    async def test_scraper_context_manager(self):
        """Test scraper as async context manager."""
        async with AmazonScraper(self.config) as scraper:
            assert scraper is not None
            assert scraper.browser is not None  # Browser should be started
    
    @pytest.mark.asyncio
    async def test_scraper_start_stop(self):
        """Test scraper start and stop."""
        scraper = AmazonScraper(self.config)
        
        await scraper.start()
        assert scraper.browser is not None
        assert scraper.context is not None
        
        await scraper.close()
        assert scraper.browser is None
        assert scraper.context is None
    
    @pytest.mark.asyncio
    @patch('amzn_scraper.scraper.async_playwright')
    async def test_scraper_with_mock(self, mock_playwright):
        """Test scraper with mocked Playwright."""
        # Mock Playwright components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Create proper async mock for playwright
        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_playwright.return_value = mock_playwright_instance
        
        scraper = AmazonScraper(self.config)
        await scraper.start()
        
        assert scraper.browser is not None
        await scraper.close()


class TestIntegration:
    """Integration tests."""
    
    def test_parser_with_sample_html(self):
        """Test parser with sample HTML."""
        parser = ProductParser()
        
        sample_html = """
        <html>
            <head><title>Test Product</title></head>
            <body>
                <h1 id="productTitle">Test Product Title</h1>
                <span class="a-price-whole">29</span>
                <span class="a-icon-alt">4.5 out of 5 stars</span>
            </body>
        </html>
        """
        
        result = parser.parse_product_page(sample_html, "https://amazon.com/dp/B08N5WRWNW")
        
        assert result is not None
        assert result["title"] == "Test Product Title"
        assert result["asin"] == "B08N5WRWNW"


# Fixtures for pytest
@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    config = Config()
    config._config["scraper"]["browser"]["headless"] = True
    config._config["scraper"]["rate_limit"]["delay_between_requests"] = 0.1
    return config


@pytest.fixture
def sample_product_data():
    """Sample product data for testing."""
    return {
        "asin": "B08N5WRWNW",
        "title": "Test Product",
        "price": "$29.99",
        "rating": 4.5,
        "review_count": 1234,
        "availability": "In Stock",
        "description": "Test product description",
        "features": ["Feature 1", "Feature 2"],
        "images": ["https://example.com/image1.jpg"],
        "specifications": {"Brand": "Test Brand"},
        "brand": "Test Brand",
        "category": "Electronics",
        "seller": "Amazon.com",
        "shipping": "Free shipping",
        "url": "https://amazon.com/dp/B08N5WRWNW",
        "scraped_at": "2023-01-01T00:00:00"
    }


if __name__ == "__main__":
    pytest.main([__file__])
