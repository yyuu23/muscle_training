"""
Test password utilities
"""


from app.utils.password import hash_password, needs_rehash, verify_password


def test_hash_password():
    """Test password hashing"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$argon2id$")


def test_verify_password_correct():
    """Test password verification with correct password"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_incorrect():
    """Test password verification with incorrect password"""
    password = "SecurePassword123!"
    wrong_password = "WrongPassword123!"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


def test_needs_rehash():
    """Test if password hash needs rehashing"""
    password = "SecurePassword123!"
    hashed = hash_password(password)

    # Fresh hash should not need rehashing
    assert needs_rehash(hashed) is False
