from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings
from rest_framework import status
from rest_framework.test import APIRequestFactory

from apps.monitoring.discord import send_discord_alert
from apps.monitoring.middleware import DiscordExceptionMiddleware
from apps.monitoring.views import ClientErrorReportView


class DiscordAlertTests(SimpleTestCase):
    @override_settings(DISCORD_WEBHOOK_URL="")
    def test_send_alert_noop_without_webhook(self):
        self.assertFalse(
            send_discord_alert(
                source="api",
                title="Test",
                message="boom",
            )
        )

    @override_settings(DISCORD_WEBHOOK_URL="https://discord.test/webhook")
    @patch("apps.monitoring.discord.urllib.request.urlopen")
    def test_send_alert_posts_embed(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.status = 204

        sent = send_discord_alert(
            source="api",
            title="Server error",
            message="Something broke",
            path="/api/teachings/",
            method="GET",
            status_code=500,
            stack="Traceback...",
        )

        self.assertTrue(sent)
        mock_urlopen.assert_called_once()
        request = mock_urlopen.call_args[0][0]
        self.assertEqual(request.full_url, "https://discord.test/webhook")
        body = request.data.decode("utf-8")
        self.assertIn("Something broke", body)
        self.assertIn("Durus Alerts", body)


class DiscordMiddlewareTests(SimpleTestCase):
    @override_settings(DISCORD_WEBHOOK_URL="https://discord.test/webhook")
    @patch("apps.monitoring.middleware.send_discord_alert")
    def test_process_exception_alerts_discord(self, mock_alert):
        factory = RequestFactory()
        request = factory.get("/boom/")
        middleware = DiscordExceptionMiddleware(lambda req: None)

        result = middleware.process_exception(request, RuntimeError("kaboom"))

        self.assertIsNone(result)
        mock_alert.assert_called_once()
        kwargs = mock_alert.call_args.kwargs
        self.assertEqual(kwargs["source"], "api")
        self.assertIn("kaboom", kwargs["message"])


class ClientErrorReportApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    @patch("apps.monitoring.views.send_discord_alert")
    def test_accepts_frontend_error_report(self, mock_alert):
        request = self.factory.post(
            "/api/client-errors/",
            {
                "message": "Failed to fetch teachings",
                "stack": "ApiError: API 500",
                "url": "https://durus.example.com/",
                "component": "Home",
            },
            format="json",
        )
        response = ClientErrorReportView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        mock_alert.assert_called_once()
        self.assertEqual(mock_alert.call_args.kwargs["source"], "frontend")

    def test_rejects_empty_message(self):
        request = self.factory.post("/api/client-errors/", {}, format="json")
        response = ClientErrorReportView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
