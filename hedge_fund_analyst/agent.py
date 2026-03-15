import os
import sys
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.agents.loop_agent import LoopAgent

from tools import (
    get_stock_price,
    get_financial_statements,
    get_analyst_recommendations,
    get_price_history,
    get_company_news,
    get_social_sentiment,
    get_competitors,
    get_macro_risk_factors,
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

COMPANY_TO_TICKER = {
    "apple": "AAPL", "microsoft": "MSFT", "google": "GOOGL",
    "alphabet": "GOOGL", "amazon": "AMZN", "meta": "META",
    "facebook": "META", "netflix": "NFLX", "nvidia": "NVDA",
    "tesla": "TSLA", "amd": "AMD", "intel": "INTC",
    "qualcomm": "QCOM", "broadcom": "AVGO", "salesforce": "CRM",
    "oracle": "ORCL", "adobe": "ADBE", "paypal": "PYPL",
    "uber": "UBER", "lyft": "LYFT", "airbnb": "ABNB",
    "shopify": "SHOP", "snowflake": "SNOW", "palantir": "PLTR",
    "spotify": "SPOT", "snap": "SNAP", "pinterest": "PINS",
    "zoom": "ZM", "ibm": "IBM", "cisco": "CSCO",
    "jpmorgan": "JPM", "jp morgan": "JPM", "goldman": "GS",
    "goldman sachs": "GS", "morgan stanley": "MS",
    "bank of america": "BAC", "wells fargo": "WFC",
    "citigroup": "C", "citi": "C", "blackstone": "BX",
    "visa": "V", "mastercard": "MA", "amex": "AXP",
    "american express": "AXP", "berkshire": "BRK-B",
    "gm": "GM", "general motors": "GM", "ford": "F",
    "rivian": "RIVN", "lucid": "LCID", "nio": "NIO",
    "pfizer": "PFE", "moderna": "MRNA", "unitedhealth": "UNH",
    "abbvie": "ABBV", "eli lilly": "LLY", "lilly": "LLY",
    "exxon": "XOM", "chevron": "CVX", "bp": "BP",
    "walmart": "WMT", "target": "TGT", "costco": "COST",
    "starbucks": "SBUX", "mcdonalds": "MCD", "nike": "NKE",
    "disney": "DIS",
}

STOP_WORDS = {
    "I", "A", "AN", "THE", "IS", "IT", "IN", "ON", "AT", "TO",
    "DO", "BE", "OR", "AND", "FOR", "BUY", "SELL", "GET", "CAN",
    "ME", "MY", "US", "IF", "OF", "AS", "BY", "UP", "NO", "SO",
    "GO", "HI", "OK", "ALL", "ARE", "WAS", "HAS", "HAD", "HAVE",
    "WILL", "WHAT", "ABOUT", "SHOULD", "GIVE", "TELL", "STOCK",
    "REPORT", "ANALYSIS", "THINK", "WANT", "NEED", "HOW", "WHO",
    "WHY", "WHEN", "WHERE", "WHICH", "THEIR", "THEY", "THAT",
    "THIS", "FROM", "WITH", "YOUR", "OUR", "NOT", "BUT", "ANY",
    "AI", "API", "ETF", "IPO", "CEO", "CFO", "CTO", "USA", "USD",
}

def extract_ticker_from_text(text: str) -> str:
    text_clean = text.strip()
    matches = re.findall(r'\b([A-Z]{1,5}(?:-[A-B])?)\b', text_clean)
    for match in matches:
        if match not in STOP_WORDS and len(match) >= 2:
            return match
    text_lower = text_clean.lower()
    for company, ticker in COMPANY_TO_TICKER.items():
        if company in text_lower:
            return ticker
    return "UNKNOWN"

def extract_ticker_tool(user_message: str) -> dict:
    """Extracts the stock ticker symbol from the user's message.

    Args:
        user_message: The raw message from the user requesting stock analysis.

    Returns:
        dict: Contains the extracted ticker symbol and status.
    """
    ticker = extract_ticker_from_text(user_message)
    if ticker == "UNKNOWN":
        return {"status": "error", "ticker": "UNKNOWN",
                "message": "Could not identify a stock. Please provide a ticker like NVDA or AAPL."}
    return {"status": "success", "ticker": ticker,
            "message": f"Ticker identified: {ticker}. Starting research pipeline."}

orchestrator_agent = LlmAgent(
    name="OrchestratorAgent",
    model=MODEL,
    description="Extracts the stock ticker from the user message and stores it in session state.",
    instruction="""You are the orchestrator of an AI hedge fund research system.

Call extract_ticker_tool with the user's exact message.
After calling the tool output ONLY the ticker symbol (e.g. NVDA). Nothing else.
No greetings. No explanations. Just the ticker.
""",
    tools=[extract_ticker_tool],
    output_key="ticker",
)

news_agent = LlmAgent(
    name="NewsAgent",
    model=MODEL,
    description="Fetches and analyses recent news about the company.",
    instruction="""You are a financial news analyst at a top hedge fund.
The stock ticker is: {ticker}

Do NOT ask for input. Call get_company_news immediately with ticker="{ticker}".

After results:
1. Identify 3-5 most market-moving stories.
2. For each: what happened, market impact, why it matters.
3. Overall sentiment: BULLISH | BEARISH | NEUTRAL.

Write your report now. No greetings.
""",
    tools=[get_company_news],
    output_key="news_analysis",
)

financials_agent = LlmAgent(
    name="FinancialsAgent",
    model=MODEL,
    description="Analyses financial statements, earnings, and valuation.",
    instruction="""You are a CFA-level financial analyst at a hedge fund.
The stock ticker is: {ticker}

Do NOT ask for input. Call these tools immediately with ticker="{ticker}":
1. get_financial_statements
2. get_analyst_recommendations
3. get_price_history (period="1y")

Assess: revenue growth, margins, debt, cash flow, P/E, red flags.
Give a FINANCIAL SCORE 1-10. Include specific numbers.
Write your analysis now. No greetings.
""",
    tools=[get_financial_statements, get_analyst_recommendations, get_price_history, get_stock_price],
    output_key="financials_analysis",
)

sentiment_agent = LlmAgent(
    name="SentimentAgent",
    model=MODEL,
    description="Analyses short interest, insider activity, and institutional ownership.",
    instruction="""You are a market intelligence analyst.
The stock ticker is: {ticker}

Do NOT ask for input. Call get_social_sentiment immediately with ticker="{ticker}".

Analyse: short interest, insider activity, institutional ownership.
Rate: BULLISH | BEARISH | NEUTRAL.
Write your report now. No greetings.
""",
    tools=[get_social_sentiment],
    output_key="sentiment_analysis",
)

competitor_agent = LlmAgent(
    name="CompetitorAgent",
    model=MODEL,
    description="Benchmarks the company against key competitors.",
    instruction="""You are a competitive intelligence analyst at a hedge fund.
The stock ticker is: {ticker}

Do NOT ask for input. Call get_competitors immediately with ticker="{ticker}".

Assess: P/E, revenue growth, margins, ROE vs peers.
Is the company a leader or laggard? What is its moat?
Write your analysis now. No greetings.
""",
    tools=[get_competitors],
    output_key="competitor_analysis",
)

risk_agent = LlmAgent(
    name="RiskAgent",
    model=MODEL,
    description="Evaluates macro risk, beta, and identifies red flags.",
    instruction="""You are a risk management specialist at a hedge fund.
The stock ticker is: {ticker}

Do NOT ask for input. Call these tools immediately with ticker="{ticker}":
1. get_macro_risk_factors
2. get_stock_price

Identify: market risk, financial risk, business risk, macro risk.
Assign RISK LEVEL: LOW | MODERATE | HIGH | VERY HIGH.
Write your assessment now. No greetings.
""",
    tools=[get_macro_risk_factors, get_stock_price],
    output_key="risk_analysis",
)

research_pipeline = SequentialAgent(
    name="ResearchPipeline",
    description="Runs all 5 specialist agents sequentially.",
    sub_agents=[news_agent, financials_agent, sentiment_agent, competitor_agent, risk_agent],
)

synthesis_agent = LlmAgent(
    name="SynthesisAgent",
    model=MODEL,
    description="Synthesizes all research into a comprehensive investment memo.",
    instruction="""You are a senior portfolio manager at a top-tier hedge fund.

Research for {ticker}:
- News: {news_analysis}
- Financials: {financials_analysis}
- Sentiment: {sentiment_analysis}
- Competitors: {competitor_analysis}
- Risk: {risk_analysis}

Write a complete INVESTMENT MEMO with ALL 8 sections:

# INVESTMENT MEMO: {ticker}
Date: [today's date]
Analyst: AI Hedge Fund Research System

## EXECUTIVE SUMMARY
BUY/HOLD/SELL with specific price context.

## INVESTMENT THESIS
3 specific data-backed reasons.

## FINANCIAL ANALYSIS
Revenue, margins, EPS, P/E, debt, FCF with real numbers.

## MARKET POSITION & COMPETITIVE LANDSCAPE
Specific peer comparisons, moat, threats.

## NEWS & CATALYSTS
Specific recent news stories and upcoming catalysts.

## MARKET SENTIMENT & POSITIONING
Short interest %, insider names/amounts, institutional %.

## RISK ASSESSMENT
Top 3-5 risks with severity (LOW/MEDIUM/HIGH/CRITICAL).

## RECOMMENDATION
**Rating**: BUY / HOLD / SELL
**Conviction**: HIGH / MEDIUM / LOW
**Time Horizon**: Short-term / Medium-term / Long-term
**Key Monitoring Points**: 2-3 specific things to watch.

Use REAL DATA from the research only.
""",
    output_key="investment_memo",
)

reviewer_agent = LlmAgent(
    name="ReviewerAgent",
    model=MODEL,
    description="Quality-gates the memo. Outputs APPROVED or REVISION_NEEDED.",
    instruction="""You are a compliance officer reviewing a memo for: {ticker}

Memo: {investment_memo}

Check: all 8 sections present? Specific numbers? Clear BUY/HOLD/SELL? Risks with severity?

If ALL pass: output -> APPROVED
If any fail: output -> REVISION_NEEDED: [what is missing]

Output ONLY one of those two. Nothing else.
""",
    output_key="review_verdict",
)

refinement_loop = LoopAgent(
    name="RefinementLoop",
    description="Synthesis then review loop. Max 2 iterations.",
    sub_agents=[synthesis_agent, reviewer_agent],
    max_iterations=2,
)

root_agent = SequentialAgent(
    name="HedgeFundAnalyst",
    description=(
        "AI Hedge Fund Analyst — type any stock name or ticker. "
        "Examples: 'NVDA', 'Analyse Apple', 'Should I buy Tesla?'"
    ),
    sub_agents=[orchestrator_agent, research_pipeline, refinement_loop],
)