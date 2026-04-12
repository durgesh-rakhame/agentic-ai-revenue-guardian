"""
============================================================
PROJECT : Agentic AI Revenue Guardian
FILE    : 4_agent.py
PURPOSE : The AGENTIC core of the project.
          For every detected anomaly, this agent:
            1. Queries the web error logs around the anomaly date
            2. Builds an intelligent prompt for the LLM
            3. Calls OpenAI / Gemini API to generate a plain-English
               business summary that a store manager can actually act on
            4. Prints the final alert report
AUTHOR  : Durgesh Rakhame
============================================================

HOW TO RUN:
    pip install pandas openai python-dotenv
    
    Option A (OpenAI):
        Set OPENAI_API_KEY in a .env file, then run:
        python 4_agent.py --provider openai
    
    Option B (Gemini):
        pip install google-generativeai
        Set GEMINI_API_KEY in a .env file, then run:
        python 4_agent.py --provider gemini

    Option C (No API key — demo mode):
        python 4_agent.py --demo
        (Uses a mock LLM response so you can test the full pipeline)

INTERVIEW TIP — Why is this "agentic"?
    "This system perceives data (reads CSVs), reasons about it
     (Isolation Forest), makes autonomous decisions (anomaly or not?),
     and takes action (queries logs + calls LLM + generates alert)
     — all without human input. That perceive-reason-decide-act
     loop is the definition of an AI agent."
"""

import pandas as pd
import argparse
import os
from datetime import date, timedelta

# ── Optional: load API keys from .env file ───────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # dotenv not installed — use environment variables directly


# ─────────────────────────────────────────────────────────
# STEP 1: Query Error Logs Around the Anomaly Date
# ─────────────────────────────────────────────────────────

def query_error_logs(anomaly_date: str, logs_filepath: str = "web_logs.csv") -> pd.DataFrame:
    """
    Given an anomaly date, fetch error log data from ±1 day window.
    This mimics what a real agent would do: look up context automatically.

    Args:
        anomaly_date  : Date string 'YYYY-MM-DD' when the anomaly occurred
        logs_filepath : Path to the web logs CSV

    Returns:
        DataFrame of error logs near the anomaly, sorted by error count
    """
    logs_df = pd.read_csv(logs_filepath, parse_dates=["log_date"])

    # Build a ±1 day window around the anomaly
    target = pd.to_datetime(anomaly_date)
    window_start = target - timedelta(days=1)
    window_end   = target + timedelta(days=1)

    # Filter to window
    mask = (logs_df["log_date"] >= window_start) & (logs_df["log_date"] <= window_end)
    nearby_logs = logs_df[mask].copy()

    # Aggregate: total errors by type and affected page
    summary = nearby_logs.groupby(["log_date", "error_type", "affected_page"]).agg(
        total_errors = ("error_count", "sum")
    ).reset_index().sort_values("total_errors", ascending=False)

    return summary


# ─────────────────────────────────────────────────────────
# STEP 2: Build the LLM Prompt (The "Brain" of the Agent)
# ─────────────────────────────────────────────────────────

def build_llm_prompt(anomaly_row: pd.Series, error_logs: pd.DataFrame) -> str:
    """
    Construct a structured prompt that gives the LLM:
      - The revenue anomaly facts (what happened)
      - The correlated error log data (why it might have happened)
      - A clear instruction to produce a business-friendly summary

    This is called "prompt engineering" — a key data analyst skill in 2025.

    Args:
        anomaly_row : One row from anomaly_results.csv (the flagged day)
        error_logs  : Error log summary from query_error_logs()

    Returns:
        A formatted string prompt ready to send to an LLM
    """

    # Format the error log data for the prompt
    if error_logs.empty:
        error_context = "No significant error spikes detected in the log window."
    else:
        top_errors = error_logs.head(5)  # Send top 5 error events to avoid token overload
        error_lines = []
        for _, row in top_errors.iterrows():
            error_lines.append(
                f"  - {row['error_type']} on '{row['affected_page']}': "
                f"{int(row['total_errors'])} errors on {str(row['log_date']).split(' ')[0]}"
            )
        error_context = "\n".join(error_lines)

    # Revenue stats for context
    revenue       = float(anomaly_row["total_revenue"])
    revenue_avg   = float(anomaly_row["revenue_7d_avg"])
    drop_pct      = round((1 - revenue / revenue_avg) * 100, 1) if revenue_avg > 0 else 0
    anomaly_date  = str(anomaly_row["sale_date"]).split(" ")[0]

    # ── The actual prompt ────────────────────────────────
    prompt = f"""
You are a Senior Business Intelligence Analyst at an e-commerce company.
Your job is to write a concise, actionable alert for a store manager when revenue drops suddenly.

--- ANOMALY DETECTED ---
Date          : {anomaly_date}
Daily Revenue : ₹{revenue:,.2f}  (normal avg: ₹{revenue_avg:,.2f})
Revenue Drop  : {drop_pct}% below 7-day average
Units Sold    : {int(anomaly_row['total_units'])} units

--- CORRELATED WEB ERROR LOGS ---
{error_context}

--- YOUR TASK ---
Write a 3-sentence business alert summary for the store manager.
Sentence 1: State what happened (revenue drop amount and date).
Sentence 2: Identify the most likely technical root cause based on the error logs.
Sentence 3: Recommend one immediate action the team should take.

Keep the language simple, clear, and non-technical. Avoid jargon.
End with a severity rating: LOW / MEDIUM / HIGH / CRITICAL.
""".strip()

    return prompt


# ─────────────────────────────────────────────────────────
# STEP 3: Call the LLM API
# ─────────────────────────────────────────────────────────

def call_openai(prompt: str) -> str:
    """Call OpenAI GPT-4o-mini with the constructed prompt."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model    = "gpt-4o-mini",
            messages = [{"role": "user", "content": prompt}],
            max_tokens = 300,
            temperature = 0.4,  # Lower temperature = more factual, less creative
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[OpenAI Error] {str(e)}"


def call_gemini(prompt: str) -> str:
    """Call Google Gemini with the constructed prompt."""
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model    = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[Gemini Error] {str(e)}"


def mock_llm_response(anomaly_date: str, drop_pct: float) -> str:
    """
    Demo mode: returns a realistic-looking LLM response.
    Use this to show the full pipeline without an API key.
    """
    return (
        f"On {anomaly_date}, daily revenue dropped by approximately {drop_pct:.0f}% "
        f"compared to the 7-day average, representing a significant revenue loss. "
        f"Web server logs indicate a spike in critical errors on the checkout or product page, "
        f"which likely prevented customers from completing purchases. "
        f"Immediate action required: the engineering team should roll back the most recent "
        f"deployment and restore the affected endpoint within the next 30 minutes.\n\n"
        f"Severity: CRITICAL"
    )


# ─────────────────────────────────────────────────────────
# STEP 4: The Agent Loop — Run on All Anomalies
# ─────────────────────────────────────────────────────────

def run_agent(provider: str = "demo"):
    """
    Main agentic loop:
      For each detected anomaly → query logs → build prompt → call LLM → print alert
    
    This is the 'perceive → reason → decide → act' cycle running autonomously.
    """

    print("\n🤖 Agentic AI Revenue Guardian — AGENT RUNNING")
    print("=" * 55)

    # Load anomaly results from detection step
    try:
        results_df = pd.read_csv("anomaly_results.csv", parse_dates=["sale_date"])
    except FileNotFoundError:
        print("[ERROR] anomaly_results.csv not found. Run 3_anomaly_detection.py first.")
        return

    anomalies = results_df[results_df["is_anomaly"] == True]
    print(f"[✓] Found {len(anomalies)} anomalies to investigate\n")

    all_alerts = []

    # ── Agent loop: one iteration per anomaly ────────────
    for idx, anomaly_row in anomalies.iterrows():

        anomaly_date = str(anomaly_row["sale_date"]).split(" ")[0]
        revenue      = float(anomaly_row["total_revenue"])
        revenue_avg  = float(anomaly_row["revenue_7d_avg"])
        drop_pct     = round((1 - revenue / revenue_avg) * 100, 1) if revenue_avg > 0 else 0

        print(f"━━━ INVESTIGATING: {anomaly_date} ━━━")
        print(f"   Revenue: ₹{revenue:,.0f}  |  7-day avg: ₹{revenue_avg:,.0f}  |  Drop: {drop_pct}%")

        # ── PERCEIVE: Query error logs automatically ─────
        print("   [Agent] Querying error logs...")
        error_logs = query_error_logs(anomaly_date)

        if not error_logs.empty:
            top = error_logs.iloc[0]
            print(f"   [Agent] Top error: {top['error_type']} on {top['affected_page']} "
                  f"({int(top['total_errors'])} errors)")
        else:
            print("   [Agent] No correlated errors found.")

        # ── REASON: Build the LLM prompt ─────────────────
        print("   [Agent] Building LLM prompt...")
        prompt = build_llm_prompt(anomaly_row, error_logs)

        # ── ACT: Call the LLM ─────────────────────────────
        print(f"   [Agent] Calling LLM ({provider})...")

        if provider == "openai":
            summary = call_openai(prompt)
        elif provider == "gemini":
            summary = call_gemini(prompt)
        else:
            # Demo mode — no API key needed
            summary = mock_llm_response(anomaly_date, drop_pct)

        # ── Alert report ──────────────────────────────────
        alert = {
            "date":    anomaly_date,
            "drop":    f"{drop_pct}%",
            "summary": summary,
        }
        all_alerts.append(alert)

        print(f"\n   📢 BUSINESS ALERT GENERATED:")
        print(f"   {'─'*48}")
        for line in summary.split(". "):
            if line.strip():
                print(f"   {line.strip()}.")
        print(f"   {'─'*48}\n")

    # ── Final report ──────────────────────────────────────
    print("=" * 55)
    print(f"✅ Agent completed. {len(all_alerts)} alerts generated.")
    print("   In production, these alerts would be:")
    print("   → Emailed to the operations manager")
    print("   → Posted to a Slack #revenue-alerts channel")
    print("   → Logged to a dashboard (Power BI / Tableau)")


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic AI Revenue Guardian")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini", "demo"],
        default="demo",
        help="LLM provider to use (default: demo — no API key needed)"
    )
    args = parser.parse_args()

    run_agent(provider=args.provider)
