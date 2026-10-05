"""Sends transactional email.

Two transports:
- Brevo's HTTP API (https://api.brevo.com) when BREVO_API_KEY is set - sends over HTTPS,
  so it works on hosts that block outbound SMTP (confirmed on Render: both port 587 and
  465 timed out connecting to smtp.gmail.com - a hard platform-level network block, not a
  config issue). This is the production path.
- Raw SMTP via aiosmtplib otherwise - the Python equivalent of Nodemailer (same protocol,
  same job; there's no Node runtime in this backend). Works fine for local dev.

Dev fallback: with neither configured, the OTP is logged instead of emailed, mirroring the
app's existing "optional, fail soft" pattern for AI providers and DATA_ENCRYPTION_KEY.
"""

import html
import logging
import random
from email.message import EmailMessage

import aiosmtplib
import httpx
from fastapi import HTTPException, status

from app.config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Same gentle, plain-spoken, "kind friend" voice as the in-app chat and crisis copy.
_AFFIRMATIONS = [
    "Small steps still count as moving forward.",
    "You don't have to have it all figured out today.",
    "Taking a moment for yourself is never wasted time.",
    "However today feels, you showed up - that matters.",
    "Progress doesn't have to be loud to be real.",
    "Be as kind to yourself as you'd be to a friend.",
]


def generate_otp() -> str:
    return "".join(random.choices("0123456789", k=settings.otp_length))


def _otp_email_text(name: str, otp: str, expire_minutes: int, affirmation: str) -> str:
    return (
        f"Hi {name},\n\n"
        "A little sunshine for your inbox - here's your MindEase code:\n\n"
        f"    {otp}\n\n"
        f"It's good for the next {expire_minutes} minutes.\n\n"
        f"A small reminder: {affirmation}\n\n"
        "Didn't request this? No action needed, just ignore this email.\n\n"
        "- MindEase"
    )


def _otp_email_html(name: str, otp: str, expire_minutes: int, affirmation: str) -> str:
    safe_name = html.escape(name) or "there"
    otp_spaced = html.escape(otp)
    affirmation_safe = html.escape(affirmation)
    return f"""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Your MindEase code</title>
    <style>
      @media only screen and (max-width: 480px) {{
        .container {{ width: 100% !important; }}
        .otp-box {{ font-size: 28px !important; letter-spacing: 6px !important; }}
      }}
    </style>
  </head>
  <body style="margin:0;padding:0;background-color:#F3F9F5;font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#F3F9F5;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" class="container" width="480" cellpadding="0" cellspacing="0" style="width:480px;max-width:100%;background-color:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 30px rgba(31,74,58,0.08);">
            <tr>
              <td style="background-image:linear-gradient(135deg,#F5AD78,#3F9690);background-color:#3F9690;padding:36px 32px;text-align:center;">
                <div style="font-size:30px;line-height:1;margin-bottom:8px;">&#127807;&#9728;&#65039;</div>
                <div style="font-family:Georgia,'Playfair Display',serif;font-size:24px;font-weight:700;color:#ffffff;letter-spacing:0.5px;">MindEase</div>
                <div style="font-size:13px;color:rgba(255,255,255,0.92);margin-top:4px;">A little sunshine for your inbox</div>
              </td>
            </tr>
            <tr>
              <td style="padding:36px 32px 8px;">
                <p style="margin:0 0 4px;font-size:15px;color:#1F3B2E;">Hi {safe_name},</p>
                <p style="margin:0 0 24px;font-size:15px;line-height:1.6;color:#4A5D54;">
                  Glad you're here. Enter this code to finish getting set up - it's good for the next {expire_minutes} minutes.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                  <tr>
                    <td align="center" class="otp-box" style="background-color:#EAF4EE;border:1.5px dashed #3F8F6E;border-radius:16px;padding:20px 12px;font-family:'Courier New',monospace;font-size:34px;font-weight:700;letter-spacing:10px;color:#2F6B52;">
                      {otp_spaced}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:20px 32px 0;">
                <p style="margin:0;font-size:12.5px;color:#8A988F;text-align:center;">Didn't request this? You can safely ignore this email.</p>
              </td>
            </tr>
            <tr>
              <td style="padding:28px 32px 32px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#FBF6EF;border-radius:14px;">
                  <tr>
                    <td style="padding:16px 20px;font-size:13.5px;line-height:1.6;color:#6B5A42;">
                      <strong style="color:#C9793A;">&#10024; A small reminder:</strong> {affirmation_safe}
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 32px;text-align:center;">
                <div style="margin-bottom:10px;">
                  <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background-color:#3F8F6E;margin:0 3px;"></span>
                  <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background-color:#3F9690;margin:0 3px;"></span>
                  <span style="display:inline-block;width:7px;height:7px;border-radius:50%;background-color:#F5AD78;margin:0 3px;"></span>
                </div>
                <p style="margin:0;font-size:12px;color:#9AA69D;">MindEase &middot; A supportive companion for your well-being</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>"""


async def _attempt_send(message: EmailMessage, port: int, implicit_tls: bool) -> None:
    """One connection attempt. 465 = implicit TLS from the first byte; 587/anything
    else = plaintext connect then STARTTLS. Hosts that block one submission port
    sometimes allow the other, so callers try both before giving up."""
    if implicit_tls:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            use_tls=True,
            timeout=15,
        )
    else:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=True,
            timeout=15,
        )


async def _send_via_brevo(to_email: str, to_name: str, subject: str, text: str, html_body: str) -> None:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.brevo_api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json={
                    "sender": {"name": settings.smtp_from_name, "email": settings.smtp_from_email},
                    "to": [{"email": to_email, "name": to_name or to_email}],
                    "subject": subject,
                    "htmlContent": html_body,
                    "textContent": text,
                },
            )
        resp.raise_for_status()
        logger.info("OTP email sent to %s via Brevo", to_email)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Brevo send failed for %s", to_email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification email. Please try again shortly.",
        ) from exc


async def _send_via_smtp(to_email: str, to_name: str, subject: str, text: str, html_body: str) -> None:
    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(text)
    message.add_alternative(html_body, subtype="html")

    # Try the configured port/mode first, then the other submission port as a
    # fallback - some hosts block 587 (STARTTLS) but allow 465 (implicit TLS), or
    # vice versa, and there's no way to know which without just trying both.
    configured_port = settings.smtp_port
    configured_implicit = configured_port == 465
    fallback_port = 465 if configured_port != 465 else 587

    first_error: Exception | None = None
    try:
        await _attempt_send(message, configured_port, configured_implicit)
        logger.info("OTP email sent to %s via %s:%s", to_email, settings.smtp_host, configured_port)
        return
    except Exception as exc:  # noqa: BLE001
        first_error = exc
        logger.warning(
            "SMTP send to %s via port %s failed (%s), retrying on port %s",
            to_email,
            configured_port,
            exc,
            fallback_port,
        )

    try:
        await _attempt_send(message, fallback_port, fallback_port == 465)
        logger.info(
            "OTP email sent to %s via %s:%s (fallback port)", to_email, settings.smtp_host, fallback_port,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed to send OTP email to %s on both port %s and fallback port %s",
            to_email,
            configured_port,
            fallback_port,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification email. Please try again shortly.",
        ) from (exc if first_error is None else first_error)


async def send_otp_email(to_email: str, to_name: str, otp: str) -> None:
    affirmation = random.choice(_AFFIRMATIONS)
    subject = "A little sunshine for you ☀️ - your MindEase code inside"

    if not settings.smtp_from_email or (not settings.brevo_api_key and not settings.smtp_host):
        logger.warning(
            "No email transport configured; verification code for %s is %s (dev fallback, not emailed)",
            to_email,
            otp,
        )
        return

    text = _otp_email_text(to_name, otp, settings.otp_expire_minutes, affirmation)
    html_body = _otp_email_html(to_name, otp, settings.otp_expire_minutes, affirmation)

    if settings.brevo_api_key:
        await _send_via_brevo(to_email, to_name, subject, text, html_body)
    else:
        await _send_via_smtp(to_email, to_name, subject, text, html_body)
