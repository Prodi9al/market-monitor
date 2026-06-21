"""
Price & volume spike detection across stocks, crypto, and forex.

Free-tier friendly:
- Crypto: CoinGecko (no API key needed)
- Stocks/Forex: Alpha Vantage (free key, rate-limited to ~5 calls/min, 500/day)
"""
import time
import requests
from collections import deque
from settings import load_config, env

# Rolling price history per ticker, used to compute % change and volume baseline
_history = {}  # symbol -> deque of (timestamp, price, volume)

HISTORY_WINDOW = 60  # keep last N samples per symbol


def _track(symbol: str, price: float, volume: float = None):
    if symbol not in _history:
        _history[symbol] = deque(maxlen=HISTORY_WINDOW)
    _history[symbol].append((time.time(), price, volume))


def _check_spike(symbol: str, cfg: dict) -> dict | None:
    hist = _history.get(symbol)
    if not hist or len(hist) < 2:
        return None

    window_seconds = cfg["spike_thresholds"]["window_minutes"] * 60
    now_ts, now_price, now_vol = hist[-1]

    # find the oldest sample still within the window
    baseline = None
    for ts, price, vol in hist:
        if now_ts - ts <= window_seconds:
            baseline = (ts, price, vol)
            break
    if not baseline:
        baseline = hist[0]

    _, base_price, base_vol = baseline
    if base_price == 0:
        return None

    pct_change = ((now_price - base_price) / base_price) * 100
    threshold = cfg["spike_thresholds"]["price_pct_change"]

    volume_flag = False
    if now_vol and base_vol and base_vol > 0:
        vol_ratio = now_vol / base_vol
        if vol_ratio >= cfg["spike_thresholds"]["volume_multiplier"]:
            volume_flag = True

    if abs(pct_change) >= threshold or volume_flag:
        return {
            "symbol": symbol,
            "pct_change": round(pct_change, 2),
            "current_price": now_price,
            "volume_flag": volume_flag,
            "direction": "up" if pct_change > 0 else "down",
        }
    return None


def fetch_crypto_prices(tickers: list[str]) -> list[dict]:
    """CoinGecko free endpoint, no API key required."""
    ids = ",".join(tickers)
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd&include_24hr_vol=true"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    results = []
    for ticker in tickers:
        if ticker not in data:
            continue
        price = data[ticker]["usd"]
        volume = data[ticker].get("usd_24h_vol")
        _track(ticker, price, volume)
        results.append({"symbol": ticker, "price": price, "volume": volume})
    return results


def fetch_stock_or_forex_price(symbol: str) -> dict | None:
    """Alpha Vantage GLOBAL_QUOTE endpoint. Works for stock tickers.
    For forex pairs, use fetch_forex_rate instead."""
    api_key = env("ALPHA_VANTAGE_API_KEY")
    url = "https://www.alphavantage.co/query"
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key}
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    quote = resp.json().get("Global Quote", {})
    if not quote:
        return None
    price = float(quote.get("05. price", 0))
    volume = float(quote.get("06. volume", 0))
    _track(symbol, price, volume)
    return {"symbol": symbol, "price": price, "volume": volume}


def fetch_forex_rate(pair: str) -> dict | None:
    """pair like 'EURUSD' -> from=EUR, to=USD"""
    api_key = env("ALPHA_VANTAGE_API_KEY")
    from_cur, to_cur = pair[:3], pair[3:]
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": from_cur,
        "to_currency": to_cur,
        "apikey": api_key,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    rate_data = resp.json().get("Realtime Currency Exchange Rate", {})
    if not rate_data:
        return None
    price = float(rate_data.get("5. Exchange Rate", 0))
    _track(pair, price, None)
    return {"symbol": pair, "price": price, "volume": None}


def run_price_checks(cfg: dict) -> list[dict]:
    """Poll all configured assets, return any detected spikes."""
    spikes = []

    if cfg["assets"]["crypto"]["enabled"]:
        try:
            fetch_crypto_prices(cfg["assets"]["crypto"]["tickers"])
        except Exception as e:
            print(f"[price_monitor] crypto fetch error: {e}")

    if cfg["assets"]["stocks"]["enabled"]:
        for ticker in cfg["assets"]["stocks"]["tickers"]:
            try:
                fetch_stock_or_forex_price(ticker)
                time.sleep(13)  # Alpha Vantage free tier: ~5 calls/min
            except Exception as e:
                print(f"[price_monitor] stock fetch error for {ticker}: {e}")

    if cfg["assets"]["forex"]["enabled"]:
        for pair in cfg["assets"]["forex"]["pairs"]:
            try:
                fetch_forex_rate(pair)
                time.sleep(13)
            except Exception as e:
                print(f"[price_monitor] forex fetch error for {pair}: {e}")

    for symbol in list(_history.keys()):
        spike = _check_spike(symbol, cfg)
        if spike:
            spikes.append(spike)

    return spikes


if __name__ == "__main__":
    cfg = load_config()
    print(run_price_checks(cfg))
