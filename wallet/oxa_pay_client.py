"""
OXA Pay API Client - Handles communication with OXA Pay payment gateway
"""
import os
import requests
import logging
import hmac
import hashlib
import json
from typing import Optional, Dict, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class OxaPayClient:
    """
    Client for interacting with OXA Pay API.
    Handles authentication, request signing, and API calls.
    """
    
    BASE_URL = "https://api.oxapay.com/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OXA Pay client.
        
        Args:
            api_key: Merchant API key. If None, reads from OXAPAY_API_KEY setting or environment.
        """
        self.api_key = api_key or getattr(settings, 'OXAPAY_API_KEY', None) or os.getenv('OXAPAY_API_KEY')
        if not self.api_key:
            raise ValueError("OXAPAY_API_KEY must be set in environment or Django settings")
        
        self.session = requests.Session()
        # OXA Pay requires merchant_api_key as a header
        # Note: Some APIs are sensitive to header formatting, ensure no extra spaces
        self.session.headers.update({
            'Content-Type': 'application/json',
            'merchant_api_key': self.api_key.strip()  # Remove any whitespace
        })
        
        # Debug: Log header format (without exposing full key)
        logger.debug(f"OXA Pay client initialized with API key length: {len(self.api_key)}")
    
    def generate_white_label_payment(
        self,
        amount: float,
        pay_currency: str = 'btc',
        currency: str = 'usd',
        network: Optional[str] = None,
        lifetime: int = 60,
        callback_url: Optional[str] = None,
        order_id: Optional[str] = None,
        email: Optional[str] = None,
        description: Optional[str] = None,
        auto_withdrawal: bool = True,
        under_paid_coverage: Optional[float] = None,
        fee_paid_by_payer: Optional[int] = None,
        to_currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a white-label payment (returns payment details, not a URL).
        
        Args:
            amount: Payment amount
            pay_currency: Currency to receive payment in (e.g., 'btc', 'eth')
            currency: Currency for amount calculation (e.g., 'usd')
            network: Blockchain network (e.g., 'Bitcoin Network')
            lifetime: Expiration time in minutes (15-2880, default: 60)
            callback_url: URL to receive payment notifications
            order_id: Unique order ID for reference
            email: Payer email address
            description: Order details
            auto_withdrawal: If True, auto-withdraw to address in settings
            under_paid_coverage: Acceptable underpayment percentage (0-60)
            fee_paid_by_payer: 1 = payer pays fee, 0 = merchant pays
            to_currency: Currency to convert to (only USDT supported)
        
        Returns:
            Dict with payment details (track_id, address, amount, etc.)
        """
        url = f"{self.BASE_URL}/payment/white-label"
        
        payload = {
            'amount': amount,
            'pay_currency': pay_currency,
            'currency': currency,
        }
        
        if network:
            payload['network'] = network
        if lifetime:
            payload['lifetime'] = lifetime
        if callback_url:
            payload['callback_url'] = callback_url
        if order_id:
            payload['order_id'] = order_id
        if email:
            payload['email'] = email
        if description:
            payload['description'] = description
        if auto_withdrawal is not None:
            # OXA Pay expects integer 0 or 1, not boolean
            payload['auto_withdrawal'] = int(1 if auto_withdrawal else 0)
        if under_paid_coverage is not None:
            # OXA Pay expects percentage as number (0-60)
            payload['under_paid_coverage'] = float(under_paid_coverage)
        if fee_paid_by_payer is not None:
            payload['fee_paid_by_payer'] = fee_paid_by_payer
        if to_currency:
            payload['to_currency'] = to_currency
        
        try:
            # OXA Pay expects JSON as string in data parameter, not json parameter
            # Match their example format: data=json.dumps(data)
            response = self.session.post(
                url, 
                data=json.dumps(payload), 
                timeout=30
            )
            
            # Log full response for debugging
            logger.debug(f"OXA Pay response status: {response.status_code}")
            logger.debug(f"OXA Pay response headers: {dict(response.headers)}")
            logger.debug(f"OXA Pay request payload: {json.dumps(payload, indent=2)}")
            
            # Try to parse response even if status is not 200
            try:
                data = response.json()
                logger.debug(f"OXA Pay response data: {json.dumps(data, indent=2)}")
            except:
                logger.error(f"OXA Pay response body (not JSON): {response.text[:500]}")
                data = {}
            
            # Check status code first
            if response.status_code == 401:
                error_msg = data.get('error', {}).get('message', 'Unauthorized')
                error_key = data.get('error', {}).get('key', '')
                raise ValueError(f"OXA Pay authentication failed (401): {error_msg} (key: {error_key}). Please verify your API key is correct.")
            
            if response.status_code == 400:
                error = data.get('error', {})
                error_msg = error.get('message', 'Bad Request')
                error_key = error.get('key', '')
                error_type = error.get('type', '')
                logger.error(f"OXA Pay 400 error details: {json.dumps(error, indent=2)}")
                raise ValueError(f"OXA Pay validation error (400): {error_msg} (key: {error_key}, type: {error_type}). Please check your request parameters.")
            
            response.raise_for_status()
            
            if data.get('status') != 200:
                error = data.get('error', {})
                error_msg = error.get('message', 'Unknown error')
                error_key = error.get('key', '')
                raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key})")
            
            return data.get('data', {})
            
        except ValueError:
            # Re-raise ValueError as-is (our custom errors)
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OXA Pay API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error = error_data.get('error', {})
                    error_msg = error.get('message', str(e))
                    error_key = error.get('key', '')
                    error_type = error.get('type', '')
                    logger.error(f"OXA Pay error response: {json.dumps(error_data, indent=2)}")
                    raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key}, type: {error_type})")
                except:
                    logger.error(f"OXA Pay raw response: {e.response.text[:500]}")
            raise ValueError(f"Failed to generate OXA Pay payment: {e}")
    
    def generate_static_address(
        self,
        network: str,
        callback_url: Optional[str] = None,
        order_id: Optional[str] = None,
        email: Optional[str] = None,
        description: Optional[str] = None,
        auto_withdrawal: bool = True,
        to_currency: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a static address for receiving payments.
        
        Args:
            network: Blockchain network (e.g., 'Bitcoin Network')
            callback_url: URL to receive payment notifications
            order_id: Unique order ID for reference
            email: Payer email address
            description: Order details
            auto_withdrawal: If True, auto-withdraw to address in settings
            to_currency: Currency to convert to (only USDT supported)
        
        Returns:
            Dict with static address details (track_id, address, qr_code, etc.)
        """
        url = f"{self.BASE_URL}/payment/static-address"
        
        payload = {
            'network': network,
        }
        
        if callback_url:
            payload['callback_url'] = callback_url
        if order_id:
            payload['order_id'] = order_id
        if email:
            payload['email'] = email
        if description:
            payload['description'] = description
        if auto_withdrawal is not None:
            # OXA Pay expects integer 0 or 1, not boolean
            payload['auto_withdrawal'] = int(1 if auto_withdrawal else 0)
        if to_currency:
            payload['to_currency'] = to_currency
        
        try:
            # OXA Pay expects JSON as string in data parameter, not json parameter
            # Match their example format: data=json.dumps(data)
            response = self.session.post(
                url, 
                data=json.dumps(payload), 
                timeout=30
            )
            
            # Log full response for debugging
            logger.debug(f"OXA Pay response status: {response.status_code}")
            logger.debug(f"OXA Pay response headers: {dict(response.headers)}")
            
            # Try to parse response even if status is not 200
            try:
                data = response.json()
                logger.debug(f"OXA Pay response data: {data}")
            except:
                logger.error(f"OXA Pay response body (not JSON): {response.text[:500]}")
                data = {}
            
            # Check status code first
            if response.status_code == 401:
                error_msg = data.get('error', {}).get('message', 'Unauthorized')
                error_key = data.get('error', {}).get('key', '')
                raise ValueError(f"OXA Pay authentication failed (401): {error_msg} (key: {error_key}). Please verify your API key is correct.")
            
            response.raise_for_status()
            
            if data.get('status') != 200:
                error = data.get('error', {})
                error_msg = error.get('message', 'Unknown error')
                error_key = error.get('key', '')
                raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key})")
            
            return data.get('data', {})
            
        except ValueError:
            # Re-raise ValueError as-is (our custom errors)
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OXA Pay API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                    raise ValueError(f"OXA Pay API error: {error_msg}")
                except:
                    pass
            raise ValueError(f"Failed to generate OXA Pay static address: {e}")
    
    def get_static_address_list(
        self,
        track_id: Optional[str] = None,
        network: Optional[str] = None,
        currency: Optional[str] = None,
        address: Optional[str] = None,
        have_tx: Optional[bool] = None,
        order_id: Optional[str] = None,
        email: Optional[str] = None,
        page: int = 1,
        size: int = 10
    ) -> Dict[str, Any]:
        """
        Get list of static addresses.
        
        Returns:
            Dict with list of addresses and pagination metadata
        """
        url = f"{self.BASE_URL}/payment/static-address"
        
        params = {
            'page': page,
            'size': size
        }
        
        if track_id:
            params['track_id'] = track_id
        if network:
            params['network'] = network
        if currency:
            params['currency'] = currency
        if address:
            params['address'] = address
        if have_tx is not None:
            params['have_tx'] = have_tx
        if order_id:
            params['order_id'] = order_id
        if email:
            params['email'] = email
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 200:
                error = data.get('error', {})
                raise ValueError(f"OXA Pay API error: {error.get('message', 'Unknown error')}")
            
            return data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"OXA Pay API request failed: {e}")
            raise ValueError(f"Failed to get static address list: {e}")
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook callback signature.
        
        Note: This method is deprecated. OXA Pay uses HMAC-SHA512 with "HMAC" header.
        The webhook handler in webhooks.py now handles signature verification directly.
        
        Args:
            payload: Raw request body (string)
            signature: Signature from HMAC header
        
        Returns:
            True if signature is valid
        """
        # OXA Pay uses HMAC-SHA512 (not SHA256) with API key as secret
        expected_signature = hmac.new(
            self.api_key.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha512  # Changed from sha256 to sha512
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)
    
    def get_payment_status(self, track_id: str) -> Dict[str, Any]:
        """
        Get payment status by track_id.
        Note: This endpoint may not be in the provided docs, but is typically available.
        
        Args:
            track_id: Payment track ID
        
        Returns:
            Dict with payment status details
        """
        # This endpoint may need to be confirmed with OXA Pay documentation
        # For now, we'll use the static address list to check status
        addresses = self.get_static_address_list(track_id=track_id)
        if addresses.get('list'):
            return addresses['list'][0]
        return {}
    
    def generate_invoice(
        self,
        amount: float,
        currency: str = 'usd',
        lifetime: int = 60,
        callback_url: Optional[str] = None,
        return_url: Optional[str] = None,
        order_id: Optional[str] = None,
        email: Optional[str] = None,
        description: Optional[str] = None,
        thanks_message: Optional[str] = None,
        fee_paid_by_payer: Optional[int] = None,
        under_paid_coverage: Optional[float] = None,
        to_currency: Optional[str] = None,
        auto_withdrawal: Optional[bool] = None,
        mixed_payment: Optional[bool] = None,
        sandbox: bool = False
    ) -> Dict[str, Any]:
        """
        Generate an invoice and obtain a payment URL.
        
        Args:
            amount: Payment amount
            currency: Currency for amount calculation (e.g., 'usd')
            lifetime: Expiration time in minutes (15-2880, default: 60)
            callback_url: URL to receive payment notifications
            return_url: URL to redirect payer after successful payment
            order_id: Unique order ID for reference
            email: Payer email address
            description: Order details
            thanks_message: Message displayed after successful payment
            fee_paid_by_payer: 1 = payer pays fee, 0 = merchant pays
            under_paid_coverage: Acceptable underpayment percentage (0-60)
            to_currency: Currency to convert to (only USDT supported)
            auto_withdrawal: If True, auto-withdraw to address in settings
            mixed_payment: If True, allow paying remainder with different currency
            sandbox: If True, use sandbox/test environment
        
        Returns:
            Dict with invoice details (track_id, payment_url, expired_at, etc.)
        """
        url = f"{self.BASE_URL}/payment/invoice"
        
        payload = {
            'amount': amount,
            'currency': currency,
            'lifetime': lifetime,
            'sandbox': sandbox,
        }
        
        if callback_url:
            payload['callback_url'] = callback_url
        if return_url:
            payload['return_url'] = return_url
        if order_id:
            payload['order_id'] = order_id
        if email:
            payload['email'] = email
        if description:
            payload['description'] = description
        if thanks_message:
            payload['thanks_message'] = thanks_message
        if fee_paid_by_payer is not None:
            payload['fee_paid_by_payer'] = int(fee_paid_by_payer)
        if under_paid_coverage is not None:
            payload['under_paid_coverage'] = float(under_paid_coverage)
        if to_currency:
            payload['to_currency'] = to_currency
        if auto_withdrawal is not None:
            payload['auto_withdrawal'] = int(1 if auto_withdrawal else 0)
        if mixed_payment is not None:
            payload['mixed_payment'] = int(1 if mixed_payment else 0)
        
        try:
            # OXA Pay expects JSON as string in data parameter
            response = self.session.post(
                url, 
                data=json.dumps(payload), 
                timeout=30
            )
            
            # Log full response for debugging
            logger.debug(f"OXA Pay response status: {response.status_code}")
            logger.debug(f"OXA Pay request payload: {json.dumps(payload, indent=2)}")
            
            # Try to parse response even if status is not 200
            try:
                data = response.json()
                logger.debug(f"OXA Pay response data: {json.dumps(data, indent=2)}")
            except:
                logger.error(f"OXA Pay response body (not JSON): {response.text[:500]}")
                data = {}
            
            # Check status code first
            if response.status_code == 401:
                error_msg = data.get('error', {}).get('message', 'Unauthorized')
                error_key = data.get('error', {}).get('key', '')
                raise ValueError(f"OXA Pay authentication failed (401): {error_msg} (key: {error_key}). Please verify your API key is correct.")
            
            if response.status_code == 400:
                error = data.get('error', {})
                error_msg = error.get('message', 'Bad Request')
                error_key = error.get('key', '')
                error_type = error.get('type', '')
                logger.error(f"OXA Pay 400 error details: {json.dumps(error, indent=2)}")
                raise ValueError(f"OXA Pay validation error (400): {error_msg} (key: {error_key}, type: {error_type}). Please check your request parameters.")
            
            response.raise_for_status()
            
            if data.get('status') != 200:
                error = data.get('error', {})
                error_msg = error.get('message', 'Unknown error')
                error_key = error.get('key', '')
                raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key})")
            
            return data.get('data', {})
            
        except ValueError:
            # Re-raise ValueError as-is (our custom errors)
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OXA Pay API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error = error_data.get('error', {})
                    error_msg = error.get('message', str(e))
                    error_key = error.get('key', '')
                    error_type = error.get('type', '')
                    logger.error(f"OXA Pay error response: {json.dumps(error_data, indent=2)}")
                    raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key}, type: {error_type})")
                except:
                    logger.error(f"OXA Pay raw response: {e.response.text[:500]}")
            raise ValueError(f"Failed to generate OXA Pay invoice: {e}")
    
    def get_accepted_currencies(self) -> Dict[str, Any]:
        """
        Get list of accepted cryptocurrencies configured in OXA Pay account.
        
        Returns:
            Dict with list of accepted currencies
        """
        url = f"{self.BASE_URL}/payment/accepted-currencies"
        
        try:
            response = self.session.get(url, timeout=30)
            
            # Log full response for debugging
            logger.debug(f"OXA Pay response status: {response.status_code}")
            
            # Try to parse response even if status is not 200
            try:
                data = response.json()
                logger.debug(f"OXA Pay response data: {json.dumps(data, indent=2)}")
            except:
                logger.error(f"OXA Pay response body (not JSON): {response.text[:500]}")
                data = {}
            
            # Check status code first
            if response.status_code == 401:
                error_msg = data.get('error', {}).get('message', 'Unauthorized')
                error_key = data.get('error', {}).get('key', '')
                raise ValueError(f"OXA Pay authentication failed (401): {error_msg} (key: {error_key}). Please verify your API key is correct.")
            
            response.raise_for_status()
            
            if data.get('status') != 200:
                error = data.get('error', {})
                error_msg = error.get('message', 'Unknown error')
                error_key = error.get('key', '')
                raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key})")
            
            return data.get('data', {})
            
        except ValueError:
            # Re-raise ValueError as-is (our custom errors)
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"OXA Pay API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error = error_data.get('error', {})
                    error_msg = error.get('message', str(e))
                    error_key = error.get('key', '')
                    error_type = error.get('type', '')
                    logger.error(f"OXA Pay error response: {json.dumps(error_data, indent=2)}")
                    raise ValueError(f"OXA Pay API error: {error_msg} (key: {error_key}, type: {error_type})")
                except:
                    logger.error(f"OXA Pay raw response: {e.response.text[:500]}")
            raise ValueError(f"Failed to get accepted currencies: {e}")


# Import os for environment variable access
import os

