from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, TestCase, override_settings

from apps.teachings.models import Teaching
from apps.telegram_sync import storage
from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import (
    TelegramConfig,
    build_message_url,
    get_telegram_config,
)
from apps.telegram_sync.messages import (
    detect_media_type,
    message_to_teaching_payload,
    parse_caption_titles,
)
from apps.telegram_sync.downloader import (
    claim_pending_teachings,
    has_priority_pending,
    mark_failed,
    mark_ready,
    try_reuse_existing_r2_object,
)
from apps.telegram_sync.models import ChannelSyncState
from apps.telegram_sync.sync import (
    SyncStats,
    advance_recent_sync_state,
    advance_sync_state,
    catch_up_min_id,
    get_or_create_sync_state,
    history_iter_kwargs,
    history_offset_id,
    record_live_message,
    reset_sync_state,
    upsert_teaching,
)
from telethon.tl.types import DocumentAttributeAudio, DocumentAttributeFilename

SAMPLE_CAPTION = """\
✅حكم اقتناء الصور وأقسامها في الفقه الإسلامي

✅👉Le jugement juridique relatif à la possession des images et leurs différentes catégories en droit islamique (fiqh).

Durus Ustaz Alhusayny Ba(dkr)🔦                                     👇🌴دروس أستاذالحسين با(دكار)🔦
https://t.me/durusustazalhusaynba
"""


def _message(**kwargs):
    defaults = {
        "id": 42,
        "message": "Premier enseignement\nDétails",
        "date": datetime(2024, 1, 15, tzinfo=timezone.utc),
        "audio": None,
        "voice": None,
        "document": None,
        "media": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TelegramConfigTests(SimpleTestCase):
    @override_settings(TELEGRAM_API_ID=None, TELEGRAM_API_HASH="")
    def test_missing_credentials_raise_clear_error(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            "TELEGRAM_API_ID, TELEGRAM_API_HASH",
        ):
            get_telegram_config()

    def test_config_creates_session_parent_directory(self):
        with TemporaryDirectory() as temp_directory:
            session_path = Path(temp_directory) / "nested" / "durus"

            with override_settings(
                TELEGRAM_API_ID=12345,
                TELEGRAM_API_HASH="test-hash",
                TELEGRAM_CHANNEL_ID=-1001234567890,
                TELEGRAM_CHANNEL_USERNAME="examplechannel",
                TELEGRAM_SESSION_PATH=str(session_path),
            ):
                config = get_telegram_config()

            self.assertEqual(config.session_path, session_path)
            self.assertEqual(config.channel_username, "examplechannel")
            self.assertTrue(session_path.parent.is_dir())


class BuildMessageUrlTests(SimpleTestCase):
    def test_uses_username_when_present(self):
        self.assertEqual(
            build_message_url(
                message_id=42,
                channel_id=-1001087177387,
                channel_username="durusustazalhusaynba",
            ),
            "https://t.me/durusustazalhusaynba/42",
        )

    def test_falls_back_to_private_path(self):
        self.assertEqual(
            build_message_url(
                message_id=42,
                channel_id=-1001087177387,
                channel_username="",
            ),
            "https://t.me/c/1087177387/42",
        )


class TelegramClientTests(SimpleTestCase):
    @patch("apps.telegram_sync.client.TelegramClient")
    def test_client_uses_explicit_configuration(self, client_class):
        config = TelegramConfig(
            api_id=12345,
            api_hash="test-hash",
            channel_id=-1001234567890,
            channel_username="demo",
            session_path=Path("/tmp/durus"),
        )

        create_telegram_client(config)

        client_class.assert_called_once_with(
            str(config.session_path),
            config.api_id,
            config.api_hash,
        )


class R2ReconciliationTests(SimpleTestCase):
    def setUp(self):
        self.config = storage.R2Config(
            account_id="account",
            access_key_id="key",
            secret_access_key="secret",
            bucket_name="bucket",
            endpoint_url="https://example.invalid",
            region="auto",
        )

    @patch("apps.telegram_sync.storage.get_r2_client")
    def test_find_existing_key_uses_known_exact_key(self, get_client):
        client = get_client.return_value

        key = storage.find_existing_teaching_key(
            channel_id=-1001,
            message_id=42,
            known_key="teachings/-1001/42.mp3",
            config=self.config,
        )

        self.assertEqual(key, "teachings/-1001/42.mp3")
        client.head_object.assert_called_once_with(
            Bucket="bucket",
            Key="teachings/-1001/42.mp3",
        )
        client.list_objects_v2.assert_not_called()

    @patch("apps.telegram_sync.storage.get_r2_client")
    def test_find_existing_key_discovers_object_by_prefix(self, get_client):
        client = get_client.return_value
        client.list_objects_v2.return_value = {
            "Contents": [{"Key": "teachings/-1001/42.ogg"}],
        }

        key = storage.find_existing_teaching_key(
            channel_id=-1001,
            message_id=42,
            config=self.config,
        )

        self.assertEqual(key, "teachings/-1001/42.ogg")
        client.list_objects_v2.assert_called_once_with(
            Bucket="bucket",
            Prefix="teachings/-1001/42.",
            MaxKeys=1,
        )


class CaptionTitleParsingTests(SimpleTestCase):
    def test_parses_bilingual_caption(self):
        title_ar, title_fr = parse_caption_titles(SAMPLE_CAPTION)

        self.assertEqual(
            title_ar,
            "حكم اقتناء الصور وأقسامها في الفقه الإسلامي",
        )
        self.assertEqual(
            title_fr,
            "Le jugement juridique relatif à la possession des images "
            "et leurs différentes catégories en droit islamique (fiqh).",
        )
        self.assertNotIn("t.me/", title_ar)
        self.assertNotIn("t.me/", title_fr)
        self.assertNotIn("Durus", title_fr)
        self.assertNotIn("✅", title_ar)
        self.assertNotIn("👉", title_fr)

    def test_empty_caption(self):
        self.assertEqual(parse_caption_titles(""), ("", ""))
        self.assertEqual(parse_caption_titles("   \n  "), ("", ""))

    def test_arabic_only(self):
        title_ar, title_fr = parse_caption_titles("✅عنوان عربي فقط\n\nhttps://t.me/x")
        self.assertEqual(title_ar, "عنوان عربي فقط")
        self.assertEqual(title_fr, "")

    def test_french_only(self):
        title_ar, title_fr = parse_caption_titles(
            "✅👉Un titre uniquement en français.\n\nDurus Ustaz foo"
        )
        self.assertEqual(title_ar, "")
        self.assertEqual(title_fr, "Un titre uniquement en français.")


class MessageMappingTests(SimpleTestCase):
    def test_ignores_non_audio_messages(self):
        message = _message(message="Texte seul")
        self.assertIsNone(detect_media_type(message))
        self.assertIsNone(message_to_teaching_payload(message, -1001))

    def test_maps_audio_document_with_bilingual_caption(self):
        document = SimpleNamespace(
            id=987654321,
            size=2048,
            mime_type="audio/mpeg",
            attributes=[
                DocumentAttributeAudio(duration=120, voice=False, title="Cours Aqida"),
                DocumentAttributeFilename(file_name="cours.mp3"),
            ],
        )
        message = _message(
            audio=document,
            document=document,
            media=document,
            message=SAMPLE_CAPTION,
        )

        payload = message_to_teaching_payload(
            message,
            -1001087177387,
            channel_username="durusustazalhusaynba",
        )

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.media_type, Teaching.MediaType.AUDIO)
        self.assertEqual(
            payload.title_ar,
            "حكم اقتناء الصور وأقسامها في الفقه الإسلامي",
        )
        self.assertIn("jugement juridique", payload.title_fr)
        self.assertEqual(payload.description, SAMPLE_CAPTION.strip())
        self.assertEqual(payload.file_name, "cours.mp3")
        self.assertEqual(payload.telegram_file_id, "987654321")
        self.assertEqual(payload.telegram_message_id, 42)
        self.assertEqual(
            payload.telegram_message_url,
            "https://t.me/durusustazalhusaynba/42",
        )

    def test_falls_back_to_audio_metadata_when_caption_empty(self):
        document = SimpleNamespace(
            id=987654321,
            size=2048,
            mime_type="audio/mpeg",
            attributes=[
                DocumentAttributeAudio(duration=120, voice=False, title="Cours Aqida"),
                DocumentAttributeFilename(file_name="cours.mp3"),
            ],
        )
        message = _message(
            audio=document,
            document=document,
            media=document,
            message="",
        )

        payload = message_to_teaching_payload(message, -1001087177387)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.title_ar, "Cours Aqida")
        self.assertEqual(payload.title_fr, "")

    def test_maps_voice_notes(self):
        document = SimpleNamespace(
            id=111,
            size=512,
            mime_type="audio/ogg",
            attributes=[DocumentAttributeAudio(duration=10, voice=True)],
        )
        message = _message(voice=document, document=document, message="")

        payload = message_to_teaching_payload(message, -1001)

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.media_type, Teaching.MediaType.VOICE)


class SyncStateTests(TestCase):
    def test_cursor_advances_and_resumes(self):
        state = get_or_create_sync_state(-1001)
        self.assertIsNone(history_offset_id(state))

        state = advance_sync_state(state, scanned_ids=[300, 250, 200])
        self.assertEqual(state.newest_synced_message_id, 300)
        self.assertEqual(state.oldest_synced_message_id, 200)
        self.assertEqual(history_offset_id(state), 200)
        self.assertFalse(state.history_complete)

        state = advance_sync_state(state, scanned_ids=[199, 150])
        self.assertEqual(state.oldest_synced_message_id, 150)
        self.assertEqual(state.newest_synced_message_id, 300)

        state = advance_sync_state(state, scanned_ids=[])
        self.assertTrue(state.history_complete)

        state = reset_sync_state(state)
        self.assertIsNone(state.oldest_synced_message_id)
        self.assertIsNone(state.newest_synced_message_id)
        self.assertFalse(state.history_complete)
        self.assertEqual(ChannelSyncState.objects.count(), 1)

    def test_record_live_message_advances_newest_cursor(self):
        state = record_live_message(-1001, 500)
        self.assertEqual(state.newest_synced_message_id, 500)
        self.assertIsNotNone(state.last_synced_at)

        state = record_live_message(-1001, 510)
        self.assertEqual(state.newest_synced_message_id, 510)

        # An older id (e.g. out-of-order delivery) never moves the cursor back.
        state = record_live_message(-1001, 505)
        self.assertEqual(state.newest_synced_message_id, 510)
        self.assertEqual(ChannelSyncState.objects.count(), 1)

    def test_recent_cursor_advances_without_changing_history_cursor(self):
        state = get_or_create_sync_state(-1001)
        state = advance_sync_state(state, scanned_ids=[100, 75, 50])

        state = advance_recent_sync_state(state, scanned_ids=[101, 102])

        self.assertEqual(state.newest_synced_message_id, 102)
        self.assertEqual(state.oldest_synced_message_id, 50)
        self.assertFalse(state.history_complete)


class ManualCatchUpTests(TestCase):
    def test_catch_up_requires_existing_newest_cursor(self):
        state = get_or_create_sync_state(-1001)
        with self.assertRaises(ValueError):
            catch_up_min_id(state)

        advance_sync_state(state, scanned_ids=[100, 75, 50])
        state.refresh_from_db()
        self.assertEqual(catch_up_min_id(state), 100)

    def test_catch_up_iter_kwargs_use_min_id_ascending(self):
        self.assertEqual(
            history_iter_kwargs(
                limit=2,
                catch_up=True,
                min_id=100,
                offset_id=None,
            ),
            {"limit": 2, "min_id": 100, "reverse": True},
        )
        self.assertEqual(
            history_iter_kwargs(
                limit=2,
                catch_up=False,
                min_id=None,
                offset_id=50,
            ),
            {"limit": 2, "offset_id": 50},
        )

    @patch("apps.telegram_sync.management.commands.sync_history.sync_channel_history")
    def test_sync_history_command_catch_up_flag(self, sync_history):
        async def fake_sync(**kwargs):
            return SyncStats(
                scanned=2,
                matched=1,
                created=1,
                updated=0,
                skipped=1,
                min_id=100,
                oldest_synced_message_id=50,
                newest_synced_message_id=102,
            )

        sync_history.side_effect = fake_sync
        out = StringIO()

        call_command("sync_history", "--catch-up", "--limit", "2", stdout=out)

        sync_history.assert_called_once_with(
            limit=2,
            dry_run=False,
            reset=False,
            catch_up=True,
        )
        self.assertIn("Catch-up sync completed.", out.getvalue())
        self.assertIn("Catch-up after message ID: 100", out.getvalue())

    def test_sync_history_rejects_reset_with_catch_up(self):
        with self.assertRaises(CommandError):
            call_command("sync_history", "--catch-up", "--reset")


class UpsertTeachingTests(TestCase):
    def test_upsert_is_idempotent(self):
        document = SimpleNamespace(
            id=1,
            size=100,
            mime_type="audio/mpeg",
            attributes=[DocumentAttributeFilename(file_name="a.mp3")],
        )
        message = _message(audio=document, document=document, message=SAMPLE_CAPTION)
        payload = message_to_teaching_payload(
            message,
            -1001,
            channel_username="durusustazalhusaynba",
        )
        assert payload is not None

        first, created_first = upsert_teaching(payload)
        second, created_second = upsert_teaching(payload)

        self.assertTrue(created_first)
        self.assertFalse(created_second)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(Teaching.objects.count(), 1)
        self.assertTrue(first.title_ar)
        self.assertTrue(first.title_fr)
        self.assertEqual(first.download_status, Teaching.DownloadStatus.PENDING)
        self.assertEqual(
            first.telegram_message_url,
            "https://t.me/durusustazalhusaynba/42",
        )

    def test_reupsert_preserves_download_progress(self):
        document = SimpleNamespace(
            id=1,
            size=100,
            mime_type="audio/mpeg",
            attributes=[DocumentAttributeFilename(file_name="a.mp3")],
        )
        message = _message(audio=document, document=document, message=SAMPLE_CAPTION)
        payload = message_to_teaching_payload(message, -1001)
        assert payload is not None

        teaching, _ = upsert_teaching(payload)
        teaching.download_status = Teaching.DownloadStatus.READY
        teaching.storage_key = "teachings/-1001/42.mp3"
        teaching.save(update_fields=["download_status", "storage_key"])

        again, created = upsert_teaching(payload)

        self.assertFalse(created)
        self.assertEqual(again.download_status, Teaching.DownloadStatus.READY)
        self.assertEqual(again.storage_key, "teachings/-1001/42.mp3")


class DownloadClaimTests(TestCase):
    def _make_pending(self, message_id, published):
        return Teaching.objects.create(
            telegram_channel_id=-1001,
            telegram_message_id=message_id,
            media_type=Teaching.MediaType.AUDIO,
            file_name=f"{message_id}.mp3",
            published_at=published,
            download_status=Teaching.DownloadStatus.PENDING,
        )

    def test_claim_moves_newest_first_to_processing(self):
        older = self._make_pending(10, datetime(2024, 1, 1, tzinfo=timezone.utc))
        newer = self._make_pending(20, datetime(2024, 6, 1, tzinfo=timezone.utc))

        claimed = claim_pending_teachings(1)

        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].pk, newer.pk)

        older.refresh_from_db()
        newer.refresh_from_db()
        self.assertEqual(newer.download_status, Teaching.DownloadStatus.PROCESSING)
        self.assertEqual(older.download_status, Teaching.DownloadStatus.PENDING)

    def test_admin_requested_downloads_claimed_before_newest(self):
        older_requested = self._make_pending(
            10, datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        older_requested.download_requested_at = datetime(
            2024, 7, 1, tzinfo=timezone.utc
        )
        older_requested.save(update_fields=["download_requested_at"])
        self._make_pending(20, datetime(2024, 6, 1, tzinfo=timezone.utc))

        self.assertTrue(has_priority_pending())

        claimed = claim_pending_teachings(1)

        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].pk, older_requested.pk)

    def test_priority_requests_claimed_oldest_request_first(self):
        second_request = self._make_pending(
            10, datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        second_request.download_requested_at = datetime(
            2024, 7, 2, tzinfo=timezone.utc
        )
        second_request.save(update_fields=["download_requested_at"])

        first_request = self._make_pending(
            20, datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        first_request.download_requested_at = datetime(
            2024, 7, 1, tzinfo=timezone.utc
        )
        first_request.save(update_fields=["download_requested_at"])

        claimed = claim_pending_teachings(1)

        self.assertEqual(claimed[0].pk, first_request.pk)

    def test_priority_only_claim_excludes_backlog(self):
        priority = self._make_pending(10, datetime(2024, 1, 1, tzinfo=timezone.utc))
        priority.download_requested_at = datetime(2024, 7, 1, tzinfo=timezone.utc)
        priority.save(update_fields=["download_requested_at"])
        backlog = self._make_pending(20, datetime(2024, 6, 1, tzinfo=timezone.utc))

        claimed = claim_pending_teachings(2, priority_only=True)

        self.assertEqual(len(claimed), 1)
        self.assertEqual(claimed[0].pk, priority.pk)
        backlog.refresh_from_db()
        self.assertEqual(backlog.download_status, Teaching.DownloadStatus.PENDING)

    def test_mark_ready_and_failed(self):
        teaching = self._make_pending(30, datetime(2024, 1, 1, tzinfo=timezone.utc))
        teaching.download_requested_at = datetime(2024, 7, 1, tzinfo=timezone.utc)
        teaching.force_redownload = True
        teaching.save(update_fields=["download_requested_at", "force_redownload"])

        mark_ready(teaching, "teachings/-1001/30.mp3")
        teaching.refresh_from_db()
        self.assertEqual(teaching.download_status, Teaching.DownloadStatus.READY)
        self.assertEqual(teaching.storage_key, "teachings/-1001/30.mp3")
        self.assertIsNotNone(teaching.downloaded_at)
        self.assertIsNone(teaching.download_requested_at)
        self.assertFalse(teaching.force_redownload)

        teaching.download_requested_at = datetime(2024, 7, 1, tzinfo=timezone.utc)
        teaching.save(update_fields=["download_requested_at"])

        mark_failed(teaching, "boom")
        teaching.refresh_from_db()
        self.assertEqual(teaching.download_status, Teaching.DownloadStatus.FAILED)
        self.assertEqual(teaching.download_error, "boom")
        self.assertIsNone(teaching.download_requested_at)
        self.assertFalse(has_priority_pending())

    @patch("apps.telegram_sync.downloader.storage.find_existing_teaching_key")
    def test_reuse_skips_r2_check_when_force_redownload(self, find_key):
        teaching = self._make_pending(40, datetime(2024, 1, 1, tzinfo=timezone.utc))
        teaching.force_redownload = True
        teaching.save(update_fields=["force_redownload"])

        self.assertIsNone(try_reuse_existing_r2_object(teaching))
        find_key.assert_not_called()

    @patch("apps.telegram_sync.downloader.storage.find_existing_teaching_key")
    def test_reuse_returns_existing_key_when_not_forced(self, find_key):
        teaching = self._make_pending(50, datetime(2024, 1, 1, tzinfo=timezone.utc))
        find_key.return_value = "teachings/-1001/50.mp3"

        self.assertEqual(
            try_reuse_existing_r2_object(teaching),
            "teachings/-1001/50.mp3",
        )
        find_key.assert_called_once()
