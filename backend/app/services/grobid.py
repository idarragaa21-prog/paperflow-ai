from __future__ import annotations

from xml.etree import ElementTree as ET

import httpx

from app.config import settings
from app.core.logger import logger

TEI_NS = {"tei": "http://www.tei-c.org/ns/1.0"}


async def process_fulltext(pdf_bytes: bytes, *, filename: str) -> str | None:
    if not settings.GROBID_ENABLED:
        return None

    try:
        async with httpx.AsyncClient(timeout=settings.GROBID_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.GROBID_URL.rstrip('/')}/api/processFulltextDocument",
                files={"input": (filename, pdf_bytes, "application/pdf")},
                data={
                    "consolidateHeader": "1",
                    "consolidateCitations": "1",
                    "includeRawCitations": "1",
                    "includeRawAffiliations": "1",
                },
            )
            response.raise_for_status()
            return response.text
    except Exception as exc:
        logger.warning(f"GROBID fulltext parsing failed: {exc}")
        return None


def extract_tei_structure(tei_xml: str | None) -> dict:
    if not tei_xml:
        return {"sections": [], "references": [], "title": None}

    try:
        root = ET.fromstring(tei_xml)
    except ET.ParseError:
        return {"sections": [], "references": [], "title": None}

    title = root.findtext(".//tei:titleStmt/tei:title", default=None, namespaces=TEI_NS)
    sections = []
    for div in root.findall(".//tei:text/tei:body/tei:div", TEI_NS):
        heading = div.findtext("./tei:head", default=None, namespaces=TEI_NS)
        paragraphs = [" ".join(node.itertext()).strip() for node in div.findall("./tei:p", TEI_NS)]
        text = "\n\n".join(item for item in paragraphs if item)
        if heading or text:
            sections.append({"heading": heading, "text": text})

    references = []
    for bibl in root.findall(".//tei:listBibl/tei:biblStruct", TEI_NS):
        ref_title = bibl.findtext(".//tei:title", default=None, namespaces=TEI_NS)
        authors = []
        for author in bibl.findall(".//tei:author", TEI_NS):
            name = " ".join(part.strip() for part in author.itertext() if part.strip())
            if name:
                authors.append(name)
        year = bibl.findtext(".//tei:imprint/tei:date", default=None, namespaces=TEI_NS)
        references.append({"title": ref_title, "authors": authors, "year": year})

    return {"sections": sections, "references": references, "title": title}
