# gets data/stats
# pyright: reportSelfClsParameterName=false
# The decorator pattern below (init_ticker) replaces the first parameter
# (a yfinance.Ticker) at runtime. Methods intentionally omit `self`.
# Disabling the "parameter must be a supertype of its class" check project-wide
# for this file since it's a deliberate meta-programming design choice.

import yfinance as yf
from typing import Annotated, Callable, Any, Optional
from pandas import DataFrame
import pandas as pd
from functools import wraps

from .utils import save_output, SavePathType, decorate_all_methods


def init_ticker(func: Callable) -> Callable:
    """Decorator to initialize yf.Ticker and pass it to the function."""

    @wraps(func)
    def wrapper(symbol: Annotated[str, "ticker symbol"], *args, **kwargs) -> Any:
        ticker = yf.Ticker(symbol)
        return func(ticker, *args, **kwargs)

    return wrapper

from typing_extensions import deprecated

@deprecated("Utilities only for stocks are deprecated.")
@decorate_all_methods(init_ticker)
class YFinanceUtils:

    def get_stock_data(
        symbol: Annotated[str, "ticker symbol"],
        start_date: Annotated[
            str, "start date for retrieving stock price data, YYYY-mm-dd"
        ],
        end_date: Annotated[
            str, "end date for retrieving stock price data, YYYY-mm-dd"
        ],
        save_path: Optional[str] = None,
    ) -> DataFrame:
        """retrieve stock price data for designated ticker symbol"""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        # add one day to the end_date so that the data range is inclusive
        end_dt = pd.to_datetime(end_date) + pd.DateOffset(days=1)
        end_str = end_dt.strftime("%Y-%m-%d")
        stock_data = ticker.history(start=start_date, end=end_str)
        # save_output(stock_data, f"Stock data for {ticker.ticker}", save_path)
        return stock_data

    def get_stock_info(
        symbol: Annotated[str, "ticker symbol"],
    ) -> dict:
        """Fetches and returns latest stock information."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        stock_info = ticker.info
        return stock_info

    def get_asset_info(
        symbol: Annotated[str, "ticker symbol"],
        save_path: Optional[str] = None,
    ) -> DataFrame:
        """Fetches and returns asset information as a DataFrame."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        info = ticker.info
        asset_info = {
            "Asset Name": info.get("shortName", "N/A"),
            "Industry": info.get("industry", "N/A"),
            "Sector": info.get("sector", "N/A"),
            "Country": info.get("country", "N/A"),
            "Website": info.get("website", "N/A"),
        }
        asset_info_df = DataFrame([asset_info])
        if save_path:
            asset_info_df.to_csv(save_path)
            print(f"Asset info for {ticker.ticker} saved to {save_path}")
        return asset_info_df

    def get_stock_dividends(
        symbol: Annotated[str, "ticker symbol"],
        save_path: Optional[str] = None,
    ) -> DataFrame:
        """Fetches and returns the latest dividends data as a DataFrame."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        dividends: DataFrame = ticker.dividends  # type: ignore[assignment]
        if save_path:
            dividends.to_csv(save_path)
            print(f"Dividends for {ticker.ticker} saved to {save_path}")
        return dividends

    def get_income_stmt(
        symbol: Annotated[str, "ticker symbol"],
    ) -> DataFrame:
        """Fetches and returns the latest income statement of the asset as a DataFrame."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        income_stmt = ticker.financials
        return income_stmt

    def get_balance_sheet(
        symbol: Annotated[str, "ticker symbol"],
    ) -> DataFrame:
        """Fetches and returns the latest balance sheet of the asset as a DataFrame."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        balance_sheet = ticker.balance_sheet
        return balance_sheet

    def get_cash_flow(
        symbol: Annotated[str, "ticker symbol"],
    ) -> DataFrame:
        """Fetches and returns the latest cash flow statement of the asset as a DataFrame."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        cash_flow = ticker.cashflow
        return cash_flow

    def get_analyst_recommendations(
        symbol: Annotated[str, "ticker symbol"],
    ) -> tuple:
        """Fetches the latest analyst recommendations and returns the most common recommendation and its count."""
        ticker: yf.Ticker = symbol  # type: ignore[assignment]
        recommendations = ticker.recommendations
        if recommendations.empty:
            return None, 0  # No recommendations available

        # Assuming 'period' column exists and needs to be excluded
        row_0 = recommendations.iloc[0, 1:]  # Exclude 'period' column if necessary

        # Find the maximum voting result
        max_votes = row_0.max()
        majority_voting_result = row_0[row_0 == max_votes].index.tolist()

        return majority_voting_result[0], max_votes
