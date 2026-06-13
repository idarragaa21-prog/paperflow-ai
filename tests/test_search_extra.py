from metaforge.extract import extract_to_csv_row, fields_for
from metaforge.screen import cohen_kappa
from metaforge.search import _dedup, _parse_pubmed
import xml.etree.ElementTree as ET


def test_cohen_kappa_perfect_and_none():
    assert cohen_kappa(["include", "exclude", "maybe"], ["include", "exclude", "maybe"]) == 1.0
    assert cohen_kappa(["include", "include"], ["exclude", "exclude"]) == 0.0
    assert cohen_kappa([], []) is None


def test_cohen_kappa_partial():
    k = cohen_kappa(["include", "include", "exclude", "maybe"], ["include", "exclude", "exclude", "maybe"])
    assert -1.0 <= k <= 1.0


def test_dedup_by_doi_and_pmid():
    a = [{"doi": "10.1/x", "pmid": "1", "title": "A", "abstract": "", "pdf_url": None, "is_oa": False}]
    b = [{"doi": "10.1/X", "pmid": "1", "title": "A", "abstract": "full", "pdf_url": "u", "is_oa": True}]
    merged, dropped = _dedup([a, b])
    assert dropped == 1 and len(merged) == 1
    assert merged[0]["abstract"] == "full"  # abstract merged in
    assert merged[0]["pdf_url"] == "u"


def test_fields_for_measure():
    assert fields_for("OR") == ["a_events", "b_non_events", "c_events", "d_non_events"]
    assert fields_for("HR") == ["effect_value", "ci_lower_95", "ci_upper_95"]
    assert fields_for("BOGUS") == ["yi", "se"]


def test_extract_to_csv_row():
    ext = {"study_label": "Smith 2020", "effect_measure": "HR",
           "fields": {"effect_value": 0.8, "ci_lower_95": 0.6, "ci_upper_95": None}}
    row = extract_to_csv_row(ext)
    assert row == '"Smith 2020",HR,0.8,0.6,'


def test_parse_pubmed_minimal():
    xml = """<PubmedArticle><MedlineCitation><PMID>123</PMID>
      <Article><ArticleTitle>A cohort study.</ArticleTitle>
      <Abstract><AbstractText>We followed adults.</AbstractText></Abstract>
      <AuthorList><Author><LastName>Smith</LastName><Initials>J</Initials></Author></AuthorList>
      <Journal><Title>BMJ</Title><JournalIssue><PubDate><Year>2019</Year></PubDate></JournalIssue></Journal>
      </Article></MedlineCitation>
      <PubmedData><ArticleIdList><ArticleId IdType="doi">10.1/x</ArticleId></ArticleIdList></PubmedData>
      </PubmedArticle>"""
    rec = _parse_pubmed(ET.fromstring(xml))
    assert rec["pmid"] == "123"
    assert rec["title"] == "A cohort study"
    assert rec["doi"] == "10.1/x"
    assert "Smith J" in rec["authors"]
    assert rec["source"] == "PubMed"
