from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from telethon.tl.custom.message import Message
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename

from apps.teachings.models import Teaching
from apps.telegram_sync.config import build_message_url

TITLE_MAX_LENGTH = 500

# Strip leading non-letters (emoji, arrows, punctuation, spaces) until Latin/Arabic letter.
_LEADING_NON_LETTER_RE = re.compile(r"^[^\w\u0600-\u06FF]+", re.UNICODE)

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_LATIN_RE = re.compile(r"[A-Za-z\u00C0-\u024F]")

_FOOTER_URL_RE = re.compile(r"(?i)t\.me/")
_FOOTER_LATIN_BRAND_RE = re.compile(r"(?i)durus\s*ustaz")
_FOOTER_ARABIC_BRAND_RE = re.compile(r"دروس.*أستاذ|أستاذ.*دروس")


@dataclass(frozen=True)
class TeachingPayload:
    telegram_message_id: int
    telegram_channel_id: int
    telegram_message_url: str
    title_ar: str
    title_fr: str
    description: str
    media_type: str
    telegram_file_id: str
    file_name: str
    file_size: int | None
    published_at: datetime | None


def _document_file_name(message: Message) -> str:
    document = message.document
    if document is None:
        return ""

    for attribute in document.attributes:
        if isinstance(attribute, DocumentAttributeFilename):
            return attribute.file_name or ""

    return ""


def _audio_metadata_title(message: Message) -> str:
    document = message.document
    if document is not None:
        for attribute in document.attributes:
            if isinstance(attribute, DocumentAttributeAudio) and attribute.title:
                return attribute.title[:TITLE_MAX_LENGTH]

    file_name = _document_file_name(message)
    if file_name:
        return file_name[:TITLE_MAX_LENGTH]

    return ""


def _strip_leading_decoration(line: str) -> str:
    return _LEADING_NON_LETTER_RE.sub("", line).strip()


def _is_footer_line(line: str) -> bool:
    if not line:
        return True
    if _FOOTER_URL_RE.search(line):
        return True
    if _FOOTER_LATIN_BRAND_RE.search(line):
        return True
    if _FOOTER_ARABIC_BRAND_RE.search(line):
        return True
    arabic, latin = _script_counts(line)
    return arabic == 0 and latin == 0


def _script_counts(line: str) -> tuple[int, int]:
    arabic = len(_ARABIC_RE.findall(line))
    latin = len(_LATIN_RE.findall(line))
    return arabic, latin


def parse_caption_titles(text: str) -> tuple[str, str]:
    """Extract (title_ar, title_fr) from a channel caption.

    Expected shape: Arabic title line, then French title line, then branding footer.
    """
    title_ar = ""
    title_fr = ""

    for raw_line in (text or "").splitlines():
        line = _strip_leading_decoration(raw_line.strip())
        if _is_footer_line(line):
            continue

        arabic, latin = _script_counts(line)
        if arabic == 0 and latin == 0:
            continue

        if arabic >= latin:
            if not title_ar:
                title_ar = line[:TITLE_MAX_LENGTH]
        else:
            if not title_fr:
                title_fr = line[:TITLE_MAX_LENGTH]

        if title_ar and title_fr:
            break

    return title_ar, title_fr


def detect_media_type(message: Message) -> str | None:
    if message.voice:
        return Teaching.MediaType.VOICE

    if message.audio:
        return Teaching.MediaType.AUDIO

    document = message.document
    if document is None:
        return None

    mime_type = (document.mime_type or "").lower()
    if mime_type.startswith("audio/"):
        return Teaching.MediaType.DOCUMENT

    for attribute in document.attributes:
        if isinstance(attribute, DocumentAttributeAudio):
            if attribute.voice:
                return Teaching.MediaType.VOICE
            return Teaching.MediaType.DOCUMENT

    return None


def message_to_teaching_payload(
    message: Message,
    channel_id: int,
    channel_username: str = "",
) -> TeachingPayload | None:
    media_type = detect_media_type(message)
    if media_type is None:
        return None

    document = message.document
    description = (message.message or "").strip()
    title_ar, title_fr = parse_caption_titles(description)

    if not title_ar and not title_fr:
        fallback = _audio_metadata_title(message)
        if fallback:
            title_ar = fallback

    file_name = _document_file_name(message)
    file_size = document.size if document is not None else None
    telegram_file_id = str(document.id) if document is not None else ""
    telegram_message_url = build_message_url(
        message_id=message.id,
        channel_id=channel_id,
        channel_username=channel_username,
    )

    return TeachingPayload(
        telegram_message_id=message.id,
        telegram_channel_id=channel_id,
        telegram_message_url=telegram_message_url,
        title_ar=title_ar,
        title_fr=title_fr,
        description=description,
        media_type=media_type,
        telegram_file_id=telegram_file_id,
        file_name=file_name,
        file_size=file_size,
        published_at=message.date,
    )
