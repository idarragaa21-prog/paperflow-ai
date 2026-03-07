from __future__ import annotations

from pathlib import Path

import pytest


def test_encrypted_pdf_detected(tmp_path):
    import fitz

    plain = tmp_path / "a.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(plain)
    doc.close()

    enc = tmp_path / "enc.pdf"
    doc = fitz.open(plain)
    doc.save(enc, encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="x", user_pw="y")
    doc.close()

    d2 = fitz.open(enc)
    try:
        assert d2.is_encrypted is True
    finally:
        d2.close()
