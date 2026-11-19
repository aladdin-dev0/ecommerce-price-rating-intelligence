"""
E-commerce Price & Rating Intelligence System
Module: visualizer.py

Purpose:
    Generates publication-quality, high-resolution (300 DPI) visualizations
    tailored for executive presentations and GitHub portfolio showcases:
    1. Strategic Competitive Matrix (The 4 Quadrants & VFMI bubbles)
    2. Category Price Gaps and Benchmark Spreads
    3. Top 10 'Hidden Gems' (Ranked by Value-for-Money Index)
    4. Capital Exposure & Inventory Risk Breakdown
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("MarketVisualizer")

# Set global aesthetic theme
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams.update({
    "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "font.family": "sans-serif",
    "figure.titlesize": 16,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.autolayout": False,
    "figure.dpi": 300,
})


class MarketVisualizer:
    """
    Renders and exports executive business charts from processed intelligence data.
    """

    def __init__(self, processed_csv_path: str, output_dir: str):
        self.processed_csv_path = processed_csv_path
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.df = self._load_data()

    def _load_data(self) -> pd.DataFrame:
        if not os.path.exists(self.processed_csv_path):
            raise FileNotFoundError(f"Processed file not found at: {self.processed_csv_path}")
        df = pd.read_csv(self.processed_csv_path)
        logger.info(f"Loaded processed data: {len(df)} records.")
        return df

    def plot_strategic_quadrant_matrix(self) -> str:
        """
        Chart 1: 4-Quadrant Strategic Matrix (Rating vs Price with VFMI Bubble Size).
        Highlights Market Opportunities (Hidden Gems) vs Capital Risks.
        """
        df = self.df
        fig, ax = plt.subplots(figsize=(11, 7))

        median_price = df["price_gbp"].median()
        rating_threshold = 3.5

        # Palette definition
        palette = {
            "Hidden Gem (High Value Opportunity)": "#10B981",    # Emerald Green
            "Premium Leader (High Quality, High Margin)": "#3B82F6", # Royal Blue
            "Overpriced Risk (High Price, Low Rating)": "#EF4444",   # Coral Red
            "Budget Underperformer (Low Rating, Low Price)": "#F59E0B", # Amber
            "Mid-Market Stable": "#94A3B8",                          # Slate Gray
        }

        # Size mapping based on VFMI
        sizes = np.clip(df["vfmi_index"] * 40, 60, 450)

        # Plot points
        sns.scatterplot(
            data=df,
            x="price_gbp",
            y="rating_score",
            hue="strategic_segment",
            palette=palette,
            size=sizes,
            sizes=(60, 450),
            alpha=0.85,
            edgecolor="black",
            linewidth=0.8,
            legend="brief",
            ax=ax,
        )

        # Reference quadrant dividing lines
        ax.axvline(median_price, color="#64748B", linestyle="--", linewidth=1.2, alpha=0.8)
        ax.axhline(rating_threshold, color="#64748B", linestyle="--", linewidth=1.2, alpha=0.8)

        # Quadrant labels in background
        x_min, x_max = df["price_gbp"].min() - 2, df["price_gbp"].max() + 4
        ax.text(x_min + 1, 4.8, "HIDDEN GEMS\n(High Rating, Accessible Price)",
                fontsize=9, fontweight="bold", color="#059669", alpha=0.9, va="top")
        ax.text(x_max - 2, 4.8, "PREMIUM LEADERS\n(High Rating, High Price)",
                fontsize=9, fontweight="bold", color="#2563EB", alpha=0.9, ha="right", va="top")
        ax.text(x_max - 2, 1.2, "OVERPRICED RISKS\n(Low Rating, High Price)",
                fontsize=9, fontweight="bold", color="#DC2626", alpha=0.9, ha="right", va="bottom")
        ax.text(x_min + 1, 1.2, "BUDGET UNDERPERFORMERS\n(Low Rating, Low Price)",
                fontsize=9, fontweight="bold", color="#D97706", alpha=0.9, va="bottom")

        # Annotate top 2 Hidden Gems
        top_gems = df[df["strategic_segment"] == "Hidden Gem (High Value Opportunity)"].nlargest(2, "vfmi_index")
        for _, row in top_gems.iterrows():
            ax.annotate(
                f"{row['title'][:22]}...\n(VFMI: {row['vfmi_index']})",
                xy=(row["price_gbp"], row["rating_score"]),
                xytext=(row["price_gbp"] + 2, row["rating_score"] + 0.25),
                fontsize=8,
                fontweight="bold",
                color="#047857",
                arrowprops=dict(arrowstyle="->", color="#059669", lw=1),
                bbox=dict(boxstyle="round,pad=0.3", fc="#ECFDF5", ec="#10B981", alpha=0.9),
            )

        # Annotate top Overpriced Risk
        top_risk = df[df["strategic_segment"] == "Overpriced Risk (High Price, Low Rating)"].nlargest(1, "price_gbp")
        for _, row in top_risk.iterrows():
            ax.annotate(
                f"Risk: {row['title'][:20]}...\n(£{row['price_gbp']} | 1 Star)",
                xy=(row["price_gbp"], row["rating_score"]),
                xytext=(row["price_gbp"] - 14, row["rating_score"] + 0.35),
                fontsize=8,
                fontweight="bold",
                color="#B91C1C",
                arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1),
                bbox=dict(boxstyle="round,pad=0.3", fc="#FEF2F2", ec="#EF4444", alpha=0.9),
            )

        # Layout, axes, and title
        ax.set_title("Strategic Competitive Matrix: Price vs. Rating & Value Index", pad=15, fontweight="bold")
        ax.set_xlabel("Product Price (£ GBP) [Dashed line = Market Median: £{:.2f}]".format(median_price))
        ax.set_ylabel("Customer Star Rating (1 to 5 Stars)")
        ax.set_ylim(0.5, 5.5)
        ax.set_yticks([1, 2, 3, 4, 5])

        # Customize legend
        handles, labels = ax.get_legend_handles_labels()
        # Keep only segment labels, discard size numbers from legend
        seg_handles = [h for h, l in zip(handles, labels) if l in palette]
        seg_labels = [l for l in labels if l in palette]
        ax.legend(seg_handles, seg_labels, loc="lower center", bbox_to_anchor=(0.5, -0.22),
                  ncol=3, frameon=True, fontsize=8.5)

        out_path = os.path.join(self.output_dir, "01_strategic_quadrant_matrix.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Chart 1 saved: {out_path}")
        return out_path

    def plot_category_price_spread(self) -> str:
        """
        Chart 2: Category Price Benchmarks & Spreads for Top Active Categories.
        Highlights price volatility and average ratings per sector.
        """
        df = self.df
        top_cats = (
            df.groupby("category")
            .filter(lambda x: len(x) >= 3)["category"]
            .value_counts()
            .index.tolist()
        )
        if not top_cats:
            top_cats = df["category"].value_counts().head(8).index.tolist()

        filtered_df = df[df["category"].isin(top_cats)].copy()

        # Order categories by median price descending
        order = (
            filtered_df.groupby("category")["price_gbp"]
            .median()
            .sort_values(ascending=False)
            .index
        )

        fig, ax = plt.subplots(figsize=(10, 6))

        # Boxplot with overlaid stripplot for individual products
        sns.boxplot(
            data=filtered_df,
            x="price_gbp",
            y="category",
            hue="category",
            order=order,
            palette="Blues_r",
            legend=False,
            fliersize=0,
            linewidth=1.2,
            boxprops=dict(alpha=0.6),
            ax=ax,
        )
        sns.stripplot(
            data=filtered_df,
            x="price_gbp",
            y="category",
            order=order,
            color="#1E3A8A",
            size=6,
            jitter=0.2,
            alpha=0.7,
            ax=ax,
        )

        # Annotate category average rating next to each label
        cat_ratings = filtered_df.groupby("category")["rating_score"].mean().to_dict()
        for idx, cat_name in enumerate(order):
            avg_r = cat_ratings.get(cat_name, 0.0)
            ax.text(
                df["price_gbp"].max() + 1,
                idx,
                f"Avg: {avg_r:.1f} Stars",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="#1E3A8A",
            )

        ax.set_title("Category Price Benchmarks & Pricing Dispersions (Top Categories)", pad=15, fontweight="bold")
        ax.set_xlabel("Price Range (£ GBP)")
        ax.set_ylabel("Product Category")
        ax.set_xlim(df["price_gbp"].min() - 3, df["price_gbp"].max() + 10)

        out_path = os.path.join(self.output_dir, "02_category_price_spread_benchmarks.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Chart 2 saved: {out_path}")
        return out_path

    def plot_top_value_for_money_gems(self) -> str:
        """
        Chart 3: Top 10 Best Value-for-Money Index (VFMI) products.
        Executive ranking of underpriced, top-rated products.
        """
        df = self.df
        top10 = df.nlargest(10, "vfmi_index").sort_values("vfmi_index", ascending=True)

        fig, ax = plt.subplots(figsize=(10, 6))

        bars = ax.barh(
            y=range(len(top10)),
            width=top10["vfmi_index"],
            color="#10B981",
            edgecolor="#059669",
            alpha=0.85,
            height=0.65,
        )

        # Labels formatting: short title + category
        y_labels = [
            f"{row['title'][:25]}... ({row['category']})"
            for _, row in top10.iterrows()
        ]
        ax.set_yticks(range(len(top10)))
        ax.set_yticklabels(y_labels, fontsize=9)

        # Add data labels on each bar: Rating, Price, VFMI
        for idx, bar in enumerate(bars):
            val = bar.get_width()
            price = top10.iloc[idx]["price_gbp"]
            rating = top10.iloc[idx]["rating_score"]
            ax.text(
                val + 0.2,
                bar.get_y() + bar.get_height() / 2,
                f"VFMI: {val:.2f} | £{price:.2f} | {rating} Stars",
                va="center",
                fontsize=8.5,
                fontweight="bold",
                color="#065F46",
            )

        ax.set_title("Top 10 'Hidden Gems': Ranked by Value-for-Money Index (VFMI)", pad=15, fontweight="bold")
        ax.set_xlabel("Value-for-Money Index (Rating / Relative Category Price Ratio)")
        ax.set_xlim(0, top10["vfmi_index"].max() + 3.5)

        out_path = os.path.join(self.output_dir, "03_top_value_for_money_gems.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Chart 3 saved: {out_path}")
        return out_path

    def plot_inventory_risk_exposure(self) -> str:
        """
        Chart 4: Inventory Capital Exposure & Dead-Stock Risk Breakdown.
        Evaluates capital allocation across strategic segments.
        """
        df = self.df
        segment_capital = (
            df.groupby("strategic_segment")["inventory_value_gbp"]
            .sum()
            .reset_index()
            .sort_values(by="inventory_value_gbp", ascending=False)
        )

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Colors corresponding to segments
        color_map = {
            "Hidden Gem (High Value Opportunity)": "#10B981",
            "Premium Leader (High Quality, High Margin)": "#3B82F6",
            "Overpriced Risk (High Price, Low Rating)": "#EF4444",
            "Budget Underperformer (Low Rating, Low Price)": "#F59E0B",
            "Mid-Market Stable": "#94A3B8",
        }
        segment_colors = [color_map.get(s, "#CBD5E1") for s in segment_capital["strategic_segment"]]

        # 1. Donut chart of Total Inventory Value by Segment
        wedges, texts, autotexts = ax1.pie(
            segment_capital["inventory_value_gbp"],
            labels=None,
            autopct="%1.1f%%",
            pctdistance=0.75,
            colors=segment_colors,
            startangle=140,
            wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_fontweight("bold")
            at.set_color("black")

        total_cap = df["inventory_value_gbp"].sum()
        ax1.text(0, 0, f"Total\n£{total_cap:,.0f}", ha="center", va="center", fontsize=11, fontweight="bold")
        ax1.set_title("Capital Distribution by Strategic Segment", pad=10, fontweight="bold")

        # Custom legend for donut
        short_labels = [
            f"{s[:20]} (£{v:,.0f})"
            for s, v in zip(segment_capital["strategic_segment"], segment_capital["inventory_value_gbp"])
        ]
        ax1.legend(wedges, short_labels, loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=1, fontsize=8)

        # 2. Risk Exposure by Price Tier
        tier_data = (
            df.groupby(["price_tier", "capital_at_risk_flag"])["inventory_value_gbp"]
            .sum()
            .unstack(fill_value=0)
            .reindex(["Budget", "Mid-Range", "Premium"])
        )
        
        # Ensure True/False columns exist
        if True not in tier_data.columns:
            tier_data[True] = 0.0
        if False not in tier_data.columns:
            tier_data[False] = 0.0

        bar_width = 0.5
        ax2.bar(tier_data.index, tier_data[False], label="Low Risk Capital", color="#3B82F6", alpha=0.85, width=bar_width)
        ax2.bar(tier_data.index, tier_data[True], bottom=tier_data[False], label="Capital At Risk (Low Rating)", color="#EF4444", alpha=0.9, width=bar_width)

        for i, tier in enumerate(tier_data.index):
            total_tier = tier_data.loc[tier, False] + tier_data.loc[tier, True]
            risk_tier = tier_data.loc[tier, True]
            if risk_tier > 0:
                ax2.text(i, total_tier + 200, f"Risk: £{risk_tier:,.0f}", ha="center", fontsize=8.5, fontweight="bold", color="#B91C1C")

        ax2.set_title("Tied-up Capital & Dead-Stock Risk by Price Tier", pad=10, fontweight="bold")
        ax2.set_ylabel("Total Inventory Value (£ GBP)")
        ax2.set_xlabel("Pricing Tier")
        ax2.legend(loc="upper left", fontsize=8.5)

        fig.suptitle("Inventory Capital Exposure & Risk Assessment", fontsize=15, fontweight="bold", y=1.02)
        out_path = os.path.join(self.output_dir, "04_inventory_capital_at_risk.png")
        plt.tight_layout()
        plt.savefig(out_path, dpi=300, bbox_inches="tight")
        plt.close()
        logger.info(f"Chart 4 saved: {out_path}")
        return out_path

    def render_all(self):
        """
        Generate all four visual intelligence reports.
        """
        logger.info("Generating full visualization suite...")
        p1 = self.plot_strategic_quadrant_matrix()
        p2 = self.plot_category_price_spread()
        p3 = self.plot_top_value_for_money_gems()
        p4 = self.plot_inventory_risk_exposure()
        logger.info("All 4 visualizations generated and saved successfully!")
        return [p1, p2, p3, p4]


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, ".."))

    processed_path = os.path.join(project_root, "data", "processed", "ecommerce_data_processed.csv")
    output_figures_dir = os.path.join(project_root, "reports", "figures")

    visualizer = MarketVisualizer(
        processed_csv_path=processed_path,
        output_dir=output_figures_dir,
    )
    visualizer.render_all()


if __name__ == "__main__":
    main()
