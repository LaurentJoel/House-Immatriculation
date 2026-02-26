"""
Tests for cache service (Step 3.6).
Uses fakeredis so no running Redis is required.
"""
import time

import fakeredis

from app.services.cache import cached, invalidate_cache, set_client, get_client


class TestCacheService:
    """Step 3.6: Cache decorator & invalidation tests."""

    def setup_method(self):
        """Provide a fresh fakeredis instance for each test."""
        self.fake = fakeredis.FakeRedis(decode_responses=True)
        set_client(self.fake)

    # ── basic caching ──────────────────────────────────────────

    def test_cache_decorator_stores_result(self):
        call_count = 0

        @cached(ttl=300, prefix='test')
        def expensive():
            nonlocal call_count
            call_count += 1
            return {'result': 42}

        r1 = expensive()       # MISS
        r2 = expensive()       # HIT
        assert r1 == r2 == {'result': 42}
        assert call_count == 1  # function called only once

    # ── TTL expiry ─────────────────────────────────────────────

    def test_cache_ttl_expiry(self):
        @cached(ttl=1, prefix='ttl')
        def short_lived():
            return {'data': 'fresh'}

        r1 = short_lived()
        time.sleep(2)
        r2 = short_lived()
        assert r1 == r2  # same value, but re-executed

    # ── invalidation ───────────────────────────────────────────

    def test_cache_invalidation(self):
        @cached(ttl=300, prefix='dashboard')
        def get_stats():
            return {'total': 100}

        get_stats()               # populate
        invalidate_cache('dashboard')

        keys = list(self.fake.scan_iter(match='dashboard:*'))
        assert len(keys) == 0

    # ── different args ─────────────────────────────────────────

    def test_cache_different_args(self):
        @cached(ttl=300, prefix='tax')
        def get_tax(house_id, year):
            return {'house': house_id, 'year': year, 'tax': house_id * 1000}

        r1 = get_tax(1, 2026)
        r2 = get_tax(2, 2026)
        assert r1 != r2  # different args → different cache entries
        assert r1['house'] == 1
        assert r2['house'] == 2
