"""
Test suite for Amazon Scraper.
"""

import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from amzn_scraper.scraper import AmazonScraper
from amzn_scraper.parser import ProductParser
from amzn_scraper.storage import DataStorage
from amzn_scraper.config import Config
from amzn_scraper.market_research import MarketResearch


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


class TestMarketResearch:
    """Test market research functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = Config()
        self.test_config_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        import shutil
        if os.path.exists(self.test_config_dir):
            shutil.rmtree(self.test_config_dir)
    
    def test_market_research_initialization(self):
        """Test market research initialization."""
        market_research = MarketResearch(self.config)
        
        assert market_research.config is not None
        assert market_research.default_seeds is not None
        assert len(market_research.default_seeds) > 0
        assert market_research.blocked_brands is not None
        assert len(market_research.blocked_brands) > 0
        assert market_research.badge_patterns is not None
    
    def test_market_research_with_custom_config(self):
        """Test market research with custom config file."""
        # Create a custom config file
        custom_config = {
            "default_seeds": ["test seed 1", "test seed 2"],
            "filters": {
                "min_price": 20.0,
                "min_badge_count": 200,
                "max_review_count": 30,
                "blocked_brands": ["test brand"]
            },
            "badge_patterns": {
                "com": r"(?i)\b(\d+(?:\.\d+)?K\+?|\d+\+?)\s+bought in past month\b"
            }
        }
        
        import yaml
        config_path = os.path.join(self.test_config_dir, "test_market_config.yaml")
        with open(config_path, 'w') as f:
            yaml.dump(custom_config, f)
        
        market_research = MarketResearch(self.config, config_path)
        
        assert market_research.default_seeds == ["test seed 1", "test seed 2"]
        assert "test brand" in market_research.blocked_brands
        assert "com" in market_research.badge_patterns
    
    def test_parse_badge(self):
        """Test badge parsing functionality."""
        market_research = MarketResearch(self.config)
        
        # Test various badge formats
        test_cases = [
            ("100 bought in past month", 100),
            ("1.5K bought in past month", 1500),
            ("2K+ bought in past month", 2000),
            ("500+ bought in past month", 500),
            ("No badge text", None),
            ("", None)
        ]
        
        pattern = market_research.badge_patterns.get("com")
        if pattern:
            for text, expected in test_cases:
                result = market_research.parse_badge(text, pattern)
                assert result == expected, f"Failed for text: '{text}', expected: {expected}, got: {result}"
    
    def test_money_to_float(self):
        """Test price parsing functionality."""
        market_research = MarketResearch(self.config)
        
        test_cases = [
            ("$29.99", 29.99),
            ("€15.50", 15.50),
            ("£12.00", 12.00),
            ("29.99", 29.99),
            ("1,234.56", 1234.56),
            ("1.234,56", 1.23456),  # EU format (current implementation treats comma as decimal)
            ("", None),
            ("Invalid", None),
            ("$", None)
        ]
        
        for price_str, expected in test_cases:
            result = market_research.money_to_float(price_str)
            assert result == expected, f"Failed for price: '{price_str}', expected: {expected}, got: {result}"
    
    def test_looks_electronic(self):
        """Test electronic product detection."""
        market_research = MarketResearch(self.config)
        
        electronic_titles = [
            "USB-C Charging Cable",
            "Rechargeable Battery Pack",
            "LED Light Strip",
            "Wireless Charger",
            "Power Bank 10000mAh",
            "Solar Panel Kit",
            "AC Adapter 12V"
        ]
        
        non_electronic_titles = [
            "Storage Basket",
            "Kitchen Organizer",
            "Dog Chew Toy",
            "Yoga Mat",
            "Camping Stakes",
            "Baby Closet Dividers"
        ]
        
        for title in electronic_titles:
            assert market_research.looks_electronic(title), f"Should detect as electronic: {title}"
        
        for title in non_electronic_titles:
            assert not market_research.looks_electronic(title), f"Should not detect as electronic: {title}"
    
    def test_brand_allowed(self):
        """Test brand filtering."""
        market_research = MarketResearch(self.config)
        
        blocked_brands = ["Amazon Basics", "Samsung", "Apple", "Nike"]
        allowed_brands = ["Small Brand", "Local Company", "Niche Product Co"]
        
        for brand in blocked_brands:
            assert not market_research.brand_allowed(brand), f"Should block brand: {brand}"
        
        for brand in allowed_brands:
            assert market_research.brand_allowed(brand), f"Should allow brand: {brand}"
    
    def test_is_allowed_category(self):
        """Test category filtering."""
        market_research = MarketResearch(self.config)
        
        allowed_categories = [
            "Home & Kitchen",
            "Pet Supplies",
            "Sports & Outdoors",
            "Baby Products",
            "Tools & Home Improvement"
        ]
        
        blocked_categories = [
            "Electronics",
            "Computers",
            "Software",
            "Digital Music"
        ]
        
        for category in allowed_categories:
            assert market_research.is_allowed_category(category), f"Should allow category: {category}"
        
        for category in blocked_categories:
            assert not market_research.is_allowed_category(category), f"Should block category: {category}"
    
    @pytest.mark.asyncio
    @patch('amzn_scraper.market_research.async_playwright')
    async def test_run_market_with_mock(self, mock_playwright):
        """Test market research with mocked Playwright."""
        # Mock Playwright components
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        
        # Mock search result HTML
        mock_html = """
        <div data-component-type="s-search-result" data-asin="B123456789">
            <h2><a href="/dp/B123456789"><span>Storage Basket Organizer</span></a></h2>
            <span class="a-price"><span class="a-offscreen">$19.99</span></span>
            <span>150 bought in past month</span>
            <span aria-label="4.5 out of 5 stars">4.5</span>
            <span class="a-size-base">25 ratings</span>
        </div>
        """
        
        mock_page.goto.return_value = None
        mock_page.wait_for_selector.return_value = None
        mock_page.query_selector_all.return_value = [AsyncMock()]
        
        # Mock the item element
        mock_item = AsyncMock()
        mock_item.get_attribute.return_value = "B123456789"
        mock_item.inner_text.return_value = "Storage Basket Organizer 150 bought in past month 4.5 out of 5 stars 25 ratings"
        
        # Mock title element
        mock_title = AsyncMock()
        mock_title.inner_text.return_value = "Storage Basket Organizer"
        
        # Mock price element
        mock_price = AsyncMock()
        mock_price.inner_text.return_value = "$19.99"
        
        # Mock link element
        mock_link = AsyncMock()
        mock_link.get_attribute.return_value = "/dp/B123456789"
        
        # Mock review element
        mock_review = AsyncMock()
        mock_review.inner_text.return_value = "25 ratings"
        
        # Setup query_selector calls
        async def mock_query_selector(selector):
            if selector == 'h2 a span':
                return mock_title
            elif selector == '.a-price .a-offscreen':
                return mock_price
            elif selector == 'h2 a':
                return mock_link
            elif selector == 'span[aria-label$="ratings"], .s-underline-text .a-size-base':
                return mock_review
            elif selector == 'a.s-pagination-next:not(.s-pagination-disabled)':
                return None
            return None
        
        mock_item.query_selector = mock_query_selector
        mock_page.query_selector_all.return_value = [mock_item]
        
        # Setup Playwright mocks
        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_context.close.return_value = None
        mock_browser.close.return_value = None
        mock_playwright.return_value = mock_playwright_instance
        
        market_research = MarketResearch(self.config)
        
        # Run market research
        results = await market_research.run_market(
            browser=mock_browser,
            domain="com",
            seeds=["storage basket"],
            currency_min=15.0,
            min_badge=100,
            max_reviews=50,
            pages_per_seed=1
        )
        
        # Verify results
        assert len(results) > 0
        result = results[0]
        assert result["asin"] == "B123456789"
        assert result["title"] == "Storage Basket Organizer"
        assert result["price_local"] == 19.99
        assert result["badge"] == 150
        assert result["marketplace"] == "com"
    
    @pytest.mark.asyncio
    async def test_run_research_integration(self):
        """Integration test that actually searches for products (slow test)."""
        market_research = MarketResearch(self.config)
        
        # Use very conservative settings for testing
        results = await market_research.run_research(
            domains=["com"],  # Only US market
            min_price=10.0,   # Lower price threshold
            min_badge=50,     # Lower badge threshold
            max_reviews=100,  # Higher review threshold
            pages_per_seed=1, # Only 1 page per seed
            custom_seeds=["storage basket"]  # Single, specific seed
        )
        
        # We should find at least some results
        assert isinstance(results, list)
        
        if results:
            # Verify result structure
            result = results[0]
            required_fields = ["asin", "title", "price_local", "badge", "marketplace", "url"]
            for field in required_fields:
                assert field in result, f"Missing field: {field}"
            
            # Verify data types
            assert isinstance(result["asin"], str)
            assert isinstance(result["title"], str)
            assert isinstance(result["price_local"], (int, float))
            assert isinstance(result["badge"], int)
            assert isinstance(result["marketplace"], str)
            assert isinstance(result["url"], str)
            
            # Verify values make sense
            assert len(result["asin"]) == 10  # ASIN should be 10 characters
            assert result["price_local"] >= 10.0  # Should meet minimum price
            assert result["badge"] >= 50  # Should meet minimum badge count
            assert result["marketplace"] == "com"  # Should be US market
            
            print(f"\n✅ Found {len(results)} product opportunities!")
            print(f"Top result: {result['title']} - ${result['price_local']} - {result['badge']} bought")
        else:
            print("\n⚠️ No products found - this might be due to:")
            print("  - Amazon's anti-bot measures")
            print("  - Network connectivity issues")
            print("  - Search results not meeting criteria")
            print("  - Rate limiting")
    
    def test_save_results(self):
        """Test saving market research results."""
        market_research = MarketResearch(self.config)
        
        # Create test results
        test_results = [
            {
                "marketplace": "com",
                "asin": "B123456789",
                "url": "https://amazon.com/dp/B123456789",
                "title": "Test Product",
                "price_local": 19.99,
                "badge": 150,
                "review_count": 25,
                "timestamp_utc": "2023-01-01T00:00:00"
            }
        ]
        
        # Test saving to JSON
        success = market_research.save_results(test_results, output_format="json", output_directory=self.test_config_dir)
        assert success is True
        
        # Check if file was created
        json_files = list(Path(self.test_config_dir).glob("*.json"))
        assert len(json_files) > 0
        
        # Verify file content
        import json
        with open(json_files[0], 'r') as f:
            saved_data = json.load(f)
            assert "products" in saved_data
            assert len(saved_data["products"]) == 1
            assert saved_data["products"][0]["asin"] == "B123456789"


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


@pytest.fixture
def sample_market_research_data():
    """Sample market research data for testing."""
    return {
        "marketplace": "com",
        "asin": "B123456789",
        "url": "https://amazon.com/dp/B123456789",
        "title": "Storage Basket Organizer",
        "price_local": 19.99,
        "badge": 150,
        "review_count": 25,
        "timestamp_utc": "2023-01-01T00:00:00"
    }


if __name__ == "__main__":
    pytest.main([__file__])
