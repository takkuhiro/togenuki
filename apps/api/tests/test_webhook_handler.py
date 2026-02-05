"""Tests for Gmail Pub/Sub Webhook Handler."""

import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from src.main import app


class TestWebhookEndpoint:
    """Tests for POST /api/webhook/gmail endpoint."""

    @pytest.fixture
    def valid_pubsub_message(self) -> dict:
        """Create a valid Pub/Sub message payload."""
        data = {
            "emailAddress": "user@example.com",
            "historyId": "12345"
        }
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
        return {
            "message": {
                "data": encoded_data,
                "messageId": "msg-123",
                "publishTime": "2024-01-01T00:00:00Z"
            },
            "subscription": "projects/test/subscriptions/gmail-push"
        }

    @pytest.fixture
    def invalid_pubsub_message_missing_data(self) -> dict:
        """Create a Pub/Sub message without data field."""
        return {
            "message": {
                "messageId": "msg-123",
                "publishTime": "2024-01-01T00:00:00Z"
            },
            "subscription": "projects/test/subscriptions/gmail-push"
        }

    @pytest.fixture
    def invalid_pubsub_message_invalid_base64(self) -> dict:
        """Create a Pub/Sub message with invalid base64 data."""
        return {
            "message": {
                "data": "not-valid-base64!!!",
                "messageId": "msg-123",
                "publishTime": "2024-01-01T00:00:00Z"
            },
            "subscription": "projects/test/subscriptions/gmail-push"
        }

    @pytest.mark.asyncio
    async def test_webhook_returns_200_immediately(
        self, valid_pubsub_message: dict
    ):
        """Test that webhook returns 200 OK immediately for valid message."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            with patch(
                "src.routers.webhook.process_gmail_notification",
                new_callable=AsyncMock
            ):
                response = await client.post(
                    "/api/webhook/gmail",
                    json=valid_pubsub_message
                )

        assert response.status_code == 200
        assert response.json() == {"status": "accepted"}

    @pytest.mark.asyncio
    async def test_webhook_decodes_pubsub_message_correctly(
        self, valid_pubsub_message: dict
    ):
        """Test that webhook correctly decodes base64 Pub/Sub data."""
        from src.routers.webhook import decode_pubsub_data

        # Test the decode function directly
        data = {
            "emailAddress": "user@example.com",
            "historyId": "12345"
        }
        encoded = base64.b64encode(json.dumps(data).encode()).decode()

        result = decode_pubsub_data(encoded)

        assert result.emailAddress == "user@example.com"
        assert result.historyId == "12345"

    @pytest.mark.asyncio
    async def test_webhook_returns_400_for_missing_data(
        self, invalid_pubsub_message_missing_data: dict
    ):
        """Test that webhook returns 400 for message without data field."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/webhook/gmail",
                json=invalid_pubsub_message_missing_data
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_returns_400_for_invalid_base64(
        self, invalid_pubsub_message_invalid_base64: dict
    ):
        """Test that webhook returns 400 for invalid base64 data."""
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/webhook/gmail",
                json=invalid_pubsub_message_invalid_base64
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_returns_400_for_invalid_json_in_data(self):
        """Test that webhook returns 400 when decoded data is not valid JSON."""
        invalid_json_data = base64.b64encode(b"not json").decode()
        payload = {
            "message": {
                "data": invalid_json_data,
                "messageId": "msg-123",
                "publishTime": "2024-01-01T00:00:00Z"
            },
            "subscription": "projects/test/subscriptions/gmail-push"
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/webhook/gmail",
                json=payload
            )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_webhook_adds_to_background_tasks(
        self, valid_pubsub_message: dict
    ):
        """Test that webhook adds processing to background tasks."""
        from fastapi import BackgroundTasks

        mock_bg_tasks = MagicMock(spec=BackgroundTasks)

        # Test that is_duplicate_notification returns False so task is added
        with patch(
            "src.routers.webhook.is_duplicate_notification",
            return_value=False
        ):
            from src.routers.webhook import (
                handle_gmail_webhook,
                PubSubMessage,
                process_gmail_notification,
            )

            payload = PubSubMessage(**valid_pubsub_message)
            await handle_gmail_webhook(payload, mock_bg_tasks)

        # Verify background task was added
        mock_bg_tasks.add_task.assert_called_once()
        call_args = mock_bg_tasks.add_task.call_args
        assert call_args[0][0] == process_gmail_notification
        assert call_args[0][1] == "user@example.com"
        assert call_args[0][2] == "12345"


class TestDuplicateNotificationDetection:
    """Tests for duplicate notification detection based on historyId."""

    @pytest.fixture
    def pubsub_message_with_history(self) -> dict:
        """Create a Pub/Sub message with specific historyId."""
        def _create(history_id: str) -> dict:
            data = {
                "emailAddress": "user@example.com",
                "historyId": history_id
            }
            encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
            return {
                "message": {
                    "data": encoded_data,
                    "messageId": f"msg-{history_id}",
                    "publishTime": "2024-01-01T00:00:00Z"
                },
                "subscription": "projects/test/subscriptions/gmail-push"
            }
        return _create

    @pytest.mark.asyncio
    async def test_duplicate_history_id_is_detected(
        self, pubsub_message_with_history
    ):
        """Test that duplicate historyId notifications are detected and skipped."""
        message1 = pubsub_message_with_history("99999")
        message2 = pubsub_message_with_history("99999")  # Same historyId

        call_count = 0

        async def count_calls(email: str, history_id: str):
            nonlocal call_count
            call_count += 1

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            with patch(
                "src.routers.webhook.process_gmail_notification",
                side_effect=count_calls
            ):
                with patch(
                    "src.routers.webhook.is_duplicate_notification",
                    side_effect=[False, True]  # First is new, second is duplicate
                ):
                    response1 = await client.post(
                        "/api/webhook/gmail",
                        json=message1
                    )
                    response2 = await client.post(
                        "/api/webhook/gmail",
                        json=message2
                    )

        # Both should return 200 (we always acknowledge Pub/Sub)
        assert response1.status_code == 200
        assert response2.status_code == 200
        # But processing should only happen once
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_different_history_ids_are_processed(
        self, pubsub_message_with_history
    ):
        """Test that different historyIds trigger separate processing."""
        message1 = pubsub_message_with_history("11111")
        message2 = pubsub_message_with_history("22222")

        call_count = 0

        async def count_calls(email: str, history_id: str):
            nonlocal call_count
            call_count += 1

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            with patch(
                "src.routers.webhook.process_gmail_notification",
                side_effect=count_calls
            ):
                with patch(
                    "src.routers.webhook.is_duplicate_notification",
                    return_value=False  # Both are new
                ):
                    await client.post("/api/webhook/gmail", json=message1)
                    await client.post("/api/webhook/gmail", json=message2)

        assert call_count == 2


class TestPubSubMessageSchema:
    """Tests for Pub/Sub message validation schema."""

    @pytest.mark.asyncio
    async def test_missing_message_field_returns_422(self):
        """Test that missing 'message' field returns 422 validation error."""
        payload = {"subscription": "test"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/webhook/gmail",
                json=payload
            )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_subscription_field_returns_422(self):
        """Test that missing 'subscription' field returns 422 validation error."""
        data = {"emailAddress": "user@example.com", "historyId": "12345"}
        payload = {
            "message": {
                "data": base64.b64encode(json.dumps(data).encode()).decode(),
                "messageId": "msg-123",
                "publishTime": "2024-01-01T00:00:00Z"
            }
        }

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/webhook/gmail",
                json=payload
            )

        assert response.status_code == 422
