"""Create in-app notifications and optionally email them and post them to Slack/Teams.

Delivery never blocks or breaks the request that caused it: email and webhooks run on a
background thread and every failure is logged and swallowed.
"""
import json
import logging
import re
import threading
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

from apps.accounts.models import User

from .models import Notification

log = logging.getLogger(__name__)

MENTION_RE = re.compile(r"(?<![\w@])@([\w.@+-]+)")


def find_mentions(text):
    """Active users named with @username in text (case-insensitive)."""
    names = {m.rstrip(".,;:!?-") for m in MENTION_RE.findall(text or "")}
    names.discard("")
    if not names:
        return []
    found = []
    for u in User.objects.filter(is_active=True):
        if u.username.lower() in {n.lower() for n in names}:
            found.append(u)
    return found


def _run(fn, *args):
    """Run fn in the background, or inline when NOTIFY_SYNC is set (tests)."""
    if getattr(settings, "NOTIFY_SYNC", False):
        fn(*args)
    else:
        threading.Thread(target=fn, args=args, daemon=True).start()


def _send_email(address, title, body, link):
    try:
        base = settings.FRONTEND_URL.rstrip("/")
        text = f"{body}\n\n{base}/#{link}" if link and base else body
        send_mail(f"[PMS] {title}", text or title, settings.DEFAULT_FROM_EMAIL, [address], fail_silently=False)
    except Exception:  # noqa: BLE001 - delivery must never break the app
        log.exception("Email notification failed")


def _post_webhook(text):
    url = settings.NOTIFY_WEBHOOK_URL
    if not url:
        return
    try:
        req = urllib.request.Request(url, data=json.dumps({"text": text}).encode(),
                                     headers={"Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(req, timeout=5).read()  # noqa: S310 - URL comes from our own settings
    except Exception:  # noqa: BLE001
        log.exception("Webhook notification failed")


def notify(users, kind, title, body="", link="", actor=None, webhook=False):
    """Notify each distinct, active user except the person who caused the event."""
    seen, recipients = set(), []
    for u in users:
        if u is None or u.pk in seen or not u.is_active:
            continue
        if actor is not None and u.pk == actor.pk:
            continue
        seen.add(u.pk)
        recipients.append(u)
    if not recipients:
        return []
    rows = Notification.objects.bulk_create([
        Notification(user=u, actor=actor, kind=kind, title=title[:200], body=body, link=link)
        for u in recipients])
    for u in recipients:
        if u.email and u.email_notifications:
            _run(_send_email, u.email, title, body, link)
    if webhook:
        who = actor.get_full_name() or actor.username if actor else "System"
        _run(_post_webhook, f"{title}\n{body}\n(by {who})".strip())
    return rows
