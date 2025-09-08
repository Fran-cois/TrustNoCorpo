from pathlib import Path

import types
import subprocess

import pytest

from TrustNoCorpo.core import trustnocorpo
from TrustNoCorpo.keys import KeyManager


def _make_dummy_pdf(path: Path):
    path.write_bytes(b"%PDF-1.4\n% dummy\n")


def test_rasterize_skips_when_gs_absent(monkeypatch, temp_home, temp_project):
    # Ensure keys exist
    km = KeyManager()
    assert km.generate_user_keys("tester", "pw")

    tex = temp_project / "doc.tex"
    tex.write_text("\\documentclass{article}\\begin{document}Hi\\end{document}")

    cms = trustnocorpo(project_dir=str(temp_project))

    # Mock LaTeX to produce a dummy PDF
    def fake_run(tex_path, build_dir, *args, **kwargs):
        build_dir = Path(build_dir)
        build_dir.mkdir(exist_ok=True)
        out = build_dir / (Path(tex_path).stem + ".pdf")
        _make_dummy_pdf(out)
        return str(out)

    monkeypatch.setattr(cms, "_run_latex_build", fake_run)

    # Simulate Ghostscript not available
    monkeypatch.setattr("shutil.which", lambda name: None)

    assert cms.init_project(force=True)

    pdf_path = cms.build(str(tex), classification="CONFIDENTIAL", protect_pdf=False, rasterize=True, raster_dpi=110)
    assert pdf_path is not None
    # Should not have rasterized, path remains original name
    assert Path(pdf_path).name == "doc.pdf"


def test_rasterize_generates_image_pdf_when_gs_present(monkeypatch, temp_home, temp_project):
    km = KeyManager()
    assert km.generate_user_keys("tester", "pw")

    tex = temp_project / "doc.tex"
    tex.write_text("\\documentclass{article}\\begin{document}Hi\\end{document}")

    cms = trustnocorpo(project_dir=str(temp_project))

    def fake_run(tex_path, build_dir, *args, **kwargs):
        build_dir = Path(build_dir)
        build_dir.mkdir(exist_ok=True)
        out = build_dir / (Path(tex_path).stem + ".pdf")
        _make_dummy_pdf(out)
        return str(out)

    monkeypatch.setattr(cms, "_run_latex_build", fake_run)

    # Simulate Ghostscript present
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gs" if name == "gs" else None)

    # Simulate successful gs invocation: create the expected output file and return code 0
    def fake_run_subproc(cmd, stdout=None, stderr=None):
        # last two args are src pdf, we placed '-o', outpath earlier; find '-o' to get output
        try:
            o_idx = cmd.index("-o")
            out_path = Path(cmd[o_idx + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            _make_dummy_pdf(out_path)
        except Exception:
            pass
        return types.SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run_subproc)

    assert cms.init_project(force=True)

    dpi = 144
    pdf_path = cms.build(str(tex), classification="CONFIDENTIAL", protect_pdf=False, rasterize=True, raster_dpi=dpi)
    assert pdf_path is not None
    assert Path(pdf_path).name == f"doc.r{dpi}.pdf"


def test_rasterize_fallback_on_failure(monkeypatch, temp_home, temp_project):
    km = KeyManager()
    assert km.generate_user_keys("tester", "pw")

    tex = temp_project / "doc.tex"
    tex.write_text("\\documentclass{article}\\begin{document}Hi\\end{document}")

    cms = trustnocorpo(project_dir=str(temp_project))

    def fake_run(tex_path, build_dir, *args, **kwargs):
        build_dir = Path(build_dir)
        build_dir.mkdir(exist_ok=True)
        out = build_dir / (Path(tex_path).stem + ".pdf")
        _make_dummy_pdf(out)
        return str(out)

    monkeypatch.setattr(cms, "_run_latex_build", fake_run)

    # Simulate Ghostscript present
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/gs" if name == "gs" else None)

    # Simulate failure (non-zero return code)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=1))

    assert cms.init_project(force=True)

    pdf_path = cms.build(str(tex), classification="CONFIDENTIAL", protect_pdf=False, rasterize=True, raster_dpi=200)
    assert pdf_path is not None
    # Should fall back to original name
    assert Path(pdf_path).name == "doc.pdf"
