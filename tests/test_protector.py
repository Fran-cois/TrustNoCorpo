from pathlib import Path

import pytest

from TrustNoCorpo.protector import PDFProtector


def make_dummy_pdf(path: Path):
    try:
        import PyPDF2
    except Exception:  # pragma: no cover - dependency missing
        pytest.skip("PyPDF2 not installed")

    writer = PyPDF2.PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with open(path, "wb") as f:
        writer.write(f)


def test_protect_and_unprotect_roundtrip(tmp_path):
    src = tmp_path / "a.pdf"
    make_dummy_pdf(src)

    prot = PDFProtector()

    protected = prot.protect_pdf(str(src), password="pass-123", build_hash="abcd", classification="CONFIDENTIAL", auto_password=False)
    assert protected and Path(protected).exists()

    # Ensure file is actually encrypted
    assert prot.check_pdf_protection(protected) is True

    # Now unprotect
    unprotected = prot.unprotect_pdf(protected, password="pass-123")
    assert unprotected and Path(unprotected).exists()
