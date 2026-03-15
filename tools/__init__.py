"""Tools package for the Hedge Fund Analyst multi-agent system."""

from .financial_tools import (
    get_stock_price,
    get_financial_statements,
    get_analyst_recommendations,
    get_price_history,
)
from .news_tools import (
    get_company_news,
    get_social_sentiment,
)
from .market_tools import (
    get_competitors,
    get_macro_risk_factors,
)

__all__ = [
    "get_stock_price",
    "get_financial_statements",
    "get_analyst_recommendations",
    "get_price_history",
    "get_company_news",
    "get_social_sentiment",
    "get_competitors",
    "get_macro_risk_factors",
]
