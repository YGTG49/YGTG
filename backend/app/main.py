"""FastAPI application that sends emails using an SMTP pool."""
from __future__ import annotations

import asyncio
import csv
import re
from email.message import EmailMessage
from io import StringIO
from string import Template
import time
from typing import Any, Dict, List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .email_pool import pool
from .rate_limiter import RateLimiter

app = FastAPI(title="Transactional Email API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rate_limiter = RateLimiter(settings.rate_limit_count, settings.rate_limit_period)


class SafeTemplate(Template):
    """Template subclass that safely handles missing keys."""

    def safe_substitute_dict(self, mapping: Dict[str, Any]) -> str:
        sanitized = {k: "" if v is None else str(v) for k, v in mapping.items()}
        return super().safe_substitute(sanitized)


def _render_template(raw: str, data: Dict[str, Any]) -> str:
    template = SafeTemplate(raw)
    return template.safe_substitute_dict(data)


def _strip_html(html: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", html)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


async def _send_email(recipient: str, subject: str, sender: str, body: str) -> None:
    message = EmailMessage()
    message["To"] = recipient
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(_strip_html(body) or body)
    message.add_alternative(body, subtype="html")

    def _sync_send() -> None:
        with pool.acquire() as connection:
            connection.send_message(message)

    await rate_limiter.acquire()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _sync_send)


def _normalize_sender(sender: str | None) -> str:
    sender = sender or settings.default_sender
    if not sender:
        raise HTTPException(status_code=400, detail="No sender provided and DEFAULT_SENDER is unset.")
    if "@" not in sender:
        raise HTTPException(status_code=400, detail="Sender must be a valid email address.")
    return sender


@app.on_event("startup")
def on_startup() -> None:
    pool.warmup()


@app.on_event("shutdown")
def on_shutdown() -> None:
    pool.close()


@app.post("/send")
async def send_emails(
    subject: str = Form(..., description="Email subject (Template syntax supported)."),
    sender: str | None = Form(None, description="Email sender address."),
    template_name: str = Form(..., description="Template identifier."),
    template_body: str = Form(..., description="HTML body for the template."),
    csv_file: UploadFile = File(..., description="CSV with an 'email' column and optional merge fields."),
) -> Dict[str, Any]:
    sender_address = _normalize_sender(sender)

    if csv_file.content_type not in {"text/csv", "application/vnd.ms-excel", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="The uploaded file must be a CSV.")

    try:
        raw_csv = (await csv_file.read()).decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Unable to decode CSV file as UTF-8.") from exc

    reader = csv.DictReader(StringIO(raw_csv))
    lowered = [name.lower() for name in reader.fieldnames or []]
    if "email" not in lowered:
        raise HTTPException(status_code=400, detail="CSV must include an 'email' column.")

    sent: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    start = time.perf_counter()

    for row in reader:
        row_lower = {
            (reader.fieldnames or [])[idx].lower(): value.strip() if isinstance(value, str) else value
            for idx, value in enumerate(row.values())
        }
        recipient = row_lower.get("email")
        if not recipient:
            skipped.append({"reason": "missing_email", "row": row_lower})
            continue

        merge_data = {k: v for k, v in row_lower.items() if k != "email"}
        rendered_subject = _render_template(subject, {**merge_data, "email": recipient})
        rendered_body = _render_template(template_body, {**merge_data, "email": recipient})

        try:
            await _send_email(recipient, rendered_subject, sender_address, rendered_body)
        except Exception as exc:  # pragma: no cover - FastAPI handles logging
            skipped.append({"reason": str(exc), "row": row_lower})
            continue

        sent.append({"email": recipient, "template": template_name})

    elapsed = time.perf_counter() - start
    return {
        "sent": len(sent),
        "skipped": skipped,
        "duration_seconds": round(elapsed, 2),
        "template": template_name,
    }


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}
