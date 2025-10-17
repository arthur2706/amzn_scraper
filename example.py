#!/usr/bin/env python3
"""
Example script demonstrating Amazon scraper usage.
"""

import asyncio
import json
from amzn_scraper import AmazonScraper, Config


async def main():
    """Main example function."""
    print("🚀 Amazon Scraper Example")
    print("=" * 50)
    
    # Initialize scraper with custom config
    config = Config()
    
    # Example 1: Scrape a single product
    print("\n📦 Example 1: Scraping a single product")
    print("-" * 40)
    
    async with AmazonScraper(config) as scraper:
        # Example Amazon product URL (you can replace with any real Amazon product)
        test_url = "https://www.amazon.com/dp/B08N5WRWNW"  # Example Echo Dot
        
        print(f"Scraping: {test_url}")
        product = await scraper.scrape_product(test_url)
        
        if product:
            print("✅ Successfully scraped product!")
            print(f"Title: {product.get('title', 'N/A')}")
            print(f"Price: {product.get('price', 'N/A')}")
            print(f"Rating: {product.get('rating', 'N/A')}")
            print(f"Reviews: {product.get('review_count', 'N/A')}")
            print(f"Availability: {product.get('availability', 'N/A')}")
            print(f"ASIN: {product.get('asin', 'N/A')}")
        else:
            print("❌ Failed to scrape product")
    
    # Example 2: Search for products
    print("\n🔍 Example 2: Searching for products")
    print("-" * 40)
    
    async with AmazonScraper(config) as scraper:
        search_query = "wireless headphones"
        print(f"Searching for: {search_query}")
        
        search_results = await scraper.search_products(search_query, max_pages=1)
        
        if search_results:
            print(f"✅ Found {len(search_results)} products!")
            for i, product in enumerate(search_results[:3], 1):  # Show first 3
                print(f"{i}. {product.get('title', 'Unknown')} - {product.get('price', 'N/A')}")
        else:
            print("❌ No products found")
    
    # Example 3: Save data to different formats
    print("\n💾 Example 3: Saving data to JSON")
    print("-" * 40)
    
    from amzn_scraper import DataStorage
    
    # Configure JSON storage
    storage = DataStorage(output_format="json", output_directory="data")
    
    async with AmazonScraper(config) as scraper:
        scraper.storage = storage  # Use custom storage
        
        # Scrape and save
        test_urls = ["https://www.amazon.com/dp/B08N5WRWNW"]
        success = await scraper.scrape_and_save(test_urls)
        
        if success:
            print("✅ Data saved to JSON file!")
        else:
            print("❌ Failed to save data")
    
    # Example 4: Get scraper statistics
    print("\n📊 Example 4: Scraper statistics")
    print("-" * 40)
    
    async with AmazonScraper(config) as scraper:
        stats = scraper.get_stats()
        print("Scraper Configuration:")
        print(f"  Output Format: {stats['config']['output_format']}")
        print(f"  Rate Limit Delay: {stats['config']['rate_limit_delay']}s")
        print(f"  Max Retries: {stats['config']['max_retries']}")
        print(f"  Proxy Enabled: {stats['config']['proxy_enabled']}")
    
    print("\n🎉 Example completed!")
    print("\nNext steps:")
    print("1. Check the 'data' folder for output files")
    print("2. Modify config.yaml to customize settings")
    print("3. Use the CLI: py -m amzn_scraper.cli product <URL>")
    print("4. Check README.md for more examples")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Example interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error running example: {e}")
        print("Make sure you have:")
        print("1. Installed dependencies: py -m pip install -r requirements.txt")
        print("2. Installed Playwright: py -m playwright install chromium")
