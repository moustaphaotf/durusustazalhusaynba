from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from apps.telegram_sync.client import create_telegram_client
from apps.telegram_sync.config import TelegramConfig, get_telegram_config

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
                TELEGRAM_SESSION_PATH=str(session_path),
            ):
                config = get_telegram_config()

            self.assertEqual(config.session_path, session_path)
            self.assertTrue(session_path.parent.is_dir())


class TelegramClientTests(SimpleTestCase):
    @patch("apps.telegram_sync.client.TelegramClient")
    def test_client_uses_explicit_configuration(self, client_class):
        config = TelegramConfig(
            api_id=12345,
            api_hash="test-hash",
            channel_id=-1001234567890,
            session_path=Path("/tmp/durus"),
        )

        create_telegram_client(config)

        client_class.assert_called_once_with(
            str(config.session_path),
            config.api_id,
            config.api_hash,
        )
