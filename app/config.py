import os
from dataclasses import dataclass


@dataclass
class Config:
    github_app_name: str
    github_app_client_id: str
    github_app_private_key: str
    allowed_audience: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        github_app_name = os.getenv("GITHUB_APP_NAME") or ""
        client_id = os.getenv("GITHUB_APP_CLIENT_ID") or ""
        private_key = os.getenv("GITHUB_APP_PRIVATE_KEY") or ""
        allowed_audience = os.getenv("ALLOWED_AUDIENCE") or ""

        missing_config = []
        if not github_app_name:
            missing_config.append("GITHUB_APP_NAME")
        if not client_id:
            missing_config.append("GITHUB_APP_CLIENT_ID")
        if not private_key:
            missing_config.append("GITHUB_APP_PRIVATE_KEY")
        if not allowed_audience:
            missing_config.append("ALLOWED_AUDIENCE")

        if missing_config:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_config)}"
            )

        return cls(
            github_app_name=github_app_name,
            github_app_client_id=client_id,
            github_app_private_key=private_key,
            allowed_audience=allowed_audience,
        )
