"""
Robust blockchain monitoring system with error handling, retries, and health checks
"""
import time
import logging
import requests
from typing import Optional, Dict, List, Tuple
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from datetime import timedelta

logger = logging.getLogger(__name__)


class MonitoringError(Exception):
    """Base exception for monitoring errors"""
    pass


class APIError(MonitoringError):
    """API request failed"""
    pass


class RateLimitError(APIError):
    """Rate limit exceeded"""
    pass


class RetryableError(APIError):
    """Temporary error that can be retried"""
    pass


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.
    Opens circuit after consecutive failures, closes after success.
    """
    
    def __init__(self, failure_threshold=5, recovery_timeout=60, half_open_max_calls=3):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half_open
        self.half_open_calls = 0
    
    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half_open'
                self.half_open_calls = 0
                logger.info("Circuit breaker: Moving to half-open state")
            else:
                raise APIError("Circuit breaker is OPEN - too many failures")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call"""
        if self.state == 'half_open':
            self.half_open_calls += 1
            if self.half_open_calls >= self.half_open_max_calls:
                self.state = 'closed'
                self.failure_count = 0
                logger.info("Circuit breaker: Closed - service recovered")
        elif self.state == 'closed':
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == 'half_open':
            self.state = 'open'
            logger.warning("Circuit breaker: Opened - service still failing")
        elif self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.error(f"Circuit breaker: Opened after {self.failure_count} failures")


class RobustBlockchainMonitor:
    """
    Enhanced blockchain monitor with retries, error handling, and health checks.
    Supports both testnet and mainnet.
    """
    
    def __init__(self, network, max_retries=3, retry_delay=1, backoff_factor=2):
        self.network = network
        self.base_url = network.effective_explorer_api_url.rstrip('/')
        self.timeout = 10
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.backoff_factor = backoff_factor
        
        # Circuit breaker per network
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            half_open_max_calls=3
        )
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 0.5  # Minimum 500ms between requests
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict:
        """
        Make HTTP request with retry logic and error handling.
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                
                # Use circuit breaker
                def _request():
                    response = requests.get(
                        url,
                        params=params,
                        timeout=self.timeout,
                        headers={'User-Agent': 'GlobalBanker/1.0'}
                    )
                    response.raise_for_status()
                    return response.json()
                
                result = self.circuit_breaker.call(_request)
                return result
                
            except requests.exceptions.Timeout as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise RetryableError(f"Request timeout after {self.max_retries} attempts: {e}")
            
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:  # Rate limit
                    retry_after = int(e.response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limit exceeded, waiting {retry_after}s...")
                    time.sleep(retry_after)
                    continue
                elif e.response.status_code >= 500:  # Server error
                    last_exception = e
                    if attempt < self.max_retries - 1:
                        delay = self.retry_delay * (self.backoff_factor ** attempt)
                        logger.warning(f"Server error {e.response.status_code} (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        raise RetryableError(f"Server error after {self.max_retries} attempts: {e}")
                else:  # Client error (4xx)
                    raise APIError(f"HTTP {e.response.status_code}: {e}")
            
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (self.backoff_factor ** attempt)
                    logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise RetryableError(f"Connection error after {self.max_retries} attempts: {e}")
            
            except Exception as e:
                raise APIError(f"Unexpected error: {e}")
        
        raise last_exception
    
    def _get_api_url(self, endpoint: str, address: Optional[str] = None) -> str:
        """
        Get the correct API URL based on network (testnet/mainnet).
        """
        # Detect testnet by address format if provided
        if address:
            is_testnet_address = (
                address.startswith('tb1') or  # Testnet bech32
                address.startswith('2') or    # Testnet P2SH
                address.startswith('m') or    # Testnet P2PKH
                address.startswith('n')       # Testnet P2PKH
            )
        else:
            is_testnet_address = False
        
        # Use effective testnet status
        use_testnet = self.network.effective_is_testnet or is_testnet_address
        
        # Blockstream Esplora API
        if 'blockstream' in self.base_url.lower() or 'esplora' in self.base_url.lower():
            if use_testnet:
                if '/testnet/api' not in self.base_url:
                    testnet_url = self.base_url.replace('/api', '/testnet/api')
                    if '/testnet/api' not in testnet_url:
                        testnet_url = f"{self.base_url.rstrip('/')}/testnet/api"
                else:
                    testnet_url = self.base_url
                base = testnet_url
            else:
                # Ensure mainnet URL
                base = self.base_url.replace('/testnet/api', '/api')
        else:
            base = self.base_url
        
        return f"{base}/{endpoint}"
    
    def health_check(self) -> Tuple[bool, str]:
        """
        Check if the blockchain API is healthy.
        Returns (is_healthy, message)
        """
        try:
            url = self._get_api_url("blocks/tip/height")
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            height = int(response.text)
            return True, f"API healthy, current block height: {height}"
        except Exception as e:
            return False, f"API unhealthy: {e}"
    
    def get_current_block_height(self) -> Optional[int]:
        """Get current block height with error handling"""
        try:
            url = self._get_api_url("blocks/tip/height")
            result = self._make_request(url)
            if isinstance(result, str):
                return int(result)
            return result
        except Exception as e:
            logger.error(f"Error getting block height: {e}")
            return None
    
    def get_address_transactions(self, address: str) -> List[Dict]:
        """Get all transactions for an address with error handling"""
        try:
            url = self._get_api_url(f"address/{address}/txs", address)
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Error getting transactions for {address}: {e}")
            return []
    
    def get_transaction(self, txid: str) -> Optional[Dict]:
        """Get transaction details by hash with error handling"""
        try:
            url = self._get_api_url(f"tx/{txid}")
            return self._make_request(url)
        except Exception as e:
            logger.error(f"Error getting transaction {txid}: {e}")
            return None
    
    def inspect_transaction_for_address(self, txid: str, address: str) -> Tuple[int, bool, Optional[int]]:
        """
        Inspect a transaction and return total sats received by address,
        confirmation status, and block height.
        """
        tx = self.get_transaction(txid)
        if not tx:
            return 0, False, None
        
        # Calculate total received by this address
        total_received = 0
        
        if 'blockstream' in self.base_url.lower():
            # Blockstream Esplora format
            for vout in tx.get('vout', []):
                scriptpubkey_address = vout.get('scriptpubkey_address')
                if scriptpubkey_address == address:
                    total_received += vout.get('value', 0)
            
            status = tx.get('status', {})
            confirmed = status.get('confirmed', False)
            block_height = status.get('block_height')
        else:
            # Generic format
            for output in tx.get('outputs', []):
                if output.get('address') == address:
                    total_received += output.get('value', 0)
            
            confirmed = tx.get('confirmed', False)
            block_height = tx.get('block_height')
        
        return total_received, confirmed, block_height
    
    def compute_confirmations(self, tx_block_height: Optional[int]) -> int:
        """Compute number of confirmations for a transaction"""
        if tx_block_height is None:
            return 0
        
        current_height = self.get_current_block_height()
        if current_height is None:
            return 0
        
        return max(0, current_height - tx_block_height + 1)

