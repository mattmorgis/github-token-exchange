# Getting GitHub OIDC Tokens for Local Development

GitHub Actions OIDC tokens can only be generated within a GitHub Actions workflow. Here are two approaches for local development:

## Option 1: Use a GitHub Action to Generate a Token

Create a workflow that outputs the OIDC token:

```yaml
name: Get OIDC Token
on:
  workflow_dispatch:

jobs:
  get-token:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Get OIDC Token
        run: |
          TOKEN=$(curl -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=my-github-app" | jq -r '.value')
          echo "::add-mask::$TOKEN"
          echo "OIDC Token (copy this for local testing):"
          echo "$TOKEN"
```

## Option 2: Create a Test Workflow

Add this workflow to your repo at `.github/workflows/test-token-exchange.yml`:

```yaml
name: Test Token Exchange
on:
  workflow_dispatch:

jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Get OIDC Token and Test Endpoint
        run: |
          TOKEN=$(curl -H "Authorization: Bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" \
            "$ACTIONS_ID_TOKEN_REQUEST_URL&audience=my-github-app" | jq -r '.value')
          
          # Test your local endpoint (using ngrok or similar)
          curl -X POST https://your-ngrok-url.ngrok.io/github/github-app-token-exchange \
            -H "Content-Type: application/json" \
            -d "{\"oidc_token\": \"$TOKEN\"}"
```

## Option 3: Mock Token for Development

For pure local testing without GitHub Actions, you can temporarily modify your endpoint to accept a mock token:

```python
# Add this to your endpoint for local testing only
if request.oidc_token == "LOCAL_DEV_TOKEN":
    # Skip validation for local testing
    return TokenExchangeResponse(token="local-dev-token")
```

## Testing the Endpoint Locally

1. Run your FastAPI app:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Test with a mock token:
   ```bash
   curl -X POST http://localhost:8000/github/github-app-token-exchange \
     -H "Content-Type: application/json" \
     -d '{"oidc_token": "LOCAL_DEV_TOKEN"}'
   ```

3. For real token testing, use Option 1 or 2 above to get a real OIDC token from GitHub Actions.