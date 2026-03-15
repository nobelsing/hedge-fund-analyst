# 🏦 AI Hedge Fund Analyst
### Multi-Agent Investment Research System — Built with Google ADK

A complex multi-agent system that produces institutional-grade investment memos by orchestrating 7+ specialized AI agents running in parallel and sequence with a quality-review feedback loop.

---

## Architecture

```
SequentialAgent (HedgeFundAnalyst)
│
├── ParallelAgent (ParallelResearchSwarm)     ← All 5 run SIMULTANEOUSLY
│   ├── NewsAgent          → news_analysis
│   ├── FinancialsAgent    → financials_analysis
│   ├── SentimentAgent     → sentiment_analysis
│   ├── CompetitorAgent    → competitor_analysis
│   └── RiskAgent          → risk_analysis
│
└── LoopAgent (RefinementLoop)                ← Iterates until quality passes
    ├── SynthesisAgent     → investment_memo  (reads all 5 outputs from state)
    └── ReviewerAgent      → review_verdict   (APPROVED or REVISION_NEEDED)
```

**Total agents: 8**
**ADK primitives used: LlmAgent, ParallelAgent, SequentialAgent, LoopAgent**

---

## Setup

### 1. Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- A Google Gemini API key ([get one free here](https://aistudio.google.com/app/apikey))

### 2. Install dependencies
```bash
cd hedge_fund_analyst
uv sync
```

### 3. Configure API keys
Edit `.env` and add your keys:
```env
GOOGLE_API_KEY=your_actual_key_here
```

Optional (for richer data):
```env
NEWS_API_KEY=your_newsapi_key       # https://newsapi.org (free tier)
ALPHA_VANTAGE_API_KEY=your_key      # https://alphavantage.co (free tier)
```

---

## Running the Agent

### Option A: ADK Web UI (recommended for hackathon demo)
```bash
# Run from the hedge_fund_analyst root directory
uv run adk web
```
Open http://localhost:8000 — select **HedgeFundAnalyst** — type a ticker like `Analyse NVDA`

### Option B: Command Line
```bash
uv run python run.py NVDA
uv run python run.py AAPL
uv run python run.py "Give me a full analysis of Tesla"
```

### Option C: ADK CLI
```bash
uv run adk run hedge_fund_analyst
```

---

## Example Queries

```
Analyse NVDA
Give me an investment memo for Apple
Should I buy or sell Microsoft stock?
Research Amazon for me
What's your view on Tesla TSLA?
Analyse JPMorgan Chase
```

---

## Project Structure

```
hedge_fund_analyst/
├── pyproject.toml              # uv/pip dependencies
├── .env                        # API keys (never commit this)
├── run.py                      # Programmatic runner
├── README.md
│
├── hedge_fund_analyst/         # ADK agent package
│   ├── __init__.py
│   └── agent.py                # All 8 agents + pipeline definition
│
└── tools/                      # Data retrieval tools
    ├── __init__.py
    ├── financial_tools.py      # yfinance: prices, financials, analyst ratings
    ├── news_tools.py           # NewsAPI + yfinance news fallback
    └── market_tools.py         # Competitors, macro risk, sector ETFs
```

---

## Agent Roles

| Agent | Type | Tools Used | Output Key |
|-------|------|-----------|------------|
| NewsAgent | LlmAgent | `get_company_news` | `news_analysis` |
| FinancialsAgent | LlmAgent | `get_financial_statements`, `get_analyst_recommendations`, `get_price_history` | `financials_analysis` |
| SentimentAgent | LlmAgent | `get_social_sentiment` | `sentiment_analysis` |
| CompetitorAgent | LlmAgent | `get_competitors` | `competitor_analysis` |
| RiskAgent | LlmAgent | `get_macro_risk_factors`, `get_stock_price` | `risk_analysis` |
| ParallelResearchSwarm | ParallelAgent | — | runs all 5 above |
| SynthesisAgent | LlmAgent | — | `investment_memo` |
| ReviewerAgent | LlmAgent | — | `review_verdict` |
| RefinementLoop | LoopAgent | — | iterates Synthesis + Reviewer |
| HedgeFundAnalyst | SequentialAgent | — | **root_agent** |

---

## How It Works (ADK Concepts Demonstrated)

### 1. `output_key` + Session State
Each specialist agent writes its report to `session.state` using `output_key`. The SynthesisAgent reads all 5 reports by referencing `{news_analysis}`, `{financials_analysis}`, etc. in its instruction template.

### 2. ParallelAgent (Fan-Out)
All 5 specialist agents run concurrently — this is ~5x faster than running them sequentially. ADK handles thread safety of the shared session state.

### 3. LoopAgent (Quality Gate)
The ReviewerAgent outputs either `APPROVED` or `REVISION_NEEDED`. The LoopAgent checks the `review_verdict` key and exits the loop when it sees `APPROVED` or after `max_iterations=3` passes.

### 4. SequentialAgent (Pipeline)
The outer SequentialAgent ensures the parallel research phase completes before synthesis begins.

---

## Data Sources

| Data Type | Source | Requires Key? |
|-----------|--------|--------------|
| Stock prices & fundamentals | yfinance | No |
| Financial statements | yfinance | No |
| Analyst recommendations | yfinance | No |
| Price history & technicals | yfinance | No |
| Company news | yfinance (fallback) | No |
| Company news (richer) | NewsAPI | Yes (free) |
| Short interest & insider data | yfinance | No |
| Competitor benchmarking | yfinance | No |
| Sector ETF performance | yfinance | No |

The system works fully with zero API keys (besides Google Gemini). Optional keys unlock richer news coverage.

---

## Customisation

### Add more competitor mappings
In `tools/market_tools.py`, extend the `COMPETITOR_MAP` dict:
```python
COMPETITOR_MAP = {
    "YOUR_TICKER": ["COMP1", "COMP2", "COMP3"],
    ...
}
```

### Change the model
In `.env`:
```env
GEMINI_MODEL=gemini-2.5-pro   # Better quality, slower
GEMINI_MODEL=gemini-2.5-flash  # Default — fast and capable
```

### Add more review iterations
In `hedge_fund_analyst/agent.py`:
```python
refinement_loop = LoopAgent(
    ...
    max_iterations=5,  # Allow more refinement passes
)
```
