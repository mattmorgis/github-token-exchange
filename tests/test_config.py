import os
from unittest.mock import patch

import pytest

from app.config import Config


def test_config_from_env_success() -> None:
    """Should create config when all env vars present"""
    with patch.dict(
        os.environ,
        {
            "GITHUB_APP_NAME": "test_name",
            "GITHUB_APP_CLIENT_ID": "test_id",
            "GITHUB_APP_PRIVATE_KEY": "test_key",
            "ALLOWED_AUDIENCE": "test_aud",
        },
    ):
        config = Config.from_env()
        assert config.github_app_client_id == "test_id"


def test_config_from_env_missing_vars() -> None:
    """Should raise ValueError when env vars missing"""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing required environment variables"):
            Config.from_env()
