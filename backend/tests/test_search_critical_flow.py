"""Tests for the critical search → download flow.

Covers:
  1. Cache key determinism and completeness (max_results, source, case-insensitive)
  2. Federated merge + deduplication
  3. Relevance ranking
  4. Filter application end-to-end
  5. Persistence scoped to individual search (no global dedup)
  6. Download uses caller-provided oa_url as first priority
"""
from __future__ import annotations

import pytest

from app.services.cache import CacheManager
from app.services.federated_search import (
    _normalize_title,
    _passes_filters,
    _record_key,
    _relevance_score,
)
from app.schemas.search import SearchFilters


# ─────────────────────────────────────────────
# 1. CACHE KEY DETERMINISM & COMPLETENESS
# ─────────────────────────────────────────────

class TestCacheKey:
    def setup_method(self):
        self.cm = CacheManager()

    def test_same_query_same_key(self):
        k1 = self.cm.generate_search_key("hip fracture", {"year_from": 2020}, max_results=20, source="pubmed")
        k2 = self.cm.generate_search_key("hip fracture", {"year_from": 2020}, max_results=20, source="pubmed")
        assert k1 == k2

    def test_different_max_results_different_key(self):
        k1 = self.cm.generate_search_key("hip fracture", None, max_results=10, source="pubmed")
        k2 = self.cm.generate_search_key("hip fracture", None, max_results=20, source="pubmed")
        assert k1 != k2, "Different max_results must produce different cache keys"

    def test_different_source_different_key(self):
        k1 = self.cm.generate_search_key("hip fracture", None, max_results=20, source="pubmed")
        k2 = self.cm.generate_search_key("hip fracture", None, max_results=20, source="federated")
        assert k1 != k2, "Different source must produce different cache keys"

    def test_filter_order_irrelevant(self):
        k1 = self.cm.generate_search_key("test", {"year_from": 2020, "year_to": 2024}, max_results=20, source="federated")
        k2 = self.cm.generate_search_key("test", {"year_to": 2024, "year_from": 2020}, max_results=20, source="federated")
        assert k1 == k2

    def test_case_insensitive_query(self):
        k1 = self.cm.generate_search_key("Hip Fracture", None, max_results=20, source="pubmed")
        k2 = self.cm.generate_search_key("hip fracture", None, max_results=20, source="pubmed")
        assert k1 == k2, "Cache key should be case-insensitive"

    def test_key_prefix_matches_source(self):
        k = self.cm.generate_search_key("test", None, max_results=10, source="federated")
        assert k.startswith("search:federated:"), f"Key prefix should match source, got: {k}"

    def test_whitespace_normalization(self):
        k1 = self.cm.generate_search_key("  hip  fracture ", None, max_results=20, source="pubmed")
        k2 = self.cm.generate_search_key("hip  fracture", None, max_results=20, source="pubmed")
        assert k1 == k2


# ─────────────────────────────────────────────
# 2. DEDUPLICATION (within a single search)
# ─────────────────────────────────────────────

class TestDeduplication:
    def test_record_key_by_doi(self):
        a = {"doi": "10.1000/test", "pmid": None, "title": "A"}
        b = {"doi": "10.1000/test", "pmid": "123", "title": "B"}
        assert _record_key(a) == _record_key(b), "Same DOI should produce same dedup key"

    def test_record_key_by_pmid(self):
        a = {"doi": None, "pmid": "12345", "title": "A"}
        b = {"doi": None, "pmid": "12345", "title": "Different"}
        assert _record_key(a) == _record_key(b)

    def test_record_key_title_fallback(self):
        a = {"doi": None, "pmid": None, "title": "Fracture Healing", "pub_year": 2023}
        b = {"doi": None, "pmid": None, "title": "fracture healing", "pub_year": 2023}
        assert _record_key(a) == _record_key(b), "Title-based key should be case-insensitive"

    def test_record_key_different_titles_different_keys(self):
        a = {"doi": None, "pmid": None, "title": "Alpha Study", "pub_year": 2023}
        b = {"doi": None, "pmid": None, "title": "Beta Study", "pub_year": 2023}
        assert _record_key(a) != _record_key(b)


# ─────────────────────────────────────────────
# 3. FILTER APPLICATION
# ─────────────────────────────────────────────

class TestFilters:
    def test_no_filters_passes(self):
        assert _passes_filters({"pub_year": 2020}, None) is True

    def test_year_from(self):
        f = SearchFilters(year_from=2020)
        assert _passes_filters({"pub_year": 2019}, f) is False
        assert _passes_filters({"pub_year": 2020}, f) is True
        assert _passes_filters({"pub_year": 2021}, f) is True

    def test_year_to(self):
        f = SearchFilters(year_to=2022)
        assert _passes_filters({"pub_year": 2023}, f) is False
        assert _passes_filters({"pub_year": 2022}, f) is True

    def test_open_access_only(self):
        f = SearchFilters(open_access_only=True)
        assert _passes_filters({"is_open_access": False}, f) is False
        assert _passes_filters({"is_open_access": True}, f) is True

    def test_journal_substring_match(self):
        f = SearchFilters(journal="lancet")
        assert _passes_filters({"journal": "The Lancet"}, f) is True
        assert _passes_filters({"journal": "BMJ"}, f) is False

    def test_source_filter(self):
        f = SearchFilters(source="pubmed")
        assert _passes_filters({"source": "pubmed"}, f) is True
        assert _passes_filters({"source": "doaj"}, f) is False

    def test_combined_filters(self):
        f = SearchFilters(year_from=2020, open_access_only=True)
        assert _passes_filters({"pub_year": 2021, "is_open_access": True}, f) is True
        assert _passes_filters({"pub_year": 2021, "is_open_access": False}, f) is False
        assert _passes_filters({"pub_year": 2019, "is_open_access": True}, f) is False

    def test_missing_year_passes_year_filter(self):
        """Items without pub_year should not be filtered by year filters."""
        f = SearchFilters(year_from=2020)
        # pub_year is None — filter checks isinstance(pub_year, int), so should pass
        assert _passes_filters({"pub_year": None}, f) is True


# ─────────────────────────────────────────────
# 4. RELEVANCE RANKING
# ─────────────────────────────────────────────

class TestRelevanceRanking:
    def test_higher_title_overlap_scores_higher(self):
        query = "ACL reconstruction"
        a = {"title": "ACL reconstruction outcomes", "pub_year": 2023, "doi": "10.1/a", "abstract": "text", "journal": "J", "authors": ["X"], "is_open_access": True, "oa_url": "http://x.pdf", "pmid": "1"}
        b = {"title": "Knee biomechanics study", "pub_year": 2023, "doi": "10.1/b", "abstract": "text", "journal": "J", "authors": ["X"], "is_open_access": True, "oa_url": "http://y.pdf", "pmid": "2"}
        assert _relevance_score(a, query) > _relevance_score(b, query)

    def test_newer_paper_scores_higher(self):
        query = "hip"
        base = {"title": "Hip replacement", "doi": "10.1/a", "abstract": "text", "journal": "J", "authors": ["X"], "is_open_access": True, "oa_url": "http://x.pdf", "pmid": "1"}
        a = {**base, "pub_year": 2024}
        b = {**base, "pub_year": 2005, "doi": "10.1/b", "pmid": "2"}
        assert _relevance_score(a, query) > _relevance_score(b, query)

    def test_oa_with_url_scores_higher(self):
        query = "test"
        base = {"title": "Test study", "pub_year": 2023, "doi": "10.1/a", "abstract": "text", "journal": "J", "authors": ["X"], "pmid": "1"}
        a = {**base, "is_open_access": True, "oa_url": "http://x.pdf"}
        b = {**base, "is_open_access": False, "oa_url": None, "doi": "10.1/b", "pmid": "2"}
        assert _relevance_score(a, query) > _relevance_score(b, query)

    def test_complete_metadata_scores_higher(self):
        query = "test"
        a = {"title": "Test", "pub_year": 2023, "doi": "10.1/a", "pmid": "1", "abstract": "Full abstract here", "journal": "Nature", "authors": ["Author A"], "is_open_access": False, "oa_url": None}
        b = {"title": "Test", "pub_year": 2023, "doi": None, "pmid": None, "abstract": None, "journal": None, "authors": [], "is_open_access": False, "oa_url": None}
        assert _relevance_score(a, query) > _relevance_score(b, query)

    def test_score_range_0_to_1(self):
        query = "test"
        item = {"title": "Test Study 2024", "pub_year": 2024, "doi": "10.1/a", "pmid": "1", "abstract": "text", "journal": "J", "authors": ["A"], "is_open_access": True, "oa_url": "http://x.pdf"}
        score = _relevance_score(item, query)
        assert 0.0 <= score <= 1.0


# ─────────────────────────────────────────────
# 5. OA URL PRIORITY IN DOWNLOAD
# ─────────────────────────────────────────────

class TestDownloadOAUrlPriority:
    """Verify that PaperDownloadService uses caller-provided oa_url first."""

    @pytest.mark.asyncio
    async def test_oa_url_used_first(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.paper_service import PaperDownloadService, DownloadResult

        service = PaperDownloadService()

        fake_client = AsyncMock()
        # Simulate a valid PDF response (starts with %PDF, ends with %%EOF)
        fake_pdf = b"%PDF-1.4 fake content %%EOF"
        fake_response = MagicMock()
        fake_response.content = fake_pdf
        fake_response.status_code = 200
        fake_response.headers = {"content-type": "application/pdf"}
        fake_response.raise_for_status = MagicMock()
        fake_client.get = AsyncMock(return_value=fake_response)

        with patch("app.services.paper_service.storage_manager") as mock_storage:
            mock_storage.validate_pdf.return_value = True

            result = await service.download_open_access_pdf(
                doi="10.1000/test",
                pmid="12345",
                oa_url="https://specific-oa-link.org/paper.pdf",
                client=fake_client,
            )

        assert result.source == "user_provided_oa"
        assert result.resolved_url == "https://specific-oa-link.org/paper.pdf"
        # The client should have been called with the user-provided URL
        fake_client.get.assert_called_once()
        call_url = fake_client.get.call_args[0][0]
        assert call_url == "https://specific-oa-link.org/paper.pdf"

    @pytest.mark.asyncio
    async def test_fallback_when_oa_url_not_provided(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.paper_service import PaperDownloadService
        from app.services.oa_resolvers import OAResolved

        service = PaperDownloadService()

        fake_client = AsyncMock()
        fake_pdf = b"%PDF-1.4 fake content %%EOF"
        fake_response = MagicMock()
        fake_response.content = fake_pdf
        fake_response.headers = {"content-type": "application/pdf"}
        fake_response.raise_for_status = MagicMock()
        fake_client.get = AsyncMock(return_value=fake_response)

        with patch.object(service.unpaywall, "resolve", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = OAResolved(url_for_pdf="https://unpaywall.org/resolved.pdf", source="unpaywall")
            with patch("app.services.paper_service.storage_manager") as mock_storage:
                mock_storage.validate_pdf.return_value = True

                result = await service.download_open_access_pdf(
                    doi="10.1000/test",
                    pmid=None,
                    oa_url=None,
                    client=fake_client,
                )

        assert result.source == "unpaywall"
        assert result.resolved_url == "https://unpaywall.org/resolved.pdf"


# ─────────────────────────────────────────────
# 6. SCHEMA VALIDATION
# ─────────────────────────────────────────────

class TestSchemaValidation:
    def test_paper_download_request_accepts_oa_url(self):
        from app.schemas.papers import PaperDownloadRequest
        import uuid

        req = PaperDownloadRequest(
            project_id=uuid.uuid4(),
            doi="10.1000/test",
            title="Test",
            oa_url="https://example.com/paper.pdf",
        )
        assert req.oa_url == "https://example.com/paper.pdf"

    def test_batch_download_ref_accepts_oa_url(self):
        from app.schemas.papers import BatchDownloadPaperRef

        ref = BatchDownloadPaperRef(
            doi="10.1000/test",
            title="Test",
            oa_url="https://example.com/paper.pdf",
        )
        assert ref.oa_url == "https://example.com/paper.pdf"

    def test_paper_metadata_has_relevance_score(self):
        from app.schemas.search import PaperMetadata

        pm = PaperMetadata(title="Test", relevance_score=0.85, source="pubmed")
        assert pm.relevance_score == 0.85
        assert pm.source == "pubmed"


# ─────────────────────────────────────────────
# 7. TITLE NORMALIZATION
# ─────────────────────────────────────────────

class TestTitleNormalization:
    def test_basic(self):
        assert _normalize_title("  Hello World ") == "hello world"

    def test_strips_punctuation(self):
        assert _normalize_title("ACL: A Meta-Analysis!") == "acl a metaanalysis"

    def test_none_input(self):
        assert _normalize_title(None) == ""


# ─────────────────────────────────────────────
# 8. CACHE KEY — internal whitespace normalization
# ─────────────────────────────────────────────

class TestCacheKeyWhitespace:
    def setup_method(self):
        from app.services.cache import CacheManager
        self.cm = CacheManager()

    def test_internal_double_space_normalized(self):
        """'hip  fracture' and 'hip fracture' must produce the same key."""
        k1 = self.cm.generate_search_key("hip  fracture", None, max_results=20, source="pubmed")
        k2 = self.cm.generate_search_key("hip fracture", None, max_results=20, source="pubmed")
        assert k1 == k2, "Internal multiple spaces should be normalized to single space"

    def test_leading_trailing_and_internal_spaces(self):
        k1 = self.cm.generate_search_key("  ACL   reconstruction  ", None, max_results=20, source="federated")
        k2 = self.cm.generate_search_key("ACL reconstruction", None, max_results=20, source="federated")
        assert k1 == k2


# ─────────────────────────────────────────────
# 9. PUBMED POST-PROCESSING (Bug #6 fix)
# ─────────────────────────────────────────────

class TestPubmedPostProcessing:
    """Verify /search/pubmed applies same filters and ranking as /search/federated."""

    def _make_item(self, **kwargs):
        base = {
            "pmid": "99999", "pmcid": None, "doi": "10.1/x",
            "title": "Test Study", "authors": ["A"],
            "journal": "Test J", "pub_year": 2023,
            "abstract": "Abstract text", "source": "pubmed",
            "language": "eng", "is_open_access": True, "oa_url": None,
        }
        return {**base, **kwargs}

    def test_year_filter_applied(self):
        from app.services.federated_search import _passes_filters
        from app.schemas.search import SearchFilters
        item = self._make_item(pub_year=2018)
        f = SearchFilters(year_from=2020)
        assert _passes_filters(item, f) is False

    def test_pmcid_promotes_oa_url(self):
        """When pmcid present and oa_url is None, should generate PMC URL."""
        from app.api.search import _postprocess_pubmed
        item = self._make_item(pmcid="PMC1234567", oa_url=None, is_open_access=False)
        results = _postprocess_pubmed([item], "Test", None)
        assert results[0]["oa_url"] is not None
        assert "PMC1234567" in results[0]["oa_url"]
        assert results[0]["is_open_access"] is True

    def test_ranking_attached(self):
        from app.api.search import _postprocess_pubmed
        item = self._make_item()
        results = _postprocess_pubmed([item], "Test Study", None)
        assert "relevance_score" in results[0]
        assert results[0]["relevance_score"] is not None

    def test_dedup_within_search(self):
        """Same doi appearing twice should only appear once (record_key uses doi first)."""
        from app.api.search import _postprocess_pubmed
        item_a = self._make_item(pmid="11111", doi="10.1/same", title="First version")
        item_b = self._make_item(pmid="22222", doi="10.1/same", title="Duplicate version")
        results = _postprocess_pubmed([item_a, item_b], "test", None)
        assert len(results) == 1

    def test_results_sorted_by_relevance(self):
        """Results must be sorted descending by relevance_score."""
        from app.api.search import _postprocess_pubmed
        items = [
            self._make_item(pmid="1", title="Hip surgery biomechanics 2024", pub_year=2024, doi="10.1/a", abstract="full"),
            self._make_item(pmid="2", title="Something unrelated", pub_year=2001, doi=None, abstract=None, oa_url=None, is_open_access=False),
            self._make_item(pmid="3", title="Hip fracture review", pub_year=2020, doi="10.1/c", abstract="text"),
        ]
        results = _postprocess_pubmed(items, "Hip surgery", None)
        scores = [r["relevance_score"] for r in results]
        assert scores == sorted(scores, reverse=True), "Results must be sorted descending by relevance"


# ─────────────────────────────────────────────
# 10. DOWNLOAD — oa_url-only papers (Regression test for Bug #1)
# ─────────────────────────────────────────────

class TestDownloadOAUrlOnly:
    """Verify download works with oa_url alone (no DOI, no PMID) — covers DOAJ papers."""

    @pytest.mark.asyncio
    async def test_oa_url_only_download_succeeds(self):
        from unittest.mock import AsyncMock, MagicMock, patch
        from app.services.paper_service import PaperDownloadService, DownloadResult

        service = PaperDownloadService()

        fake_pdf = b"%PDF-1.4 content %%EOF"
        fake_resp = MagicMock()
        fake_resp.content = fake_pdf
        fake_resp.status_code = 200
        fake_resp.headers = {"content-type": "application/pdf"}
        fake_resp.raise_for_status = MagicMock()

        fake_client = AsyncMock()
        fake_client.get = AsyncMock(return_value=fake_resp)

        with patch("app.services.paper_service.storage_manager") as mock_storage:
            mock_storage.validate_pdf.return_value = True
            result = await service.download_open_access_pdf(
                doi=None,
                pmid=None,
                oa_url="https://doaj-paper.org/fulltext.pdf",
                client=fake_client,
            )

        assert result.source == "user_provided_oa"
        assert result.resolved_url == "https://doaj-paper.org/fulltext.pdf"
        fake_client.get.assert_called_once_with(
            "https://doaj-paper.org/fulltext.pdf",
            timeout=60,
            follow_redirects=True,
        )

    @pytest.mark.asyncio
    async def test_no_identifier_no_oa_url_raises(self):
        from unittest.mock import AsyncMock
        from app.services.paper_service import PaperDownloadService, PaperServiceError

        service = PaperDownloadService()
        fake_client = AsyncMock()

        with pytest.raises(PaperServiceError):
            await service.download_open_access_pdf(
                doi=None, pmid=None, oa_url=None, client=fake_client,
            )

    def test_schema_allows_oa_url_without_doi_pmid(self):
        """PaperDownloadRequest must be constructable with only oa_url."""
        from app.schemas.papers import PaperDownloadRequest
        import uuid
        # Should not raise — oa_url alone is now valid
        req = PaperDownloadRequest(
            project_id=uuid.uuid4(),
            title="DOAJ paper with only OA URL",
            oa_url="https://doaj.org/fulltext.pdf",
        )
        assert req.doi is None
        assert req.pmid is None
        assert req.oa_url == "https://doaj.org/fulltext.pdf"
