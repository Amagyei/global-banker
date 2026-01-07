"""
Rate limiting utilities for wallet endpoints.
Uses django-ratelimit for request throttling.
"""
import logging
from functools import wraps
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger(__name__)

# Try to import django-ratelimit
try:
    from django_ratelimit.decorators import ratelimit
    from django_ratelimit.exceptions import Ratelimited
    RATELIMIT_AVAILABLE = True
except ImportError:
    RATELIMIT_AVAILABLE = False
    logger.warning("django-ratelimit not available - rate limiting disabled")


def rate_limit_exceeded(request, exception=None):
    """
    Custom view for rate limit exceeded errors.
    Returns a JSON response with 429 status.
    """
    return JsonResponse(
        {
            'detail': 'Rate limit exceeded. Please try again later.',
            'retry_after': 60,  # Suggest retry after 60 seconds
        },
        status=429
    )


class RateLimitMixin:
    """
    Mixin to add rate limiting to DRF ViewSets.
    Apply different limits based on action.
    """
    
    # Default rate limits (requests per minute)
    rate_limits = {
        'list': '60/m',      # 60 requests per minute for list
        'retrieve': '60/m',  # 60 requests per minute for retrieve
        'create': '10/m',    # 10 requests per minute for create
        'update': '10/m',    # 10 requests per minute for update
        'destroy': '5/m',    # 5 requests per minute for destroy
    }
    
    def get_rate_limit_key(self, request):
        """Get rate limit key based on user"""
        if request.user.is_authenticated:
            return f"user:{request.user.id}"
        return f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"
    
    def check_rate_limit(self, request, action):
        """
        Check if request should be rate limited.
        Returns True if allowed, False if rate limited.
        """
        if not RATELIMIT_AVAILABLE:
            return True
        
        if not getattr(settings, 'RATELIMIT_ENABLE', True):
            return True
        
        # Get rate limit for this action
        rate = self.rate_limits.get(action, '30/m')
        
        # Check rate limit
        from django.core.cache import cache
        key = f"ratelimit:{self.get_rate_limit_key(request)}:{action}"
        
        # Parse rate (e.g., "10/m" -> 10 requests per 60 seconds)
        count, period = rate.split('/')
        count = int(count)
        period_seconds = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(period, 60)
        
        # Get current count
        current = cache.get(key, 0)
        
        if current >= count:
            logger.warning(f"Rate limit exceeded for {key}")
            return False
        
        # Increment count
        cache.set(key, current + 1, period_seconds)
        return True
    
    def dispatch(self, request, *args, **kwargs):
        """Override dispatch to add rate limiting"""
        action = getattr(self, 'action', None)
        
        if action and not self.check_rate_limit(request, action):
            return rate_limit_exceeded(request)
        
        return super().dispatch(request, *args, **kwargs)


def wallet_rate_limit(rate='10/m', key='user', block=True):
    """
    Decorator for rate limiting wallet views.
    
    Args:
        rate: Rate limit string (e.g., '10/m' for 10 per minute)
        key: Key to use for rate limiting ('user' or 'ip')
        block: Whether to block the request if rate limited
    """
    def decorator(view_func):
        if not RATELIMIT_AVAILABLE:
            return view_func
        
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            # Check rate limit
            from django.core.cache import cache
            
            if key == 'user' and request.user.is_authenticated:
                limit_key = f"ratelimit:user:{request.user.id}:{view_func.__name__}"
            else:
                limit_key = f"ratelimit:ip:{request.META.get('REMOTE_ADDR', 'unknown')}:{view_func.__name__}"
            
            # Parse rate
            count, period = rate.split('/')
            count = int(count)
            period_seconds = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}.get(period, 60)
            
            # Get current count
            current = cache.get(limit_key, 0)
            
            if current >= count and block:
                logger.warning(f"Rate limit exceeded for {limit_key}")
                return rate_limit_exceeded(request)
            
            # Increment count
            cache.set(limit_key, current + 1, period_seconds)
            
            return view_func(request, *args, **kwargs)
        
        return wrapped_view
    return decorator


# Specific rate limiters for different wallet operations
def payment_rate_limit(view_func):
    """Rate limit for payment creation (5 per minute)"""
    return wallet_rate_limit(rate='5/m', key='user')(view_func)


def topup_rate_limit(view_func):
    """Rate limit for top-up creation (10 per minute)"""
    return wallet_rate_limit(rate='10/m', key='user')(view_func)


def withdrawal_rate_limit(view_func):
    """Rate limit for withdrawals (3 per minute)"""
    return wallet_rate_limit(rate='3/m', key='user')(view_func)

