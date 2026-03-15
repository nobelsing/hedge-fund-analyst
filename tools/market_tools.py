"""
tools/market_tools.py
Competitor comparison, market data, and risk assessment tools.
"""

import os
import json

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False


def get_competitors(ticker: str) -> dict:
    """Identifies key competitors of a company and retrieves comparative metrics.

    Args:
        ticker: The stock ticker symbol (e.g. 'AAPL', 'NVDA').

    Returns:
        dict: status and result with competitor tickers, their valuations, growth rates, and market positioning.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    # Curated competitor map for common tickers — extendable
    COMPETITOR_MAP = {
        # Tech / Semiconductors
        "NVDA": ["AMD", "INTC", "QCOM", "AVGO"],
        "AMD": ["NVDA", "INTC", "QCOM"],
        "INTC": ["NVDA", "AMD", "QCOM", "TSM"],
        "AAPL": ["MSFT", "GOOGL", "AMZN", "META"],
        "MSFT": ["AAPL", "GOOGL", "AMZN", "CRM"],
        "GOOGL": ["MSFT", "META", "AMZN", "SNAP"],
        "META": ["GOOGL", "SNAP", "PINS", "TWTR"],
        "AMZN": ["MSFT", "GOOGL", "BABA", "WMT"],
        "TSLA": ["GM", "F", "RIVN", "NIO", "STLA"],
        # Finance
        "JPM": ["BAC", "WFC", "GS", "MS", "C"],
        "BAC": ["JPM", "WFC", "C", "GS"],
        "GS": ["MS", "JPM", "BAC", "BX"],
        # Energy
        "XOM": ["CVX", "BP", "SHEL", "COP"],
        "CVX": ["XOM", "BP", "SHEL", "COP"],
    }

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        sector = info.get("sector", "")
        industry = info.get("industry", "")

        # Get competitors from map or use sector peers
        competitor_tickers = COMPETITOR_MAP.get(ticker.upper(), [])

        if not competitor_tickers:
            return {
                "status": "success",
                "data": {
                    "ticker": ticker.upper(),
                    "sector": sector,
                    "industry": industry,
                    "note": f"No curated competitor list for {ticker}. Sector: {sector}, Industry: {industry}",
                    "competitors": [],
                }
            }

        # Fetch basic data for each competitor
        competitor_data = []
        for comp_ticker in competitor_tickers:
            try:
                comp = yf.Ticker(comp_ticker)
                comp_info = comp.info
                competitor_data.append({
                    "ticker": comp_ticker,
                    "name": comp_info.get("longName", comp_ticker),
                    "market_cap": comp_info.get("marketCap", "N/A"),
                    "pe_ratio": comp_info.get("trailingPE", "N/A"),
                    "revenue_growth": comp_info.get("revenueGrowth", "N/A"),
                    "profit_margin": comp_info.get("profitMargins", "N/A"),
                    "return_on_equity": comp_info.get("returnOnEquity", "N/A"),
                    "price_to_sales": comp_info.get("priceToSalesTrailing12Months", "N/A"),
                    "52_week_return": _calc_52w_return(comp_ticker),
                })
            except Exception:
                competitor_data.append({"ticker": comp_ticker, "error": "Could not fetch data"})

        # Main company metrics for comparison
        main_metrics = {
            "ticker": ticker.upper(),
            "name": info.get("longName", ticker),
            "market_cap": info.get("marketCap", "N/A"),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "revenue_growth": info.get("revenueGrowth", "N/A"),
            "profit_margin": info.get("profitMargins", "N/A"),
            "return_on_equity": info.get("returnOnEquity", "N/A"),
            "price_to_sales": info.get("priceToSalesTrailing12Months", "N/A"),
            "52_week_return": _calc_52w_return(ticker.upper()),
        }

        return {
            "status": "success",
            "data": {
                "subject_company": main_metrics,
                "competitors": competitor_data,
                "sector": sector,
                "industry": industry,
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


def _calc_52w_return(ticker: str) -> str:
    """Helper: calculates 52-week price return."""
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty or len(hist) < 2:
            return "N/A"
        start = float(hist["Close"].iloc[0])
        end = float(hist["Close"].iloc[-1])
        return f"{round(((end / start) - 1) * 100, 1)}%"
    except Exception:
        return "N/A"


def get_macro_risk_factors(ticker: str) -> dict:
    """Analyzes macroeconomic risk factors affecting the stock including sector ETF performance, beta, and broader market correlations.

    Args:
        ticker: The stock ticker symbol.

    Returns:
        dict: status and result with beta, correlation to market, sector performance, and identified risk factors.
    """
    if not YFINANCE_AVAILABLE:
        return {"status": "error", "error_message": "yfinance not installed"}

    SECTOR_ETFS = {
        "Technology": "XLK",
        "Consumer Cyclical": "XLY",
        "Consumer Defensive": "XLP",
        "Healthcare": "XLV",
        "Financial Services": "XLF",
        "Energy": "XLE",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Basic Materials": "XLB",
        "Communication Services": "XLC",
        "Industrials": "XLI",
    }

    try:
        stock = yf.Ticker(ticker.upper())
        info = stock.info
        sector = info.get("sector", "")
        sector_etf = SECTOR_ETFS.get(sector, "SPY")

        # Get 1Y price history for beta/correlation calc
        stock_hist = stock.history(period="1y")["Close"].pct_change().dropna()
        spy_hist = yf.Ticker("SPY").history(period="1y")["Close"].pct_change().dropna()
        sector_hist = yf.Ticker(sector_etf).history(period="1y")["Close"].pct_change().dropna()

        # Align indices
        common_dates = stock_hist.index.intersection(spy_hist.index)
        s = stock_hist.loc[common_dates]
        m = spy_hist.loc[common_dates]

        # Correlation with SPY
        correlation = float(s.corr(m)) if len(s) > 10 else "N/A"

        # Sector ETF 1Y return
        sector_1y_return = "N/A"
        try:
            sec_hist = yf.Ticker(sector_etf).history(period="1y")["Close"]
            sector_1y_return = f"{round(((float(sec_hist.iloc[-1]) / float(sec_hist.iloc[0])) - 1) * 100, 1)}%"
        except Exception:
            pass

        # SPY 1Y return
        spy_1y_return = "N/A"
        try:
            spy_full = spy_hist  # already pct_change
            spy_close = yf.Ticker("SPY").history(period="1y")["Close"]
            spy_1y_return = f"{round(((float(spy_close.iloc[-1]) / float(spy_close.iloc[0])) - 1) * 100, 1)}%"
        except Exception:
            pass

        # Identify risk flags
        risk_flags = []
        beta = info.get("beta")
        if isinstance(beta, (int, float)):
            if beta > 1.5:
                risk_flags.append(f"High beta ({beta:.2f}) — stock moves significantly more than the market")
            elif beta < 0:
                risk_flags.append(f"Negative beta ({beta:.2f}) — inverse correlation with market")

        debt_to_equity = info.get("debtToEquity")
        if isinstance(debt_to_equity, (int, float)) and debt_to_equity > 200:
            risk_flags.append(f"High debt-to-equity ratio ({debt_to_equity:.0f}%)")

        short_pct = info.get("shortPercentOfFloat")
        if isinstance(short_pct, (int, float)) and short_pct > 0.15:
            risk_flags.append(f"High short interest ({short_pct*100:.1f}% of float) — bearish institutional sentiment")

        pe = info.get("trailingPE")
        if isinstance(pe, (int, float)) and pe > 50:
            risk_flags.append(f"Elevated P/E ratio ({pe:.1f}x) — priced for significant growth")

        return {
            "status": "success",
            "data": {
                "ticker": ticker.upper(),
                "beta": info.get("beta", "N/A"),
                "market_correlation_1y": round(correlation, 3) if isinstance(correlation, float) else correlation,
                "sector": sector,
                "sector_etf": sector_etf,
                "sector_1y_return": sector_1y_return,
                "spy_1y_return": spy_1y_return,
                "country": info.get("country", "N/A"),
                "currency": info.get("currency", "N/A"),
                "fiscal_year_end": info.get("lastFiscalYearEnd", "N/A"),
                "audit_risk": info.get("auditRisk", "N/A"),
                "board_risk": info.get("boardRisk", "N/A"),
                "compensation_risk": info.get("compensationRisk", "N/A"),
                "shareholder_rights_risk": info.get("shareHolderRightsRisk", "N/A"),
                "overall_risk": info.get("overallRisk", "N/A"),
                "risk_flags": risk_flags if risk_flags else ["No major risk flags identified"],
            }
        }
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
