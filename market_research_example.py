#!/usr/bin/env python3
"""
Market Research Example Script

This script demonstrates how to use the market research functionality
to find product opportunities on Amazon.
"""

import asyncio
import json
from amzn_scraper import MarketResearch, Config


async def main():
    """Main market research example."""
    print("🔍 Amazon Market Research Example")
    print("=" * 50)
    
    # Initialize configuration
    config = Config()
    
    # Create market research instance
    market_research = MarketResearch(config)
    
    print("\n📊 Running market research...")
    print("Looking for products with:")
    print("  - High sales volume (100+ bought in past month)")
    print("  - Low review count (< 50 reviews)")
    print("  - Price > $15")
    print("  - Non-electronic products")
    print("  - Excluding major brands")
    
    # Run market research
    opportunities = await market_research.run_research(
        domains=["com"],  # Start with just US market
        min_price=15.0,
        min_badge=100,
        max_reviews=50,
        pages_per_seed=3,  # Limit pages for demo
        custom_seeds=["storage basket", "organizer bins", "adhesive hooks"]  # Custom search terms
    )
    
    if opportunities:
        print(f"\n✅ Found {len(opportunities)} product opportunities!")
        print("\n🏆 Top Opportunities:")
        print("-" * 60)
        
        for i, opp in enumerate(opportunities[:10], 1):
            print(f"{i:2d}. {opp['title'][:50]}...")
            print(f"    💰 Price: ${opp['price_local']:.2f}")
            print(f"    🛒 Badge: {opp['badge']:,} bought in past month")
            print(f"    ⭐ Reviews: {opp['review_count'] or 'N/A'}")
            print(f"    🌐 Marketplace: amazon.{opp['marketplace']}")
            print(f"    🔗 URL: {opp['url']}")
            print()
        
        if len(opportunities) > 10:
            print(f"    ... and {len(opportunities) - 10} more opportunities")
        
        # Save results
        print("\n💾 Saving results...")
        success = market_research.save_results(opportunities, output_format="json")
        
        if success:
            print("✅ Results saved to data/ directory")
        else:
            print("❌ Failed to save results")
        
        # Show summary statistics
        print("\n📈 Summary Statistics:")
        print(f"  Total opportunities: {len(opportunities)}")
        
        if opportunities:
            avg_price = sum(opp['price_local'] for opp in opportunities) / len(opportunities)
            max_badge = max(opp['badge'] for opp in opportunities)
            min_badge = min(opp['badge'] for opp in opportunities)
            
            print(f"  Average price: ${avg_price:.2f}")
            print(f"  Highest sales volume: {max_badge:,} bought")
            print(f"  Lowest sales volume: {min_badge:,} bought")
            
            # Count by marketplace
            marketplaces = {}
            for opp in opportunities:
                market = opp['marketplace']
                marketplaces[market] = marketplaces.get(market, 0) + 1
            
            print(f"  By marketplace:")
            for market, count in marketplaces.items():
                print(f"    amazon.{market}: {count} opportunities")
    
    else:
        print("\n❌ No product opportunities found")
        print("Try adjusting the search criteria:")
        print("  - Lower minimum badge count")
        print("  - Lower minimum price")
        print("  - Increase maximum review count")
        print("  - Try different search seeds")
    
    print("\n🎯 Next Steps:")
    print("1. Review the opportunities in the data/ directory")
    print("2. Research the top products manually")
    print("3. Check competition and market saturation")
    print("4. Consider product development or sourcing")
    print("5. Use different search terms for more opportunities")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Market research interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error running market research: {e}")
        print("Make sure you have:")
        print("1. Installed dependencies: py -m pip install -r requirements.txt")
        print("2. Installed Playwright: py -m playwright install chromium")
        print("3. Check your internet connection")

