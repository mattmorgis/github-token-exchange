from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .auth import (
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidOIDCTokenError,
    TokenExpiredError,
    validate_oidc_token,
)
from .config import Config
from .github import (
    GitHubAPIError,
    GitHubAppNotInstalledError,
    InstallationTokenError,
    create_installation_access_token,
    get_installation_id,
)


class TokenExchangeRequest(BaseModel):
    oidc_token: str


class TokenExchangeResponse(BaseModel):
    token: str


load_dotenv()

app = FastAPI(
    title="GitHub App Token Exchange",
    description="Secure token exchange service: Convert GitHub Actions OIDC tokens to GitHub App access tokens",
)


@app.post("/github/github-app-token-exchange")
async def exchange_token(request: TokenExchangeRequest) -> TokenExchangeResponse:
    """
    Exchange a GitHub Actions OIDC token for a GitHub App installation access token.

    The process:
    1. Validate the OIDC token from GitHub Actions
    2. Extract repository information from the token
    3. Check if the GitHub App is installed in that repository
    4. Generate an installation access token

    Returns:
        TokenExchangeResponse with the access token

    Raises:
        400: Configuration errors
        401: Token validation errors
        403: GitHub App not installed
        500: Internal server errors
    """
    try:
        # Load configuration
        config = Config.from_env()

        # Validate the OIDC token
        payload = await validate_oidc_token(request.oidc_token, config)

        # Extract repository information
        repository = payload.get("repository")

        if not repository:
            raise InvalidOIDCTokenError(
                "OIDC token missing required repository information"
            )

        print(f"DEBUG: Successfully verified token for {repository}")

        # Check if the app is installed in the repository
        installation_id = await get_installation_id(repository, config)

        # Generate installation access token
        installation_token = await create_installation_access_token(
            installation_id, config
        )

        return TokenExchangeResponse(token=installation_token)

    except ValueError as e:
        # Configuration errors
        raise HTTPException(status_code=500, detail=str(e))
    except TokenExpiredError as e:
        print(f"DEBUG: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except (InvalidAudienceError, InvalidIssuerError, InvalidOIDCTokenError) as e:
        print(f"DEBUG: {e}")
        raise HTTPException(status_code=401, detail=str(e))
    except GitHubAppNotInstalledError as e:
        print(f"DEBUG: {e}")
        raise HTTPException(
            status_code=403,
            detail=str(e),
        )
    except (GitHubAPIError, InstallationTokenError) as e:
        print(f"DEBUG: GitHub API error: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to communicate with GitHub API"
        )
    except Exception as e:
        print(f"DEBUG: Unexpected error: {e}")
        # Don't expose internal errors to users - log them but return generic message
        raise HTTPException(
            status_code=500,
            detail="Internal server error occurred during token exchange",
        )
