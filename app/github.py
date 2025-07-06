from datetime import datetime, timedelta, timezone

import httpx
import jwt

from .config import Config


class GitHubAppNotInstalledError(Exception):
    """Raised when GitHub App is not installed in the repository."""

    def __init__(self, repository: str, app_name: str):
        self.repository = repository
        self.app_name = app_name
        super().__init__(
            f"GitHub App '{app_name}' is not installed in repository '{repository}'"
        )


class GitHubAPIError(Exception):
    """Raised when GitHub API calls fail."""

    pass


class InstallationTokenError(Exception):
    """Raised when creating installation access token fails."""

    pass


async def create_jwt(config: Config) -> str:
    """
    Create a JWT for GitHub App authentication.

    Args:
        config: Configuration containing client ID and private key

    Returns:
        JWT token string
    """
    # Following GitHub's recommendation: iat should be 60 seconds in the past
    now = datetime.now(timezone.utc)
    iat_time = now - timedelta(seconds=60)  # 60 seconds in the past
    exp_time = now + timedelta(minutes=10)  # 10 minutes in the future (max allowed)

    payload = {
        "iat": int(iat_time.timestamp()),
        "exp": int(exp_time.timestamp()),
        "iss": config.github_app_client_id,  # Client ID as per GitHub's recommendation
    }

    return jwt.encode(payload, config.github_app_private_key, algorithm="RS256")


async def get_installation_id(repo: str, config: Config) -> int:
    """
    Get the installation ID for a GitHub App in a specific repository.

    Args:
        repo: Repository name (owner/repo)
        config: Configuration for GitHub App

    Returns:
        Installation ID

    Raises:
        GitHubAppNotInstalledError: App is not installed in the repository
        GitHubAPIError: API call failed for other reasons
    """
    # Create JWT for authentication
    jwt_token = await create_jwt(config)

    async with httpx.AsyncClient() as client:
        # Check if app is installed in the repository
        response = await client.get(
            f"https://api.github.com/repos/{repo}/installation",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code == 200:
            data = response.json()
            return int(data["id"])
        elif response.status_code == 401:
            # This happens when the JWT is valid but the app isn't installed anywhere
            # GitHub returns 401 "Bad credentials" instead of 404, which is confusing
            raise GitHubAppNotInstalledError(repo, config.github_app_name)
        else:
            # Some other error
            raise GitHubAPIError(
                f"Failed to check GitHub App installation for '{repo}': "
                f"{response.status_code} - {response.text}"
            )


async def create_installation_access_token(installation_id: int, config: Config) -> str:
    """
    Create an installation access token for the GitHub App.

    Args:
        installation_id: GitHub App installation ID
        config: Configuration for GitHub App

    Returns:
        Installation access token

    Raises:
        InstallationTokenError: Failed to create installation token
    """
    # Create JWT for authentication
    jwt_token = await create_jwt(config)

    async with httpx.AsyncClient() as client:
        # Create installation access token
        response = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            },
        )

        if response.status_code == 201:
            data = response.json()
            return str(data["token"])
        else:
            raise InstallationTokenError(
                f"Failed to create installation access token: {response.status_code} - {response.text}"
            )
