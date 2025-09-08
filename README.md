

# **TrustNoCorpo**

**Cryptographic PDF tracking for LaTeX builds** — with optional PDF password protection and an **encrypted audit log** per project.

> Track who built what, when, and how — directly from your LaTeX toolchain or Python.

---

## **Features**

* 🔒 **Encrypted audit log** stored locally under **.trustnocorpo/**
* 🔐 **Optional PDF password protection** (via pypdf)
* 🧰 **Drop-in CLI** for initializing projects and building PDFs
* 🐍 **Python API** for programmatic builds
* 🧪 **Testing without LaTeX** (LaTeX calls are mocked in tests)

---

## **Quick start**

### **Install (editable)**

```
python3 -m pip install -e .
```

### **Run tests**

```
pytest -q
```

### **Initialize a project**

```
trustnocorpo init
```

This creates a **.trustnocorpo/** workspace in your repo and copies helpful templates (e.g., a Makefile).

### **Build a document (CLI)**

```
trustnocorpo build path/to/document.tex --classification=CONFIDENTIAL
# or shorthand:
trustnocorpo path/to/document.tex --classification=CONFIDENTIAL

# Watermark controls (optional)
trustnocorpo build path/to/document.tex \
  --classification=CONFIDENTIAL \
  --watermark "CONFIDENTIAL" \
  --wm-opacity 35 \
  --wm-angle 30 \
  --wm-tile

# Per-recipient token embedding (optional)
trustnocorpo build path/to/document.tex --classification=CONFIDENTIAL --recipient-id bob123

# Rasterize to harden watermarks (requires Ghostscript `gs`)
trustnocorpo build path/to/document.tex --classification=CONFIDENTIAL --rasterize --raster-dpi 150
```

> The **--classification** flag tags builds (e.g., **INTERNAL**, **CONFIDENTIAL**, **SECRET**) in the encrypted audit trail.
> Watermark controls and rasterization are optional defense-in-depth features.

---

## **Python API**

```
from tnc.core import trustnocorpo

cms = trustnocorpo()
cms.init_project()  # creates .trustnocorpo/ if missing
pdf_path = cms.build(
    "document.tex",
    classification="SECRET",
    watermark_text="SECRET",
    watermark_opacity=40,
    watermark_angle=45,
    watermark_tile=False,
    rasterize=True,       # requires Ghostscript
    raster_dpi=150,
    recipient_token="alice-token-123",
)
print("PDF:", pdf_path)
```

---

## **Makefile template**

A portable Makefile is provided at **example/Makefile**. Typical usage:

```
# Adjust as needed
DOC          ?= document.tex
CLASS        ?= CONFIDENTIAL

.PHONY: pdf
pdf:
	# Build with tracking + classification label
	trustnocorpo $(DOC) --classification=$(CLASS)

.PHONY: init
init:
	trustnocorpo init
```

> Use **make init** once per repo; **make pdf** thereafter.

---

## **Requirements & notes**

* **LaTeX toolchain** (e.g., **lualatex**/**pdflatex**/**xelatex**) is only required when you actually compile PDFs.
  * **Tests** do **not** require LaTeX; they mock the LaTeX layer.
* **PDF protection**: implemented with **pypdf**.
* **Audit storage**: encrypted SQLite database lives under **.trustnocorpo/** within your project directory.
* **Rasterization (optional)**: requires **Ghostscript** (`gs`) on your PATH. If missing, the step is skipped gracefully.

### LaTeX package (optional)

You can also drive presentation from LaTeX using the bundled package `tnc.sty`:

```
\usepackage{tnc}
\tncclass{CONFIDENTIAL}
\tncwatermark{CONFIDENTIAL}
\tncwatermarksetup{opacity=35,angle=30,tile=false}
\tncfooterfingerprint{TNC Demo Build}
% \tncrecipient{alice-token-123}
```

The CLI parameters and the LaTeX macros are compatible; prefer the CLI for automation and per-build overrides.

---

## **CLI availability**

The **trustnocorpo** command is installed via the package’s **console script** entry point.

After **pip install -e .**, ensure your environment is active and your shell can see the script on **PATH**. If not:

* Activate your virtualenv (**source venv/bin/activate**) or
* Rehash your shims (e.g., **hash -r** in bash/zsh) or
* Run via **python -m tnc.cli** as a fallback.

For all options:

```
trustnocorpo --help
```

---

## **How it fits in your LaTeX workflow**

1. **Initialize once** per repository: **trustnocorpo init**.
2. **Build** via CLI or your Makefile: trustnocorpo path/to.tex --classification=INTERNAL**.**
3. **Ship the PDF**; the build metadata (who/when/what) is logged **encrypted** in **.trustnocorpo/**.

> You keep full control: all tracking is local to your project unless you choose to export logs.

---

## **Troubleshooting**

* **trustnocorpo: command not found**
  Activate your virtual environment or re-open your shell; confirm **pip show** lists the package.
* **LaTeX not found**
  Ensure **pdflatex**/**xelatex** is on **PATH**. Only needed for real builds, not for tests.
* **PDF not protected as expected**
  Verify you passed the appropriate protection options (see **--help**) and that the output path isn’t being overwritten by another tool.

---

## **Contributing**

PRs welcome! Please:

1. Add or update tests for new behavior.
2. Keep CLI and Python API examples in this README in sync.
3. Run **pytest -q** before submitting.

---

## **License**

See **LICENSE** in the repository.

---

## **Appendix: Design goals**

* **Minimal friction** for LaTeX users (works with existing Makefiles).
* **Local-first & private**: encrypted logs live in your repo.
* **Explicit classification** to reduce accidental leaks.
* **Scriptable** via CLI and Python for CI/CD integration.

---
