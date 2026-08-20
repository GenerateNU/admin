from typing import Protocol

import httpx

from admin.core.config import ResendConfig
from admin.core.logging import get_logger

logger = get_logger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"

MONO_STACK = "'Courier New', Consolas, monospace"
SANS_STACK = "Helvetica, Arial, sans-serif"
INK = "#000000"
PAPER = "#ffffff"


def invitation_email_html(*, role_name: str, accept_url: str) -> str:
    return f"""
    <div style="font-family:{SANS_STACK}; max-width:480px; margin:0 auto; padding:32px 24px;
                background:{PAPER}; border:2px solid {INK};">
      <div style="font-family:{MONO_STACK}; font-weight:700; font-size:20px;
                  letter-spacing:0.5px; text-transform:uppercase; color:{INK};
                  margin-bottom:24px;">
        Generate Admin
      </div>
      <p style="font-size:14px; color:{INK}; line-height:1.6; margin:0 0 24px;">
        You've been invited to Generate Admin as <strong>{role_name}</strong>.
      </p>
      <a href="{accept_url}"
         style="display:inline-block; background:{INK}; color:{PAPER}; text-decoration:none;
                font-family:{MONO_STACK}; font-weight:700; text-transform:uppercase;
                font-size:13px; letter-spacing:0.5px; padding:12px 20px; border:2px solid {INK};">
        Accept invitation
      </a>
    </div>
    """


class EmailSender(Protocol):
    async def send_invitation(
        self, *, email: str, role_name: str, token: str, app_url: str
    ) -> None: ...


class ResendEmailSender:
    def __init__(self, config: ResendConfig, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client

    async def send_invitation(
        self, *, email: str, role_name: str, token: str, app_url: str
    ) -> None:
        accept_url = f"{app_url}/?invite_token={token}"
        try:
            response = await self._client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {self._config.api_key.get_secret_value()}"},
                json={
                    "from": self._config.from_email,
                    "to": email,
                    "subject": "You're invited to Generate Admin",
                    "html": invitation_email_html(role_name=role_name, accept_url=accept_url),
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            logger.warning(
                "invitation_email_failed",
                email=email,
                status=error.response.status_code,
                body=error.response.text,
            )
        except httpx.HTTPError as error:
            logger.warning("invitation_email_failed", email=email, error=str(error))


class NullEmailSender:
    async def send_invitation(
        self, *, email: str, role_name: str, token: str, app_url: str
    ) -> None:
        logger.warning(
            "resend_not_configured",
            detail=f"invitation email to {email} was not sent; accept at "
            f"{app_url}/?invite_token={token}",
        )


def build_email_sender(config: ResendConfig, client: httpx.AsyncClient) -> EmailSender:
    if config.is_configured:
        return ResendEmailSender(config, client)
    return NullEmailSender()
