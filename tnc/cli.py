"""
trustnocorpo Command Line Interface
=============================
Main CLI entry point for the trustnocorpo standalone package.
"""

import argparse
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
        footer_fingerprint=args.footer_fingerprint,
        only_password=getattr(args, 'only_password', False),
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
        """
    )
    
    parser.add_argument(
        '--project-dir', '-d',
        help='Project directory (default: current directory)',
        default=None
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
    build_parser.add_argument('--footer-fingerprint', action='store_true',
                             help='Inject user fingerprint in the PDF footer')
    build_parser.add_argument('--only-password', action='store_true',
                             help='Suppress all output except the final password line')
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
    
    # Shorthand: if first arg looks like a .tex file, rewrite to 'build <tex>'
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0].lower().endswith('.tex'):
        raw_args = ['build'] + raw_args

    # Parse arguments
    args = parser.parse_args(raw_args)
    
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
