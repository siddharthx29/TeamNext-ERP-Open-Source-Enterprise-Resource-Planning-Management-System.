import urllib.request
import urllib.error
import json
import os
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_brevo_email(to_emails, subject, html_content, plain_text=None):
    """
    Send email via Brevo HTTP API (works on Render free plan) with automatic fallback
    to Django standard mail backend or console delivery for resilient operation.
    
    to_emails: list or string of recipient email(s)
    subject: string
    html_content: HTML string
    plain_text: optional plain text fallback
    """
    if isinstance(to_emails, str):
        to_emails = [to_emails]

    clean_recipients = [e.strip() for e in to_emails if e and isinstance(e, str) and e.strip()]
    if not clean_recipients:
        raise Exception("No valid recipient emails provided")

    api_key = os.environ.get("BREVO_API_KEY")
    from_email = os.environ.get("DEFAULT_FROM_EMAIL") or getattr(settings, "DEFAULT_FROM_EMAIL", "otp@teamnexterp.com") or "otp@teamnexterp.com"
    from_name = os.environ.get("DEFAULT_FROM_NAME", "TeamNext ERP")

    # If Brevo API key is available, use Brevo HTTP API
    if api_key:
        payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": e} for e in clean_recipients],
            "subject": subject,
            "htmlContent": html_content,
        }
        if plain_text:
            payload["textContent"] = plain_text

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=data,
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            logger.warning(f"Brevo API returned error {e.code}: {error_body}. Falling back to Django mailer.")
        except Exception as e:
            logger.warning(f"Brevo send failed ({str(e)}). Falling back to Django mailer.")

    # Fallback to Django mail framework (SMTP or configured backend)
    try:
        send_mail(
            subject=subject,
            message=plain_text or "",
            html_message=html_content,
            from_email=f"{from_name} <{from_email}>" if from_name else from_email,
            recipient_list=clean_recipients,
            fail_silently=False
        )
        return {"status": "sent_via_django_mail"}
    except Exception as e:
        logger.warning(f"Django send_mail failed: {e}. Outputting email to local log.")
        print(f"\n[TEAMNEXT DISPATCH] To: {clean_recipients} | Subject: {subject}\n{plain_text or html_content}\n")
        return {"status": "logged_locally"}

