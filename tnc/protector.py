"""
trustnocorpo PDF Protection Module
============================
Simplified PDF password protection for the standalone package.
"""

import os
import hashlib
from pathlib import Path
from typing import Optional

# Prefer pypdf; fall back to PyPDF2 if unavailable
try:
    from pypdf import PdfReader as _PdfReader, PdfWriter as _PdfWriter
    _PDF_BACKEND = "pypdf"
except Exception:
    try:
        import PyPDF2 as _PyPDF2
        _PdfReader = _PyPDF2.PdfReader  # type: ignore[attr-defined]
        _PdfWriter = _PyPDF2.PdfWriter  # type: ignore[attr-defined]
        _PDF_BACKEND = "PyPDF2"
    except Exception:
        _PdfReader = None  # type: ignore[assignment]
        _PdfWriter = None  # type: ignore[assignment]
        _PDF_BACKEND = None


class PDFProtector:
    """
    Simplified PDF password protection.
    
    Provides automatic password generation and PDF protection capabilities.
    """
    
    def __init__(self):
        """Initialize PDF protector"""
        pass
    
    def protect_pdf(self, 
                   pdf_path: str, 
                   password: Optional[str] = None,
                   build_hash: str = "",
                   classification: str = "",
                   auto_password: bool = True,
                   quiet: bool = False) -> Optional[str]:
        """
        Protect a PDF with password.
        
        Args:
            pdf_path: Path to PDF file
            password: Custom password (auto-generated if None)
            build_hash: Build hash for password generation
            classification: Document classification
            auto_password: Whether to auto-generate password
            
        Returns:
            Path to protected PDF (string) or None if failed
        """
        if not _PDF_BACKEND:
            if not quiet:
                print("⚠️ PDF backend not available. Install with: pip install pypdf")
            return pdf_path
        
        try:
            pdf_path = Path(pdf_path)
            if not pdf_path.exists():
                if not quiet:
                    print(f"❌ PDF not found: {pdf_path}")
                return None
            
            # Generate password if needed
            if not password and auto_password:
                password = self._generate_context_password(build_hash, classification)
                if not quiet:
                    print(f"🔑 Auto-generated password: {password}")
            
            if not password:
                if not quiet:
                    print("❌ No password provided")
                return None
            
            # Create protected PDF
            protected_path = pdf_path.parent / f"{pdf_path.stem}_protected.pdf"
            
            with open(pdf_path, 'rb') as input_file:
                reader = _PdfReader(input_file)  # type: ignore[misc]
                writer = _PdfWriter()  # type: ignore[misc]
                
                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)
                
                # Encrypt with password
                # For both pypdf and PyPDF2, encrypt(user_password) is supported
                writer.encrypt(password)  # type: ignore[attr-defined]
                
                # Write protected PDF
                with open(protected_path, 'wb') as output_file:
                    writer.write(output_file)
            
            if not quiet:
                print(f"✅ PDF protected: {protected_path}")
            return str(protected_path)
            
        except Exception as e:
            if not quiet:
                print(f"❌ PDF protection failed: {e}")
            return None
    
    def unprotect_pdf(self, 
                     protected_path: str, 
                     password: Optional[str] = None,
                     build_hash: str = "",
                     quiet: bool = False) -> Optional[str]:
        """
        Unprotect a password-protected PDF.
        
        Args:
            protected_path: Path to protected PDF
            password: Password (auto-derived if None)
            build_hash: Build hash for password derivation
            
        Returns:
            Path to unprotected PDF or None if failed
        """
        if not _PDF_BACKEND:
            if not quiet:
                print("⚠️ PDF backend not available")
            return None
        
        try:
            protected_path = Path(protected_path)
            if not protected_path.exists():
                if not quiet:
                    print(f"❌ Protected PDF not found: {protected_path}")
                return None
            
            # Try to derive password if not provided
            if not password and build_hash:
                password = self._generate_context_password(build_hash, "")
                if not quiet:
                    print(f"🔑 Using derived password: {password}")
            
            if not password:
                if not quiet:
                    print("❌ No password provided for unprotection")
                return None
            
            # Create unprotected PDF
            unprotected_path = protected_path.parent / f"{protected_path.stem.replace('_protected', '')}_unprotected.pdf"
            
            with open(protected_path, 'rb') as input_file:
                reader = _PdfReader(input_file)  # type: ignore[misc]
                
                # Decrypt with password
                if getattr(reader, "is_encrypted", False):
                    res = reader.decrypt(password)  # type: ignore[attr-defined]
                    # PyPDF2 returns 0/1; pypdf may return an int or raise
                    if isinstance(res, int) and res == 0:
                        if not quiet:
                            print("❌ Incorrect password")
                        return None
                
                writer = _PdfWriter()  # type: ignore[misc]
                
                # Copy all pages
                for page in reader.pages:
                    writer.add_page(page)
                
                # Write unprotected PDF
                with open(unprotected_path, 'wb') as output_file:
                    writer.write(output_file)
            
            if not quiet:
                print(f"✅ PDF unprotected: {unprotected_path}")
            return str(unprotected_path)
            
        except Exception as e:
            if not quiet:
                print(f"❌ PDF unprotection failed: {e}")
            return None
    
    def _generate_context_password(self, build_hash: str, classification: str) -> str:
        """
        Generate context-aware password.
        
        Args:
            build_hash: Build hash
            classification: Document classification
            
        Returns:
            Generated password
        """
        # Create context string
        context = f"trustnocorpo-{build_hash}-{classification}".lower()
        
        # Generate hash
        hash_obj = hashlib.sha256(context.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Format as readable password (tnc-prefixed)
        password = f"tnc-{hash_hex[:4]}-{hash_hex[4:8]}-{hash_hex[8:12]}"
        
        return password
    
    def check_pdf_protection(self, pdf_path: str) -> bool:
        """
        Check if a PDF is password protected.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            True if protected, False otherwise
        """
        if not _PDF_BACKEND:
            return False
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = _PdfReader(file)  # type: ignore[misc]
                return bool(getattr(reader, "is_encrypted", False))
        except Exception:
            return False

    def extract_tokens(self, pdf_path: str):
        """
        Extract embedded recipient tokens from a PDF.

        Sources scanned:
        - PDF metadata (keywords, subject)
        - XMP metadata (if available via reader.metadata)
        - Page text for invisible carrier strings like 'TNC_TOKEN: <token>'

        Returns:
            (set[str], dict) -> (tokens, metadata summary)
        """
        tokens = set()
        meta_summary = {}
        if not _PDF_BACKEND:
            return tokens, meta_summary

        try:
            with open(pdf_path, 'rb') as f:
                reader = _PdfReader(f)  # type: ignore[misc]

                # Basic document info
                info = getattr(reader, 'metadata', None) or {}
                # pypdf returns DocumentInformation-like mapping
                md = {}
                try:
                    for k in ("/Title", "/Author", "/Subject", "/Keywords"):
                        if hasattr(info, 'get'):
                            v = info.get(k)
                        else:
                            v = getattr(info, k[1:], None)
                        if v:
                            md[k] = str(v)
                except Exception:
                    pass
                meta_summary.update(md)

                # Parse keywords/subject for token markers
                for field in (md.get("/Keywords", ""), md.get("/Subject", "")):
                    if not field:
                        continue
                    for part in str(field).replace(";", ",").split(","):
                        part = part.strip()
                        if part.lower().startswith("tnc-token-"):
                            tokens.add(part.split("tnc-token-")[-1])

                # Scan pages for invisible carrier
                try:
                    for page in reader.pages:
                        try:
                            text = page.extract_text() or ""
                        except Exception:
                            text = ""
                        if "TNC_TOKEN:" in text:
                            # naive parse
                            for frag in text.split("TNC_TOKEN:"):
                                frag = frag.strip()
                                if not frag:
                                    continue
                                token = frag.split()[0]
                                if token:
                                    tokens.add(token.replace("~", "").strip())
                except Exception:
                    pass

            return tokens, meta_summary
        except Exception:
            return tokens, meta_summary
