"""Sends transactional email over SMTP.

This is the Python equivalent of Nodemailer (same SMTP protocol, same job) - there is
no Node runtime in this backend, so aiosmtplib is the direct, non-workaround substitute.

Dev fallback: with SMTP_HOST unset, the OTP is logged instead of emailed, mirroring the
app's existing "optional, fail soft" pattern for AI providers and DATA_ENCRYPTION_KEY -
local dev needs no mail account configured.
"""

import html
import logging
import random
from email.message import EmailMessage

import aiosmtplib
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


async def send_otp_email(to_email: str, to_name: str, otp: str) -> None:
    affirmation = random.choice(_AFFIRMATIONS)
    subject = "A little sunshine for you ☀️ - your MindEase code inside"

    if not settings.smtp_host or not settings.smtp_from_email:
        logger.warning(
            "SMTP not configured; verification code for %s is %s (dev fallback, not emailed)",
            to_email,
            otp,
        )
        return

    message = EmailMessage()
    message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(_otp_email_text(to_name, otp, settings.otp_expire_minutes, affirmation))
    message.add_alternative(
        _otp_email_html(to_name, otp, settings.otp_expire_minutes, affirmation),
        subtype="html",
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_use_tls,
        )
        logger.info("OTP email sent to %s via %s", to_email, settings.smtp_host)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send OTP email to %s", to_email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not send the verification email. Please try again shortly.",
        ) from exc
