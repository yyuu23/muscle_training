"""
Test validation utilities
"""


from app.utils.validation import validate_display_name, validate_password, validate_username


class TestUsernameValidation:
    """Test username validation"""

    def test_valid_username(self):
        """Test valid usernames"""
        valid, error = validate_username("testuser")
        assert valid is True
        assert error is None

        valid, error = validate_username("test_user")
        assert valid is True

        valid, error = validate_username("test-user")
        assert valid is True

        valid, error = validate_username("用户123")
        assert valid is True

    def test_username_too_short(self):
        """Test username too short"""
        valid, error = validate_username("ab")
        assert valid is False
        assert "at least 3 characters" in error

    def test_username_too_long(self):
        """Test username too long"""
        valid, error = validate_username("a" * 51)
        assert valid is False
        assert "at most 50 characters" in error

    def test_username_invalid_characters(self):
        """Test username with invalid characters"""
        valid, error = validate_username("test@user")
        assert valid is False
        assert "letters, numbers, underscores, hyphens, and Chinese characters" in error


class TestPasswordValidation:
    """Test password validation"""

    def test_valid_password(self):
        """Test valid passwords"""
        valid, error = validate_password("SecurePassword123!")
        assert valid is True
        assert error is None

    def test_password_too_short(self):
        """Test password too short"""
        valid, error = validate_password("Short1!")
        assert valid is False
        assert "at least 12 characters" in error

    def test_password_too_long(self):
        """Test password too long"""
        valid, error = validate_password("a" * 129)
        assert valid is False
        assert "at most 128 characters" in error


class TestDisplayNameValidation:
    """Test display name validation"""

    def test_valid_display_name(self):
        """Test valid display names"""
        valid, error = validate_display_name("Test User")
        assert valid is True
        assert error is None

        valid, error = validate_display_name("测试用户")
        assert valid is True

    def test_display_name_empty(self):
        """Test empty display name"""
        valid, error = validate_display_name("")
        assert valid is False
        assert "required" in error

    def test_display_name_too_long(self):
        """Test display name too long"""
        valid, error = validate_display_name("a" * 101)
        assert valid is False
        assert "at most 100 characters" in error
