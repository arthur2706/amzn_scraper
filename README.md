# Amazon Scraper

A powerful Python package for scraping Amazon product data using Playwright. This scraper provides comprehensive product information extraction with support for multiple storage formats, rate limiting, proxy rotation, and robust error handling.

## Features

- **Modern Browser Automation**: Uses Playwright for reliable JavaScript rendering and anti-detection
- **Comprehensive Data Extraction**: Extracts product details, pricing, ratings, reviews, specifications, and more
- **Multiple Storage Formats**: Support for CSV, JSON, and database storage (SQLite, PostgreSQL, MySQL)
- **Rate Limiting**: Built-in rate limiting with configurable delays and request limits
- **Proxy Support**: Rotating proxy support for large-scale scraping
- **Error Handling**: Robust retry mechanisms with exponential backoff
- **Configurable**: YAML-based configuration with environment variable support
- **Async Support**: Full async/await support for high-performance scraping

## Installation

### Prerequisites

- Python 3.8 or higher
- Playwright browsers (installed automatically)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/yourusername/amzn_scraper.git
cd amzn_scraper

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Install the package in development mode
pip install -e .
```

### Install Dependencies Only

```bash
pip install playwright beautifulsoup4 python-dotenv pyyaml pandas sqlalchemy requests lxml fake-useragent
playwright install chromium
```

## Quick Start

### Basic Usage

```python
import asyncio
from amzn_scraper import AmazonScraper

async def main():
    # Initialize scraper
    async with AmazonScraper() as scraper:
        # Scrape a single product
        product_data = await scraper.scrape_product("https://www.amazon.com/dp/B08N5WRWNW")
        print(product_data)
        
        # Scrape multiple products
        urls = [
            "https://www.amazon.com/dp/B08N5WRWNW",
            "https://www.amazon.com/dp/B08N5WRWNW"
        ]
        products = await scraper.scrape_products(urls)
        
        # Search for products
        search_results = await scraper.search_products("laptop", max_pages=2)

if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration

Create a `config.yaml` file to customize scraper behavior:

```yaml
scraper:
  rate_limit:
    delay_between_requests: 2.0  # seconds
    max_requests_per_minute: 30
    random_delay_range: [0.5, 1.5]
  
  browser:
    headless: true
    viewport:
      width: 1920
      height: 1080
    user_agent: "auto"  # or specify custom user agent
    timeout: 30000  # milliseconds
  
  retry:
    max_retries: 3
    retry_delay: 5.0
    exponential_backoff: true

storage:
  output_format: "csv"  # csv, json, database
  output_directory: "data"
  database:
    enabled: false
    type: "sqlite"
    connection_string: "sqlite:///amazon_products.db"

proxy:
  enabled: false
  rotation: true
  proxies: []  # Add proxy URLs here
```

### Environment Variables

Copy `.env.example` to `.env` and configure sensitive settings:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
DB_CONNECTION_STRING=sqlite:///amazon_products.db
PROXY_ENABLED=false
HEADLESS_MODE=true
RATE_LIMIT_DELAY=2.0
```

## Usage Examples

### Scrape Product Details

```python
import asyncio
from amzn_scraper import AmazonScraper

async def scrape_single_product():
    async with AmazonScraper() as scraper:
        product = await scraper.scrape_product("https://www.amazon.com/dp/B08N5WRWNW")
        
        if product:
            print(f"Title: {product['title']}")
            print(f"Price: {product['price']}")
            print(f"Rating: {product['rating']}")
            print(f"Reviews: {product['review_count']}")
            print(f"Availability: {product['availability']}")

asyncio.run(scrape_single_product())
```

### Search and Scrape Multiple Products

```python
async def search_and_scrape():
    async with AmazonScraper() as scraper:
        # Search for products
        search_results = await scraper.search_products("wireless headphones", max_pages=3)
        
        # Extract URLs from search results
        urls = [product['url'] for product in search_results if product['url']]
        
        # Scrape detailed product information
        detailed_products = await scraper.scrape_products(urls)
        
        return detailed_products

products = asyncio.run(search_and_scrape())
```

### Market Research - Find Product Opportunities

```python
from amzn_scraper import MarketResearch, Config

async def find_opportunities():
    config = Config()
    market_research = MarketResearch(config)
    
    # Find products with high sales volume but low reviews
    opportunities = await market_research.run_research(
        domains=["com", "co.uk"],  # Amazon domains to search
        min_price=15.0,            # Minimum price threshold
        min_badge=100,             # Minimum "bought in past month" count
        max_reviews=50,            # Maximum review count
        pages_per_seed=5           # Pages to scrape per search term
    )
    
    return opportunities

opportunities = asyncio.run(find_opportunities())
```

### Save Data to Different Formats

```python
from amzn_scraper import AmazonScraper, DataStorage

async def scrape_and_save():
    # Configure storage for JSON output
    storage = DataStorage(output_format="json", output_directory="output")
    
    async with AmazonScraper() as scraper:
        scraper.storage = storage  # Use custom storage
        
        urls = ["https://www.amazon.com/dp/B08N5WRWNW"]
        await scraper.scrape_and_save(urls)

asyncio.run(scrape_and_save())
```

### Database Storage

```python
from amzn_scraper import AmazonScraper, DataStorage

# Configure database storage
db_config = {
    'enabled': True,
    'type': 'sqlite',
    'connection_string': 'sqlite:///products.db'
}

storage = DataStorage(
    output_format="database",
    database_config=db_config
)

async with AmazonScraper() as scraper:
    scraper.storage = storage
    await scraper.scrape_and_save(["https://www.amazon.com/dp/B08N5WRWNW"])
```

## Data Structure

The scraper extracts the following product information:

```python
{
    'asin': 'B08N5WRWNW',
    'title': 'Product Title',
    'price': '$29.99',
    'rating': 4.5,
    'review_count': 1234,
    'availability': 'In Stock',
    'description': 'Product description...',
    'features': ['Feature 1', 'Feature 2'],
    'images': ['https://example.com/image1.jpg'],
    'specifications': {'Brand': 'Brand Name', 'Model': 'Model Number'},
    'brand': 'Brand Name',
    'category': 'Electronics',
    'seller': 'Amazon.com',
    'shipping': 'Free shipping',
    'url': 'https://www.amazon.com/dp/B08N5WRWNW',
    'scraped_at': '2023-01-01T00:00:00'
}
```

## Configuration Options

### Scraper Settings

- `rate_limit.delay_between_requests`: Delay between requests in seconds
- `rate_limit.max_requests_per_minute`: Maximum requests per minute
- `rate_limit.random_delay_range`: Random delay range for human-like behavior
- `browser.headless`: Run browser in headless mode
- `browser.viewport`: Browser viewport dimensions
- `browser.user_agent`: User agent string ("auto" for random)
- `browser.timeout`: Page load timeout in milliseconds
- `retry.max_retries`: Maximum retry attempts
- `retry.retry_delay`: Delay between retries
- `retry.exponential_backoff`: Use exponential backoff for retries

### Storage Settings

- `output_format`: Storage format ("csv", "json", "database")
- `output_directory`: Directory for file outputs
- `database.enabled`: Enable database storage
- `database.type`: Database type ("sqlite", "postgresql", "mysql")
- `database.connection_string`: Database connection string

### Proxy Settings

- `proxy.enabled`: Enable proxy support
- `proxy.rotation`: Rotate between proxies
- `proxy.proxies`: List of proxy URLs
- `proxy.timeout`: Proxy timeout in seconds

## Testing

Run the test suite:

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=amzn_scraper tests/
```

## Project Structure

```
amzn_scraper/
├── src/
│   └── amzn_scraper/
│       ├── __init__.py          # Package initialization
│       ├── scraper.py           # Main scraper class
│       ├── parser.py            # HTML parsing logic
│       ├── storage.py           # Data storage handlers
│       └── config.py            # Configuration management
├── tests/
│   ├── __init__.py
│   └── test_scraper.py          # Test suite
├── data/                        # Output directory
├── config.yaml                  # Main scraper configuration
├── market_research.yaml         # Market research specific configuration
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
└── README.md                    # This file
```

## Command Line Interface

The scraper includes a powerful CLI for easy usage:

```bash
# Scrape single product
py -m amzn_scraper.cli product "https://www.amazon.com/dp/B08N5WRWNW"

# Search products
py -m amzn_scraper.cli search "laptop" --pages 2

# Scrape multiple products
py -m amzn_scraper.cli products "url1" "url2" "url3"

# Market research - find product opportunities
py -m amzn_scraper.cli market-research --domains com co.uk --min-price 20 --min-badge 200

# Market research with custom search terms
py -m amzn_scraper.cli market-research --seeds "kitchen organizer" "pet toys" "yoga accessories"

# Market research with all options
py -m amzn_scraper.cli market-research \
  --domains com co.uk de fr \
  --min-price 15.0 \
  --min-badge 100 \
  --max-reviews 50 \
  --pages-per-seed 7 \
  --seeds "storage basket" "organizer bins"
```

### Market Research CLI Options

The `market-research` command helps you find product opportunities by searching for items with:
- High sales volume ("bought in past month" badges)
- Low review counts (indicating newer/less saturated products)
- Non-electronic products (to avoid complex electronics)
- Excluded major brands (to find niche opportunities)

### Market Research Configuration

Market research settings are configured in `market_research.yaml`:

```yaml
# Default search seeds
default_seeds:
  - "storage basket"
  - "organizer bins"
  - "adhesive hooks"

# Filtering criteria
filters:
  min_price: 15.0
  min_badge_count: 100
  max_review_count: 50
  pages_per_seed: 7
  exclude_electronics: true
  
  # Blocked brands
  blocked_brands:
    - "amazon basics"
    - "philips"
    - "samsung"
    # ... more brands

# Badge patterns for different domains
badge_patterns:
  com: "(?i)\\b(\\d+(?:\\.\\d+)?K\\+?|\\d+\\+?)\\s+bought in past month\\b"
  co.uk: "(?i)\\b(\\d+(?:\\.\\d+)?K\\+?|\\d+\\+?)\\s+bought in past month\\b"
  de: "(?i)\\b(\\d+(?:\\.\\d+)?K\\+?|\\d+\\+?)\\s*mal im letzten monat gekauft\\b"
  fr: "(?i)\\b(\\d+(?:\\.\\d+)?K\\+?|\\d+\\+?)\\s*achet[ée] au cours du dernier mois\\b"
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and research purposes only. Please respect Amazon's Terms of Service and robots.txt. The authors are not responsible for any misuse of this software. Always ensure you have permission to scrape data and comply with applicable laws and regulations.

## Support

If you encounter any issues or have questions:

1. Check the [Issues](https://github.com/yourusername/amzn_scraper/issues) page
2. Create a new issue with detailed information
3. Join our [Discussions](https://github.com/yourusername/amzn_scraper/discussions) for community support
