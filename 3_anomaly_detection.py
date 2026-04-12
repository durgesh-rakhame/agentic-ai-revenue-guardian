"""
============================================================
PROJECT : Agentic AI Revenue Guardian
FILE    : 3_anomaly_detection.py
PURPOSE : Use Isolation Forest (ML) to automatically detect
          revenue anomalies from the sales CSV.
          No hardcoded rules — the model learns what's "normal"
          and flags anything that doesn't fit.
AUTHOR  : Durgesh Rakhame
============================================================

HOW TO RUN:
    pip install pandas scikit-learn matplotlib
    python 3_anomaly_detection.py

INTERVIEW TIP — How to explain Isolation Forest:
    "Normal data points need many splits to isolate.
     Anomalies are rare and different, so the tree isolates
     them in very few splits. Short path = anomaly."
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────
# STEP 1: Load and aggregate the sales data
# ─────────────────────────────────────────────────────────

def load_and_aggregate(filepath: str = "sales_data.csv") -> pd.DataFrame:
    """
    Load raw sales CSV and aggregate to daily total revenue.
    Isolation Forest works on daily patterns — not individual transactions.
    """
    df = pd.read_csv(filepath, parse_dates=["sale_date"])

    # Aggregate: one row per day with total revenue and units
    daily = df.groupby("sale_date").agg(
        total_revenue = ("revenue",    "sum"),
        total_units   = ("units_sold", "sum"),
        num_products  = ("product_id", "nunique"),
    ).reset_index()

    # Feature engineering: rolling 7-day average for context
    daily["revenue_7d_avg"]   = daily["total_revenue"].rolling(7, min_periods=1).mean()
    daily["revenue_vs_avg"]   = daily["total_revenue"] / daily["revenue_7d_avg"]  # ratio
    daily["day_of_week"]      = daily["sale_date"].dt.dayofweek  # 0=Mon, 6=Sun

    print(f"[✓] Data loaded: {len(daily)} days of sales aggregated")
    return daily


# ─────────────────────────────────────────────────────────
# STEP 2: Train Isolation Forest
# ─────────────────────────────────────────────────────────

def detect_anomalies(daily_df: pd.DataFrame, contamination: float = 0.10) -> pd.DataFrame:
    """
    Train an Isolation Forest on daily sales features.
    
    Parameters:
        daily_df      : aggregated daily sales DataFrame
        contamination : expected % of anomalies in the data (0.10 = 10%)
                        We know we planted 3 anomalies in 30 days = 10%
    
    Returns:
        DataFrame with 'is_anomaly' and 'anomaly_score' columns added
    """

    # ── Feature selection ──
    # These are the signals the model will learn from
    features = [
        "total_revenue",     # Raw revenue (main signal)
        "total_units",       # Units sold (corroborating signal)
        "revenue_vs_avg",    # How far from 7-day average (normalized signal)
        "day_of_week",       # Weekdays vs weekends have different baselines
    ]

    X = daily_df[features].copy()

    # ── Scale features ──
    # Isolation Forest doesn't need scaling, but it helps with interpretability
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ── Train Isolation Forest ──
    # n_estimators = number of trees (more = more stable)
    # contamination = what % of data we expect to be anomalous
    # random_state  = reproducibility
    model = IsolationForest(
        n_estimators  = 200,
        contamination = contamination,
        random_state  = 42,
        max_samples   = "auto"
    )
    model.fit(X_scaled)

    # ── Predict ──
    # IsolationForest returns: -1 = anomaly, 1 = normal
    predictions    = model.predict(X_scaled)
    anomaly_scores = model.score_samples(X_scaled)   # More negative = more anomalous

    # Add results back to dataframe
    daily_df = daily_df.copy()
    daily_df["is_anomaly"]    = predictions == -1           # True/False flag
    daily_df["anomaly_score"] = np.round(anomaly_scores, 4) # Raw score

    # Show detected anomalies
    anomalies = daily_df[daily_df["is_anomaly"]]
    print(f"\n[✓] Isolation Forest trained on {len(daily_df)} days")
    print(f"[✓] Anomalies detected: {len(anomalies)}")
    print("\n📌 Flagged dates:")
    print(anomalies[["sale_date", "total_revenue", "anomaly_score"]].to_string(index=False))

    return daily_df


# ─────────────────────────────────────────────────────────
# STEP 3: Visualise the results
# ─────────────────────────────────────────────────────────

def plot_anomalies(daily_df: pd.DataFrame):
    """
    Plot daily revenue with anomaly dates highlighted in red.
    This chart is perfect to include in your portfolio / GitHub README.
    """
    fig, ax = plt.subplots(figsize=(14, 5))

    normal   = daily_df[~daily_df["is_anomaly"]]
    anomaly  = daily_df[ daily_df["is_anomaly"]]

    # Normal revenue line
    ax.plot(daily_df["sale_date"], daily_df["total_revenue"],
            color="#4A90D9", linewidth=1.8, label="Daily Revenue", zorder=2)

    # Highlight anomaly points
    ax.scatter(anomaly["sale_date"], anomaly["total_revenue"],
               color="#E74C3C", s=120, zorder=5, label="Anomaly Detected", marker="v")

    # 7-day rolling average line
    ax.plot(daily_df["sale_date"], daily_df["revenue_7d_avg"],
            color="#F39C12", linewidth=1.2, linestyle="--", label="7-Day Avg", zorder=3)

    # Annotate each anomaly with the date
    for _, row in anomaly.iterrows():
        ax.annotate(
            f"  {row['sale_date'].strftime('%b %d')}",
            xy=(row["sale_date"], row["total_revenue"]),
            fontsize=9, color="#E74C3C", fontweight="bold"
        )

    ax.set_title("Agentic AI Revenue Guardian — Anomaly Detection", fontsize=14, fontweight="bold")
    ax.set_xlabel("Date")
    ax.set_ylabel("Total Daily Revenue (₹)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("anomaly_chart.png", dpi=150)
    plt.show()
    print("\n[✓] Chart saved as anomaly_chart.png")


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n🔍 Agentic AI Revenue Guardian — Anomaly Detection")
    print("=" * 50)

    daily_df     = load_and_aggregate("sales_data.csv")
    daily_df     = detect_anomalies(daily_df, contamination=0.10)

    plot_anomalies(daily_df)

    # Save results for the next step (agent script)
    daily_df.to_csv("anomaly_results.csv", index=False)
    print("\n[✓] Results saved to anomaly_results.csv")
    print("✅ Run 4_agent.py next to generate LLM summaries.")
