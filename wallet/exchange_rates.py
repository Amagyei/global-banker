"""
Exchange rate service for converting cryptocurrency to USD
"""
import requests
import logging
from django.conf import settings
from django.core.cache import cache
from decimal import Decimal

logger = logging.getLogger(__name__)

# Cache exchange rates for 10 seconds to stay within CoinGecko API rate limits
# CoinGecko free tier: 10-50 calls per minute
# With 10s cache, max 6 calls per minute per rate pair (well within limits)
EXCHANGE_RATE_CACHE_TIMEOUT = 10  # 10 seconds


def get_exchange_rate(crypto_symbol: str, fiat_symbol: str = 'USD') -> Decimal:
    """
    Get current exchange rate from crypto to fiat currency.
    
    Uses CoinGecko API (free tier) for exchange rates.
    Falls back to cached value if API fails.
    
    Args:
        crypto_symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
        fiat_symbol: Fiat currency symbol (default: 'USD')
    
    Returns:
        Decimal: Exchange rate (1 crypto = X fiat)
    """
    cache_key = f'exchange_rate_{crypto_symbol}_{fiat_symbol}'
    
    # Check cache first - returns None if expired (after 10 seconds)
    try:
        cached_rate = cache.get(cache_key)
        if cached_rate is not None:
            logger.debug(f"Using cached exchange rate for {crypto_symbol}/{fiat_symbol}")
            return Decimal(str(cached_rate))
    except Exception as e:
        # Cache error (e.g., Redis connection issue) - continue to fetch from API
        logger.warning(f"Cache error (will fetch from API): {e}")
    
    # Cache expired or not found - fetch fresh rate from API
    try:
        rate = _fetch_exchange_rate_from_api(crypto_symbol, fiat_symbol)
        if rate:
            # Try to cache the rate for 10 seconds (will auto-expire)
            try:
                cache.set(cache_key, float(rate), EXCHANGE_RATE_CACHE_TIMEOUT)
                logger.debug(f"Cached new exchange rate for {crypto_symbol}/{fiat_symbol}: {rate}")
            except Exception as e:
                # Cache write failed - but we still have the rate, so continue
                logger.warning(f"Failed to cache rate (using it anyway): {e}")
            return rate
    except Exception as e:
        logger.error(f"Failed to fetch exchange rate for {crypto_symbol}/{fiat_symbol}: {e}")
    
    # Fallback to cached value (if cache is working)
    try:
        fallback_rate = cache.get(cache_key)
        if fallback_rate is not None:
            return Decimal(str(fallback_rate))
    except Exception:
        pass  # Cache not available, continue to default
    
    # Last resort: return a default rate (should not happen in production)
    logger.warning(f"Using fallback exchange rate for {crypto_symbol}/{fiat_symbol}")
    if crypto_symbol.upper() == 'BTC':
        return Decimal('50000.00')  # Rough BTC/USD fallback
    elif crypto_symbol.upper() in ['ETH', 'ETHEREUM']:
        return Decimal('3000.00')  # Rough ETH/USD fallback
    else:
        return Decimal('1.00')  # Default 1:1 if unknown


def _fetch_exchange_rate_from_api(crypto_symbol: str, fiat_symbol: str) -> Decimal:
    """
    Fetch exchange rate from CoinGecko API.
    
    Args:
        crypto_symbol: Cryptocurrency symbol
        fiat_symbol: Fiat currency symbol
    
    Returns:
        Decimal: Exchange rate
    """
    # Map symbols to CoinGecko IDs
    coin_id_map = {
        'BTC': 'bitcoin',
        'ETH': 'ethereum',
        'ETHEREUM': 'ethereum',
        'USDT': 'tether',
        'USDC': 'usd-coin',
    }
    
    coin_id = coin_id_map.get(crypto_symbol.upper(), crypto_symbol.lower())
    
    # CoinGecko free API endpoint
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {
        'ids': coin_id,
        'vs_currencies': fiat_symbol.lower(),
    }
    
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if coin_id in data and fiat_symbol.lower() in data[coin_id]:
            rate = Decimal(str(data[coin_id][fiat_symbol.lower()]))
            logger.info(f"Fetched exchange rate {crypto_symbol}/{fiat_symbol}: {rate}")
            return rate
        else:
            raise ValueError(f"Exchange rate not found for {crypto_symbol}/{fiat_symbol}")
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed for exchange rate: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Invalid API response for exchange rate: {e}")
        raise


def convert_crypto_to_usd(amount_atomic: int, crypto_symbol: str, decimals: int) -> int:
    """
    Convert cryptocurrency amount (in atomic units) to USD minor units (cents).
    
    Args:
        amount_atomic: Amount in smallest crypto unit (satoshi, wei, etc.)
        crypto_symbol: Cryptocurrency symbol
        decimals: Number of decimals for the cryptocurrency
    
    Returns:
        int: Amount in USD minor units (cents)
    """
    # Convert atomic units to whole units
    amount_crypto = Decimal(amount_atomic) / Decimal(10 ** decimals)
    
    # Get exchange rate
    rate = get_exchange_rate(crypto_symbol, 'USD')
    
    # Convert to USD and then to minor units (cents)
    amount_usd = amount_crypto * rate
    amount_minor = int(amount_usd * 100)  # Convert to cents
    
    return amount_minor

