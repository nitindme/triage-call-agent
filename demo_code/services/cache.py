# services/cache.py
class CacheService:
    def get_or_set(self, key: str, fetch_fn, ttl: int = 300):
        value = redis.get(key)
        if value is None:
            # Use distributed lock to prevent stampede
            with redis.lock(f"lock:{key}", timeout=10):
                value = redis.get(key)  # Double-check after lock
                if value is None:
                    value = fetch_fn()
                    redis.setex(key, ttl, json.dumps(value))
        return json.loads(value) if value else None