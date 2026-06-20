
import requests
from loguru import logger


def fetch_fear_and_greed_from_alternativeme():
    """
    Fetch the Fear and Greed Index from Alternative.me API.
    Returns:
        list[str]: A list of fear and greed index values. Sorted by date in descending order.
    """
    url = "https://api.alternative.me/fng/?limit=10"
    logger.debug("Starting Fear & Greed index fetch...")
    try:
        response = requests.get(url, timeout=30)
        logger.debug("Fear & Greed index fetch completed")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                return [value["value"] for value in data["data"] if "value" in value]
    except requests.exceptions.Timeout:
        logger.warning("Fear & Greed index fetch timed out after 30s")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Fear & Greed index fetch failed: {e}")
        return None
