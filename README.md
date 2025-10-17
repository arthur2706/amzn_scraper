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
├── config.yaml                  # Configuration file
├── .env.example                 # Environment variables template
├── requirements.txt             # Python dependencies
├── setup.py                     # Package setup
└── README.md                    # This file
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
