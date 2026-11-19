"""
E-commerce Price & Rating Intelligence System
Module: processor.py

Purpose:
    Cleans raw scraped e-commerce data and engineers strategic market
    intelligence metrics, including:
    - Currency and type cleaning
    - Category-level benchmark aggregations (Mean, Median, Price Spread)
    - Price positioning & gap ratios (Price vs Category Average)
    - Value-for-Money Index (VFMI)
    - 4-Quadrant Strategic Product Segmentation (Hidden Gems, Premium Leaders, etc.)
    - Inventory capital exposure & dead-stock risk flags
"""

import os
import re
import json
import logging
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("DataProcessor")


class MarketIntelligenceProcessor:
    """
    Cleans, transforms, and derives market and competitive intelligence metrics.
    """

    def __init__(self, raw_csv_path: str, processed_csv_path: str):
        self.raw_csv_path = raw_csv_path
        self.processed_csv_path = processed_csv_path
        self.df: pd.DataFrame = pd.DataFrame()
        self.summary_kpis: Dict[str, Any] = {}

    def load_data(self) -> pd.DataFrame:
        """
        Load the raw scraped dataset.
        """
        if not os.path.exists(self.raw_csv_path):
            raise FileNotFoundError(f"Raw data file not found at: {self.raw_csv_path}")
        logger.info(f"Loading raw data from: {self.raw_csv_path}")
        self.df = pd.read_csv(self.raw_csv_path)
        logger.info(f"Raw records loaded: {len(self.df)}")
        return self.df

    def clean_data(self) -> pd.DataFrame:
        """
        Clean data types, currency strings, missing values, and formatting.
        """
        df = self.df.copy()

        # 1. Clean Price column (remove £ or any non-numeric/period chars)
        def clean_price(val):
            if pd.isna(val):
                return 0.0
            match = re.search(r"[\d\.]+", str(val))
            return float(match.group()) if match else 0.0

        df["price_gbp"] = df["price_raw"].apply(clean_price)

        # 2. Clean Tax and calculate Net Price
        if "tax" in df.columns:
            df["tax_gbp"] = df["tax"].fillna(0.0).astype(float)
        else:
            df["tax_gbp"] = 0.0
        df["price_net_gbp"] = (df["price_gbp"] - df["tax_gbp"]).round(2)

        # 3. Ensure Rating is numeric (1 to 5)
        df["rating_score"] = pd.to_numeric(df["rating_score"], errors="coerce").fillna(0).astype(int)

        # 4. Stock quantity and in-stock boolean
        df["stock_quantity"] = pd.to_numeric(df["stock_quantity"], errors="coerce").fillna(0).astype(int)
        df["in_stock"] = df["stock_quantity"] > 0

        # 5. Clean Category
        df["category"] = df["category"].fillna("General").str.strip()
        df["category"] = df["category"].replace({"": "General", "Default": "General"})

        # 6. Inventory Valuation (Capital tied up in each SKU)
        df["inventory_value_gbp"] = (df["price_gbp"] * df["stock_quantity"]).round(2)

        # Drop any completely empty or duplicated URLs
        initial_len = len(df)
        df = df.drop_duplicates(subset=["product_url"]).reset_index(drop=True)
        dropped = initial_len - len(df)
        if dropped > 0:
            logger.info(f"Removed {dropped} duplicate records.")

        self.df = df
        logger.info(f"Data cleaning complete. Clean records: {len(self.df)}")
        return self.df

    def engineer_market_metrics(self) -> pd.DataFrame:
        """
        Compute category benchmarks, price gaps, Value-for-Money Index (VFMI),
        and competitive quadrant segmentation.
        """
        df = self.df.copy()

        # 1. Price Tiers (Budget, Mid-Range, Premium) across the entire catalog
        price_quantiles = df["price_gbp"].quantile([0.33, 0.67]).to_dict()
        q_low, q_high = price_quantiles[0.33], price_quantiles[0.67]

        def assign_tier(price):
            if price <= q_low:
                return "Budget"
            elif price <= q_high:
                return "Mid-Range"
            else:
                return "Premium"

        df["price_tier"] = df["price_gbp"].apply(assign_tier)

        # 2. Category-Level Benchmarks
        cat_stats = df.groupby("category")["price_gbp"].agg(
            category_mean_price="mean",
            category_median_price="median",
            category_min_price="min",
            category_max_price="max",
            category_count="count",
        ).reset_index()

        cat_stats["category_price_spread"] = (
            cat_stats["category_max_price"] - cat_stats["category_min_price"]
        ).round(2)

        # Rating benchmark per category
        cat_ratings = df.groupby("category")["rating_score"].agg(
            category_mean_rating="mean"
        ).reset_index()

        cat_benchmarks = pd.merge(cat_stats, cat_ratings, on="category")
        df = pd.merge(df, cat_benchmarks, on="category", how="left")

        # Round benchmark columns
        for col in ["category_mean_price", "category_median_price", "category_mean_rating"]:
            df[col] = df[col].round(2)

        # 3. Relative Price Positioning & Price Gap
        # Ratio of product price to its category average (>1 means premium, <1 means discount)
        df["price_to_category_mean_ratio"] = (
            df["price_gbp"] / df["category_mean_price"]
        ).round(2)
        df["price_gap_from_mean_gbp"] = (
            df["price_gbp"] - df["category_mean_price"]
        ).round(2)

        # 4. Value-for-Money Index (VFMI)
        # Raw VFMI: Rating points per £100 spent (Higher = Better consumer value)
        df["vfmi_raw"] = ((df["rating_score"] / df["price_gbp"]) * 100).round(2)

        # Category-Normalized VFMI:
        # Evaluates rating relative to how cheap/expensive the product is within its category
        # VFMI = Rating / (Price / Category_Mean_Price)
        # A 5-star product priced below category mean achieves an exceptional score (>5.0)
        df["vfmi_index"] = (
            df["rating_score"] / df["price_to_category_mean_ratio"].replace(0, 1)
        ).round(2)

        # 5. Strategic Quadrant Segmentation (Competitive Matrix)
        overall_median_price = df["price_gbp"].median()

        def segment_product(row):
            rating = row["rating_score"]
            price = row["price_gbp"]

            if rating >= 4 and price <= overall_median_price:
                return "Hidden Gem (High Value Opportunity)"
            elif rating >= 4 and price > overall_median_price:
                return "Premium Leader (High Quality, High Margin)"
            elif rating <= 2 and price > overall_median_price:
                return "Overpriced Risk (High Price, Low Rating)"
            elif rating <= 2 and price <= overall_median_price:
                return "Budget Underperformer (Low Rating, Low Price)"
            else:
                return "Mid-Market Stable"

        df["strategic_segment"] = df.apply(segment_product, axis=1)

        # 6. Dead-Stock / Capital Risk Flag
        # Flags products with low rating (<= 2 stars) where tied-up capital exceeds median inventory value
        median_inv = df["inventory_value_gbp"].median()
        df["capital_at_risk_flag"] = (
            (df["rating_score"] <= 2) & (df["inventory_value_gbp"] > median_inv)
        )

        self.df = df
        logger.info("Market intelligence metrics successfully engineered.")
        return self.df

    def save_processed_data(self) -> None:
        """
        Export enriched dataset to CSV.
        """
        os.makedirs(os.path.dirname(self.processed_csv_path), exist_ok=True)
        self.df.to_csv(self.processed_csv_path, index=False, encoding="utf-8")
        logger.info(f"Processed dataset saved to: {self.processed_csv_path}")

    def generate_executive_kpis(self) -> Dict[str, Any]:
        """
        Generate high-level Executive Market Intelligence KPIs.
        """
        df = self.df
        total_products = len(df)
        total_inventory_val = float(df["inventory_value_gbp"].sum())
        avg_price = float(df["price_gbp"].mean())
        median_price = float(df["price_gbp"].median())
        avg_rating = float(df["rating_score"].mean())

        # Top 5 Hidden Gems (Best Value-for-Money Index)
        hidden_gems = (
            df[df["strategic_segment"] == "Hidden Gem (High Value Opportunity)"]
            .sort_values(by="vfmi_index", ascending=False)
            .head(5)[["title", "category", "price_gbp", "rating_score", "vfmi_index"]]
            .to_dict(orient="records")
        )

        # Top 5 Overpriced Risks
        overpriced_risks = (
            df[df["strategic_segment"] == "Overpriced Risk (High Price, Low Rating)"]
            .sort_values(by="price_gbp", ascending=False)
            .head(5)[["title", "category", "price_gbp", "rating_score", "inventory_value_gbp"]]
            .to_dict(orient="records")
        )

        # Category summary
        cat_summary = (
            df.groupby("category")
            .agg(
                product_count=("title", "count"),
                avg_price=("price_gbp", "mean"),
                avg_rating=("rating_score", "mean"),
                total_stock=("stock_quantity", "sum"),
                total_inventory_val=("inventory_value_gbp", "sum"),
            )
            .round(2)
            .sort_values(by="product_count", ascending=False)
            .head(10)
            .to_dict(orient="index")
        )

        # Segment distribution
        segment_distribution = df["strategic_segment"].value_counts().to_dict()

        self.summary_kpis = {
            "total_products": total_products,
            "total_categories": int(df["category"].nunique()),
            "total_inventory_value_gbp": round(total_inventory_val, 2),
            "average_price_gbp": round(avg_price, 2),
            "median_price_gbp": round(median_price, 2),
            "average_rating": round(avg_rating, 2),
            "segment_distribution": segment_distribution,
            "top_hidden_gems": hidden_gems,
            "top_overpriced_risks": overpriced_risks,
            "top_categories": cat_summary,
        }
        return self.summary_kpis

    def run_pipeline(self) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Execute end-to-end processing pipeline.
        """
        self.load_data()
        self.clean_data()
        self.engineer_market_metrics()
        self.save_processed_data()
        kpis = self.generate_executive_kpis()
        return self.df, kpis


def main():
    """
    CLI execution.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))

    raw_path = os.path.join(project_root, "data", "raw", "ecommerce_data_raw.csv")
    processed_path = os.path.join(project_root, "data", "processed", "ecommerce_data_processed.csv")
    summary_json_path = os.path.join(project_root, "reports", "market_intelligence_summary.json")

    processor = MarketIntelligenceProcessor(
        raw_csv_path=raw_path,
        processed_csv_path=processed_path,
    )
    df, kpis = processor.run_pipeline()

    # Save summary JSON
    os.makedirs(os.path.dirname(summary_json_path), exist_ok=True)
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(kpis, f, indent=2, ensure_ascii=False)

    logger.info(f"Summary KPIs saved to: {summary_json_path}")
    logger.info("Processing Pipeline Completed Successfully!")


if __name__ == "__main__":
    main()
