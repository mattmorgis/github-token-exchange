from typing import Any

import jwt
from jwt import PyJWKClient

from .config import Config

# GitHub OIDC token issuer and JWKS endpoint
GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_JWKS_URI = "https://token.actions.githubusercontent.com/.well-known/jwks"


class InvalidOIDCTokenError(Exception):
    """Raised when OIDC token validation fails."""

    pass


class TokenExpiredError(InvalidOIDCTokenError):
    """Raised when OIDC token has expired."""

    pass


class InvalidAudienceError(InvalidOIDCTokenError):
    """Raised when OIDC token has invalid audience."""

    pass


class InvalidIssuerError(InvalidOIDCTokenError):
    """Raised when OIDC token has invalid issuer."""

    pass


def validate_oidc_token(token: str, config: Config) -> dict[str, Any]:
    """
    Validate GitHub OIDC token and return payload.

    Args:
        token: The OIDC token to validate
        config: Configuration containing expected audience

    Returns:
        Decoded token payload

    Raises:
        TokenExpiredError: Token has expired
        InvalidAudienceError: Token audience doesn't match expected
        InvalidIssuerError: Token issuer is not GitHub
        InvalidOIDCTokenError: Token is malformed or invalid
    """
    try:
        # Create a JWKS client to fetch GitHub's public keys
        jwks_client = PyJWKClient(GITHUB_JWKS_URI)

        # Get the signing key from the token
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        # Decode and validate the token
        payload: dict[str, Any] = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=config.allowed_audience,
            issuer=GITHUB_OIDC_ISSUER,
            options={"verify_exp": True},
        )

        return payload

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("OIDC token has expired")
    except jwt.InvalidAudienceError:
        raise InvalidAudienceError(
            f"Invalid OIDC token audience. Expected: {config.allowed_audience}"
        )
    except jwt.InvalidIssuerError:
        raise InvalidIssuerError(
            f"Invalid OIDC token issuer. Expected: {GITHUB_OIDC_ISSUER}"
        )
    except jwt.InvalidTokenError as e:
        raise InvalidOIDCTokenError(f"Invalid OIDC token: {str(e)}")
    except Exception as e:
        raise InvalidOIDCTokenError(f"Failed to validate OIDC token: {str(e)}")
