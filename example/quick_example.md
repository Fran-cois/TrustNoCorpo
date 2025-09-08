```bash
bash <<'SCRIPT'
set -euo pipefailone-shot: TEXT → TXT → PDF → watermark+metadata → encrypt (trustnocorpo if possible)Usage:(default demo text)   :  paste block as-iscustom arg text       :  TEXT="Quarterly deck v7 — do not forward." bash <(cat <<'SCRIPT' ... )   # or export TEXT beforefrom file             :  INPUT_FILE=path/to/file.txt  (env var)from stdin            :  TEXT="$(cat)"  (pipe in) then run--- tweakables ---: "${TEXT:=When you’re sick that your deck is “so confidential” it somehow lands in every VC database, give it a gentle nudge.
This file was generated in ~30 seconds and protected with TrustNoCorpo.}"
: "${INPUT_FILE:=}"                       # if set, read from this file instead of TEXT
: "${PDF_PASS:=demo-P@ssw0rd}"            # change your password
: "${OWNER:=ACME}"                        # metadata
: "${PURPOSE:=review}"                    # metadata
: "${NUDGE:=no-forwarding}"               # metadata
: "${WATERMARK:=CONFIDENTIAL — VC Leaks Cure}"TXT_OUT=${TXT_OUT:-note.txt}
PDF_OUT=${PDF_OUT:-note.pdf}
PREP_OUT=${PREP_OUT:-note.prepared.pdf}   # watermarked + metadata (not encrypted yet)
SEC_OUT=${SEC_OUT:-note.secured.pdf}say(){ printf '%s\n' "$*"; }ensure_pip(){
  if python3 -m pip --version >/dev/null 2>&1; then return; fi
  python3 -m ensurepip --upgrade >/dev/null 2>&1 || true
}ensure_py_pkg(){$1=import_name $2=pip_name  python3 - <
```
