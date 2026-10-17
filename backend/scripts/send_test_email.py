"""Send one real OTP-style email to check the email settings end to end.

Usage (from backend/, with the same env vars the server uses):
    python -m scripts.send_test_email you@example.com

On Render: Shell tab -> `python -m scripts.send_test_email you@example.com`.
Prints which transport was used, or the reason it failed.
"""

import asyncio
import logging
import sys

from fastapi import HTTPException

from app.services.email_service import email_transport, generate_otp, send_otp_email


async def main(to_email: str) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    transport = email_transport()
    if transport is None:
        print("No email transport configured. Set EMAIL_RELAY_URL + EMAIL_RELAY_SECRET (Render) or SMTP_HOST + SMTP_FROM_EMAIL (local).")
        return 1
    print(f"Sending a test code to {to_email} via {transport}...")
    try:
        await send_otp_email(to_email, "MindEase test", generate_otp())
    except HTTPException as exc:
        print(f"FAILED: {exc.detail} (see the log lines above for the provider's reason)")
        return 1
    print("Sent. Check the inbox (and the spam folder).")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1])))
