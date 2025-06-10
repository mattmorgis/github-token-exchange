from typing import Generator
from unittest.mock import Mock, patch

import jwt
import pytest

from app.auth import (
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidOIDCTokenError,
    TokenExpiredError,
    validate_oidc_token,
)
from app.config import Config


@pytest.fixture
def config() -> Config:
    return Config(
        github_app_name="test_name",
        github_app_client_id="test_client_id",
        github_app_private_key="test_private_key",
        expected_audience="test_audience",
    )


@pytest.fixture
def mock_jwt_validation() -> Generator[Mock, None, None]:
    """Mock PyJWKClient and jwt.decode"""
    with (
        patch("app.auth.PyJWKClient") as mock_client,
        patch("app.auth.jwt.decode") as mock_decode,
    ):
        # Setup mock signing key
        mock_signing_key = Mock()
        mock_signing_key.key = "mock_public_key"
        mock_client.return_value.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )

        yield mock_decode


async def test_validate_oidc_token_success(
    config: Config, mock_jwt_validation: Mock
) -> None:
    """Should return payload when token is valid"""
    expected_payload = {"repository": "test-owner/test-repo"}
    mock_jwt_validation.return_value = expected_payload

    result = await validate_oidc_token("valid.token", config)

    assert result == expected_payload


async def test_validate_oidc_token_expired(
    config: Config, mock_jwt_validation: Mock
) -> None:
    """Should raise TokenExpiredError when token expired"""
    mock_jwt_validation.side_effect = jwt.ExpiredSignatureError("Token expired")

    with pytest.raises(TokenExpiredError, match="OIDC token has expired"):
        await validate_oidc_token("expired.token", config)


async def test_validate_oidc_token_wrong_audience(
    config: Config, mock_jwt_validation: Mock
) -> None:
    """Should raise InvalidAudienceError when audience doesn't match"""
    mock_jwt_validation.side_effect = jwt.InvalidAudienceError("Wrong audience")

    with pytest.raises(InvalidAudienceError, match="Invalid OIDC token audience"):
        await validate_oidc_token("wrong.audience.token", config)


async def test_validate_oidc_token_wrong_issuer(
    config: Config, mock_jwt_validation: Mock
) -> None:
    """Should raise InvalidIssuerError when issuer doesn't match"""
    mock_jwt_validation.side_effect = jwt.InvalidIssuerError("Wrong issuer")

    with pytest.raises(InvalidIssuerError, match="Invalid OIDC token issuer"):
        await validate_oidc_token("wrong.issuer.token", config)


async def test_validate_oidc_token_malformed(
    config: Config, mock_jwt_validation: Mock
) -> None:
    """Should raise InvalidOIDCTokenError when token is malformed"""
    mock_jwt_validation.side_effect = jwt.InvalidTokenError("Invalid token format")

    with pytest.raises(InvalidOIDCTokenError, match="Invalid OIDC token"):
        await validate_oidc_token("malformed.token", config)


async def test_validate_oidc_token_unexpected_error(
    config: Config, mock_jwt_validation: Mock
) -> None:
    """Should raise InvalidOIDCTokenError for unexpected errors"""
    mock_jwt_validation.side_effect = Exception("JWKS fetch failed")

    with pytest.raises(InvalidOIDCTokenError, match="Failed to validate OIDC token"):
        await validate_oidc_token("some.token", config)
