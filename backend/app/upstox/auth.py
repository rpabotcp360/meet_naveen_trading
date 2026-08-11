import httpx

from app.core.config import get_settings
from app.core.secrets import UPSTOX_ACCESS_TOKEN, get_secret

UPSTOX_BASE = "https://api.upstox.com/v2"
UPSTOX_LOGIN_BASE = "https://api.upstox.com/v2/login/authorization/dialog"


class UpstoxAuthService:
    def __init__(self):
        self.settings = get_settings()

    def get_login_url(self) -> str:
        params = {
            "response_type": "code",
            "client_id": self.settings.upstox_api_key,
            "redirect_uri": self.settings.upstox_redirect_uri,
        }
        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{UPSTOX_LOGIN_BASE}?{query}"

    async def exchange_code(self, code: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{UPSTOX_BASE}/login/authorization/token",
                data={
                    "code": code,
                    "client_id": self.settings.upstox_api_key,
                    "client_secret": self._get_client_secret(),
                    "redirect_uri": self.settings.upstox_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            return resp.json()

    def _get_client_secret(self) -> str:
        from app.core.secrets import UPSTOX_CLIENT_SECRET, get_secret

        return get_secret(UPSTOX_CLIENT_SECRET) or ""

    def get_access_token(self) -> str | None:
        return get_secret(UPSTOX_ACCESS_TOKEN)

    def set_access_token(self, token: str) -> None:
        from app.core.secrets import set_secret

        set_secret(UPSTOX_ACCESS_TOKEN, token.strip())

    def is_authenticated(self) -> bool:
        return bool(self.get_access_token())

    def auth_mode(self) -> str:
        if self.is_authenticated():
            return "analytics_token"
        if self.settings.upstox_api_key and not self.settings.upstox_api_key.startswith("eyJ"):
            return "oauth"
        return "none"

    def auth_headers(self) -> dict[str, str]:
        token = self.get_access_token()
        if not token:
            return {}
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
