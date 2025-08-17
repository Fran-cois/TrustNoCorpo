"""
trustnocorpo Key Management Module
============================
Simplified user key management for the standalone package.
"""

import os
import json
import base64
import hashlib
import getpass
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet


class KeyManager:
    """
    Simplified key management for standalone trustnocorpo.
    
    Manages user RSA keys with master password protection.
    """
    
    def __init__(self):
        """Initialize key manager with standard paths"""
        self.keys_dir = Path.home() / ".trustnocorpo"
        self.keys_dir.mkdir(exist_ok=True)
        
        self.private_key_path = self.keys_dir / "user_private.pem"
        self.public_key_path = self.keys_dir / "user_public.pem"
        self.info_path = self.keys_dir / "user_info.json"
    
    def user_has_keys(self) -> bool:
        """Check if user keys exist"""
        return (self.private_key_path.exists() and 
                self.public_key_path.exists() and
                self.info_path.exists())
    
    def generate_user_keys(self, username: str, master_password: str) -> bool:
        """
        Generate RSA key pair for user.
        
        Args:
            username: User identifier
            master_password: Master password for key protection
            
        Returns:
            True if successful, False otherwise
        """
        try:
            print("🔐 Generating RSA-4096 key pair...")
            
            # Generate RSA key pair
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=4096
            )
            public_key = private_key.public_key()
            
            # Serialize private key with master password
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(
                    master_password.encode()
                )
            )
            
            # Serialize public key
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            # Save keys
            with open(self.private_key_path, 'wb') as f:
                f.write(private_pem)
                
            with open(self.public_key_path, 'wb') as f:
                f.write(public_pem)
            
            # Save user info
            user_info = {
                'username': username,
                'created_at': datetime.now().isoformat(),
                'fingerprint': self._generate_fingerprint(public_pem),
                'key_file': str(self.private_key_path)
            }
            
            with open(self.info_path, 'w') as f:
                json.dump(user_info, f, indent=2)
            
            print(f"✅ Keys generated successfully")
            print(f"📁 Stored in: {self.keys_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ Key generation failed: {e}")
            return False
    
    def load_private_key(self, master_password: str):
        """Load private key with master password"""
        try:
            with open(self.private_key_path, 'rb') as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=master_password.encode()
                )
            return private_key
        except Exception:
            return None
    
    def load_public_key(self):
        """Load public key"""
        try:
            with open(self.public_key_path, 'rb') as f:
                public_key = serialization.load_pem_public_key(f.read())
            return public_key
        except Exception:
            return None
    
    def encrypt_data(self, data: str, master_password: str) -> Optional[str]:
        """
        Encrypt data using hybrid RSA+AES encryption.
        
        Args:
            data: Data to encrypt
            master_password: Master password for key access
            
        Returns:
            Base64-encoded encrypted data or None if failed
        """
        try:
            private_key = self.load_private_key(master_password)
            if not private_key:
                return None
                
            public_key = private_key.public_key()
            
            # Generate AES key
            aes_key = Fernet.generate_key()
            f = Fernet(aes_key)
            
            # Encrypt data with AES
            encrypted_data = f.encrypt(data.encode())
            
            # Encrypt AES key with RSA
            encrypted_aes_key = public_key.encrypt(
                aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Combine and encode
            combined = {
                'encrypted_key': base64.b64encode(encrypted_aes_key).decode(),
                'encrypted_data': base64.b64encode(encrypted_data).decode()
            }
            
            return base64.b64encode(json.dumps(combined).encode()).decode()
            
        except Exception as e:
            print(f"❌ Encryption failed: {e}")
            return None
    
    def decrypt_data(self, encrypted_data: str, master_password: str) -> Optional[str]:
        """
        Decrypt data using hybrid RSA+AES decryption.
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            master_password: Master password for key access
            
        Returns:
            Decrypted data or None if failed
        """
        try:
            private_key = self.load_private_key(master_password)
            if not private_key:
                return None
            
            # Decode and parse
            combined = json.loads(base64.b64decode(encrypted_data).decode())
            encrypted_aes_key = base64.b64decode(combined['encrypted_key'])
            encrypted_content = base64.b64decode(combined['encrypted_data'])
            
            # Decrypt AES key with RSA
            aes_key = private_key.decrypt(
                encrypted_aes_key,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            # Decrypt data with AES
            f = Fernet(aes_key)
            decrypted_data = f.decrypt(encrypted_content)
            
            return decrypted_data.decode()
            
        except Exception as e:
            print(f"❌ Decryption failed: {e}")
            return None
    
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get user information"""
        try:
            if not self.info_path.exists():
                return None
                
            with open(self.info_path, 'r') as f:
                return json.load(f)
                
        except Exception:
            return None
    
    def get_user_fingerprint(self) -> str:
        """Get user fingerprint"""
        info = self.get_user_info()
        return info.get('fingerprint', 'unknown') if info else 'unknown'
    
    def _generate_fingerprint(self, public_key_pem: bytes) -> str:
        """Generate fingerprint from public key"""
        fingerprint = hashlib.sha256(public_key_pem).digest()
        return base64.b64encode(fingerprint).decode()[:16]
    
    def reset_keys(self) -> bool:
        """Reset all user keys"""
        try:
            for path in [self.private_key_path, self.public_key_path, self.info_path]:
                if path.exists():
                    path.unlink()
            return True
        except Exception:
            return False
