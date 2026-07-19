from unittest.mock import patch

from django.contrib import admin
from django.test import TestCase
from rest_framework.test import APIClient

from apps.teachings.admin import TeachingAdmin
from apps.teachings.models import Teaching


class TeachingListApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _make_teaching(self, message_id, status, storage_key=""):
        return Teaching.objects.create(
            telegram_channel_id=-1001,
            telegram_message_id=message_id,
            media_type=Teaching.MediaType.AUDIO,
            download_status=status,
            storage_key=storage_key,
            title_fr=f"Teaching {message_id}",
        )

    def test_list_returns_only_ready_teachings(self):
        ready = self._make_teaching(
            1,
            Teaching.DownloadStatus.READY,
            storage_key="teachings/-1001/1.mp3",
        )
        self._make_teaching(2, Teaching.DownloadStatus.PENDING)
        self._make_teaching(3, Teaching.DownloadStatus.PROCESSING)
        self._make_teaching(4, Teaching.DownloadStatus.FAILED)

        response = self.client.get("/api/teachings/")

        self.assertEqual(response.status_code, 200)
        ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(ids, [ready.pk])

    def test_retrieve_hides_non_ready_teachings(self):
        pending = self._make_teaching(5, Teaching.DownloadStatus.PENDING)

        response = self.client.get(f"/api/teachings/{pending.pk}/")

        self.assertEqual(response.status_code, 404)


class DownloadNowActionTests(TestCase):
    def setUp(self):
        self.model_admin = TeachingAdmin(Teaching, admin.site)

    def _make_teaching(self, message_id, status):
        return Teaching.objects.create(
            telegram_channel_id=-1001,
            telegram_message_id=message_id,
            media_type=Teaching.MediaType.AUDIO,
            download_status=status,
        )

    @patch.object(TeachingAdmin, "message_user")
    def test_download_now_queues_with_priority(self, message_user):
        failed = self._make_teaching(1, Teaching.DownloadStatus.FAILED)
        failed.download_error = "old error"
        failed.save(update_fields=["download_error"])

        self.model_admin.download_now(
            request=None,
            queryset=Teaching.objects.filter(pk=failed.pk),
        )

        failed.refresh_from_db()
        self.assertEqual(failed.download_status, Teaching.DownloadStatus.PENDING)
        self.assertIsNotNone(failed.download_requested_at)
        self.assertEqual(failed.download_error, "")
        message_user.assert_called_once()

    @patch.object(TeachingAdmin, "message_user")
    def test_download_now_skips_ready_and_processing(self, message_user):
        ready = self._make_teaching(2, Teaching.DownloadStatus.READY)
        ready.storage_key = "teachings/-1001/2.mp3"
        ready.save(update_fields=["storage_key"])
        processing = self._make_teaching(3, Teaching.DownloadStatus.PROCESSING)

        self.model_admin.download_now(
            request=None,
            queryset=Teaching.objects.filter(pk__in=[ready.pk, processing.pk]),
        )

        ready.refresh_from_db()
        processing.refresh_from_db()
        self.assertEqual(ready.download_status, Teaching.DownloadStatus.READY)
        self.assertEqual(ready.storage_key, "teachings/-1001/2.mp3")
        self.assertIsNone(ready.download_requested_at)
        self.assertEqual(
            processing.download_status,
            Teaching.DownloadStatus.PROCESSING,
        )
        self.assertIsNone(processing.download_requested_at)


class ReconcileWithR2ActionTests(TestCase):
    def setUp(self):
        self.model_admin = TeachingAdmin(Teaching, admin.site)

    def _make_teaching(self, message_id, status, storage_key=""):
        return Teaching.objects.create(
            telegram_channel_id=-1001,
            telegram_message_id=message_id,
            media_type=Teaching.MediaType.AUDIO,
            download_status=status,
            storage_key=storage_key,
        )

    @patch.object(TeachingAdmin, "message_user")
    @patch("apps.teachings.admin.storage.find_existing_teaching_key")
    def test_reconcile_restores_ready_or_sets_pending(
        self,
        find_key,
        message_user,
    ):
        recoverable = self._make_teaching(10, Teaching.DownloadStatus.FAILED)
        missing = self._make_teaching(
            20,
            Teaching.DownloadStatus.READY,
            storage_key="teachings/-1001/20.mp3",
        )
        processing = self._make_teaching(
            30,
            Teaching.DownloadStatus.PROCESSING,
        )
        find_key.side_effect = [
            "teachings/-1001/10.ogg",
            None,
        ]

        self.model_admin.reconcile_with_r2(
            request=None,
            queryset=Teaching.objects.filter(
                pk__in=[recoverable.pk, missing.pk, processing.pk],
            ).order_by("telegram_message_id"),
        )

        recoverable.refresh_from_db()
        missing.refresh_from_db()
        processing.refresh_from_db()
        self.assertEqual(
            recoverable.download_status,
            Teaching.DownloadStatus.READY,
        )
        self.assertEqual(
            recoverable.storage_key,
            "teachings/-1001/10.ogg",
        )
        self.assertEqual(
            missing.download_status,
            Teaching.DownloadStatus.PENDING,
        )
        self.assertEqual(missing.storage_key, "")
        self.assertEqual(
            processing.download_status,
            Teaching.DownloadStatus.PROCESSING,
        )
        self.assertEqual(find_key.call_count, 2)
        message_user.assert_called_once()

    @patch.object(TeachingAdmin, "message_user")
    def test_requeue_sets_force_redownload(self, message_user):
        ready = self._make_teaching(
            40,
            Teaching.DownloadStatus.READY,
            storage_key="teachings/-1001/40.mp3",
        )

        self.model_admin.requeue_download(
            request=None,
            queryset=Teaching.objects.filter(pk=ready.pk),
        )

        ready.refresh_from_db()
        self.assertEqual(ready.download_status, Teaching.DownloadStatus.PENDING)
        self.assertEqual(ready.storage_key, "")
        self.assertTrue(ready.force_redownload)
        message_user.assert_called_once()

    @patch.object(TeachingAdmin, "message_user")
    def test_download_now_clears_force_redownload(self, message_user):
        failed = self._make_teaching(50, Teaching.DownloadStatus.FAILED)
        failed.force_redownload = True
        failed.save(update_fields=["force_redownload"])

        self.model_admin.download_now(
            request=None,
            queryset=Teaching.objects.filter(pk=failed.pk),
        )

        failed.refresh_from_db()
        self.assertEqual(failed.download_status, Teaching.DownloadStatus.PENDING)
        self.assertFalse(failed.force_redownload)
        self.assertIsNotNone(failed.download_requested_at)
        message_user.assert_called_once()
