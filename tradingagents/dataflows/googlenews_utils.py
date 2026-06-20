import random
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    retry_if_result,
    stop_after_attempt,
    wait_exponential,
)


def is_rate_limited(response):
    """Check if the response indicates rate limiting (status code 429)"""
    return response.status_code == 429


@retry(
    retry=(
        retry_if_result(is_rate_limited)
        | retry_if_exception_type(requests.exceptions.Timeout)
    ),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
)
def make_request(url, headers):
    """Make a request with retry logic for rate limiting. Includes 30s timeout."""
    # Random delay before each request to avoid detection
    delay = random.uniform(2, 6)
    logger.debug(f"Google News request sleeping {delay:.1f}s before fetch...")
    time.sleep(delay)
    response = requests.get(url, headers=headers, timeout=30)
    return response


def getNewsData(query, start_date, end_date, max_pages=5):
    """
    Scrape Google News search results for a given query and date range.
    query: str - search query
    start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
    end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy
    max_pages: int - maximum number of pages to scrape (default 5, ≈50 results)
    """
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.54 Safari/537.36"
        )
    }

    logger.debug(
        f"Starting Google News scrape for '{query}' ({start_date} - {end_date}, max_pages={max_pages})..."
    )
    news_results = []
    page = 0
    while page < max_pages:
        offset = page * 10
        url = (
            f"https://www.google.com/search?q={query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}"
        )

        try:
            response = make_request(url, headers)
            soup = BeautifulSoup(response.content, "html.parser")
            results_on_page = soup.select("div.SoaBEf")

            if not results_on_page:
                logger.debug(
                    f"Google News page {page + 1}: no results found, stopping pagination"
                )
                break  # No more results found

            for el in results_on_page:
                try:
                    link = el.find("a")["href"]
                    title = el.select_one("div.MBeuO").get_text()
                    snippet = el.select_one(".GI74Re").get_text()
                    date = el.select_one(".LfVVr").get_text()
                    source = el.select_one(".NUnG9d span").get_text()
                    news_results.append(
                        {
                            "link": link,
                            "title": title,
                            "snippet": snippet,
                            "date": date,
                            "source": source,
                        }
                    )
                except Exception as e:
                    logger.debug(f"Google News: error processing result: {e}")
                    # If one of the fields is not found, skip this result
                    continue

            logger.debug(
                f"Google News page {page + 1}: scraped {len(results_on_page)} results (total: {len(news_results)})"
            )

            # Check for the "Next" link (pagination)
            next_link = soup.find("a", id="pnnext")
            if not next_link:
                logger.debug("Google News: no next page link, stopping pagination")
                break

            page += 1

        except requests.exceptions.Timeout:
            logger.warning(
                f"Google News scrape timed out for '{query}' on page {page + 1}, returning partial results"
            )
            break
        except Exception as e:
            logger.warning(f"Google News scrape failed after multiple retries: {e}")
            break

    logger.debug(
        f"Google News scrape complete for '{query}': {len(news_results)} results across {page + 1} pages"
    )
    return news_results
