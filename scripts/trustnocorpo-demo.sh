#!/usr/bin/env bash
set -euo pipefail

# one-shot: TEXT → TXT → PDF → watermark+metadata → encrypt (trustnocorpo if possible)
# Usage:
#   (default demo text)   :  paste block as-is
#   custom arg text       :  TEXT="Quarterly deck v7 — do not forward." bash scripts/trustnocorpo-demo.sh
#   from file             :  INPUT_FILE=path/to/file.txt  (env var)
#   from stdin            :  TEXT="$(cat)"  (pipe in) then run

# --- tweakables ---
: "${TEXT:=When you’re sick that your deck is “so confidential” it somehow lands in every VC database, give it a gentle nudge.
This file was generated in ~30 seconds and protected with TrustNoCorpo.}"
: "${INPUT_FILE:=}"                       # if set, read from this file instead of TEXT
: "${PDF_PASS:=demo-P@ssw0rd}"            # change your password
: "${OWNER:=ACME}"                        # metadata
: "${PURPOSE:=review}"                    # metadata
: "${NUDGE:=no-forwarding}"               # metadata
: "${WATERMARK:=CONFIDENTIAL — VC Leaks Cure}"

TXT_OUT=${TXT_OUT:-note.txt}
PDF_OUT=${PDF_OUT:-note.pdf}
PREP_OUT=${PREP_OUT:-note.prepared.pdf}   # watermarked + metadata (not encrypted yet)
SEC_OUT=${SEC_OUT:-note.secured.pdf}

say(){ printf '%s\n' "$*"; }

ensure_pip(){
  if python3 -m pip --version >/dev/null 2>&1; then return; fi
  python3 -m ensurepip --upgrade >/dev/null 2>&1 || true
}

ensure_py_pkg(){
  # $1=import_name $2=pip_name
  python3 - <<PY || { say "Installing $2…"; ensure_pip; python3 -m pip install --user -q -U "$2"; }
try:
    import $1  # noqa
    print("ok")
except Exception:
    raise SystemExit(1)
PY
}

ensure_trustnocorpo(){
  if command -v trustnocorpo >/dev/null 2>&1; then return; fi
  if command -v pipx >/dev/null 2>&1; then
    say "Installing trustnocorpo via pipx…"
    pipx install -q trustnocorpo || true
  else
    say "Installing trustnocorpo via pip (user)…"
    ensure_pip
    python3 -m pip install --user -q -U trustnocorpo || true
    export PATH="$HOME/.local/bin:$PATH"
  fi
}

# 1) Write TXT
if [ -n "$INPUT_FILE" ]; then
  cp "$INPUT_FILE" "$TXT_OUT"
else
  printf "%b\n" "$TEXT" > "$TXT_OUT"
fi
say "Wrote $TXT_OUT"

# 2) Make base PDF from text
ensure_py_pkg reportlab reportlab
python3 - "$TXT_OUT" "$PDF_OUT" <<'PY'
import sys, textwrap
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

txt_path, pdf_path = sys.argv[1], sys.argv[2]
c = canvas.Canvas(pdf_path, pagesize=A4)
w, h = A4
m = 2*cm
y = h - m
c.setFont("Helvetica", 12)

for line in open(txt_path, encoding="utf-8"):
    for chunk in textwrap.wrap(line.rstrip("\n"), width=95) or [""]:
        if y < m:
            c.showPage(); c.setFont("Helvetica", 12); y = h - m
        c.drawString(m, y, chunk); y -= 14
c.save()
print(f"Created {pdf_path}")
PY

# 3) Add a big diagonal watermark + metadata (no encryption yet)
ensure_py_pkg pypdf pypdf
python3 - "$PDF_OUT" "$PREP_OUT" "$WATERMARK" "$OWNER" "$PURPOSE" "$NUDGE" <<'PY'
import sys, io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

src_path, dst_path, WATERMARK, OWNER, PURPOSE, NUDGE = sys.argv[1:7]

# Create an in-memory watermark page
buf = io.BytesIO()
c = canvas.Canvas(buf, pagesize=A4)
w, h = A4
c.saveState()
c.translate(w/2, h/2)
c.rotate(30)
c.setFillGray(0.85)        # light gray
c.setFont("Helvetica-Bold", 36)
c.drawCentredString(0, 0, WATERMARK)
c.restoreState()
c.save()
buf.seek(0)

wm_page = PdfReader(buf).pages[0]
reader = PdfReader(src_path)
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(wm_page)  # overlay watermark
    writer.add_page(page)

# Basic info dictionary + custom fields
writer.add_metadata({
    "/Producer": "TrustNoCorpo demo",
    "/Creator": "TrustNoCorpo demo",
    "/Author": OWNER,
    "/Subject": PURPOSE,
    "/Keywords": f"nudge={NUDGE}",
    "/Owner": OWNER,
    "/Purpose": PURPOSE,
    "/Nudge": NUDGE,
})

with open(dst_path, "wb") as f:
    writer.write(f)
print(f"Prepared {dst_path} (watermark + metadata)")
PY

# 4) Try to encrypt with trustnocorpo protect (auto-detect flags). If it fails, fallback to Python.
USED_TNC=0
ensure_trustnocorpo
if command -v trustnocorpo >/dev/null 2>&1; then
  HELP="$(trustnocorpo protect --help 2>&1 || true)"
  PASSFLAG=""; OUTFLAG=""
  if printf '%s' "$HELP" | grep -q -- '--password'; then PASSFLAG="--password"; fi
  if printf '%s' "$HELP" | grep -q ' -p '; then PASSFLAG="${PASSFLAG:-"-p"}"; fi
  if printf '%s' "$HELP" | grep -q -- '--output'; then OUTFLAG="--output"; fi
  if printf '%s' "$HELP" | grep -q ' -o '; then OUTFLAG="${OUTFLAG:-"-o"}"; fi

  CMD=(trustnocorpo protect "$PREP_OUT")
  [ -n "$PASSFLAG" ] && CMD+=("$PASSFLAG" "$PDF_PASS")
  [ -n "$OUTFLAG" ] && CMD+=("$OUTFLAG" "$SEC_OUT")

  if "${CMD[@]}"; then
    USED_TNC=1
    say "Encrypted via trustnocorpo → $SEC_OUT"
  else
    say "trustnocorpo protect failed; falling back to Python encryption."
  fi
fi

if [ "$USED_TNC" -eq 0 ]; then
  ensure_py_pkg pypdf pypdf
  python3 - "$PREP_OUT" "$SEC_OUT" "$PDF_PASS" <<'PY'
import sys
from pypdf import PdfReader, PdfWriter
src, dst, pw = sys.argv[1], sys.argv[2], sys.argv[3]
reader = PdfReader(src)
writer = PdfWriter()
for p in reader.pages:
    writer.add_page(p)
# Use default strong encryption (pypdf chooses algorithm)
writer.encrypt(user_password=pw)
with open(dst, "wb") as f:
    writer.write(f)
print(f"Encrypted (Python fallback) → {dst}")
PY
fi

say ""
say "Done."
say "  - $TXT_OUT"
say "  - $PDF_OUT"
say "  - $PREP_OUT  (watermark + metadata)"
say "  - $SEC_OUT   (encrypted; password: $PDF_PASS)"
say ""
say "Tip: export OWNER/PURPOSE/NUDGE/WATERMARK/PDF_PASS to customize."
