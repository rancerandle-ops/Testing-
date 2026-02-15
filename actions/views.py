import hashlib
import hmac
import json

from django.conf import settings
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .email_parser import process_inbound_email
from .models import InboundEmail


def _verify_webhook(request):
    """Verify the webhook request using a shared secret (if configured)."""
    secret = settings.INBOUND_EMAIL_WEBHOOK_SECRET
    if not secret:
        return True  # No secret configured — allow all (dev mode)

    # SendGrid sends a signature in headers
    signature = request.headers.get("X-Twilio-Email-Event-Webhook-Signature", "")
    timestamp = request.headers.get("X-Twilio-Email-Event-Webhook-Timestamp", "")
    if signature and timestamp:
        payload = timestamp + request.body.decode("utf-8", errors="replace")
        expected = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(signature, expected)

    # Mailgun verification
    mg_signature = request.POST.get("signature")
    mg_token = request.POST.get("token")
    mg_timestamp = request.POST.get("timestamp")
    if mg_signature and mg_token and mg_timestamp:
        payload = f"{mg_timestamp}{mg_token}"
        expected = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(mg_signature, expected)

    return False


@csrf_exempt
@require_POST
def inbound_email_webhook(request):
    """
    Webhook endpoint for SendGrid/Mailgun inbound parse.

    Expects a POST with form-encoded fields:
      - from / sender
      - subject
      - text (plain-text body)
      - html (HTML body, optional)
      - headers (raw headers as text, optional)
    """
    if not _verify_webhook(request):
        return HttpResponseForbidden("Invalid webhook signature")

    # Extract fields — supporting both SendGrid and Mailgun field names
    sender = request.POST.get("from", request.POST.get("sender", ""))
    subject = request.POST.get("subject", "")
    body_plain = request.POST.get("text", request.POST.get("body-plain", ""))
    body_html = request.POST.get("html", request.POST.get("body-html", ""))

    # Parse Message-ID and In-Reply-To from headers
    message_id = ""
    in_reply_to = ""
    raw_headers = request.POST.get("headers", request.POST.get("message-headers", ""))
    if raw_headers:
        # Try JSON format (SendGrid sends headers as JSON array)
        try:
            parsed = json.loads(raw_headers)
            header_dict = {h[0].lower(): h[1] for h in parsed}
            message_id = header_dict.get("message-id", "")
            in_reply_to = header_dict.get("in-reply-to", "")
        except (json.JSONDecodeError, TypeError):
            # Plain text headers (Mailgun)
            for line in raw_headers.split("\n"):
                lower = line.lower()
                if lower.startswith("message-id:"):
                    message_id = line.split(":", 1)[1].strip()
                elif lower.startswith("in-reply-to:"):
                    in_reply_to = line.split(":", 1)[1].strip()

    # Extract just the email address from "Name <email>" format
    if "<" in sender and ">" in sender:
        sender = sender.split("<")[1].split(">")[0]

    email_record = InboundEmail.objects.create(
        sender=sender,
        subject=subject,
        body_plain=body_plain,
        body_html=body_html,
        message_id=message_id,
        in_reply_to=in_reply_to,
    )

    try:
        results = process_inbound_email(email_record)
        return JsonResponse({
            "status": "ok",
            "items_created": len(results),
        })
    except Exception as e:
        email_record.error = str(e)
        email_record.save()
        return JsonResponse({"status": "error", "detail": str(e)}, status=500)
