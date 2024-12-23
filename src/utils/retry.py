import time
from functools import wraps
from typing import Callable
import random

def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            x = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if x == retries:
                        raise
                    wait = (backoff_in_seconds * 2 ** x + 
                           random.uniform(0, 1))
                    print(f"Retry {x+1}/{retries} after {wait:0.1f}s")
                    time.sleep(wait)
                    x += 1
        return wrapper
    return decorator 