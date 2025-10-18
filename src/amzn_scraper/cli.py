#!/usr/bin/env python3
"""
Command-line interface for Amazon Scraper.
"""

import asyncio
import argparse
import sys
from pathlib import Path

from amzn_scraper import AmazonScraper, Config


async def scrape_single_product(url: str, config: Config):
    """Scrape a single product."""
    async with AmazonScraper(config) as scraper:
        print(f"Scraping product: {url}")
        product = await scraper.scrape_product(url)
        
        if product:
            print(f"✓ Successfully scraped: {product.get('title', 'Unknown')}")
            print(f"  Price: {product.get('price', 'N/A')}")
            print(f"  Rating: {product.get('rating', 'N/A')}")
            print(f"  Reviews: {product.get('review_count', 'N/A')}")
            return True
        else:
            print("✗ Failed to scrape product")
            return False


async def scrape_multiple_products(urls: list, config: Config):
    """Scrape multiple products."""
    async with AmazonScraper(config) as scraper:
        print(f"Scraping {len(urls)} products...")
        products = await scraper.scrape_products(urls)
        
        if products:
            print(f"✓ Successfully scraped {len(products)} products")
            return True
        else:
            print("✗ Failed to scrape any products")
            return False


async def search_products(query: str, max_pages: int, config: Config):
    """Search for products."""
    async with AmazonScraper(config) as scraper:
        print(f"Searching for: {query}")
        results = await scraper.search_products(query, max_pages=max_pages)
        
        if results:
            print(f"✓ Found {len(results)} products")
            for i, product in enumerate(results[:5], 1):  # Show first 5
                print(f"  {i}. {product.get('title', 'Unknown')} - {product.get('price', 'N/A')}")
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more")
            return True
        else:
            print("✗ No products found")
            return False


async def market_research(domains: list, min_price: float, min_badge: int, 
                         max_reviews: int, pages_per_seed: int, seeds: list, config: Config):
    """Run market research to find product opportunities."""
    from amzn_scraper.market_research import MarketResearch
    
    # Look for market_research.yaml in the project root
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    market_config_path = os.path.join(project_root, "market_research.yaml")
    
    market_research = MarketResearch(config, market_config_path)
    
    print(f"Starting market research...")
    print(f"  Domains: {', '.join(domains)}")
    print(f"  Min Price: ${min_price}")
    print(f"  Min Badge Count: {min_badge}")
    print(f"  Max Reviews: {max_reviews}")
    print(f"  Pages per seed: {pages_per_seed}")
    
    if seeds:
        print(f"  Custom seeds: {', '.join(seeds)}")
    else:
        print(f"  Using default seeds")
    
    results = await market_research.run_research(
        domains=domains,
        min_price=min_price,
        min_badge=min_badge,
        max_reviews=max_reviews,
        pages_per_seed=pages_per_seed,
        custom_seeds=seeds
    )
    
    if results:
        print(f"SUCCESS: Found {len(results)} product opportunities!")
        print("\nTop opportunities:")
        for i, product in enumerate(results[:10], 1):
            print(f"  {i}. {product.get('title', 'Unknown')}")
            print(f"     Price: ${product.get('price_local', 'N/A')}")
            print(f"     Badge: {product.get('badge', 'N/A')} bought")
            print(f"     Reviews: {product.get('review_count', 'N/A')}")
            print(f"     URL: {product.get('url', 'N/A')}")
            print()
        
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more opportunities")
        
        return True
    else:
        print("No product opportunities found")
        return False


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description="Amazon Product Scraper")
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--output-format", choices=["csv", "json", "database"], 
                       default="csv", help="Output format")
    parser.add_argument("--output-dir", default="data", help="Output directory")
    parser.add_argument("--headless", action="store_true", default=True, 
                       help="Run browser in headless mode")
    parser.add_argument("--delay", type=float, default=2.0, 
                       help="Delay between requests in seconds")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Single product scraping
    product_parser = subparsers.add_parser("product", help="Scrape a single product")
    product_parser.add_argument("url", help="Amazon product URL")
    
    # Multiple products scraping
    products_parser = subparsers.add_parser("products", help="Scrape multiple products")
    products_parser.add_argument("urls", nargs="+", help="Amazon product URLs")
    
    # Search products
    search_parser = subparsers.add_parser("search", help="Search for products")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--pages", type=int, default=1, help="Number of pages to scrape")
    
    # Market research
    market_parser = subparsers.add_parser("market-research", help="Find product opportunities based on sales volume")
    market_parser.add_argument("--domains", nargs="+", default=["com"], 
                              choices=["com", "co.uk", "de", "fr"],
                              help="Amazon domains to search")
    market_parser.add_argument("--min-price", type=float, default=15.0,
                               help="Minimum price threshold")
    market_parser.add_argument("--min-badge", type=int, default=100,
                               help="Minimum 'bought in past month' count")
    market_parser.add_argument("--max-reviews", type=int, default=50,
                               help="Maximum review count (products with fewer reviews)")
    market_parser.add_argument("--pages-per-seed", type=int, default=7,
                               help="Number of pages to scrape per search seed")
    market_parser.add_argument("--seeds", nargs="+", 
                               help="Custom search seeds (if not provided, uses default seeds)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Load configuration
    config = Config(args.config) if args.config else Config()
    
    # Override config with CLI arguments
    if args.output_format:
        config._config["storage"]["output_format"] = args.output_format
    if args.output_dir:
        config._config["storage"]["output_directory"] = args.output_dir
    if args.headless is not None:
        config._config["scraper"]["browser"]["headless"] = args.headless
    if args.delay:
        config._config["scraper"]["rate_limit"]["delay_between_requests"] = args.delay
    
    # Run appropriate command
    try:
        if args.command == "product":
            success = asyncio.run(scrape_single_product(args.url, config))
        elif args.command == "products":
            success = asyncio.run(scrape_multiple_products(args.urls, config))
        elif args.command == "search":
            success = asyncio.run(search_products(args.query, args.pages, config))
        elif args.command == "market-research":
            success = asyncio.run(market_research(
                args.domains, args.min_price, args.min_badge, 
                args.max_reviews, args.pages_per_seed, args.seeds, config
            ))
        else:
            parser.print_help()
            return
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
