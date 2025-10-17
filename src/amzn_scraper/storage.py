"""
Data storage handlers for Amazon scraper.
"""

import json
import csv
import sqlite3
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker


Base = declarative_base()


class Product(Base):
    """SQLAlchemy model for products table."""
    __tablename__ = 'products'
    
    asin = Column(String(10), primary_key=True)
    title = Column(Text)
    price = Column(String(50))
    rating = Column(Float)
    review_count = Column(Integer)
    availability = Column(String(100))
    description = Column(Text)
    features = Column(JSON)
    images = Column(JSON)
    specifications = Column(JSON)
    brand = Column(String(200))
    category = Column(String(200))
    seller = Column(String(200))
    shipping = Column(String(200))
    url = Column(Text)
    scraped_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class DataStorage:
    """Handles data storage in multiple formats."""
    
    def __init__(self, output_format: str = "csv", output_directory: str = "data", 
                 database_config: Optional[Dict[str, Any]] = None):
        """
        Initialize data storage.
        
        Args:
            output_format: Storage format ("csv", "json", "database")
            output_directory: Directory for file outputs
            database_config: Database configuration dictionary
        """
        self.output_format = output_format.lower()
        self.output_directory = Path(output_directory)
        self.database_config = database_config or {}
        
        # Create output directory if it doesn't exist
        self.output_directory.mkdir(exist_ok=True)
        
        # Initialize database if needed
        if self.output_format == "database":
            self._init_database()
    
    def _init_database(self):
        """Initialize database connection and create tables."""
        connection_string = self.database_config.get('connection_string', 'sqlite:///amazon_products.db')
        
        self.engine = create_engine(connection_string)
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
    
    def save_product(self, product_data: Dict[str, Any]) -> bool:
        """
        Save a single product.
        
        Args:
            product_data: Product data dictionary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.output_format == "csv":
                return self._save_to_csv([product_data])
            elif self.output_format == "json":
                return self._save_to_json([product_data])
            elif self.output_format == "database":
                return self._save_to_database([product_data])
            else:
                raise ValueError(f"Unsupported output format: {self.output_format}")
        except Exception as e:
            print(f"Error saving product: {e}")
            return False
    
    def save_products(self, products_data: List[Dict[str, Any]]) -> bool:
        """
        Save multiple products.
        
        Args:
            products_data: List of product data dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.output_format == "csv":
                return self._save_to_csv(products_data)
            elif self.output_format == "json":
                return self._save_to_json(products_data)
            elif self.output_format == "database":
                return self._save_to_database(products_data)
            else:
                raise ValueError(f"Unsupported output format: {self.output_format}")
        except Exception as e:
            print(f"Error saving products: {e}")
            return False
    
    def _save_to_csv(self, products_data: List[Dict[str, Any]]) -> bool:
        """Save products to CSV file."""
        if not products_data:
            return True
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_directory / f"amazon_products_{timestamp}.csv"
        
        # Flatten nested data for CSV
        flattened_data = []
        for product in products_data:
            flattened = self._flatten_product_data(product)
            flattened_data.append(flattened)
        
        # Write to CSV
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            if flattened_data:
                fieldnames = flattened_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(flattened_data)
        
        print(f"Saved {len(products_data)} products to {filename}")
        return True
    
    def _save_to_json(self, products_data: List[Dict[str, Any]]) -> bool:
        """Save products to JSON file."""
        if not products_data:
            return True
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.output_directory / f"amazon_products_{timestamp}.json"
        
        # Add metadata
        output_data = {
            "metadata": {
                "scraped_at": datetime.now().isoformat(),
                "total_products": len(products_data),
                "format_version": "1.0"
            },
            "products": products_data
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(output_data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(products_data)} products to {filename}")
        return True
    
    def _save_to_database(self, products_data: List[Dict[str, Any]]) -> bool:
        """Save products to database."""
        if not products_data:
            return True
        
        saved_count = 0
        for product_data in products_data:
            try:
                # Convert product data to Product model
                product = self._dict_to_product(product_data)
                
                # Check if product already exists
                existing = self.session.query(Product).filter_by(asin=product.asin).first()
                if existing:
                    # Update existing product
                    for key, value in product_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    existing.scraped_at = datetime.utcnow()
                else:
                    # Add new product
                    self.session.add(product)
                
                saved_count += 1
            except Exception as e:
                print(f"Error saving product {product_data.get('asin', 'unknown')}: {e}")
                continue
        
        self.session.commit()
        print(f"Saved {saved_count} products to database")
        return True
    
    def _flatten_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested product data for CSV export."""
        flattened = {}
        
        for key, value in product_data.items():
            if isinstance(value, (list, dict)):
                # Convert lists and dicts to JSON strings
                flattened[key] = json.dumps(value, ensure_ascii=False)
            else:
                flattened[key] = value
        
        return flattened
    
    def _dict_to_product(self, product_data: Dict[str, Any]) -> Product:
        """Convert dictionary to Product model."""
        # Parse scraped_at timestamp
        scraped_at = None
        if 'scraped_at' in product_data:
            try:
                scraped_at = datetime.fromisoformat(product_data['scraped_at'].replace('Z', '+00:00'))
            except:
                scraped_at = datetime.utcnow()
        
        return Product(
            asin=product_data.get('asin'),
            title=product_data.get('title'),
            price=product_data.get('price'),
            rating=product_data.get('rating'),
            review_count=product_data.get('review_count'),
            availability=product_data.get('availability'),
            description=product_data.get('description'),
            features=product_data.get('features'),
            images=product_data.get('images'),
            specifications=product_data.get('specifications'),
            brand=product_data.get('brand'),
            category=product_data.get('category'),
            seller=product_data.get('seller'),
            shipping=product_data.get('shipping'),
            url=product_data.get('url'),
            scraped_at=scraped_at
        )
    
    def load_products(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Load products from storage.
        
        Args:
            limit: Maximum number of products to load
            
        Returns:
            List of product data dictionaries
        """
        if self.output_format == "database":
            return self._load_from_database(limit)
        else:
            return self._load_from_files(limit)
    
    def _load_from_database(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load products from database."""
        query = self.session.query(Product)
        if limit:
            query = query.limit(limit)
        
        products = query.all()
        return [self._product_to_dict(product) for product in products]
    
    def _load_from_files(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Load products from files."""
        products = []
        
        if self.output_format == "json":
            json_files = list(self.output_directory.glob("*.json"))
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'products' in data:
                            products.extend(data['products'])
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        elif self.output_format == "csv":
            csv_files = list(self.output_directory.glob("*.csv"))
            for file_path in csv_files:
                try:
                    df = pd.read_csv(file_path)
                    products.extend(df.to_dict('records'))
                except Exception as e:
                    print(f"Error loading {file_path}: {e}")
        
        if limit:
            products = products[:limit]
        
        return products
    
    def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        """Convert Product model to dictionary."""
        return {
            'asin': product.asin,
            'title': product.title,
            'price': product.price,
            'rating': product.rating,
            'review_count': product.review_count,
            'availability': product.availability,
            'description': product.description,
            'features': product.features,
            'images': product.images,
            'specifications': product.specifications,
            'brand': product.brand,
            'category': product.category,
            'seller': product.seller,
            'shipping': product.shipping,
            'url': product.url,
            'scraped_at': product.scraped_at.isoformat() if product.scraped_at else None,
            'created_at': product.created_at.isoformat() if product.created_at else None
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        if self.output_format == "database":
            total_products = self.session.query(Product).count()
            latest_scrape = self.session.query(Product).order_by(Product.scraped_at.desc()).first()
            
            return {
                'total_products': total_products,
                'latest_scrape': latest_scrape.scraped_at.isoformat() if latest_scrape else None,
                'storage_type': 'database'
            }
        else:
            # Count files and products
            if self.output_format == "json":
                files = list(self.output_directory.glob("*.json"))
            else:  # csv
                files = list(self.output_directory.glob("*.csv"))
            
            total_files = len(files)
            total_products = 0
            
            for file_path in files:
                try:
                    if self.output_format == "json":
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            if 'products' in data:
                                total_products += len(data['products'])
                    else:  # csv
                        df = pd.read_csv(file_path)
                        total_products += len(df)
                except:
                    continue
            
            return {
                'total_files': total_files,
                'total_products': total_products,
                'storage_type': self.output_format
            }
    
    def close(self):
        """Close database connection if applicable."""
        if hasattr(self, 'session'):
            self.session.close()
        if hasattr(self, 'engine'):
            self.engine.dispose()
