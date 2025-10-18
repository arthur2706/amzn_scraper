"""
Product data parser for Amazon pages.
"""

import re
import json
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs


class ProductParser:
    """Parser for extracting product data from Amazon pages."""
    
    def __init__(self):
        """Initialize the parser."""
        self.price_patterns = [
            r'\$[\d,]+\.?\d*',
            r'€[\d,]+\.?\d*',
            r'£[\d,]+\.?\d*',
            r'¥[\d,]+\.?\d*'
        ]
    
    def parse_product_page(self, html: str, url: str) -> Dict[str, Any]:
        """
        Parse product data from Amazon product page HTML.
        
        Args:
            html: HTML content of the product page
            url: URL of the product page
            
        Returns:
            Dictionary containing extracted product data
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        product_data = {
            'url': url,
            'asin': self._extract_asin(url),
            'title': self._extract_title(soup),
            'price': self._extract_price(soup),
            'rating': self._extract_rating(soup),
            'review_count': self._extract_review_count(soup),
            'availability': self._extract_availability(soup),
            'description': self._extract_description(soup),
            'features': self._extract_features(soup),
            'images': self._extract_images(soup),
            'specifications': self._extract_specifications(soup),
            'brand': self._extract_brand(soup),
            'category': self._extract_category(soup),
            'seller': self._extract_seller(soup),
            'shipping': self._extract_shipping(soup),
            'scraped_at': self._get_current_timestamp()
        }
        
        return product_data
    
    def _extract_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from Amazon URL."""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/product/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'ASIN=([A-Z0-9]{10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product title."""
        selectors = [
            '#productTitle',
            'h1.a-size-large',
            'h1[data-automation-id="product-title"]',
            '.product-title',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product price."""
        selectors = [
            '.a-price-whole',
            '.a-price .a-offscreen',
            '#priceblock_dealprice',
            '#priceblock_ourprice',
            '.a-price-range',
            '[data-automation-id="product-price"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                # Clean up price text
                for pattern in self.price_patterns:
                    match = re.search(pattern, price_text)
                    if match:
                        return match.group(0)
                return price_text
        
        # Fallback: search for price patterns in the entire page
        page_text = soup.get_text()
        for pattern in self.price_patterns:
            matches = re.findall(pattern, page_text)
            if matches:
                return matches[0]
        
        return None
    
    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        """Extract product rating."""
        selectors = [
            '.a-icon-alt',
            '[data-automation-id="product-rating"]',
            '.a-star-mini .a-icon-alt'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                rating_text = element.get_text(strip=True)
                # Extract numeric rating from text like "4.5 out of 5 stars"
                match = re.search(r'(\d+\.?\d*)\s*out of 5', rating_text)
                if match:
                    return float(match.group(1))
        
        return None
    
    def _extract_review_count(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract number of reviews."""
        selectors = [
            '#acrCustomerReviewText',
            '[data-automation-id="review-count"]',
            '.a-size-base'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                review_text = element.get_text(strip=True)
                # Extract number from text like "1,234 ratings"
                match = re.search(r'([\d,]+)', review_text)
                if match:
                    return int(match.group(1).replace(',', ''))
        
        return None
    
    def _extract_availability(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product availability."""
        selectors = [
            '#availability span',
            '.a-size-medium.a-color-success',
            '.a-size-medium.a-color-price',
            '[data-automation-id="availability"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product description."""
        selectors = [
            '#feature-bullets ul',
            '.a-unordered-list',
            '#productDescription',
            '.product-description'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def _extract_features(self, soup: BeautifulSoup) -> List[str]:
        """Extract product features/bullet points."""
        features = []
        selectors = [
            '#feature-bullets li span',
            '.a-unordered-list li span',
            '.feature-bullets li'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 10:  # Filter out short/empty items
                    features.append(text)
        
        return features[:10]  # Limit to first 10 features
    
    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        """Extract product images."""
        images = []
        selectors = [
            '#landingImage',
            '.a-dynamic-image',
            '.a-spacing-small img'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                src = element.get('src') or element.get('data-src')
                if src and src.startswith('http'):
                    images.append(src)
        
        return list(set(images))[:5]  # Remove duplicates and limit to 5
    
    def _extract_specifications(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract product specifications."""
        specs = {}
        
        # Look for specification tables
        spec_tables = soup.select('#productDetails_techSpec_section_1 tr')
        for row in spec_tables:
            cells = row.select('td')
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    specs[key] = value
        
        return specs
    
    def _extract_brand(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product brand."""
        selectors = [
            '#bylineInfo',
            '.a-size-base.a-color-secondary',
            '[data-automation-id="brand-name"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                brand_text = element.get_text(strip=True)
                # Clean up brand text
                brand_text = re.sub(r'^Visit the\s+', '', brand_text)
                brand_text = re.sub(r'\s+Store$', '', brand_text)
                return brand_text
        
        return None
    
    def _extract_category(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product category."""
        breadcrumb = soup.select_one('#wayfinding-breadcrumbs_feature_div')
        if breadcrumb:
            links = breadcrumb.select('a')
            if links:
                return links[-1].get_text(strip=True)
        
        return None
    
    def _extract_seller(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract seller information."""
        selectors = [
            '#merchant-info',
            '.a-size-small.a-color-secondary',
            '[data-automation-id="seller-name"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                seller_text = element.get_text(strip=True)
                # Extract seller name from text like "Sold by Amazon.com"
                match = re.search(r'Sold by\s+(.+)', seller_text)
                if match:
                    return match.group(1)
                return seller_text
        
        return None
    
    def _extract_shipping(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract shipping information."""
        selectors = [
            '#delivery-block',
            '.a-size-small.a-color-secondary',
            '[data-automation-id="shipping-info"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        return None
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def parse_search_results(self, html: str) -> List[Dict[str, Any]]:
        """
        Parse search results page.
        
        Args:
            html: HTML content of search results page
            
        Returns:
            List of product data dictionaries
        """
        soup = BeautifulSoup(html, 'html.parser')
        products = []
        
        # Find product containers
        product_containers = soup.select('[data-component-type="s-search-result"]')
        
        for container in product_containers:
            product_data = {
                'title': self._extract_title_from_container(container),
                'price': self._extract_price_from_container(container),
                'rating': self._extract_rating_from_container(container),
                'review_count': self._extract_review_count_from_container(container),
                'image': self._extract_image_from_container(container),
                'url': self._extract_url_from_container(container),
                'asin': self._extract_asin_from_container(container)
            }
            
            if product_data['title']:  # Only add if we found a title
                products.append(product_data)
        
        return products
    
    def _extract_title_from_container(self, container: BeautifulSoup) -> Optional[str]:
        """Extract title from search result container."""
        title_element = container.select_one('h2 a span')
        if title_element:
            return title_element.get_text(strip=True)
        return None
    
    def _extract_price_from_container(self, container: BeautifulSoup) -> Optional[str]:
        """Extract price from search result container."""
        price_element = container.select_one('.a-price-whole')
        if price_element:
            return price_element.get_text(strip=True)
        return None
    
    def _extract_rating_from_container(self, container: BeautifulSoup) -> Optional[float]:
        """Extract rating from search result container."""
        rating_element = container.select_one('.a-icon-alt')
        if rating_element:
            rating_text = rating_element.get_text(strip=True)
            match = re.search(r'(\d+\.?\d*)\s*out of 5', rating_text)
            if match:
                return float(match.group(1))
        return None
    
    def _extract_review_count_from_container(self, container: BeautifulSoup) -> Optional[int]:
        """Extract review count from search result container."""
        review_element = container.select_one('.a-size-base')
        if review_element:
            review_text = review_element.get_text(strip=True)
            match = re.search(r'([\d,]+)', review_text)
            if match:
                return int(match.group(1).replace(',', ''))
        return None
    
    def _extract_image_from_container(self, container: BeautifulSoup) -> Optional[str]:
        """Extract image from search result container."""
        img_element = container.select_one('img')
        if img_element:
            return img_element.get('src') or img_element.get('data-src')
        return None
    
    def _extract_url_from_container(self, container: BeautifulSoup) -> Optional[str]:
        """Extract URL from search result container."""
        link_element = container.select_one('h2 a')
        if link_element:
            href = link_element.get('href')
            if href:
                if href.startswith('/'):
                    return f"https://www.amazon.com{href}"
                return href
        return None
    
    def _extract_asin_from_container(self, container: BeautifulSoup) -> Optional[str]:
        """Extract ASIN from search result container."""
        url = self._extract_url_from_container(container)
        if url:
            return self._extract_asin(url)
        return None

