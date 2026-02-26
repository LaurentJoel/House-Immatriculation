"""
Integration tests for Cache Integration with API (Step 4.5).
"""
import pytest
import fakeredis

from app.services import cache as cache_mod


@pytest.fixture(autouse=True)
def fake_redis():
    """Inject a fakeredis client for every test in this module."""
    fr = fakeredis.FakeRedis(decode_responses=True)
    cache_mod.set_client(fr)
    yield fr
    fr.flushall()


class TestAPICache:
    """Step 4.5: Cache decorator wired into API."""

    def test_cached_dashboard_stats(self, client, auth_headers, db_session, fake_redis):
        response1 = client.get('/api/v1/reports/dashboard', headers=auth_headers)
        response2 = client.get('/api/v1/reports/dashboard', headers=auth_headers)
        assert response1.status_code == 200
        assert response1.json == response2.json
        # Verify cache was hit on second call
        keys = list(fake_redis.scan_iter(match='dashboard:*'))
        assert len(keys) > 0

    def test_cache_invalidated_on_new_house(self, client, auth_headers, db_session, fake_redis):
        from app.models import TaxCategory
        cat = TaxCategory(code='RES', name_fr='Res', name_en='Res', base_rate_per_sqm=500)
        db_session.add(cat)
        db_session.commit()

        # Get stats (populates cache)
        client.get('/api/v1/reports/dashboard', headers=auth_headers)
        keys_before = list(fake_redis.scan_iter(match='dashboard:*'))
        assert len(keys_before) > 0

        # Add house (should invalidate cache)
        client.post('/api/v1/houses', headers=auth_headers, json={
            'commune': 'Yaounde I', 'region': 'Centre',
            'owner_name': 'Cache Test',
            'tax_category_code': 'RES',
            'coordinates': {'latitude': 3.8667, 'longitude': 11.5167},
        })
        keys_after = list(fake_redis.scan_iter(match='dashboard:*'))
        assert len(keys_after) == 0

    def test_reference_data_cached(self, client, auth_headers, db_session, fake_redis):
        response = client.get('/api/v1/admin/communes', headers=auth_headers)
        assert response.status_code == 200
        keys = list(fake_redis.scan_iter(match='ref:*'))
        assert len(keys) > 0
