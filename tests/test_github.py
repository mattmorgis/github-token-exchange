from typing import Generator
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.config import Config
from app.github import (
    GitHubAPIError,
    GitHubAppNotInstalledError,
    InstallationTokenError,
    create_installation_access_token,
    get_installation_id,
)


@pytest.fixture
def config() -> Config:
    return Config(
        github_app_name="test_name",
        github_app_client_id="test_client_id",
        github_app_private_key="test_key",
        expected_audience="test_audience",
    )


@pytest.fixture
def mock_github_api() -> Generator[AsyncMock, None, None]:
    """Mock httpx.AsyncClient"""
    with patch("app.github.httpx.AsyncClient") as mock_client:
        mock_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_jwt() -> Generator[None, None, None]:
    """Mock JWT creation"""
    with patch("app.github.jwt.encode", return_value="mock.jwt.token"):
        yield


async def test_get_installation_id_success(
    config: Config, mock_github_api: AsyncMock, mock_jwt: Generator[None, None, None]
) -> None:
    """Should return installation ID when app is installed"""
    mock_response = Mock(status_code=200)
    mock_response.json.return_value = {"id": 12345}
    mock_github_api.get.return_value = mock_response

    result = await get_installation_id("repo", config)

    assert result == 12345


async def test_get_installation_id_not_installed(
    config: Config, mock_github_api: AsyncMock, mock_jwt: Generator[None, None, None]
) -> None:
    """Should raise GitHubAppNotInstalledError when app not installed"""
    mock_github_api.get.return_value = Mock(status_code=401)

    with pytest.raises(GitHubAppNotInstalledError):
        await get_installation_id("repo", config)


async def test_get_installation_id_api_error(
    config: Config, mock_github_api: AsyncMock, mock_jwt: Generator[None, None, None]
) -> None:
    """Should raise GitHubAPIError when API call fails"""
    mock_github_api.get.return_value = Mock(status_code=500, text="Server Error")

    with pytest.raises(GitHubAPIError):
        await get_installation_id("repo", config)


async def test_create_installation_token_success(
    config: Config, mock_github_api: AsyncMock, mock_jwt: Generator[None, None, None]
) -> None:
    """Should return access token when request succeeds"""
    mock_response = Mock(status_code=201)
    mock_response.json.return_value = {"token": "ghs_access_token"}
    mock_github_api.post.return_value = mock_response

    result = await create_installation_access_token(12345, config)

    assert result == "ghs_access_token"


async def test_create_installation_token_api_error(
    config: Config, mock_github_api: AsyncMock, mock_jwt: Generator[None, None, None]
) -> None:
    """Should raise InstallationTokenError when API call fails"""
    mock_github_api.post.return_value = Mock(status_code=403, text="Forbidden")

    with pytest.raises(InstallationTokenError):
        await create_installation_access_token(12345, config)
