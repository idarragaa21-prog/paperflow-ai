from __future__ import annotations

from app.services.pubmed import PubMedClient


def test_pubmed_client_parses_minimal():
    client = PubMedClient()
    xml = """
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>123</PMID>
          <Article>
            <Abstract>
              <AbstractText>Line1</AbstractText>
              <AbstractText>Line2</AbstractText>
            </Abstract>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """.strip()

    abstracts = client._parse_efetch_abstracts(xml)
    assert abstracts["123"] == "Line1\nLine2"
