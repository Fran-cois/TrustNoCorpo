"""
trustnocorpo Core Module
==================
Main interface for the trustnocorpo cryptographic PDF tracking system.
"""

import os
import sys
import io
import contextlib
import subprocess
import tempfile
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Any
import base64

from .keys import KeyManager
from .protector import PDFProtector
from .logger import BuildLogger


class trustnocorpo:
    """
    Main trustnocorpo interface for cryptographic PDF tracking.
    
    This class provides a simple, standalone interface that:
    - Automatically sets up user keys and database
    - Manages LaTeX style integration  
    - Handles PDF generation with crypto tracking
    - Provides audit and verification capabilities
    """
    
    def __init__(self, project_dir: Optional[str] = None):
        """
        Initialize trustnocorpo system.
        
        Args:
            project_dir: Project directory (defaults to current directory)
        """
        self.project_dir = Path(project_dir or os.getcwd())
        self.trustnocorpo_dir = self.project_dir / ".trustnocorpo"
        
        # Initialize components
        self.key_manager = KeyManager()
        self.pdf_protector = PDFProtector()
        self.logger = BuildLogger(db_path=str(self.trustnocorpo_dir / "builds.db"))
        
        # LaTeX configuration
        self.latex_engine = "lualatex"
        self.use_latexmk = True
        
    def init_project(self, force: bool = False) -> bool:
        """
        Initialize trustnocorpo in the current project.
        
        Args:
            force: Force reinitialization if already exists
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create project .trustnocorpo directory
            if self.trustnocorpo_dir.exists() and not force:
                print(f"✅ trustnocorpo already initialized in {self.project_dir}")
                return True
                
            self.trustnocorpo_dir.mkdir(exist_ok=True)
            
            # Setup user keys if needed
            if not self.key_manager.user_has_keys():
                print("🔐 Setting up user encryption keys...")
                username = input("👤 Username: ").strip()
                if not username:
                    print("❌ Username required")
                    return False
                    
                import getpass
                password = getpass.getpass("🔑 Master password: ")
                if not password:
                    print("❌ Master password required")
                    return False
                    
                if not self.key_manager.generate_user_keys(username, password):
                    print("❌ Failed to generate user keys")
                    return False
                    
            # Copy LaTeX style file
            self._setup_latex_style()
            
            # Initialize database
            self.logger._init_encrypted_database()
            
            print(f"✅ trustnocorpo initialized in {self.project_dir}")
            print(f"📁 Project directory: {self.trustnocorpo_dir}")
            print("💡 Use trustnocorpo.build('document.tex') to generate tracked PDFs")
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            return False
    
    def build(self, 
              tex_file: str, 
              classification: str = "UNCLASSIFIED",
              output_dir: Optional[str] = None,
              protect_pdf: bool = True,
              pdf_password: Optional[str] = None,
              watermark_text: Optional[str] = None,
              watermark_opacity: Optional[int] = None,
              watermark_angle: Optional[int] = None,
              watermark_tile: bool = False,
              rasterize: bool = False,
              raster_dpi: int = 150,
              footer_fingerprint: bool = False,
              only_password: bool = False,
              recipient_token: Optional[str] = None) -> Optional[str]:
        """
        Build a LaTeX document with cryptographic tracking.
        
        Args:
            tex_file: Path to LaTeX file
            classification: Document classification
            output_dir: Output directory (defaults to 'build')
            protect_pdf: Whether to password-protect the PDF
            pdf_password: Custom PDF password (auto-generated if None)
            
        Returns:
            Path to generated PDF if successful, None otherwise
        """
        try:
            tex_path = Path(tex_file)
            if not tex_path.exists():
                print(f"❌ LaTeX file not found: {tex_file}")
                return None


            # Setup build environment
            build_dir = Path(output_dir or "build")
            build_dir.mkdir(exist_ok=True)

            # Ensure project style file exists (don't overwrite non-empty file)
            self._ensure_style_file()
            
            # Generate build metadata
            build_hash = self._generate_build_hash(tex_file, classification)
            generation_info = self._encode_generation_info()
            generation_time = self._encode_generation_time()
            
            if not only_password:
                print(f"🔨 Building {tex_file} with classification: {classification}")
                print(f"🔢 Build hash: {build_hash}")
            
            # Build LaTeX document
            # Compute optional footer content
            footer_text = None
            if footer_fingerprint:
                try:
                    user_info = self.key_manager.get_user_info() or {}
                    fp = user_info.get('fingerprint')
                    if fp:
                        footer_text = f"Fingerprint: {fp}"
                except Exception:
                    footer_text = None

            # Call _run_latex_build preferring extended signature; fall back to legacy
            try:
                pdf_path = self._run_latex_build(
                    tex_path, build_dir, build_hash,
                    generation_info, generation_time, classification,
                    watermark_text=watermark_text, footer_text=footer_text,
                    wm_opacity=watermark_opacity, wm_angle=watermark_angle, wm_tile=watermark_tile,
                    recipient_token=recipient_token,
                    quiet=only_password
                )
            except TypeError:
                # Legacy signature without extra keyword arguments
                pdf_path = self._run_latex_build(
                    tex_path, build_dir, build_hash,
                    generation_info, generation_time, classification
                )
            
            if not pdf_path:
                return None
                
            # Optional rasterization (before protection)
            if rasterize:
                try:
                    pdf_path = self._rasterize_pdf(pdf_path, dpi=raster_dpi)
                except Exception:
                    pass

            # Protect PDF if requested
            if protect_pdf:
                protected_path = self._protect_pdf(
                    pdf_path, build_hash, classification, pdf_password,
                    quiet=only_password
                )
                if protected_path:
                    pdf_path = protected_path
                    # Determine the password used (either provided or derived)
                    used_password = pdf_password or self.pdf_protector._generate_context_password(build_hash, classification)
                    if used_password:
                        if only_password:
                            print(used_password)
                        else:
                            print(f"🔑 Password: {used_password}")
                    
            # Log build to encrypted database (suppress prints when only_password)
            if only_password:
                with contextlib.redirect_stdout(io.StringIO()):
                    self._log_build(
                        build_hash, generation_info, generation_time,
                        classification, tex_file, pdf_path, pdf_password,
                        recipient_token=recipient_token
                    )
            else:
                self._log_build(
                    build_hash, generation_info, generation_time,
                    classification, tex_file, pdf_path, pdf_password,
                    recipient_token=recipient_token
                )
            
            if not only_password:
                print(f"✅ PDF generated: {pdf_path}")
            return str(pdf_path)
            
        except Exception as e:
            if not only_password:
                print(f"❌ Build failed: {e}")
            return None
    
    def _rasterize_pdf(self, pdf_path: str, dpi: int = 150) -> str:
        """Best-effort PDF rasterization using Ghostscript.

        Attempts to convert the input PDF into an image-based PDF to harden
        watermark removal. Requires `gs` on PATH. If Ghostscript or the
        `pdfimage24` device is not available, returns the original PDF path.

        Args:
            pdf_path: Path to the input PDF.
            dpi: Rasterization resolution.

        Returns:
            Path to the rasterized PDF if successful, else the original path.
        """
        try:
            if not shutil.which("gs"):
                return pdf_path
            src = Path(pdf_path)
            out_path = src.with_name(src.stem + f".r{dpi}.pdf")
            cmd = [
                "gs",
                "-sDEVICE=pdfimage24",  # image-based PDF device (if available)
                f"-r{int(dpi)}",
                "-dBATCH",
                "-dNOPAUSE",
                "-dSAFER",
                "-o",
                str(out_path),
                str(src),
            ]
            # Run quietly; caller handles fallbacks
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0:
                return str(out_path)
            # Fallback: keep original
            return str(src)
        except Exception:
            return pdf_path
    def list_builds(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent builds from encrypted database.
        
        Args:
            limit: Maximum number of builds to return
            
        Returns:
            List of build records
        """
        try:
            builds = self.logger.list_builds(limit)
            
            print(f"📊 Recent builds (last {len(builds)}):")
            for i, build in enumerate(builds, 1):
                print(f"  {i}. Hash: {build.get('build_hash', 'unknown')[:12]}...")
                print(f"     Classification: {build.get('classification', 'unknown')}")
                print(f"     Time: {build.get('timestamp_iso', 'unknown')}")
                print()
                
            return builds
            
        except Exception as e:
            print(f"❌ Failed to list builds: {e}")
            return []
    
    def verify_build(self, build_hash: str) -> bool:
        """
        Verify a build's cryptographic signature.
        
        Args:
            build_hash: Build hash to verify
            
        Returns:
            True if verification succeeds, False otherwise
        """
        try:
            result = self.logger.verify_build(build_hash)
            if result:
                print(f"✅ Build {build_hash} verified successfully")
                return True
            else:
                print(f"❌ Build {build_hash} verification failed")
                return False
                
        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get trustnocorpo system information.
        
        Returns:
            Dictionary with system information
        """
        try:
            user_info = self.key_manager.get_user_info() or {}
            db_stats = self.logger.get_user_builds_stats() or {}
            
            info = {
                'version': '1.0.1',
                'project_dir': str(self.project_dir),
                'trustnocorpo_dir': str(self.trustnocorpo_dir),
                'user_keys_active': self.key_manager.user_has_keys(),
                'user_fingerprint': user_info.get('fingerprint', 'unknown'),
                'total_builds': db_stats.get('total_builds', 0),
                'user_builds': db_stats.get('user_builds', 0),
            }
            
            print("📊 trustnocorpo System Information:")
            print(f"   Version: {info['version']}")
            print(f"   Project: {info['project_dir']}")
            print(f"   User keys: {'✅ Active' if info['user_keys_active'] else '❌ Not configured'}")
            print(f"   User fingerprint: {info['user_fingerprint']}")
            print(f"   Total builds: {info['total_builds']}")
            print(f"   Your builds: {info['user_builds']}")
            
            return info
            
        except Exception as e:
            print(f"❌ Failed to get system info: {e}")
            return {}
    
    def _generate_build_hash(self, tex_file: str, classification: str) -> str:
        """Generate unique build hash"""
        content = f"{tex_file}{classification}{datetime.now().isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _encode_generation_info(self) -> str:
        """Encode generation info as base64"""
        try:
            node = os.uname().nodename  # type: ignore[attr-defined]
        except AttributeError:
            try:
                import platform
                node = platform.node() or 'unknown'
            except Exception:
                node = 'unknown'
        info = f"{os.environ.get('USER', 'unknown')}@{node}"
        return base64.b64encode(info.encode()).decode()
    
    def _encode_generation_time(self) -> str:
        """Encode generation time as base64"""
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        return base64.b64encode(time_str.encode()).decode()
    
    def _setup_latex_style(self):
        """Copy LaTeX style to project directory"""
        # For the standalone package, generate a local style file
        self._create_basic_style()
        # Also copy packaged tnc.sty if available, for users who prefer \usepackage{tnc}
        try:
            import importlib.resources as ir
            with ir.as_file(ir.files('tnc.latex') / 'tnc.sty') as sty_path:  # type: ignore[attr-defined]
                if sty_path.exists():
                    target = self.project_dir / 'tnc.sty'
                    if (not target.exists()) or target.stat().st_size == 0:
                        shutil.copyfile(sty_path, target)
        except Exception:
            pass
        
    def _create_basic_style(self):
        """Create a basic LaTeX style file"""
        style_content = r"""
% trustnocorpo LaTeX Style (Embedded Version)
\NeedsTeXFormat{LaTeX2e}
\ProvidesPackage{trustnocorpo-spacial}[2025/08/17 trustnocorpo Cryptographic Style]

\RequirePackage{hyperref}
\RequirePackage{ifthen}
\RequirePackage{xcolor}
\RequirePackage{graphicx}
\RequirePackage{eso-pic}
\RequirePackage{fancyhdr}

% Cryptographic information embedding
\newcommand{\capyEmbedCryptoInfo}{%
    \ifdefined\capyBuildHash%
        \hypersetup{%
            pdfsubject={Build: \capyBuildHash},
            pdfkeywords={trustnocorpo, Crypto, \capyClassification\ifdefined\capyRecipientToken, tnc-token-\capyRecipientToken\fi}
        }%
    \fi%
}

% Optional watermark (uses \capyWatermarkText if defined)
\newcommand{\capyApplyWatermark}{%
    \ifdefined\capyWatermarkText%
        % Defaults
        \ifx\capyWmOpacity\undefined\def\capyWmOpacity{40}\fi
        \ifx\capyWmAngle\undefined\def\capyWmAngle{45}\fi
        % Single center watermark
        \AddToShipoutPictureBG*{%
            \AtPageLowerLeft{%
                \begin{minipage}[b][\paperheight]{\paperwidth}%
                    \centering
                    {\color{gray!\capyWmOpacity}\fontsize{6cm}{6cm}\selectfont\rotatebox{\capyWmAngle}{\capyWatermarkText}}%
                \end{minipage}%
            }%
        }%
        % Optional tiling (simple 3x3 grid, lighter opacity)
        \ifdefined\capyWmTile%
            \AddToShipoutPictureBG*{%
                \AtPageLowerLeft{%
                    \begingroup
                    \setlength{\unitlength}{1cm}
                    \begin{picture}(0,0)
                    \multiput(3,3)(6,0){3}{\makebox(0,0){\color{gray!\capyWmOpacity}\fontsize{2cm}{2cm}\selectfont\rotatebox{\capyWmAngle}{\capyWatermarkText}}}
                    \multiput(3,9)(6,0){3}{\makebox(0,0){\color{gray!\capyWmOpacity}\fontsize{2cm}{2cm}\selectfont\rotatebox{\capyWmAngle}{\capyWatermarkText}}}
                    \multiput(3,15)(6,0){3}{\makebox(0,0){\color{gray!\capyWmOpacity}\fontsize{2cm}{2cm}\selectfont\rotatebox{\capyWmAngle}{\capyWatermarkText}}}
                    \end{picture}
                    \endgroup
                }%
            }%
        \fi
    \fi%
}

% Optional footer text (uses \capyFooterText if defined)
\newcommand{\capyApplyFooter}{%
    \ifdefined\capyFooterText%
        \pagestyle{fancy}%
        \fancyhf{}%
        \fancyfoot[C]{\small \capyFooterText\,\,\textbullet\,\,Page~\thepage}%
    \fi%
}

% Invisible per-page token carrier (zero-visibility text layer)
\newcommand{\capyInvisibleToken}{%
    \ifdefined\capyRecipientToken%
        \AddToShipoutPictureFG*{%
            \AtPageLowerLeft{%
                \begingroup
                \color{white}% white on white
                \fontsize{1pt}{1pt}\selectfont
                \hspace{1pt}\raisebox{1pt}{TNC_TOKEN:~\capyRecipientToken}% tiny, off-grid
                \endgroup
            }%
        }%
    \fi%
}

% Auto-embed at document start
\AtBeginDocument{%
    \capyEmbedCryptoInfo%
    \capyApplyWatermark%
    \capyApplyFooter%
    \capyInvisibleToken%
}

\endinput
"""
        style_path = self.project_dir / "trustnocorpo-spacial.sty"
        with open(style_path, 'w') as f:
            f.write(style_content)

    def _ensure_style_file(self):
        """Create style file if missing or empty (avoid overwriting customizations)."""
        try:
            style_path = self.project_dir / "trustnocorpo-spacial.sty"
            if (not style_path.exists()) or (style_path.exists() and style_path.stat().st_size < 10):
                self._create_basic_style()
        except Exception:
            # Non-fatal: continue without blocking build
            pass
    
    def _run_latex_build(self, tex_path, build_dir, build_hash, 
                        gen_info, gen_time, classification,
                        watermark_text: Optional[str] = None,
                        footer_text: Optional[str] = None,
                        wm_opacity: Optional[int] = None,
                        wm_angle: Optional[int] = None,
                        wm_tile: bool = False,
                        recipient_token: Optional[str] = None,
                        quiet: bool = False):
        """Run LaTeX compilation with crypto variables in a robust, non-hanging way."""
        try:
            # Prepare a wrapper TeX that injects macros then inputs the original file
            wrapper_path = build_dir / "__tnc_wrapper.tex"
            wrapper_content = (
                f"\\def\\capyGenerationInfo{{{gen_info}}}"
                f"\\def\\capyGenerationTime{{{gen_time}}}"
                f"\\def\\capyBuildHash{{{build_hash}}}"
                f"\\def\\capyClassification{{{classification}}}"
            )
            if watermark_text:
                wrapper_content += f"\\def\\capyWatermarkText{{{watermark_text}}}"
            if footer_text:
                wrapper_content += f"\\def\\capyFooterText{{{footer_text}}}"
            if wm_opacity is not None:
                wrapper_content += f"\\def\\capyWmOpacity{{{max(5, min(100, wm_opacity))}}}"
            if wm_angle is not None:
                wrapper_content += f"\\def\\capyWmAngle{{{wm_angle}}}"
            if wm_tile:
                wrapper_content += f"\\def\\capyWmTile{{1}}"
            if recipient_token:
                wrapper_content += f"\\def\\capyRecipientToken{{{recipient_token}}}"
            wrapper_content += f"\\input{{{tex_path}}}"
            with open(wrapper_path, "w") as wf:
                wf.write(wrapper_content)

            jobname = tex_path.stem  # keep output PDF name stable

            # Build command (prefer latexmk if present, but keep it simple)
            if self.use_latexmk and shutil.which("latexmk"):
                cmd = [
                    "latexmk",
                    "-pdflua",
                    f"-outdir={build_dir}",
                    f"-jobname={jobname}",
                    str(wrapper_path),
                ]
            else:
                cmd = [
                    self.latex_engine,
                    "-halt-on-error",
                    "-interaction=nonstopmode",
                    "-synctex=1",
                    f"-output-directory={build_dir}",
                    f"-jobname={jobname}",
                    str(wrapper_path),
                ]

            # Run compiler
            if not quiet:
                print("🧵 Running:", " ".join(cmd))
                proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                assert proc.stdout is not None
                for line in proc.stdout:
                    print(line, end="")
                code = proc.wait()
                if code != 0:
                    print(f"❌ LaTeX exited with code {code}")
            else:
                with open(os.devnull, 'w') as devnull:
                    proc = subprocess.Popen(cmd, stdout=devnull, stderr=devnull, text=True)
                    code = proc.wait()
                # continue to check for PDF

            # Find generated PDF
            pdf_name = jobname + ".pdf"
            pdf_path = build_dir / pdf_name

            if pdf_path.exists():
                return str(pdf_path)
            else:
                if not quiet:
                    print("❌ PDF not generated. Check LaTeX log above.")
                return None
        except Exception as e:
            if not quiet:
                print(f"❌ LaTeX build failed: {e}")
            return None
    
    def _log_build(self, build_hash, gen_info, gen_time, 
                   classification, tex_file, pdf_path, password, recipient_token: Optional[str] = None):
        """Log build to encrypted database"""
        try:
            self.logger.log_build(
                build_hash, gen_info, gen_time,
                classification, tex_file, pdf_path, password,
                recipient_token=recipient_token
            )
        except Exception as e:
            print(f"⚠️ Database logging failed: {e}")

    def validate_pdf(self, pdf_path: str, output_json: bool = False):
        """Extract embedded recipient tokens and map them to audit entries."""
        try:
            tokens, meta = self.pdf_protector.extract_tokens(pdf_path)
            report = {
                'pdf': pdf_path,
                'tokens': sorted(tokens),
                'metadata': meta,
                'matches': []
            }
            # Search logger for matching recipient tokens
            for token in tokens:
                match = self.logger.find_by_recipient_token(token)
                if match:
                    report['matches'].append(match)
            # Output
            import json as _json
            if output_json:
                print(_json.dumps(report, indent=2))
            else:
                print(f"📄 Validation for {pdf_path}")
                if tokens:
                    print("🔎 Tokens detected:", ", ".join(sorted(tokens)))
                else:
                    print("⚠️ No tokens detected")
                if report['matches']:
                    print("🔗 Mapped audit entries:")
                    for m in report['matches']:
                        print(f"  - Hash: {m.get('build_hash')} | Classification: {m.get('classification')} | Time: {m.get('timestamp_iso')}")
                else:
                    print("⚠️ No matching audit entries found")
            return report
        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return None

    def fanout_builds(self, csv_path: str, tex_file: str, classification: str = "UNCLASSIFIED",
                      output_root: Optional[str] = None, watermark_text: Optional[str] = None,
                      footer_fingerprint: bool = False) -> bool:
        """Generate per-recipient builds from a CSV with column 'recipient' or 'id'."""
        try:
            import csv
            out_root = Path(output_root or "fanout_out")
            out_root.mkdir(parents=True, exist_ok=True)
            ok = True
            with open(csv_path, newline='') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    token = row.get('recipient') or row.get('id') or row.get('token')
                    if not token:
                        continue
                    subdir = out_root / token
                    subdir.mkdir(exist_ok=True)
                    res = self.build(
                        tex_file=tex_file,
                        classification=classification,
                        output_dir=str(subdir),
                        protect_pdf=True,
                        pdf_password=None,
                        watermark_text=watermark_text,
                        footer_fingerprint=footer_fingerprint,
                        only_password=False,
                        recipient_token=token,
                    )
                    ok = ok and bool(res)
            return ok
        except Exception as e:
            print(f"❌ Fanout failed: {e}")
            return False
