"""
TBAPS Email Service
Async email delivery for NEF Agent distribution.
Supports SMTP (Gmail/Outlook) and SendGrid.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Email template ─────────────────────────────────────────────────────────────

def _build_agent_email(
    to_name: str,
    download_url_linux: str,
    download_url_windows: str,
) -> tuple[str, str, str]:
    """
    Build (subject, plain_text, html) for the NEF Agent onboarding email.
    Returns a 3-tuple: (subject, text_body, html_body).
    """
    subject = "TBAPS Secure Agent Installation"

    text_body = f"""Hello {to_name},

You have been onboarded into the TBAPS monitoring system.

Please download and install the NEF Agent using one of the links below:

  Linux (.deb):   {download_url_linux}
  Windows (.exe): {download_url_windows}

INSTALLATION STEPS
──────────────────
Linux (Ubuntu / Debian):
  1. Download the .deb file
  2. Run: sudo dpkg -i nef-agent-*.deb

Windows:
  1. Download the .exe file
  2. Double-click to run — no technical knowledge needed

SECURITY NOTICE
───────────────
• These links are unique to you. Do not share them.
• The agent will securely connect to the TBAPS system after installation.
• If you did not expect this email, contact your administrator immediately.

If you have any questions, please contact your administrator.

— The TBAPS Security Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TBAPS Secure Agent Installation</title>
</head>
<body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#1a1f2e;border-radius:16px;border:1px solid #2d3748;overflow:hidden;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#1e3a5f,#0f2040);padding:32px 40px;text-align:center;">
              <div style="font-size:36px;margin-bottom:8px;">🛡️</div>
              <h1 style="margin:0;color:#e2e8f0;font-size:22px;font-weight:700;letter-spacing:-0.5px;">
                TBAPS Secure Agent Installation
              </h1>
              <p style="margin:8px 0 0;color:#94a3b8;font-size:13px;">
                Zero-Trust Monitoring System
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">
              <p style="color:#e2e8f0;font-size:15px;margin:0 0 16px;">Hello <strong>{to_name}</strong>,</p>
              <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 24px;">
                You have been onboarded into the <strong style="color:#3b82f6;">TBAPS</strong> monitoring system.
                Please download and install the <strong>NEF Agent</strong> using one of the links below.
                The agent will securely connect to the system upon installation.
              </p>

              <!-- Download buttons -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
                <tr>
                  <td style="padding:0 8px 0 0;">
                    <a href="{download_url_linux}"
                       style="display:block;background:#16a34a;color:#fff;text-decoration:none;
                              border-radius:10px;padding:14px 20px;text-align:center;font-size:14px;font-weight:600;">
                      🐧 Download for Linux (.deb)
                    </a>
                  </td>
                  <td style="padding:0 0 0 8px;">
                    <a href="{download_url_windows}"
                       style="display:block;background:#2563eb;color:#fff;text-decoration:none;
                              border-radius:10px;padding:14px 20px;text-align:center;font-size:14px;font-weight:600;">
                      🪟 Download for Windows (.exe)
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Steps -->
              <div style="background:#111827;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
                <h3 style="color:#e2e8f0;font-size:13px;font-weight:700;margin:0 0 12px;
                            text-transform:uppercase;letter-spacing:1px;">
                  Installation Steps
                </h3>
                <p style="color:#94a3b8;font-size:13px;margin:0 0 8px;"><strong style="color:#22c55e;">Linux:</strong></p>
                <ol style="color:#94a3b8;font-size:13px;margin:0 0 12px;padding-left:20px;line-height:1.8;">
                  <li>Download the .deb file above</li>
                  <li>Run: <code style="background:#0a0f1a;color:#4ade80;padding:2px 6px;border-radius:4px;">
                      sudo dpkg -i nef-agent-*.deb</code></li>
                </ol>
                <p style="color:#94a3b8;font-size:13px;margin:0 0 8px;"><strong style="color:#60a5fa;">Windows:</strong></p>
                <ol style="color:#94a3b8;font-size:13px;margin:0;padding-left:20px;line-height:1.8;">
                  <li>Download the .exe file above</li>
                  <li>Double-click to run — no technical knowledge needed</li>
                </ol>
              </div>

              <!-- Security notice -->
              <div style="background:#1e1a0f;border:1px solid #92400e;border-radius:10px;padding:16px 20px;margin-bottom:24px;">
                <p style="color:#fbbf24;font-size:12px;font-weight:700;margin:0 0 6px;">
                  🔒 Security Notice
                </p>
                <ul style="color:#d97706;font-size:12px;margin:0;padding-left:18px;line-height:1.7;">
                  <li>These download links are unique to you — do not share them.</li>
                  <li>The agent connects securely using end-to-end encryption.</li>
                  <li>If you did not expect this email, contact your administrator immediately.</li>
                </ul>
              </div>

              <p style="color:#64748b;font-size:13px;margin:0;">
                If you have any questions, please contact your system administrator.
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#111827;padding:20px 40px;text-align:center;border-top:1px solid #2d3748;">
              <p style="color:#4b5563;font-size:12px;margin:0;">
                This is an automated message from the TBAPS Security System.
                Do not reply to this email.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return subject, text_body, html_body


def _build_notification_email(
    to_name: str,
    login_url: str,
    role: str,
    department: Optional[str] = None,
    username: Optional[str] = None,
    temp_password: Optional[str] = None
) -> tuple[str, str, str]:
    """
    Build (subject, plain_text, html) for the Manager/HR welcome email.
    """
    role_display = role.capitalize()
    subject = f"Your TBAPS {role_display} Account Has Been Created"

    text_body = f"""Dear {to_name},

We are pleased to inform you that your {role_display} account for the TBAPS (Pragyantri) system has been successfully created.

Below are your login credentials:

Username: {username}
Password: {temp_password}

You can access the system using the following link:
{login_url}

As a {role_display}, you will have access to monitor and analyze activities related to your assigned role.

For security reasons, we strongly recommend changing your password after your first login.

If you encounter any issues, please contact the system administrator.

Best regards,
TBAPS Administration Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Your TBAPS {role_display} Account Has Been Created</title>
</head>
<body style="margin:0;padding:0;background:#0f1117;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f1117;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#1a1f2e;border-radius:16px;border:1px solid #2d3748;overflow:hidden;">
          <tr>
            <td style="background:linear-gradient(135deg,#1e3a5f,#0f2040);padding:32px 40px;text-align:center;">
              <div style="font-size:36px;margin-bottom:8px;">🛡️</div>
              <h1 style="margin:0;color:#e2e8f0;font-size:22px;font-weight:700;letter-spacing:-0.5px;">
                TBAPS {role_display} Account Created
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:32px 40px;">
              <p style="color:#e2e8f0;font-size:15px;margin:0 0 16px;">Dear <strong>{to_name}</strong>,</p>
              <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 24px;">
                We are pleased to inform you that your <strong>{role_display}</strong> account for the TBAPS (Pragyantri) system has been successfully created.
              </p>
              
              <div style="background:#111827;border-radius:10px;padding:20px 24px;margin-bottom:24px;border-left:4px solid #3b82f6;">
                <h3 style="color:#e2e8f0;font-size:14px;margin:0 0 12px;font-weight:600;">Your Login Credentials</h3>
                <p style="color:#cbd5e1;font-size:14px;margin:0 0 8px;font-family:monospace;"><strong>Username:</strong> {username}</p>
                <p style="color:#cbd5e1;font-size:14px;margin:0;font-family:monospace;"><strong>Password:</strong> {temp_password}</p>
              </div>

              <div style="text-align: center; margin: 32px 0;">
                <a href="{login_url}"
                   style="display:inline-block;background:#3b82f6;color:#fff;text-decoration:none;
                          border-radius:10px;padding:14px 28px;font-size:15px;font-weight:600;">
                  Access Dashboard
                </a>
              </div>

              <p style="color:#94a3b8;font-size:14px;line-height:1.6;margin:0 0 24px;">
                As a {role_display}, you will have access to monitor and analyze activities related to your assigned role.
              </p>

              <div style="background:#1e1a0f;border:1px solid #92400e;border-radius:10px;padding:16px 20px;margin-bottom:24px;">
                <p style="color:#fbbf24;font-size:13px;font-weight:600;margin:0 0 4px;">🔒 Security Recommendation</p>
                <p style="color:#d97706;font-size:12px;margin:0;line-height:1.5;">
                  For security reasons, we strongly recommend changing your password after your first login.
                </p>
              </div>

              <p style="color:#64748b;font-size:13px;margin:0 0 4px;">
                If you encounter any issues, please contact the system administrator.
              </p>
              <p style="color:#64748b;font-size:13px;margin:0;">
                Best regards,<br/><strong>TBAPS Administration Team</strong>
              </p>
            </td>
          </tr>
          <tr>
            <td style="background:#111827;padding:20px 40px;text-align:center;border-top:1px solid #2d3748;">
              <p style="color:#4b5563;font-size:12px;margin:0;">
                This is an automated message from the TBAPS Security System. Do not reply to this email.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    return subject, text_body, html_body


# ── SMTP sender ────────────────────────────────────────────────────────────────

async def _send_via_smtp(
    to_email: str,
    to_name: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    """Send email via SMTP using aiosmtplib."""
    try:
        import aiosmtplib
    except ImportError:
        raise RuntimeError(
            "aiosmtplib is not installed. Run: pip install aiosmtplib>=3.0.0"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS}>"
    msg["To"] = f"{to_name} <{to_email}>"

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME or None,
            password=settings.SMTP_PASSWORD or None,
            start_tls=settings.SMTP_USE_TLS,
        )
    except Exception as e:
        logger.warning(
            f"Could not connect to SMTP server ({e}). "
            f"Since we are in local development, here is the email that would have been sent:\n\n"
            f"=== EMAIL TO: {to_email} ===\n"
            f"SUBJECT: {subject}\n"
            f"BODY:\n{text_body}\n"
            f"================================="
        )


# ── SendGrid sender ────────────────────────────────────────────────────────────

async def _send_via_sendgrid(
    to_email: str,
    to_name: str,
    subject: str,
    text_body: str,
    html_body: str,
) -> None:
    """Send email via SendGrid REST API (uses httpx — already in requirements)."""
    import httpx

    if not settings.SENDGRID_API_KEY:
        raise RuntimeError("SENDGRID_API_KEY is not configured in settings.")

    payload = {
        "personalizations": [{"to": [{"email": to_email, "name": to_name}]}],
        "from": {"email": settings.EMAIL_FROM_ADDRESS, "name": settings.EMAIL_FROM_NAME},
        "subject": subject,
        "content": [
            {"type": "text/plain", "value": text_body},
            {"type": "text/html", "value": html_body},
        ],
    }

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
        )
        if resp.status_code not in (200, 202):
            raise RuntimeError(
                f"SendGrid error {resp.status_code}: {resp.text[:200]}"
            )


# ── Public API ─────────────────────────────────────────────────────────────────

async def send_agent_email(
    to_email: str,
    to_name: str,
    employee_id: str,
    download_url_linux: str,
    download_url_windows: str,
) -> None:
    """
    Compose and send the NEF Agent onboarding email to an employee.

    Args:
        to_email:              Recipient email address.
        to_name:               Recipient display name.
        employee_id:           Employee UUID (used for logging).
        download_url_linux:    Pre-built URL to the .deb installer endpoint.
        download_url_windows:  Pre-built URL to the .exe installer endpoint.

    Raises:
        RuntimeError: On delivery failure (SMTP error, SendGrid error, etc.)
    """
    subject, text_body, html_body = _build_agent_email(
        to_name=to_name,
        download_url_linux=download_url_linux,
        download_url_windows=download_url_windows,
    )

    logger.info(
        "Sending NEF Agent email",
        extra={"employee_id": employee_id, "to": to_email, "provider": settings.EMAIL_PROVIDER},
    )

    if settings.EMAIL_PROVIDER == "sendgrid":
        await _send_via_sendgrid(to_email, to_name, subject, text_body, html_body)
    else:
        await _send_via_smtp(to_email, to_name, subject, text_body, html_body)

    logger.info(
        "NEF Agent email sent successfully",
        extra={"employee_id": employee_id, "to": to_email},
    )


async def send_notification_email(
    to_email: str,
    to_name: str,
    role: str,
    department: Optional[str] = None,
    username: Optional[str] = None,
    temp_password: Optional[str] = None,
) -> None:
    """
    Compose and send a welcome notification email to a new Manager or HR user,
    including their temporary credentials.
    """
    # Assuming frontend is hosted at FRONTEND_URL
    login_url = settings.FRONTEND_URL.rstrip("/") + "/"

    subject, text_body, html_body = _build_notification_email(
        to_name=to_name,
        login_url=login_url,
        role=role,
        department=department,
        username=username,
        temp_password=temp_password,
    )

    logger.info(
        f"Sending {role} notification email",
        extra={"to": to_email, "provider": settings.EMAIL_PROVIDER},
    )

    if settings.EMAIL_PROVIDER == "sendgrid":
        await _send_via_sendgrid(to_email, to_name, subject, text_body, html_body)
    else:
        await _send_via_smtp(to_email, to_name, subject, text_body, html_body)

    logger.info(
        f"{role.capitalize()} email sent successfully",
        extra={"to": to_email},
    )
