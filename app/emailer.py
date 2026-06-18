"""Email delivery with two backends:

    stub  -> default. Nothing leaves the machine. Each message is logged and
             written to ./outbox/ as a .txt file so you can preview exactly
             what *would* be sent. Safe for demos and review.
    smtp  -> sends through a real SMTP server using stdlib smtplib.

The rest of the app only calls send_email(); it never cares which backend
is active. Swap backends with one env var (EMAIL_BACKEND).
"""
from __future__ import annotations

import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from flask import current_app

log = logging.getLogger("tuckmeet.email")


def send_email(to: str | list[str], subject: str, body: str) -> None:
    recipients = [to] if isinstance(to, str) else list(to)
    backend = current_app.config["EMAIL_BACKEND"]
    if backend == "smtp":
        _send_smtp(recipients, subject, body)
    else:
        _send_stub(recipients, subject, body)


def _send_stub(recipients: list[str], subject: str, body: str) -> None:
    sender = current_app.config["MAIL_FROM"]
    log.info("[STUB EMAIL] to=%s subject=%s", recipients, subject)
    outbox = os.path.join(current_app.root_path, "..", "outbox")
    os.makedirs(outbox, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    safe = "".join(c for c in recipients[0] if c.isalnum() or c in "._-@")
    path = os.path.join(outbox, f"{stamp}_{safe}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"From: {sender}\nTo: {', '.join(recipients)}\nSubject: {subject}\n\n{body}\n")


def _send_smtp(recipients: list[str], subject: str, body: str) -> None:
    cfg = current_app.config
    msg = EmailMessage()
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    host, port = cfg["SMTP_HOST"], cfg["SMTP_PORT"]
    if not host:
        raise RuntimeError("EMAIL_BACKEND=smtp but SMTP_HOST is not configured.")

    with smtplib.SMTP(host, port, timeout=30) as server:
        if cfg["SMTP_USE_TLS"]:
            server.starttls(context=ssl.create_default_context())
        if cfg["SMTP_USERNAME"]:
            server.login(cfg["SMTP_USERNAME"], cfg["SMTP_PASSWORD"])
        server.send_message(msg)
    log.info("[SMTP EMAIL] sent to=%s subject=%s", recipients, subject)
