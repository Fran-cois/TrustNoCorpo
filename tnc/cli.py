"""
trustnocorpo Command Line Interface
=============================
Main CLI entry point for the trustnocorpo standalone package.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

from .core import trustnocorpo
from .keys import KeyManager
from .protector import PDFProtector


def cmd_init(args):
    """Initialize trustnocorpo project"""
    cms = trustnocorpo(args.project_dir)
    success = cms.init_project(force=args.force)
    return 0 if success else 1


def cmd_build(args):
    """Build LaTeX document with crypto tracking"""
    cms = trustnocorpo(args.project_dir)
    
    # Check if project is initialized
    if not (cms.trustnocorpo_dir / "builds.db").exists():
        print("❌ trustnocorpo not initialized. Run: trustnocorpo init")
        return 1
    
    pdf_path = cms.build(
        tex_file=args.tex_file,
        classification=args.classification,
        output_dir=args.output_dir,
        protect_pdf=args.protect,
        pdf_password=args.password,
        watermark_text=args.watermark,
        watermark_opacity=args.wm_opacity,
        watermark_angle=args.wm_angle,
        watermark_tile=args.wm_tile,
        rasterize=getattr(args, 'rasterize', False),
        raster_dpi=getattr(args, 'raster_dpi', 150),
        footer_fingerprint=args.footer_fingerprint,
        only_password=getattr(args, 'only_password', False),
        recipient_token=getattr(args, 'recipient_id', None),
    )
    
    return 0 if pdf_path else 1


def cmd_list(args):
    """List recent builds"""
    cms = trustnocorpo(args.project_dir)
    builds = cms.list_builds(limit=args.limit)
    return 0 if builds else 1


def cmd_verify(args):
    """Verify a build"""
    cms = trustnocorpo(args.project_dir)
    success = cms.verify_build(args.build_hash)
    return 0 if success else 1


def cmd_info(args):
    """Show system information"""
    cms = trustnocorpo(args.project_dir)
    info = cms.get_info()
    return 0 if info else 1


def cmd_keys(args):
    """Manage user keys"""
    key_manager = KeyManager()
    
    if args.generate:
        if key_manager.user_has_keys() and not args.force:
            print("✅ User keys already exist. Use --force to regenerate.")
            return 0
        
        username = input("👤 Username: ").strip()
        if not username:
            print("❌ Username required")
            return 1
        
        import getpass
        password = getpass.getpass("🔑 Master password: ")
        if not password:
            print("❌ Master password required")
            return 1
        
        success = key_manager.generate_user_keys(username, password)
        return 0 if success else 1
    
    elif args.info:
        if not key_manager.user_has_keys():
            print("❌ No user keys found. Generate with: trustnocorpo keys --generate")
            return 1
        
        info = key_manager.get_user_info()
        if info:
            print("👤 User Key Information:")
            print(f"   Username: {info['username']}")
            print(f"   Fingerprint: {info['fingerprint']}")
            print(f"   Created: {info['created_at']}")
            print(f"   Key file: {info['key_file']}")
            return 0
        else:
            print("❌ Failed to read user info")
            return 1
    
    elif args.reset:
        confirm = input("⚠️  Reset all user keys? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            success = key_manager.reset_keys()
            if success:
                print("✅ User keys reset")
                return 0
            else:
                print("❌ Failed to reset keys")
                return 1
        else:
            print("🚫 Reset cancelled")
            return 0
    
    else:
        print("❌ Use --generate, --info, or --reset")
        return 1


def cmd_protect(args):
    """Protect/unprotect PDFs"""
    protector = PDFProtector()
    
    if args.unprotect:
        result = protector.unprotect_pdf(
            args.pdf_file,
            password=args.password,
            build_hash=args.build_hash
        )
    else:
        result = protector.protect_pdf(
            args.pdf_file,
            password=args.password,
            build_hash=args.build_hash,
            classification=args.classification,
            auto_password=args.auto_password
        )
    
    return 0 if result else 1


def cmd_validate(args):
    """Validate a leaked PDF and recover embedded token(s)."""
    cms = trustnocorpo(args.project_dir)
    report = cms.validate_pdf(args.pdf_file, output_json=args.json)
    return 0 if report else 1


def cmd_export_log(args):
    """Export encrypted log entries, optionally GPG-signing the bundle."""
    cms = trustnocorpo(args.project_dir)
    out = cms.logger.export_signed(output_dir=args.output_dir or ".", gpg_key=args.gpg_key)
    return 0 if out else 1


def cmd_fanout(args):
    """Build per-recipient PDFs with unique tokens from a CSV file."""
    cms = trustnocorpo(args.project_dir)
    return 0 if cms.fanout_builds(csv_path=args.recipients_csv,
                                  tex_file=args.tex_file,
                                  classification=args.classification,
                                  output_root=args.output_dir,
                                  watermark_text=args.watermark,
                                  footer_fingerprint=args.footer_fingerprint) else 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="trustnocorpo - Cryptographic PDF Tracking System v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  trustnocorpo init                           # Initialize project
  trustnocorpo build document.tex             # Build with tracking
  trustnocorpo build document.tex --classification=SECRET  # Classified build
  trustnocorpo document.tex --classification=SECRET        # Shorthand
  trustnocorpo list                           # List recent builds
  trustnocorpo verify abc123def               # Verify build
  trustnocorpo keys --generate                # Setup user keys
  trustnocorpo protect document.pdf           # Protect PDF
    trustnocorpo --demo                         # One-shot demo (text -> PDF -> watermark+metadata -> encrypt)
        """
    )
    
    parser.add_argument(
        '--project-dir', '-d',
        help='Project directory (default: current directory)',
        default=None
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Run one-shot demo: TEXT → TXT → PDF → watermark+metadata → encrypt'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init command
    init_parser = subparsers.add_parser('init', help='Initialize trustnocorpo project')
    init_parser.add_argument('--force', action='store_true', help='Force reinitialization')
    init_parser.set_defaults(func=cmd_init)
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build LaTeX document')
    build_parser.add_argument('tex_file', help='LaTeX file to build')
    build_parser.add_argument('--classification', '-c', default='UNCLASSIFIED', 
                             help='Document classification')
    build_parser.add_argument('--output-dir', '-o', help='Output directory')
    build_parser.add_argument('--protect', action='store_true', default=True,
                             help='Protect PDF with password')
    build_parser.add_argument('--password', '-p', help='Custom PDF password')
    build_parser.add_argument('--watermark', help='Watermark text to inject (e.g., CONFIDENTIAL)')
    build_parser.add_argument('--wm-opacity', type=int, choices=range(5, 101), metavar='PCT',
                             help='Watermark shade percent (5-100), default 40')
    build_parser.add_argument('--wm-angle', type=int, metavar='DEG',
                             help='Watermark angle in degrees, default 45')
    build_parser.add_argument('--wm-tile', action='store_true',
                             help='Tile watermark across the page (3x3)')
    build_parser.add_argument('--rasterize', action='store_true',
                             help='Rasterize PDF post-build via Ghostscript to frustrate removal of watermarks')
    build_parser.add_argument('--raster-dpi', type=int, default=150,
                             help='Rasterization DPI (affects image resolution), default 150')
    build_parser.add_argument('--footer-fingerprint', action='store_true',
                             help='Inject user fingerprint in the PDF footer')
    build_parser.add_argument('--only-password', action='store_true',
                             help='Suppress all output except the final password line')
    build_parser.add_argument('--recipient-id', help='Per-recipient token to embed (opt-in)')
    build_parser.set_defaults(func=cmd_build)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent builds')
    list_parser.add_argument('--limit', '-l', type=int, default=10,
                            help='Maximum builds to show')
    list_parser.set_defaults(func=cmd_list)
    
    # Verify command
    verify_parser = subparsers.add_parser('verify', help='Verify build integrity')
    verify_parser.add_argument('build_hash', help='Build hash to verify')
    verify_parser.set_defaults(func=cmd_verify)
    
    # Info command
    info_parser = subparsers.add_parser('info', help='Show system information')
    info_parser.set_defaults(func=cmd_info)
    
    # Keys command
    keys_parser = subparsers.add_parser('keys', help='Manage user keys')
    keys_group = keys_parser.add_mutually_exclusive_group(required=True)
    keys_group.add_argument('--generate', action='store_true', help='Generate user keys')
    keys_group.add_argument('--info', action='store_true', help='Show key information')
    keys_group.add_argument('--reset', action='store_true', help='Reset user keys')
    keys_parser.add_argument('--force', action='store_true', help='Force key regeneration')
    keys_parser.set_defaults(func=cmd_keys)
    
    # Protect command
    protect_parser = subparsers.add_parser('protect', help='Protect/unprotect PDFs')
    protect_parser.add_argument('pdf_file', help='PDF file to protect/unprotect')
    protect_parser.add_argument('--unprotect', action='store_true', 
                               help='Unprotect instead of protect')
    protect_parser.add_argument('--password', '-p', help='Custom password')
    protect_parser.add_argument('--build-hash', help='Build hash for password derivation')
    protect_parser.add_argument('--classification', help='Document classification')
    protect_parser.add_argument('--auto-password', action='store_true', default=True,
                               help='Auto-generate password')
    protect_parser.set_defaults(func=cmd_protect)

    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate a leaked PDF and recover token(s)')
    validate_parser.add_argument('pdf_file', help='Leaked PDF to validate')
    validate_parser.add_argument('--json', action='store_true', help='Output JSON report')
    validate_parser.set_defaults(func=cmd_validate)

    # Export log
    export_parser = subparsers.add_parser('export-log', help='Export encrypted log and sign bundle (GPG optional)')
    export_parser.add_argument('--output-dir', '-o', help='Directory to write the evidence bundle')
    export_parser.add_argument('--gpg-key', help='GPG key ID/email to sign with')
    export_parser.set_defaults(func=cmd_export_log)

    # Fanout
    fanout_parser = subparsers.add_parser('fanout', help='Per-recipient builds from a CSV')
    fanout_parser.add_argument('recipients_csv', help='CSV with header "recipient" or "id"')
    fanout_parser.add_argument('tex_file', help='LaTeX file to build for each recipient')
    fanout_parser.add_argument('--classification', '-c', default='UNCLASSIFIED', 
                              help='Document classification')
    fanout_parser.add_argument('--output-dir', '-o', help='Root output directory (default: fanout_out)')
    fanout_parser.add_argument('--watermark', help='Watermark text to inject (e.g., CONFIDENTIAL)')
    fanout_parser.add_argument('--footer-fingerprint', action='store_true',
                              help='Inject user fingerprint in the PDF footer')
    fanout_parser.set_defaults(func=cmd_fanout)
    
    # Shorthand: if first arg looks like a .tex file, rewrite to 'build <tex>'
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0].lower().endswith('.tex'):
        raw_args = ['build'] + raw_args

    # Parse arguments
    args = parser.parse_args(raw_args)

    # Global demo flag
    if getattr(args, 'demo', False):
        demo_script = r"""#!/usr/bin/env bash
set -euo pipefail

# one-shot: TEXT → TXT → PDF → watermark+metadata → encrypt (trustnocorpo if possible)
# Usage:
#   (default demo text)   :  paste block as-is
#   custom arg text       :  TEXT="Quarterly deck v7 — do not forward." bash <(cat <<'SCRIPT' ... )   # or export TEXT before
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
"""
        try:
            # Feed the script to bash via stdin
            subprocess.run(["bash", "-s"], input=demo_script, text=True, check=True)
            return 0
        except subprocess.CalledProcessError as e:
            print(f"❌ Demo failed (exit {e.returncode})")
            return e.returncode

    if not args.command:
        parser.print_help()
        return 1
    
    # Execute command
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\n🚫 Operation cancelled")
        return 1
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
