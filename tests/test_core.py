from pathlib import Path

import pytest

from TrustNoCorpo.core import trustnocorpo
from TrustNoCorpo.keys import KeyManager


def test_init_and_build_flow_without_latex(monkeypatch, temp_home, temp_project, tmp_path):
    # Ensure user keys exist to avoid interactive prompts
    km = KeyManager()
    assert km.generate_user_keys("tester", "pw")

    # Create a dummy .tex file
    tex_file = temp_project / "doc.tex"
    tex_file.write_text("\\documentclass{article}\\begin{document}Hello\\end{document}")

    cms = trustnocorpo(project_dir=str(temp_project))

    # Mock _run_latex_build to simulate successful PDF generation
    def fake_run(tex_path, build_dir, build_hash, gen_info, gen_time, classification):
        build_dir = Path(build_dir)
        build_dir.mkdir(exist_ok=True)
        pdf_path = build_dir / (Path(tex_path).stem + ".pdf")
        pdf_path.write_bytes(b"%PDF-1.4\n% dummy pdf content\n")
        return str(pdf_path)

    monkeypatch.setattr(cms, "_run_latex_build", fake_run)

    # Initialize project (should not prompt)
    assert cms.init_project(force=True) is True

    # Build and ensure a PDF path is returned
    pdf_path = cms.build(str(tex_file), classification="CONFIDENTIAL", protect_pdf=False)
    assert pdf_path is not None
    assert Path(pdf_path).exists()

    # Log/list builds via API
    builds = cms.list_builds(limit=5)
    assert isinstance(builds, list)
    assert any(b.get("main_file") == str(tex_file) for b in builds)
