import requests

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

COIN_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "LINK": "chainlink",
    "LTC": "litecoin",
    "DOT": "polkadot",
    "USDT": "tether",
}


def fetch_live_prices():
    ids = ",".join(COIN_IDS.values())
    url = f"{COINGECKO_BASE}/simple/price?ids={ids}&vs_currencies=usd&include_24hr_change=true"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    id_to_ticker = {v: k for k, v in COIN_IDS.items()}
    results = []
    for coin_id, info in data.items():
        ticker = id_to_ticker.get(coin_id, coin_id.upper())
        price = info.get("usd", 0)
        change_24h = info.get("usd_24h_change")
        change_str = f"{change_24h:+.2f}%" if change_24h is not None else "-"
        results.append(
            {
                "ticker": ticker,
                "price": price,
                "change_24h": change_str,
            }
        )
    return results
