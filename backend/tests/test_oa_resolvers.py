from app.services.oa_resolvers import normalize_doi, normalize_reference_identity, normalize_title


def test_normalize_doi_strips_prefix_and_lowercases():
    assert normalize_doi("https://doi.org/10.1000/ABC-123") == "10.1000/abc-123"


def test_normalize_doi_edge_cases():
    assert normalize_doi(None) is None
    assert normalize_doi("") is None
    assert normalize_doi("   ") is None
    assert normalize_doi("http://doi.org/10.1000/XYZ") == "10.1000/xyz"
    assert normalize_doi("https://dx.doi.org/10.1000/XYZ") == "10.1000/xyz"
    assert normalize_doi("  10.1000/ABC-123  ") == "10.1000/abc-123"


def test_normalize_title_collapses_whitespace_and_symbols():
    assert normalize_title("  Effects of ACL Reconstruction: a Review!  ") == "effects of acl reconstruction a review"


def test_normalize_reference_identity_builds_canonical_fields():
    identity = normalize_reference_identity(
        doi="HTTPS://doi.org/10.1000/XYZ",
        pmid="12345",
        title="Outcome Study (Phase II)",
        source="pubmed",
    )
    assert identity == {
        "doi": "10.1000/xyz",
        "pmid": "12345",
        "title_normalized": "outcome study phase ii",
        "source_provenance": "pubmed",
    }
