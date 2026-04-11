# document-miner

Goal: validate and mine documents.

Rules:
- A file ending in .pdf is not enough; validate mime, header, and extractability.
- Mark fake PDFs explicitly.
- Prefer structured extraction with confidence and warnings.
- If OCR is required, say so.
