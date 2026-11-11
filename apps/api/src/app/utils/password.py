"""
Password hashing utilities using Argon2id
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

# Initialize Argon2 hasher with secure defaults
ph = PasswordHasher(
    time_cost=2,  # Number of iterations
    memory_cost=65536,  # Memory usage in KiB (64 MB)
    parallelism=1,  # Number of parallel threads
    hash_len=32,  # Length of the hash in bytes
    salt_len=16,  # Length of random salt in bytes
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id

    Args:
        password: Plain text password (12-128 characters)

    Returns:
        Hashed password string
    """
    return ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash

    Args:
        password: Plain text password to verify
        password_hash: Stored password hash

    Returns:
        True if password matches, False otherwise
    """
    try:
        ph.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """
    Check if a password hash needs to be updated

    Args:
        password_hash: Stored password hash

    Returns:
        True if hash should be regenerated with new parameters
    """
    return ph.check_needs_rehash(password_hash)
