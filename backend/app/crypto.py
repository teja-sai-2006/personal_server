import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from argon2.low_level import hash_secret_raw, Type

# We use Argon2id for key derivation
# Parameters optimized for good security while remaining responsive
ARGON2_TIME_COST = 2
ARGON2_MEMORY_COST = 65536
ARGON2_PARALLELISM = 4
HASH_LEN = 32

def generate_random_key(length=32) -> bytes:
    """Generate a secure random key (256-bit by default)."""
    return os.urandom(length)

def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit key from a password using Argon2id."""
    return hash_secret_raw(
        secret=password.encode('utf-8'),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=HASH_LEN,
        type=Type.ID
    )

def encrypt_umk(umk: bytes, password: str) -> str:
    """Encrypt the User Master Key (UMK) using a key derived from the user's password."""
    salt = os.urandom(16)
    derived_key = derive_key_from_password(password, salt)
    
    aesgcm = AESGCM(derived_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, umk, None)
    
    # Pack into: salt (16) + nonce (12) + ciphertext (48) -> 76 bytes
    packed = salt + nonce + ciphertext
    return base64.b64encode(packed).decode('ascii')

def decrypt_emk(emk_b64: str, password: str) -> bytes:
    """Decrypt the Encrypted Master Key (EMK) to recover the UMK."""
    packed = base64.b64decode(emk_b64)
    if len(packed) < 28:
        raise ValueError("Invalid EMK format")
        
    salt = packed[:16]
    nonce = packed[16:28]
    ciphertext = packed[28:]
    
    derived_key = derive_key_from_password(password, salt)
    aesgcm = AESGCM(derived_key)
    
    try:
        umk = aesgcm.decrypt(nonce, ciphertext, None)
        return umk
    except InvalidTag:
        raise ValueError("Invalid password or corrupt EMK")

import secrets

def generate_recovery_code(emk_b64: str = None) -> str:
    """Generate a highly secure random recovery code (True Data Recovery)."""
    return secrets.token_urlsafe(24)

def hash_recovery_code(recovery_code: str) -> str:
    """Hash the recovery code for secure database storage."""
    hasher = hashlib.sha256()
    hasher.update(recovery_code.encode('utf-8'))
    hasher.update(b'RECOVERY_SALT')
    return hasher.hexdigest()

def encrypt_file_data(data: bytes, key: bytes) -> bytes:
    """Encrypt raw file data using AES-256-GCM."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, data, None)
    return nonce + ciphertext

def decrypt_file_data(encrypted_data: bytes, key: bytes) -> bytes:
    """Decrypt raw file data using AES-256-GCM."""
    nonce = encrypted_data[:12]
    ciphertext = encrypted_data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
