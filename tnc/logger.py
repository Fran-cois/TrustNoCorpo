"""
trustnocorpo Build Logger Module
===========================
Simplified encrypted build logging for the standalone package.
"""

import os
import json
import sqlite3
import hashlib
import base64
from pathlib import Path
import subprocess
import shutil
from datetime import datetime
from typing import Optional, List, Dict, Any

from cryptography.fernet import Fernet

from .keys import KeyManager


class BuildLogger:
    """
    Simplified encrypted build logging.
    
    Logs PDF builds to an encrypted SQLite database with user signatures.
    """
    
    def __init__(self, db_path: str = "builds.db"):
        """
        Initialize build logger.
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = Path(db_path)
        self.key_path = self.db_path.parent / f"{self.db_path.stem}.key"
        self.key_manager = KeyManager()
        
        # Initialize database
        self._init_encrypted_database()
    
    def _init_encrypted_database(self):
        """Initialize encrypted SQLite database"""
        try:
            # Generate or load database encryption key
            if not self.key_path.exists():
                db_key = Fernet.generate_key()
                with open(self.key_path, 'wb') as f:
                    f.write(db_key)
            else:
                with open(self.key_path, 'rb') as f:
                    db_key = f.read()
            
            self.fernet = Fernet(db_key)
            
            # Create database schema
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS encrypted_builds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    build_hash TEXT UNIQUE NOT NULL,
                    encrypted_data TEXT NOT NULL,
                    user_fingerprint TEXT NOT NULL,
                    user_signature TEXT NOT NULL,
                    timestamp_utc TEXT NOT NULL
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Database initialization failed: {e}")
    
    def log_build(self, 
                  build_hash: str,
                  generation_info: str,
                  generation_time: str,
                  classification: str,
                  main_file: str,
                  pdf_path: Optional[str] = None,
                  pdf_password: Optional[str] = None,
                  recipient_token: Optional[str] = None) -> Optional[int]:
        """
        Log a build to encrypted database.
        
        Args:
            build_hash: Unique build hash
            generation_info: Base64-encoded generation info
            generation_time: Base64-encoded generation time
            classification: Document classification
            main_file: Source LaTeX file
            pdf_path: Generated PDF path
            pdf_password: PDF password (if any)
            
        Returns:
            Build ID if successful, None otherwise
        """
        try:
            # Prepare build data
            build_data = {
                'build_hash': build_hash,
                'generation_info': generation_info,
                'generation_time': generation_time,
                'classification': classification,
                'main_file': main_file,
                'pdf_path': pdf_path,
                'pdf_password_hint': pdf_password[:8] + "..." if pdf_password else None,
                'user': os.environ.get('USER', 'unknown'),
                'timestamp_iso': datetime.now().isoformat(),
                'pdf_size': os.path.getsize(pdf_path) if pdf_path and os.path.exists(pdf_path) else 0,
                'recipient_token': recipient_token,
            }
            
            # Encrypt build data
            encrypted_token = self.fernet.encrypt(json.dumps(build_data).encode())
            # Store base64-encoded form in DB
            encrypted_data_b64 = base64.b64encode(encrypted_token).decode()

            # Generate user signature over the exact stored string
            user_fingerprint = self.key_manager.get_user_fingerprint()
            signature_data = f"{build_hash}{encrypted_data_b64}"
            user_signature = hashlib.sha256(signature_data.encode()).hexdigest()
            
            # Store in database
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO encrypted_builds
                (build_hash, encrypted_data, user_fingerprint, user_signature, timestamp_utc)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                build_hash,
                encrypted_data_b64,
                user_fingerprint,
                user_signature,
                datetime.utcnow().isoformat()
            ))
            
            build_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            print(f"✅ Build logged (ID: {build_id}, Hash: {build_hash})")
            print(f"🔑 User fingerprint: {user_fingerprint}")
            
            return build_id
            
        except Exception as e:
            print(f"❌ Build logging failed: {e}")
            return None
    
    def verify_build(self, build_hash: str) -> bool:
        """
        Verify a build's signature and data integrity.
        
        Args:
            build_hash: Build hash to verify
            
        Returns:
            True if verification succeeds, False otherwise
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT encrypted_data, user_signature, user_fingerprint
                FROM encrypted_builds WHERE build_hash = ?
            ''', (build_hash,))
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                print(f"❌ Build {build_hash} not found")
                return False
            
            encrypted_data, stored_signature, user_fingerprint = result
            
            # Verify signature
            signature_data = f"{build_hash}{encrypted_data}"
            expected_signature = hashlib.sha256(signature_data.encode()).hexdigest()
            
            if expected_signature != stored_signature:
                print(f"❌ Signature mismatch for build {build_hash}")
                return False
            
            # Try to decrypt data
            try:
                decrypted_data = self.fernet.decrypt(base64.b64decode(encrypted_data))
                build_data = json.loads(decrypted_data.decode())
                
                print(f"✅ Build {build_hash} verified successfully")
                print(f"   Classification: {build_data.get('classification', 'unknown')}")
                print(f"   User: {user_fingerprint}")
                
                return True
                
            except Exception as e:
                print(f"❌ Data decryption failed for build {build_hash}: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False
    
    def list_builds(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent builds from database.
        
        Args:
            limit: Maximum number of builds to return
            
        Returns:
            List of build records
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT build_hash, encrypted_data, user_fingerprint, timestamp_utc
                FROM encrypted_builds 
                ORDER BY timestamp_utc DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            builds = []
            for build_hash, encrypted_data, user_fingerprint, timestamp_utc in results:
                try:
                    # Decrypt build data
                    decrypted_data = self.fernet.decrypt(base64.b64decode(encrypted_data))
                    build_data = json.loads(decrypted_data.decode())
                    
                    builds.append({
                        'build_hash': build_hash,
                        'classification': build_data.get('classification', 'unknown'),
                        'main_file': build_data.get('main_file', 'unknown'),
                        'user_fingerprint': user_fingerprint,
                        'timestamp_iso': build_data.get('timestamp_iso', timestamp_utc),
                        'pdf_size': build_data.get('pdf_size', 0)
                    })
                    
                except Exception:
                    # Skip corrupted entries
                    continue
            
            return builds
            
        except Exception as e:
            print(f"❌ Failed to list builds: {e}")
            return []

    def find_by_recipient_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Return the most recent build that used the given recipient token."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute('''
                SELECT build_hash, encrypted_data, user_fingerprint, timestamp_utc
                FROM encrypted_builds 
                ORDER BY timestamp_utc DESC
            ''')
            rows = cursor.fetchall()
            conn.close()

            for build_hash, encrypted_data, user_fingerprint, timestamp_utc in rows:
                try:
                    decrypted_data = self.fernet.decrypt(base64.b64decode(encrypted_data))
                    build_data = json.loads(decrypted_data.decode())
                    if build_data.get('recipient_token') == token:
                        return {
                            'build_hash': build_hash,
                            'classification': build_data.get('classification', 'unknown'),
                            'timestamp_iso': build_data.get('timestamp_iso', timestamp_utc),
                            'user_fingerprint': user_fingerprint,
                            'main_file': build_data.get('main_file'),
                            'pdf_path': build_data.get('pdf_path'),
                        }
                except Exception:
                    continue
            return None
        except Exception:
            return None

    def export_signed(self, output_dir: str = ".", gpg_key: Optional[str] = None) -> Optional[str]:
        """
        Export decrypted build log entries into an evidence bundle and optionally GPG-sign it.

        Creates files:
        - builds.json: decrypted list of entries
        - builds.json.sha256: checksum
        - builds.json.asc: GPG detached signature (if gpg_key and gpg available)
        """
        try:
            outdir = Path(output_dir)
            outdir.mkdir(parents=True, exist_ok=True)

            # Gather all entries
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute('SELECT build_hash, encrypted_data, user_fingerprint, timestamp_utc FROM encrypted_builds ORDER BY timestamp_utc DESC')
            rows = cursor.fetchall()
            conn.close()

            entries: List[Dict[str, Any]] = []
            for build_hash, encrypted_data, user_fingerprint, timestamp_utc in rows:
                try:
                    decrypted_data = self.fernet.decrypt(base64.b64decode(encrypted_data))
                    build_data = json.loads(decrypted_data.decode())
                    build_data['build_hash'] = build_hash
                    build_data['user_fingerprint'] = user_fingerprint
                    entries.append(build_data)
                except Exception:
                    continue

            # Write JSON
            bundle_json = outdir / 'builds.json'
            with open(bundle_json, 'w') as f:
                json.dump(entries, f, indent=2)

            # Checksum
            import hashlib as _hashlib
            with open(bundle_json, 'rb') as f:
                sha = _hashlib.sha256(f.read()).hexdigest()
            with open(outdir / 'builds.json.sha256', 'w') as f:
                f.write(sha + "  builds.json\n")

            # Optional GPG sign
            if gpg_key and shutil.which('gpg'):
                asc_path = outdir / 'builds.json.asc'
                try:
                    subprocess.run([
                        'gpg', '--yes', '--armor', '--local-user', gpg_key,
                        '--output', str(asc_path), '--detach-sign', str(bundle_json)
                    ], check=True)
                except Exception as e:
                    print(f"⚠️ GPG signing failed: {e}")

            print(f"✅ Exported evidence bundle in {outdir}")
            return str(outdir)
        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None
    
    def get_user_builds_stats(self) -> Dict[str, Any]:
        """
        Get build statistics for current user.
        
        Returns:
            Dictionary with user build statistics
        """
        try:
            current_fingerprint = self.key_manager.get_user_fingerprint()
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # User builds count
            cursor.execute('''
                SELECT COUNT(*) FROM encrypted_builds 
                WHERE user_fingerprint = ?
            ''', (current_fingerprint,))
            user_builds = cursor.fetchone()[0]
            
            # Total builds count
            cursor.execute('SELECT COUNT(*) FROM encrypted_builds')
            total_builds = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'user_builds': user_builds,
                'total_builds': total_builds,
                'user_fingerprint': current_fingerprint
            }
            
        except Exception as e:
            print(f"❌ Failed to get stats: {e}")
            return {
                'user_builds': 0,
                'total_builds': 0,
                'user_fingerprint': 'unknown'
            }
