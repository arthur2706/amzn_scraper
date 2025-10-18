"""
Market research module for finding product opportunities.
"""

import re
import time
import json
import random
import asyncio
import yaml
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .config import Config


class MarketResearch:
    """Market research tool for finding product opportunities."""
    
    def __init__(self, config: Config, market_config_path: Optional[str] = None):
        """Initialize market research."""
        self.config = config
        
        # Load market research specific configuration
        self.market_config = self._load_market_config(market_config_path)
        
        # Badge patterns for different Amazon domains
        self.badge_patterns = {}
        for domain, pattern_str in self.market_config.get("badge_patterns", {}).items():
            self.badge_patterns[domain] = re.compile(pattern_str)
        
        # Pattern to identify electronic products
        electronic_patterns = self.market_config.get("electronic_patterns", [])
        if electronic_patterns:
            pattern_str = "|".join(electronic_patterns)
            self.electric_block = re.compile(f"({pattern_str})", re.I)
        else:
            # Fallback to default pattern
            self.electric_block = re.compile(
                r'(battery|batteries|rechargeable|usb|usb[-\s]?c|type[-\s]?c|led|watt|mAh|power bank|solar|adapter|charger|charging|\bAC\b|\bDC\b|plug|cord|cable|\b12v\b|\b24v\b|\b110v\b|\b220v\b)',
                re.I
            )
        
        # Default search seeds
        self.default_seeds = self.market_config.get("default_seeds", [
            "storage basket", "organizer bins", "adhesive hooks", "drawer organizer",
            "dog chew toy", "pet grooming glove", "cat litter mat",
            "yoga blocks", "resistance bands non slip", "camping stakes",
            "industrial wipes", "desiccant packets", "lab beaker set",
            "baby closet dividers", "stroller hook", "toddler balance stones"
        ])
        
        # Blocked brands
        self.blocked_brands = set(self.market_config.get("filters", {}).get("blocked_brands", [
            'amazon basics', 'philips', 'samsung', 'apple', 'bosch', 'black decker', 
            'dewalt', 'makita', 'nike', 'adidas', 'reebok', 'under armour', 
            'tommy hilfiger', 'levi s', 'dyson', '3m', 'scotch', 'gorilla', 
            'command', 'oxo', 'stanley', 'milwaukee', 'karcher', 'lenovo', 'logitech'
        ]))
        
        # Allowed categories
        self.allowed_categories = self.market_config.get("allowed_categories", [
            'home', 'kitchen', 'household', 'home & kitchen',
            'home & garden', 'garden', 'tools', 'tool',
            'pet', 'baby', 'toys', 'sports', 'outdoors',
            'industrial', 'scientific', 'smart home', 'diy',
            'patio, lawn & garden', 'toys & games', 'baby products',
            'sports & outdoors'
        ])
    
    def _load_market_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load market research configuration from YAML file."""
        if config_path is None:
            # Look for market_research.yaml in the project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "market_research.yaml"
        
        config_path = Path(config_path)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            except Exception as e:
                print(f"Warning: Could not load market research config from {config_path}: {e}")
                print("Using default market research configuration.")
        
        # Return default configuration if file doesn't exist or can't be loaded
        return {
            "default_seeds": [
                "storage basket", "organizer bins", "adhesive hooks", "drawer organizer",
                "dog chew toy", "pet grooming glove", "cat litter mat",
                "yoga blocks", "resistance bands non slip", "camping stakes",
                "industrial wipes", "desiccant packets", "lab beaker set",
                "baby closet dividers", "stroller hook", "toddler balance stones"
            ],
            "filters": {
                "min_price": 15.0,
                "min_badge_count": 100,
                "max_review_count": 50,
                "pages_per_seed": 7,
                "exclude_electronics": True,
                "blocked_brands": [
                    'amazon basics', 'philips', 'samsung', 'apple', 'bosch', 'black decker', 
                    'dewalt', 'makita', 'nike', 'adidas', 'reebok', 'under armour', 
                    'tommy hilfiger', 'levi s', 'dyson', '3m', 'scotch', 'gorilla', 
                    'command', 'oxo', 'stanley', 'milwaukee', 'karcher', 'lenovo', 'logitech'
                ]
            },
            "badge_patterns": {
                "com": r"(?i)\b(\d+(?:\.\d+)?K\+?|\d+\+?)\s+bought in past month\b",
                "co.uk": r"(?i)\b(\d+(?:\.\d+)?K\+?|\d+\+?)\s+bought in past month\b",
                "de": r"(?i)\b(\d+(?:\.\d+)?K\+?|\d+\+?)\s*mal im letzten monat gekauft\b",
                "fr": r"(?i)\b(\d+(?:\.\d+)?K\+?|\d+\+?)\s*achet[ée] au cours du dernier mois\b"
            },
            "electronic_patterns": [
                "battery", "batteries", "rechargeable", "usb", "usb[-\s]?c", "type[-\s]?c",
                "led", "watt", "mAh", "power bank", "solar", "adapter", "charger", "charging",
                "\\bAC\\b", "\\bDC\\b", "plug", "cord", "cable", "\\b12v\\b", "\\b24v\\b", "\\b110v\\b", "\\b220v\\b"
            ],
            "allowed_categories": [
                'home', 'kitchen', 'household', 'home & kitchen',
                'home & garden', 'garden', 'tools', 'tool',
                'pet', 'baby', 'toys', 'sports', 'outdoors',
                'industrial', 'scientific', 'smart home', 'diy',
                'patio, lawn & garden', 'toys & games', 'baby products',
                'sports & outdoors'
            ]
        }
    
    def parse_badge(self, text: str, pattern: re.Pattern) -> Optional[int]:
        """Parse badge count from text."""
        if not text:
            return None
        
        match = pattern.search(text)
        if not match:
            return None
        
        raw = match.group(1).lower().replace('+', '')
        val = float(raw.replace('k', '').replace(',', '.'))
        if 'k' in raw:
            val *= 1000
        
        return int(val)
    
    def money_to_float(self, price_str: str) -> Optional[float]:
        """Convert price string to float."""
        if not price_str:
            return None
        
        price_str = price_str.strip()
        # Remove currency symbols and non-digits except comma, period, minus
        cleaned = re.sub(r'[^\d,.\-]', '', price_str)
        
        # Handle different decimal/thousands separators
        if cleaned.count(',') and cleaned.count('.'):
            # Both present - determine format based on context
            if '€' in price_str or 'amazon.de' in price_str or 'amazon.fr' in price_str or 'amazon.co.uk' in price_str:
                # EU format: 1.234,56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                # US format: 1,234.56
                cleaned = cleaned.replace(',', '')
        else:
            # Single delimiter - treat comma as decimal
            cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except ValueError:
            return None
    
    def is_allowed_category(self, breadcrumb_text: str) -> bool:
        """Check if category is allowed."""
        if not breadcrumb_text:
            return False
        
        text = breadcrumb_text.lower()
        allowed_categories = [
            'home', 'kitchen', 'household', 'home & kitchen',
            'home & garden', 'garden', 'tools', 'tool',
            'pet', 'baby', 'toys', 'sports', 'outdoors',
            'industrial', 'scientific', 'smart home', 'diy',
            'patio, lawn & garden', 'toys & games', 'baby products',
            'sports & outdoors'
        ]
        
        return any(category in text for category in allowed_categories)
    
    def looks_electronic(self, title: str) -> bool:
        """Check if product looks electronic."""
        return bool(self.electric_block.search(title or ''))
    
    def normalize_brand(self, brand: str) -> str:
        """Normalize brand name."""
        return re.sub(r'[^a-z0-9]+', ' ', (brand or '').lower()).strip()
    
    def brand_allowed(self, brand: str) -> bool:
        """Check if brand is allowed."""
        normalized = self.normalize_brand(brand)
        return normalized and normalized not in self.blocked_brands and len(normalized) > 1
    
    async def run_market(self, browser: Browser, domain: str, seeds: List[str], 
                        currency_min: float, min_badge: int, max_reviews: int, 
                        pages_per_seed: int) -> List[Dict[str, Any]]:
        """Run market research for a specific domain."""
        base_url = f"https://www.amazon.{domain}"
        results = []
        
        context = await browser.new_context(locale="en-US")
        page = await context.new_page()
        
        try:
            for query in seeds:
                print(f"  Searching '{query}' on amazon.{domain}...")
                url = f"{base_url}/s?k={query.replace(' ', '+')}"
                next_url = url
                
                for page_num in range(1, pages_per_seed + 1):
                    try:
                        await page.goto(next_url, timeout=60000)
                        await page.wait_for_selector('[data-component-type="s-search-result"]', timeout=30000)
                        
                        items = await page.query_selector_all('[data-component-type="s-search-result"]')
                        
                        for item in items:
                            try:
                                asin = await item.get_attribute('data-asin')
                                if not asin:
                                    continue
                                
                                # Get title
                                title_element = await item.query_selector('h2 a span')
                                if not title_element:
                                    continue
                                title = await title_element.inner_text()
                                title = title.strip()
                                
                                # Skip electronic products
                                if self.looks_electronic(title):
                                    continue
                                
                                # Get price
                                price_element = await item.query_selector('.a-price .a-offscreen')
                                price_text = ""
                                if price_element:
                                    price_text = await price_element.inner_text()
                                
                                price = self.money_to_float(price_text)
                                if price is None or price < currency_min:
                                    continue
                                
                                # Get badge count
                                item_text = await item.inner_text()
                                badge = self.parse_badge(item_text.lower(), self.badge_patterns[domain])
                                if not badge or badge < min_badge:
                                    continue
                                
                                # Get review count
                                review_element = await item.query_selector('span[aria-label$="ratings"], .s-underline-text .a-size-base')
                                review_text = ""
                                if review_element:
                                    review_text = await review_element.inner_text()
                                
                                review_count = None
                                match = re.search(r'\d[\d,\.]*', review_text)
                                if match:
                                    review_count = int(re.sub(r'[^\d]', '', match.group(0)) or 0)
                                
                                if review_count is not None and review_count >= max_reviews:
                                    continue
                                
                                # Get product URL
                                link_element = await item.query_selector('h2 a')
                                if not link_element:
                                    continue
                                
                                href = await link_element.get_attribute('href')
                                if not href:
                                    continue
                                
                                product_url = urljoin(base_url, href)
                                
                                results.append({
                                    "marketplace": domain,
                                    "asin": asin,
                                    "url": product_url,
                                    "title": title,
                                    "price_local": price,
                                    "badge": badge,
                                    "review_count": review_count,
                                    "timestamp_utc": datetime.now(timezone.utc).isoformat()
                                })
                                
                            except Exception as e:
                                print(f"    Error processing item: {e}")
                                continue
                        
                        # Check for next page
                        next_element = await page.query_selector('a.s-pagination-next:not(.s-pagination-disabled)')
                        if not next_element:
                            break
                        
                        next_href = await next_element.get_attribute('href')
                        if not next_href:
                            break
                        
                        next_url = urljoin(base_url, next_href)
                        
                        # Rate limiting
                        await asyncio.sleep(0.8 + random.random() * 0.8)
                        
                    except Exception as e:
                        print(f"    Error on page {page_num}: {e}")
                        break
                
                print(f"    Found {len([r for r in results if r['marketplace'] == domain])} opportunities so far")
        
        finally:
            await context.close()
        
        return results
    
    async def run_research(self, domains: List[str], min_price: float = 15.0, 
                          min_badge: int = 100, max_reviews: int = 50, 
                          pages_per_seed: int = 7, custom_seeds: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Run market research across multiple domains."""
        seeds = custom_seeds if custom_seeds else self.default_seeds
        all_results = []
        
        playwright = None
        browser = None
        
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=self.config.get("scraper.browser.headless", True),
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
            
            for domain in domains:
                try:
                    print(f"Researching amazon.{domain}...")
                    domain_results = await self.run_market(
                        browser, domain, seeds, min_price, min_badge, max_reviews, pages_per_seed
                    )
                    all_results.extend(domain_results)
                    print(f"  Found {len(domain_results)} opportunities on amazon.{domain}")
                except Exception as e:
                    print(f"  Error researching amazon.{domain}: {e}")
                    continue
        
        finally:
            if browser:
                await browser.close()
            if playwright:
                await playwright.stop()
        
        # Sort by badge count (sales volume) descending
        all_results.sort(key=lambda x: x.get('badge', 0), reverse=True)
        
        return all_results
    
    def save_results(self, results: List[Dict[str, Any]], output_format: str = "json", 
                    output_directory: str = "data") -> bool:
        """Save research results to file."""
        try:
            from .storage import DataStorage
            
            storage = DataStorage(output_format=output_format, output_directory=output_directory)
            
            # Convert to product format for storage
            products = []
            for result in results:
                products.append({
                    'asin': result.get('asin'),
                    'title': result.get('title'),
                    'price': f"${result.get('price_local', 0):.2f}",
                    'rating': None,
                    'review_count': result.get('review_count'),
                    'availability': None,
                    'description': f"Market research opportunity - {result.get('badge', 0)} bought in past month",
                    'features': [],
                    'images': [],
                    'specifications': {
                        'marketplace': result.get('marketplace'),
                        'badge_count': result.get('badge'),
                        'research_timestamp': result.get('timestamp_utc')
                    },
                    'brand': None,
                    'category': None,
                    'seller': None,
                    'shipping': None,
                    'url': result.get('url'),
                    'scraped_at': result.get('timestamp_utc')
                })
            
            return storage.save_products(products)
        
        except Exception as e:
            print(f"Error saving results: {e}")
            return False
