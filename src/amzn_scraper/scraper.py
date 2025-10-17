"""
Main Amazon scraper using Playwright.
"""

import asyncio
import random
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from fake_useragent import UserAgent

from .config import Config
from .parser import ProductParser
from .storage import DataStorage


class AmazonScraper:
    """Main Amazon scraper class using Playwright."""
    
    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the Amazon scraper.
        
        Args:
            config: Configuration object. If None, uses default config.
        """
        self.config = config or Config()
        self.parser = ProductParser()
        self.storage = DataStorage(
            output_format=self.config.get("storage.output_format", "csv"),
            output_directory=self.config.get("storage.output_directory", "data"),
            database_config=self.config.get("storage.database", {})
        )
        
        # Initialize browser components
        self.playwright = None
        self.browser = None
        self.context = None
        
        # Rate limiting
        self.last_request_time = 0
        self.request_count = 0
        self.request_window_start = time.time()
        
        # User agent
        self.ua = UserAgent()
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = self.config.get("logging.level", "INFO")
        log_format = self.config.get("logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        log_file = self.config.get("logging.file", "logs/scraper.log")
        
        # Create logs directory if it doesn't exist
        Path(log_file).parent.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def start(self):
        """Start the browser and initialize Playwright."""
        self.logger.info("Starting Amazon scraper...")
        
        self.playwright = await async_playwright().start()
        
        # Browser configuration
        browser_config = self.config.get("scraper.browser", {})
        headless = browser_config.get("headless", True)
        viewport = browser_config.get("viewport", {"width": 1920, "height": 1080})
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--no-first-run',
                '--disable-default-apps',
                '--disable-extensions'
            ]
        )
        
        # Create context with settings
        context_options = {
            'viewport': viewport,
            'user_agent': self._get_user_agent(),
            'locale': 'en-US',
            'timezone_id': 'America/New_York'
        }
        
        # Add proxy if configured
        proxy_config = self.config.get("proxy", {})
        if proxy_config.get("enabled", False):
            proxy_url = self._get_proxy()
            if proxy_url:
                context_options['proxy'] = {'server': proxy_url}
        
        self.context = await self.browser.new_context(**context_options)
        
        # Add stealth settings
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        self.logger.info("Browser started successfully")
    
    async def close(self):
        """Close browser and cleanup resources."""
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
        
        self.storage.close()
        self.logger.info("Scraper closed")
    
    def _get_user_agent(self) -> str:
        """Get user agent string."""
        user_agent_config = self.config.get("scraper.browser.user_agent", "auto")
        
        if user_agent_config == "auto":
            return self.ua.random
        else:
            return user_agent_config
    
    def _get_proxy(self) -> Optional[str]:
        """Get proxy URL for rotation."""
        proxy_config = self.config.get("proxy", {})
        proxies = proxy_config.get("proxies", [])
        
        if proxies and proxy_config.get("rotation", True):
            return random.choice(proxies)
        elif proxies:
            return proxies[0]
        
        return None
    
    async def _rate_limit(self):
        """Apply rate limiting between requests."""
        rate_config = self.config.get("scraper.rate_limit", {})
        delay = rate_config.get("delay_between_requests", 2.0)
        max_requests = rate_config.get("max_requests_per_minute", 30)
        random_range = rate_config.get("random_delay_range", [0.5, 1.5])
        
        # Check requests per minute limit
        current_time = time.time()
        if current_time - self.request_window_start >= 60:
            self.request_count = 0
            self.request_window_start = current_time
        
        if self.request_count >= max_requests:
            sleep_time = 60 - (current_time - self.request_window_start)
            if sleep_time > 0:
                self.logger.info(f"Rate limit reached. Sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
                self.request_count = 0
                self.request_window_start = time.time()
        
        # Apply delay between requests
        if self.last_request_time > 0:
            elapsed = current_time - self.last_request_time
            if elapsed < delay:
                sleep_time = delay - elapsed
                # Add random delay
                random_delay = random.uniform(*random_range)
                sleep_time += random_delay
                
                self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    async def _create_page(self) -> Page:
        """Create a new page with proper settings."""
        page = await self.context.new_page()
        
        # Set timeout
        timeout = self.config.get("scraper.browser.timeout", 30000)
        page.set_default_timeout(timeout)
        
        # Block unnecessary resources to speed up loading
        await page.route("**/*", lambda route: (
            route.abort() if route.request.resource_type in ["image", "stylesheet", "font"] 
            else route.continue_()
        ))
        
        return page
    
    async def scrape_product(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single product page.
        
        Args:
            url: Amazon product URL
            
        Returns:
            Product data dictionary or None if failed
        """
        if not self.browser:
            await self.start()
        
        await self._rate_limit()
        
        retry_config = self.config.get("scraper.retry", {})
        max_retries = retry_config.get("max_retries", 3)
        retry_delay = retry_config.get("retry_delay", 5.0)
        exponential_backoff = retry_config.get("exponential_backoff", True)
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Scraping product: {url} (attempt {attempt + 1})")
                
                page = await self._create_page()
                
                # Navigate to product page
                response = await page.goto(url, wait_until="domcontentloaded")
                
                if not response or response.status >= 400:
                    self.logger.warning(f"Failed to load page: {response.status if response else 'No response'}")
                    await page.close()
                    continue
                
                # Wait for content to load
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # Get page content
                html = await page.content()
                await page.close()
                
                # Parse product data
                product_data = self.parser.parse_product_page(html, url)
                
                if product_data and product_data.get('title'):
                    self.logger.info(f"Successfully scraped product: {product_data.get('title', 'Unknown')}")
                    return product_data
                else:
                    self.logger.warning("No product data extracted")
                    
            except Exception as e:
                self.logger.error(f"Error scraping product (attempt {attempt + 1}): {e}")
                
                if attempt < max_retries:
                    sleep_time = retry_delay
                    if exponential_backoff:
                        sleep_time *= (2 ** attempt)
                    
                    self.logger.info(f"Retrying in {sleep_time} seconds...")
                    await asyncio.sleep(sleep_time)
                else:
                    self.logger.error(f"Failed to scrape product after {max_retries + 1} attempts")
        
        return None
    
    async def scrape_products(self, urls: List[str]) -> List[Dict[str, Any]]:
        """
        Scrape multiple product pages.
        
        Args:
            urls: List of Amazon product URLs
            
        Returns:
            List of product data dictionaries
        """
        self.logger.info(f"Starting to scrape {len(urls)} products")
        
        products = []
        failed_urls = []
        
        for i, url in enumerate(urls, 1):
            self.logger.info(f"Progress: {i}/{len(urls)}")
            
            product_data = await self.scrape_product(url)
            if product_data:
                products.append(product_data)
            else:
                failed_urls.append(url)
        
        self.logger.info(f"Scraping completed. Success: {len(products)}, Failed: {len(failed_urls)}")
        
        if failed_urls:
            self.logger.warning(f"Failed URLs: {failed_urls}")
        
        return products
    
    async def search_products(self, query: str, max_pages: int = 1) -> List[Dict[str, Any]]:
        """
        Search for products and scrape results.
        
        Args:
            query: Search query
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of product data dictionaries
        """
        if not self.browser:
            await self.start()
        
        base_url = self.config.get("amazon.base_url", "https://www.amazon.com")
        search_url = f"{base_url}/s?k={query.replace(' ', '+')}"
        
        self.logger.info(f"Searching for: {query}")
        
        all_products = []
        
        for page_num in range(max_pages):
            await self._rate_limit()
            
            try:
                page = await self._create_page()
                
                # Navigate to search page
                if page_num > 0:
                    url = f"{search_url}&page={page_num + 1}"
                else:
                    url = search_url
                
                response = await page.goto(url, wait_until="domcontentloaded")
                
                if not response or response.status >= 400:
                    self.logger.warning(f"Failed to load search page: {response.status if response else 'No response'}")
                    await page.close()
                    break
                
                # Wait for search results to load
                await page.wait_for_load_state("networkidle", timeout=10000)
                
                # Get page content
                html = await page.content()
                await page.close()
                
                # Parse search results
                search_results = self.parser.parse_search_results(html)
                
                if search_results:
                    self.logger.info(f"Found {len(search_results)} products on page {page_num + 1}")
                    all_products.extend(search_results)
                else:
                    self.logger.info(f"No products found on page {page_num + 1}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error searching products (page {page_num + 1}): {e}")
                break
        
        self.logger.info(f"Search completed. Found {len(all_products)} products")
        return all_products
    
    async def scrape_and_save(self, urls: List[str]) -> bool:
        """
        Scrape products and save to storage.
        
        Args:
            urls: List of Amazon product URLs
            
        Returns:
            True if successful, False otherwise
        """
        products = await self.scrape_products(urls)
        
        if products:
            success = self.storage.save_products(products)
            if success:
                self.logger.info(f"Saved {len(products)} products to storage")
                return True
            else:
                self.logger.error("Failed to save products to storage")
                return False
        else:
            self.logger.warning("No products to save")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraper and storage statistics."""
        storage_stats = self.storage.get_stats()
        
        return {
            'storage_stats': storage_stats,
            'config': {
                'output_format': self.config.get("storage.output_format"),
                'rate_limit_delay': self.config.get("scraper.rate_limit.delay_between_requests"),
                'max_retries': self.config.get("scraper.retry.max_retries"),
                'proxy_enabled': self.config.get("proxy.enabled")
            }
        }
