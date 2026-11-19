"""
E-commerce Price & Rating Intelligence System
Main Application Pipeline Orchestrator

Usage:
    python main.py                  # Runs complete pipeline (uses cached raw data if present, or scrapes 3 pages)
    python main.py --scrape         # Forces a fresh scrape (default 5 pages)
    python main.py --pages 10       # Scrapes 10 pages and generates reports
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Configure Windows stdout for UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.scraper import EcommerceScraper
from src.processor import MarketIntelligenceProcessor
from src.visualizer import MarketVisualizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PipelineOrchestrator")


def print_banner():
    banner = r"""
================================================================================
          E-COMMERCE PRICE & RATING INTELLIGENCE SYSTEM
             Competitive Intelligence & Market Analytics
================================================================================
"""
    print(banner)


def run_pipeline(
    pages: int = 5,
    force_scrape: bool = False,
    delay: float = 0.1,
    no_details: bool = False,
):
    print_banner()

    raw_csv = os.path.join(PROJECT_ROOT, "data", "raw", "ecommerce_data_raw.csv")
    processed_csv = os.path.join(PROJECT_ROOT, "data", "processed", "ecommerce_data_processed.csv")
    reports_dir = os.path.join(PROJECT_ROOT, "reports", "figures")

    # Step 1: Web Scraping Ingestion
    should_scrape = force_scrape or (not os.path.exists(raw_csv))

    if should_scrape:
        logger.info(f"==> STEP 1: Starting Web Scraper (Target: {pages} pages)...")
        scraper = EcommerceScraper(delay=delay)
        scraper.scrape(start_page=1, max_pages=pages, fetch_details=not no_details)
        scraper.save_to_csv(raw_csv)
    else:
        logger.info(f"==> STEP 1: Existing raw data found at: {raw_csv}. (Skipping scraping. Use --scrape to re-scrape).")

    # Step 2: Processing & Feature Engineering
    logger.info("==> STEP 2: Cleaning Data & Engineering Market Intelligence Metrics...")
    processor = MarketIntelligenceProcessor(
        raw_csv_path=raw_csv,
        processed_csv_path=processed_csv,
    )
    df, kpis = processor.run_pipeline()

    # Step 3: Visualization Suite
    logger.info("==> STEP 3: Generating Publication-Grade Visualizations...")
    visualizer = MarketVisualizer(
        processed_csv_path=processed_csv,
        output_dir=reports_dir,
    )
    saved_charts = visualizer.render_all()

    # Step 4: Executive Terminal Dashboard
    print("\n" + "=" * 80)
    print("                    EXECUTIVE MARKET INTELLIGENCE BRIEF")
    print("=" * 80)
    print(f" Catalog Products Analyzed:   {kpis['total_products']}")
    print(f" Total Categories Monitored: {kpis['total_categories']}")
    print(f" Total Capital in Stock:     £{kpis['total_inventory_value_gbp']:,.2f}")
    print(f" Market Average Price:       £{kpis['average_price_gbp']:.2f}")
    print(f" Market Median Price:        £{kpis['median_price_gbp']:.2f}")
    print(f" Overall Market Star Rating: {kpis['average_rating']:.2f} / 5.0")
    print("-" * 80)
    print(" Strategic Product Quadrants:")
    for segment, count in kpis["segment_distribution"].items():
        print(f"   • {segment:<45}: {count} products")
    print("-" * 80)
    print(" Top 3 'Hidden Gems' (Best Value-for-Money Index):")
    for idx, gem in enumerate(kpis["top_hidden_gems"][:3], 1):
        print(f"   {idx}. {gem['title'][:32]:<34} | £{gem['price_gbp']:<5.2f} | {gem['rating_score']} Stars | VFMI: {gem['vfmi_index']}")
    print("-" * 80)
    print(" Top 3 'Overpriced Risks' (High Capital Exposure & Low Ratings):")
    for idx, risk in enumerate(kpis["top_overpriced_risks"][:3], 1):
        print(f"   {idx}. {risk['title'][:32]:<34} | £{risk['price_gbp']:<5.2f} | {risk['rating_score']} Stars | Tied Capital: £{risk['inventory_value_gbp']:,.2f}")
    print("-" * 80)
    print(" Generated Visual Intelligence Reports (Saved to reports/figures/):")
    for chart in saved_charts:
        print(f"   [+] {os.path.basename(chart)}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="E-commerce Price & Rating Intelligence Master Orchestrator"
    )
    parser.add_argument(
        "--scrape",
        action="store_true",
        help="Force a fresh web scraping run.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=5,
        help="Number of pages to scrape if scraping is executed (default: 5).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between requests in seconds (default: 0.1).",
    )
    parser.add_argument(
        "--no-details",
        action="store_true",
        help="Skip fetching product detail pages during scraping.",
    )

    args = parser.parse_args()
    run_pipeline(
        pages=args.pages,
        force_scrape=args.scrape,
        delay=args.delay,
        no_details=args.no_details,
    )


if __name__ == "__main__":
    main()
