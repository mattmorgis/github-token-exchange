from typing import Generator
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth import InvalidOIDCTokenError, TokenExpiredError
from app.github import GitHubAPIError, GitHubAppNotInstalledError
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_config() -> Generator[Mock, None, None]:
    """Mock Config.from_env()"""
    with patch("app.main.Config.from_env") as mock:
        mock.return_value.github_app_name = "test_name"
        mock.return_value.github_app_client_id = "test_id"
        mock.return_value.github_app_private_key = "test_key"
        mock.return_value.expected_audience = "test_audience"
        yield mock


@pytest.fixture
def mock_validate_oidc() -> Generator[Mock, None, None]:
    """Mock OIDC token validation"""
    with patch("app.main.validate_oidc_token") as mock:
        mock.return_value = {
            "repository": "test-owner/test-repo",
        }
        yield mock


@pytest.fixture
def mock_github_api() -> Generator[dict[str, Mock], None, None]:
    """Mock GitHub API functions"""
    with (
        patch("app.main.get_installation_id") as mock_get_id,
        patch("app.main.create_installation_access_token") as mock_create_token,
    ):
        mock_get_id.return_value = 12345
        mock_create_token.return_value = "ghs_access_token"

        yield {"get_installation_id": mock_get_id, "create_token": mock_create_token}


def test_exchange_token_success(
    client: TestClient,
    mock_config: Mock,
    mock_validate_oidc: Mock,
    mock_github_api: dict[str, Mock],
) -> None:
    """Should return token when full flow succeeds"""
    response = client.post(
        "/github/github-app-token-exchange", json={"oidc_token": "valid.oidc.token"}
    )

    assert response.status_code == 200
    assert response.json() == {"token": "ghs_access_token"}


def test_exchange_token_missing_config(client: TestClient) -> None:
    """Should return 500 when config missing"""
    with patch(
        "app.main.Config.from_env",
        side_effect=ValueError(
            "Missing required environment variables: GITHUB_APP_CLIENT_ID"
        ),
    ):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "any.token"}
        )

    assert response.status_code == 500
    assert "Missing required environment variables" in response.json()["detail"]


def test_exchange_token_expired_oidc(
    client: TestClient, mock_config: Mock, mock_github_api: dict[str, Mock]
) -> None:
    """Should return 401 when OIDC token expired"""
    with patch(
        "app.main.validate_oidc_token",
        side_effect=TokenExpiredError("OIDC token has expired"),
    ):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "expired.token"}
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "OIDC token has expired"


def test_exchange_token_invalid_oidc(
    client: TestClient, mock_config: Mock, mock_github_api: dict[str, Mock]
) -> None:
    """Should return 401 when OIDC token invalid"""
    with patch(
        "app.main.validate_oidc_token",
        side_effect=InvalidOIDCTokenError("Invalid token"),
    ):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "invalid.token"}
        )

    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


def test_exchange_token_missing_repository_info(
    client: TestClient, mock_config: Mock, mock_github_api: dict[str, Mock]
) -> None:
    """Should return 401 when OIDC token missing repository info"""
    with patch("app.main.validate_oidc_token", return_value={"some": "other_data"}):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "incomplete.token"}
        )

    assert response.status_code == 401
    assert "missing required repository information" in response.json()["detail"]


def test_exchange_token_app_not_installed(
    client: TestClient, mock_config: Mock, mock_validate_oidc: Mock
) -> None:
    """Should return 403 when GitHub App not installed"""
    with patch(
        "app.main.get_installation_id",
        side_effect=GitHubAppNotInstalledError("test-owner", "test-repo"),
    ):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "valid.token"}
        )

    assert response.status_code == 403
    assert "is not installed in repository" in response.json()["detail"]


def test_exchange_token_github_api_error(
    client: TestClient, mock_config: Mock, mock_validate_oidc: Mock
) -> None:
    """Should return 500 when GitHub API fails"""
    with patch(
        "app.main.get_installation_id", side_effect=GitHubAPIError("API failed")
    ):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "valid.token"}
        )

    assert response.status_code == 500
    assert "Failed to communicate with GitHub API" in response.json()["detail"]


def test_exchange_token_unexpected_error(
    client: TestClient, mock_config: Mock, mock_validate_oidc: Mock
) -> None:
    """Should return 500 for unexpected errors without exposing internals"""
    with patch(
        "app.main.get_installation_id",
        side_effect=Exception("Something weird happened"),
    ):
        response = client.post(
            "/github/github-app-token-exchange", json={"oidc_token": "valid.token"}
        )

    assert response.status_code == 500
    assert (
        response.json()["detail"]
        == "Internal server error occurred during token exchange"
    )
    # Should NOT expose the internal error message
    assert "Something weird happened" not in response.json()["detail"]
