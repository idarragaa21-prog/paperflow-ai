from __future__ import annotations

from app.services.cache import CacheManager


def test_cache_key_stable():
    c = CacheManager()
    k1 = c.generate_search_key("hip fracture", {"year_from": 2020, "year_to": 2024})
    k2 = c.generate_search_key("hip fracture", {"year_to": 2024, "year_from": 2020})
    assert k1 == k2
