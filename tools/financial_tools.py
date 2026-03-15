"""
tools/financial_tools.py
Financial data retrieval tools using yfinance and Alpha Vantage.
These are plain Python functions — ADK picks them up automatically
from their docstrings.
"""

import os
import json
import requests
from datetime import datetime, timedelta

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


# ---------------------------------------------------------------------------
# Stock price & fundamentals
# ---------------------------------------------------------------------------

def get_stock_price(ticker: str) -> dict:
    """Retrieves the current stock price and basic market data for a ticker symbol.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA', 'TSLA').

    Returns:
        dict: status and result containing price, market cap, volume, 52-week range.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
        prev_close = info.get("previousClose", "N/A")
        change_pct = "N/A"
        if isinstance(price, (int, float)) and isinstance(prev_close, (int, float)) and prev_close != 0:
            change_pct = round(((price - prev_close) / prev_close) * 100, 2)

        result = {
            "ticker": ticker.upper(),
            "company_name": info.get("longName", ticker),
            "current_price": price,
            "previous_close": prev_close,
            "change_pct": change_pct,
            "market_cap": info.get("marketCap", "N/A"),
            "volume": info.get("volume", "N/A"),
            "avg_volume": info.get("averageVolume", "N/A"),
            "52_week_high": info.get("fiftyTwoWeekHigh", "N/A"),
            "52_week_low": info.get("fiftyTwoWeekLow", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "forward_pe": info.get("forwardPE", "N/A"),
            "sector": info.get("sector", "N/A"),
            "industry": info.get("industry", "N/A"),
        }
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_financial_statements(ticker: str) -> dict:
    """Retrieves key financial statement data: income statement, balance sheet, and cash flow metrics.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'MSFT').

    Returns:
        dict: status and result with revenue, profit margins, debt levels, cash flow data.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        financials = {
            "ticker": ticker.upper(),
            "revenue_ttm": info.get("totalRevenue", "N/A"),
            "gross_profit": info.get("grossProfits", "N/A"),
            "ebitda": info.get("ebitda", "N/A"),
            "net_income": info.get("netIncomeToCommon", "N/A"),
            "eps_ttm": info.get("trailingEps", "N/A"),
            "eps_forward": info.get("forwardEps", "N/A"),
            "revenue_growth_yoy": info.get("revenueGrowth", "N/A"),
            "earnings_growth_yoy": info.get("earningsGrowth", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A"),
            "operating_margin": info.get("operatingMargins", "N/A"),
            "return_on_equity": info.get("returnOnEquity", "N/A"),
            "return_on_assets": info.get("returnOnAssets", "N/A"),
            "total_cash": info.get("totalCash", "N/A"),
            "total_debt": info.get("totalDebt", "N/A"),
            "debt_to_equity": info.get("debtToEquity", "N/A"),
            "free_cashflow": info.get("freeCashflow", "N/A"),
            "operating_cashflow": info.get("operatingCashflow", "N/A"),
            "dividend_yield": info.get("dividendYield", "N/A"),
            "payout_ratio": info.get("payoutRatio", "N/A"),
        }

        # Try to get last 4 quarters of revenue from income statement
        try:
            income_stmt = stock.quarterly_income_stmt
            if not income_stmt.empty and "Total Revenue" in income_stmt.index:
                q_revenues = income_stmt.loc["Total Revenue"].head(4).to_dict()
                financials["quarterly_revenue"] = {
                    str(k.date()): v for k, v in q_revenues.items()
                }
        except Exception:
            pass

        return {"status": "success", "data": financials}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_analyst_recommendations(ticker: str) -> dict:
    """Retrieves analyst ratings, price targets, and recommendation trends for a stock.

    Args:
        ticker: The stock ticker symbol.

    Returns:
        dict: status and result with buy/sell/hold counts, average price target, recommendation consensus.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info

        recs = {
            "ticker": ticker.upper(),
            "recommendation": info.get("recommendationKey", "N/A"),
            "recommendation_mean": info.get("recommendationMean", "N/A"),
            "number_of_analysts": info.get("numberOfAnalystOpinions", "N/A"),
            "target_high_price": info.get("targetHighPrice", "N/A"),
            "target_low_price": info.get("targetLowPrice", "N/A"),
            "target_mean_price": info.get("targetMeanPrice", "N/A"),
            "target_median_price": info.get("targetMedianPrice", "N/A"),
        }

        # Get recent upgrades/downgrades
        try:
            upgrades_df = stock.upgrades_downgrades
            if upgrades_df is not None and not upgrades_df.empty:
                recent = upgrades_df.head(5).reset_index()
                recs["recent_rating_changes"] = recent.to_dict(orient="records")
        except Exception:
            pass

        return {"status": "success", "data": recs}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def get_price_history(ticker: str, period: str = "1y") -> dict:
    """Retrieves historical price data and calculates technical indicators for trend analysis.

    Args:
        ticker: The stock ticker symbol.
        period: Time period for history. Options: '1mo', '3mo', '6mo', '1y', '2y', '5y'.

    Returns:
        dict: status and result with price history summary, moving averages, volatility metrics.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    try:
        stock = yf.Ticker(ticker.upper())
        hist = stock.history(period=period)

        if hist.empty:
            return {"status": "error", "error_message": f"No price history found for {ticker}"}

        closes = hist["Close"]
        current = float(closes.iloc[-1])
        start = float(closes.iloc[0])

        # Moving averages
        ma50 = float(closes.tail(50).mean()) if len(closes) >= 50 else float(closes.mean())
        ma200 = float(closes.tail(200).mean()) if len(closes) >= 200 else float(closes.mean())

        # Volatility (annualized std dev of daily returns)
        daily_returns = closes.pct_change().dropna()
        volatility = float(daily_returns.std() * (252 ** 0.5) * 100)  # annualized %

        # Momentum: 1-month and 3-month returns
        momentum_1m = ((current / float(closes.iloc[-21])) - 1) * 100 if len(closes) >= 21 else "N/A"
        momentum_3m = ((current / float(closes.iloc[-63])) - 1) * 100 if len(closes) >= 63 else "N/A"

        result = {
            "ticker": ticker.upper(),
            "period": period,
            "current_price": round(current, 2),
            "period_start_price": round(start, 2),
            "period_return_pct": round(((current / start) - 1) * 100, 2),
            "period_high": round(float(hist["High"].max()), 2),
            "period_low": round(float(hist["Low"].min()), 2),
            "ma_50": round(ma50, 2),
            "ma_200": round(ma200, 2),
            "above_ma50": current > ma50,
            "above_ma200": current > ma200,
            "golden_cross": ma50 > ma200,
            "annualized_volatility_pct": round(volatility, 2),
            "momentum_1m_pct": round(momentum_1m, 2) if isinstance(momentum_1m, float) else momentum_1m,
            "momentum_3m_pct": round(momentum_3m, 2) if isinstance(momentum_3m, float) else momentum_3m,
            "avg_daily_volume": round(float(hist["Volume"].mean())),
        }
        return {"status": "success", "data": result}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
