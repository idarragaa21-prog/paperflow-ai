from __future__ import annotations

from app.services.cache import CacheManager


def test_cache_key_stable():
    c = CacheManager()
    k1 = c.generate_search_key("hip fracture", {"year_from": 2020, "year_to": 2024}, max_results=20, source="federated")
    k2 = c.generate_search_key("hip fracture", {"year_to": 2024, "year_from": 2020}, max_results=20, source="federated")
    assert k1 == k2


def test_cache_key_changes_when_query_shape_changes():
    c = CacheManager()
    base = c.generate_search_key("hip fracture", {"year_from": 2020}, max_results=20, source="federated")
    different_limit = c.generate_search_key("hip fracture", {"year_from": 2020}, max_results=10, source="federated")
    different_source = c.generate_search_key("hip fracture", {"year_from": 2020}, max_results=20, source="pubmed")
    assert base != different_limit
    assert base != different_source
