import os
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from jwt import PyJWKClient
from pydantic import BaseModel

load_dotenv()

# GitHub OIDC token issuer and JWKS endpoint
GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
GITHUB_JWKS_URI = "https://token.actions.githubusercontent.com/.well-known/jwks"

# Get GitHub App configuration from environment
client_id = os.getenv("GITHUB_APP_CLIENT_ID")
private_key = os.getenv("GITHUB_APP_PRIVATE_KEY")
expected_audience = os.getenv("EXPECTED_AUDIENCE")


class TokenExchangeRequest(BaseModel):
    oidc_token: str


class TokenExchangeResponse(BaseModel):
    token: str


app = FastAPI(
    title="GitHub App Token Exchange",
    description="Secure token exchange service: Convert GitHub Actions OIDC tokens to GitHub App access tokens",
)


@app.post("/github/github-app-token-exchange")
async def exchange_token(request: TokenExchangeRequest) -> TokenExchangeResponse:
    try:
        # Create a JWKS client to fetch GitHub's public keys
        jwks_client = PyJWKClient(GITHUB_JWKS_URI)

        # Get the signing key from the token
        signing_key = jwks_client.get_signing_key_from_jwt(request.oidc_token)

        # Decode and validate the token
        payload = jwt.decode(
            request.oidc_token,
            signing_key.key,
            algorithms=["RS256"],
            audience=expected_audience,
            issuer=GITHUB_OIDC_ISSUER,
            options={"verify_exp": True},
        )

        # Extract relevant claims from the token
        repository = payload.get("repository")
        repository_owner = payload.get("repository_owner")

        if not client_id or not private_key:
            raise HTTPException(
                status_code=500, detail="GitHub App configuration missing"
            )

        # Check if the app is installed in the repository
        installation_id = await get_installation_id(
            client_id, private_key, repository_owner, repository
        )

        if not installation_id:
            raise HTTPException(
                status_code=403,
                detail=f"GitHub App is not installed in {repository_owner}/{repository}",
            )

        # Generate installation access token
        installation_token = await create_installation_access_token(
            client_id, private_key, installation_id
        )

        return TokenExchangeResponse(token=installation_token)

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid audience")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid issuer")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Token validation failed: {str(e)}"
        )


async def create_jwt(client_id: str, private_key: str) -> str:
    """Create a JWT for GitHub App authentication."""
    # JWT expires in 10 minutes (GitHub's maximum)
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=10)

    payload = {
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
        "iss": client_id,
    }

    # Ensure private key has proper line endings
    if not private_key.startswith("-----BEGIN RSA PRIVATE KEY-----"):
        private_key = f"-----BEGIN RSA PRIVATE KEY-----\n{private_key}\n-----END RSA PRIVATE KEY-----"

    return jwt.encode(payload, private_key, algorithm="RS256")


async def get_installation_id(
    client_id: str, private_key: str, owner: str, repo: str
) -> int | None:
    """Get the installation ID for a GitHub App in a specific repository."""
    # Create JWT for authentication
    jwt_token = await create_jwt(client_id, private_key)

    async with httpx.AsyncClient() as client:
        # Check if app is installed in the repository
        response = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/installation",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code == 200:
            data = response.json()
            return int(data["id"])
        elif response.status_code == 404:
            return None
        else:
            raise Exception(
                f"Failed to check installation: {response.status_code} - {response.text}"
            )


async def create_installation_access_token(
    client_id: str, private_key: str, installation_id: int
) -> str:
    """Create an installation access token for the GitHub App."""
    # Create JWT for authentication
    jwt_token = await create_jwt(client_id, private_key)

    async with httpx.AsyncClient() as client:
        # Create installation access token
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            },
            json={
                # Token expires in 1 hour (default)
                # You can add permissions and repositories here if needed
            },
        )

        if response.status_code == 201:
            data = response.json()
            return str(data["token"])
        else:
            raise Exception(
                f"Failed to create installation token: {response.status_code} - {response.text}"
            )
