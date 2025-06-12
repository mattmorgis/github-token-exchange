# GitHub Token Exchange

A secure token exchange service that converts [GitHub Actions OIDC tokens](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect) into [GitHub App installation access tokens](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app). This enables GitHub Action workflows to authenticate as a GitHub App for repository operations like creating PRs, issues, and comments.

## Overview

GitHub Actions workflows can use OIDC tokens to authenticate with external services. This service converts those OIDC tokens into GitHub App access tokens, allowing workflows to act as a GitHub App without requiring the App's private key to be stored in the repository(s).

## How It Works

1. Receives an OIDC token from a GitHub Actions workflow
2. Validates the token with GitHub's public keys and an `aud` check
3. Creates a JWT signed with your app's private key and exchanges for an installation access token
4. Returns a short-lived access token to perform operations as the GitHub App

```mermaid
sequenceDiagram
    participant GHA as GitHub Actions
    participant TE as Token Exchange
    participant GitHub as GitHub API

    GHA->>TE: POST /exchange with OIDC token
    TE->>GitHub: Validate OIDC token
    GitHub-->>TE: Token claims (repo, org, etc.)
    TE->>GitHub: Get app installation for repo
    GitHub-->>TE: Installation ID
    TE->>TE: Create JWT with App private key
    TE->>GitHub: Exchange JWT for access token
    GitHub-->>TE: Installation access token
    TE-->>GHA: Return access token
    GHA->>GitHub: Use token for API calls
```

## Usage

### Quick Start

Run the token exchange service using Docker:

```bash
docker run -p 8080:8080 \
  -e ALLOWED_AUDIENCE="your-audience" \
  -e GITHUB_APP_NAME="Your App Name" \
  -e GITHUB_APP_CLIENT_ID="your-app-client-id" \
  -e GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
your-private-key-content
-----END RSA PRIVATE KEY-----" \
  ghcr.io/mattmorgis/github-token-exchange:latest
```

### Environment Variables

Set these environment variables (see `.env.example`):

- `ALLOWED_AUDIENCE`: The audience value your workflows will use in OIDC requests
- `GITHUB_APP_NAME`: Your GitHub App's name
- `GITHUB_APP_CLIENT_ID`: Your GitHub App's client ID
- `GITHUB_APP_PRIVATE_KEY`: Your GitHub App's private key (RSA format)

### GitHub Actions Workflow

Add this to your workflow to exchange OIDC tokens for GitHub App tokens:

```yaml
jobs:
  use-github-app:
    runs-on: ubuntu-latest
    permissions:
      id-token: write # Required for OIDC
      contents: read
    steps:
      - name: Get GitHub App Access Token
        id: get-app-access-token
        run: |
          # Get OIDC token from GitHub Actions
          OIDC_TOKEN=$(curl -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=your-audience" | jq -r '.value')

          # Exchange for GitHub App token
          APP_TOKEN=$(curl -X POST https://your-service-url/exchange \
            -H "Content-Type: application/json" \
            -d "{\"token\": \"$OIDC_TOKEN\"}" | jq -r '.access_token')

          echo "::add-mask::$APP_TOKEN"
          echo "token=$APP_TOKEN" >> $GITHUB_OUTPUT

      - name: Use GitHub App Access Token
        env:
          GH_TOKEN: ${{ steps.get-app-access-token.token }}
        run: |
          # Now you can use the token with GitHub CLI or API
          gh api /user
```

### Local Testing

Use [ngrok](https://ngrok.com) to expose your local service for testing:

```bash
ngrok http 8080
```

Then use the ngrok URL in your GitHub Actions workflow.

### Testing OIDC Tokens

This repository includes a workflow (`.github/workflows/oidc-token.yaml`) that generates an OIDC token for testing. Add it to your repo and run it manually to get a token saved as an artifact.

### Customization

To implement custom validation (e.g., restricting to specific repositories):

1. Fork this repository
2. Modify the validation logic in `app/auth.py`
3. Build and deploy your customized version

## Development

This project uses [`uv`](https://docs.astral.sh/uv/) for Python dependency management.

### Setup

Copy the environment file and configure:

```bash
cp .env.example .env
# Edit .env with your GitHub App credentials
```

Create virtual env and install dependencies

```bash
uv sync
source .venv/bin/activate
```

Install pre-commit

```bash
pre-commit install
```

### Running

```bash
# Run development server with auto-reload
uv run fastapi dev app/main.py

# Run production server
uv run fastapi run

# Run tests
uv run pytest

# Type checking
uv run mypy .

# Linting & Formatting
uv run ruff check
uv run ruff check --fix # auto fix
uv run ruff format --check
uv run ruff format # auto format

```
