import httpx
import jwt
from fastapi import FastAPI, HTTPException
from jwt import PyJWKClient
from pydantic import BaseModel


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
    # GitHub OIDC token issuer and JWKS endpoint
    GITHUB_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
    GITHUB_JWKS_URI = "https://token.actions.githubusercontent.com/.well-known/jwks"
    EXPECTED_AUDIENCE = "my-github-app"

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
            audience=EXPECTED_AUDIENCE,
            issuer=GITHUB_OIDC_ISSUER,
            options={"verify_exp": True},
        )

        # Extract relevant claims from the token
        repository = payload.get("repository")
        repository_owner = payload.get("repository_owner")
        actor = payload.get("actor")
        workflow = payload.get("workflow")

        # TODO: Exchange for GitHub App installation token
        # For now, return a test token
        return TokenExchangeResponse(token=f"exchanged-token-for-{repository}")

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
