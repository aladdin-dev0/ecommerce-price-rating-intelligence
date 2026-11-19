"""
E-commerce Price & Rating Intelligence System
Module: scraper.py

Purpose:
    Robust, modular web scraper built for extracting product catalog data,
    pricing, star ratings, stock availability, and category intelligence
    from e-commerce web pages with multi-page pagination support.
"""

import os
import re
import time
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
import pandas as pd


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("EcommerceScraper")


class EcommerceScraper:
    """
    A professional, configurable web scraper for e-commerce intelligence.
    
    Attributes:
        base_url (str): The root URL for the catalog.
        delay (float): Politeness delay between HTTP requests (in seconds).
        session (requests.Session): Persistent HTTP session for connection pooling.
        products (List[Dict[str, Any]]): Collected product records.
    """

    RATING_MAP = {
        "One": 1,
        "Two": 2,
        "Three": 3,
        "Four": 4,
        "Five": 5,
    }

    DEFAULT_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def __init__(self, base_url: str = "http://books.toscrape.com/", delay: float = 0.2):
        """
        Initialize the scraper with base URL and request delay.
        """
        self.base_url = base_url.rstrip("/") + "/"
        self.catalogue_base = urljoin(self.base_url, "catalogue/")
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.DEFAULT_HEADERS)
        self.products: List[Dict[str, Any]] = []

    def _get_soup(self, url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
        """
        Perform a safe GET request and return a BeautifulSoup parsed object.
        """
        try:
            response = self.session.get(url, timeout=timeout)
            if response.status_code == 404:
                logger.info(f"Page returned 404 (End of pagination reached): {url}")
                return None
            response.raise_for_status()
            return BeautifulSoup(response.content, "html.parser")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return None

    def _parse_rating(self, rating_class: str) -> int:
        """
        Convert textual rating representation ('Three') into numerical score (3).
        """
        return self.RATING_MAP.get(rating_class, 0)

    def _parse_stock_quantity(self, stock_text: str) -> int:
        """
        Extract numerical quantity from stock text (e.g., 'In stock (22 available)').
        """
        match = re.search(r"\((\d+)\s+available\)", stock_text)
        if match:
            return int(match.group(1))
        if "in stock" in stock_text.lower():
            return 1
        return 0

    def scrape_product_detail(self, product_url: str) -> Dict[str, Any]:
        """
        Fetch the detail page for an individual product to extract
        granular intelligence (category, UPC, exact stock count, tax).
        """
        soup = self._get_soup(product_url)
        if not soup:
            return {
                "category": "Unknown",
                "upc": "",
                "stock_quantity": 0,
                "tax": 0.0,
            }

        # Category from breadcrumbs
        crumbs = soup.find("ul", class_="breadcrumb")
        category = "Unknown"
        if crumbs:
            li_tags = crumbs.find_all("li")
            if len(li_tags) >= 3:
                category = li_tags[2].text.strip()

        # Table data (UPC, Tax, etc.)
        table = soup.find("table", class_="table-striped")
        table_data = {}
        if table:
            for row in table.find_all("tr"):
                header = row.th.text.strip() if row.th else ""
                value = row.td.text.strip() if row.td else ""
                table_data[header] = value

        # Stock quantity
        stock_elem = soup.find("p", class_="instock availability")
        stock_text = stock_elem.text.strip() if stock_elem else ""
        stock_qty = self._parse_stock_quantity(stock_text)

        # Tax
        tax_str = table_data.get("Tax", "£0.00")
        tax_match = re.search(r"[\d\.]+", tax_str)
        tax_value = float(tax_match.group()) if tax_match else 0.0

        return {
            "category": category,
            "upc": table_data.get("UPC", ""),
            "stock_quantity": stock_qty,
            "tax": tax_value,
        }

    def scrape_page(self, page_number: int, fetch_details: bool = True) -> List[Dict[str, Any]]:
        """
        Scrape a single catalogue page and return the list of extracted products.
        """
        page_url = f"{self.catalogue_base}page-{page_number}.html"
        logger.info(f"Scraping Page {page_number}: {page_url}")

        soup = self._get_soup(page_url)
        if not soup:
            return []

        product_cards = soup.find_all("article", class_="product_pod")
        page_products = []

        for card in product_cards:
            try:
                # Title & relative link
                h3 = card.find("h3")
                link_tag = h3.find("a") if h3 else None
                title = link_tag.get("title", "").strip() if link_tag else "Unknown"
                rel_url = link_tag.get("href", "") if link_tag else ""
                product_url = urljoin(self.catalogue_base, rel_url)

                # Price
                price_elem = card.find("p", class_="price_color")
                price_raw = price_elem.text.strip() if price_elem else ""

                # Star rating
                rating_elem = card.find("p", class_="star-rating")
                rating_classes = rating_elem.get("class", []) if rating_elem else []
                rating_str = [c for c in rating_classes if c != "star-rating"]
                rating_text = rating_str[0] if rating_str else "Unknown"
                rating_score = self._parse_rating(rating_text)

                # Availability
                avail_elem = card.find("p", class_="instock")
                availability = avail_elem.text.strip() if avail_elem else "Unknown"
                in_stock = "in stock" in availability.lower()

                # Image URL
                img_elem = card.find("img", class_="thumbnail")
                img_rel = img_elem.get("src", "") if img_elem else ""
                image_url = urljoin(self.base_url, img_rel)

                product_record = {
                    "title": title,
                    "price_raw": price_raw,
                    "rating_text": rating_text,
                    "rating_score": rating_score,
                    "availability": availability,
                    "in_stock": in_stock,
                    "product_url": product_url,
                    "image_url": image_url,
                    "page_number": page_number,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                }

                # Optional detail page enrichment
                if fetch_details and product_url:
                    time.sleep(self.delay)
                    details = self.scrape_product_detail(product_url)
                    product_record.update(details)
                else:
                    product_record.update({
                        "category": "General",
                        "upc": "",
                        "stock_quantity": 1 if in_stock else 0,
                        "tax": 0.0,
                    })

                page_products.append(product_record)

            except Exception as e:
                logger.warning(f"Error parsing product card on page {page_number}: {e}")
                continue

        logger.info(f"Page {page_number} processed: {len(page_products)} products retrieved.")
        return page_products

    def scrape(
        self,
        start_page: int = 1,
        max_pages: int = 5,
        fetch_details: bool = True
    ) -> pd.DataFrame:
        """
        Execute full catalog scraping with pagination support.
        
        Args:
            start_page (int): Page to start crawling from.
            max_pages (int): Maximum number of pages to scrape.
            fetch_details (bool): Whether to fetch individual product detail pages.
            
        Returns:
            pd.DataFrame: Structured DataFrame of all scraped products.
        """
        self.products = []
        logger.info(f"Starting crawl: {max_pages} pages max, fetch_details={fetch_details}")
        start_time = time.time()

        for page_idx in range(start_page, start_page + max_pages):
            page_data = self.scrape_page(page_idx, fetch_details=fetch_details)
            if not page_data:
                logger.info(f"Stopping pagination: No products found on page {page_idx}.")
                break
            self.products.extend(page_data)
            time.sleep(self.delay)

        elapsed = time.time() - start_time
        logger.info(
            f"Crawl completed in {elapsed:.2f}s! Total products collected: {len(self.products)}"
        )
        return self.to_dataframe()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert scraped records to a Pandas DataFrame.
        """
        return pd.DataFrame(self.products)

    def save_to_csv(self, output_path: str) -> str:
        """
        Save the collected products to a CSV file with Windows file-lock fallback.
        """
        df = self.to_dataframe()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        try:
            df.to_csv(output_path, index=False, encoding="utf-8")
            actual_path = output_path
        except PermissionError:
            base, ext = os.path.splitext(output_path)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            actual_path = f"{base}_{timestamp}{ext}"
            df.to_csv(actual_path, index=False, encoding="utf-8")
            logger.warning(f"File was locked by another process. Saved to fallback: {actual_path}")
        
        logger.info(f"Dataset successfully saved to: {actual_path} ({len(df)} rows)")
        return actual_path


def main():
    """
    Command Line Interface entry point for running the scraper directly.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="E-commerce Price & Rating Intelligence Scraper"
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Number of pages to scrape (20 items/page). Default: 5 (100 items).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Politeness delay between requests in seconds. Default: 0.15",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip fetching individual product pages (faster, but omits Category & UPC).",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/ecommerce_data_raw.csv",
        help="Output CSV path. Default: data/raw/ecommerce_data_raw.csv",
    )

    args = parser.parse_args()

    # Resolve project root relative to this file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))
    output_abs_path = os.path.join(project_root, args.output)

    scraper = EcommerceScraper(delay=args.delay)
    scraper.scrape(
        start_page=1,
        max_pages=args.pages,
        fetch_details=not args.no_details
    )
    scraper.save_to_csv(output_abs_path)


if __name__ == "__main__":
    main()
