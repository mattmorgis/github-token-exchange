from fastapi import FastAPI
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
    return TokenExchangeResponse(token="test")
