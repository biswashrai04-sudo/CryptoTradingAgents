
import requests
from loguru import logger


def fetch_news_from_blockbeats(count = 10):
    url = f"https://api.theblockbeats.news/v1/open-api/open-flash?page=1&size={count}&type=push&lang=cn"
    logger.debug("Starting BlockBeats news fetch...")
    try:
        response = requests.get(url, timeout=30)
        logger.debug(f"BlockBeats news fetch completed (status {response.status_code})")
        if response.status_code == 200:
            data = response.json()
            if "data" in data and "data" in data["data"] and isinstance(data["data"]["data"], list):
                return data["data"]["data"]
            else:
                logger.warning("No 'data' key found in BlockBeats response.")
                return []
        else:
            logger.warning(f"BlockBeats error: {response.status_code} - {response.text}")
            return []
    except requests.exceptions.Timeout:
        logger.warning("BlockBeats news fetch timed out after 30s")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"BlockBeats news fetch failed: {e}")
        return []
