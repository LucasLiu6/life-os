from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.telegram import client as telegram_client


client = TestClient(app)


def test_send_telegram_message_requires_bot_token() -> None:
    settings = Mock(telegram_bot_token=None, telegram_chat_id="123")
    with patch("app.telegram.client.settings", settings):
        try:
            telegram_client.send_telegram_message("hello", chat_id="123")
        except RuntimeError as error:
            assert "TELEGRAM_BOT_TOKEN" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")


def test_send_telegram_message_requires_chat_id() -> None:
    settings = Mock(telegram_bot_token="token", telegram_chat_id=None)
    with patch("app.telegram.client.settings", settings):
        try:
            telegram_client.send_telegram_message("hello")
        except RuntimeError as error:
            assert "TELEGRAM_CHAT_ID" in str(error)
        else:
            raise AssertionError("Expected RuntimeError")


def test_send_telegram_message_uses_configured_chat_id() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    settings = Mock(telegram_bot_token="token", telegram_chat_id="configured-chat")

    with (
        patch("app.telegram.client.settings", settings),
        patch("app.telegram.client.httpx.post", return_value=response) as post,
    ):
        telegram_client.send_telegram_message("hello")

    post.assert_called_once_with(
        "https://api.telegram.org/bottoken/sendMessage",
        json={"chat_id": "configured-chat", "text": "hello"},
        timeout=10,
    )


def test_send_telegram_message_uses_explicit_chat_id() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    settings = Mock(telegram_bot_token="token", telegram_chat_id="configured-chat")

    with (
        patch("app.telegram.client.settings", settings),
        patch("app.telegram.client.httpx.post", return_value=response) as post,
    ):
        telegram_client.send_telegram_message("hello", chat_id="webhook-chat")

    assert post.call_args.kwargs["json"] == {
        "chat_id": "webhook-chat",
        "text": "hello",
    }


def test_send_telegram_message_splits_long_messages() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    settings = Mock(telegram_bot_token="token", telegram_chat_id="configured-chat")

    with (
        patch("app.telegram.client.settings", settings),
        patch("app.telegram.client.httpx.post", return_value=response) as post,
    ):
        telegram_client.send_telegram_message("x" * 3901)

    assert post.call_count == 2
    assert len(post.call_args_list[0].kwargs["json"]["text"]) == 3900
    assert len(post.call_args_list[1].kwargs["json"]["text"]) == 1


def test_send_test_message_route_returns_sent() -> None:
    with patch("app.api.telegram.send_telegram_message") as send:
        response = client.post("/telegram/send-test-message")

    assert response.status_code == 200
    assert response.json() == {"status": "sent"}
    send.assert_called_once_with("Life OS test message.")


def test_webhook_unknown_shape_is_ignored() -> None:
    with patch("app.api.telegram.send_telegram_message") as send:
        response = client.post("/telegram/webhook", json={"not_message": {}})

    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    send.assert_not_called()


def test_webhook_start_sends_welcome_message() -> None:
    with patch("app.api.telegram.send_telegram_message") as send:
        response = client.post(
            "/telegram/webhook",
            json={"message": {"chat": {"id": 123}, "text": "/start"}},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "handled"}
    send.assert_called_once()
    assert "Welcome to Life OS" in send.call_args.args[0]
    assert send.call_args.kwargs["chat_id"] == "123"


def test_webhook_morning_calls_generator_and_sends_result() -> None:
    with (
        patch("app.api.telegram.generate_morning_briefing", return_value="Morning brief") as generator,
        patch("app.api.telegram.send_telegram_message") as send,
    ):
        response = client.post(
            "/telegram/webhook",
            json={"message": {"chat": {"id": 123}, "text": "/morning"}},
        )

    assert response.status_code == 200
    generator.assert_called_once_with()
    send.assert_called_once_with("Morning brief", chat_id="123")


def test_webhook_evening_calls_generator_and_sends_result() -> None:
    with (
        patch("app.api.telegram.generate_evening_checkin", return_value="Evening check-in") as generator,
        patch("app.api.telegram.send_telegram_message") as send,
    ):
        response = client.post(
            "/telegram/webhook",
            json={"message": {"chat": {"id": 123}, "text": "/evening"}},
        )

    assert response.status_code == 200
    generator.assert_called_once_with()
    send.assert_called_once_with("Evening check-in", chat_id="123")


def test_webhook_weekly_calls_generator_and_sends_result() -> None:
    with (
        patch("app.api.telegram.generate_weekly_review", return_value="Weekly review") as generator,
        patch("app.api.telegram.send_telegram_message") as send,
    ):
        response = client.post(
            "/telegram/webhook",
            json={"message": {"chat": {"id": 123}, "text": "/weekly"}},
        )

    assert response.status_code == 200
    generator.assert_called_once_with(None, None)
    send.assert_called_once_with("Weekly review", chat_id="123")


def test_webhook_unknown_text_sends_help_without_parser() -> None:
    with (
        patch("app.api.telegram.send_telegram_message") as send,
        patch("app.services.evening_reply_parser.parse_evening_reply") as parser,
    ):
        response = client.post(
            "/telegram/webhook",
            json={"message": {"chat": {"id": 123}, "text": "I finished my work"}},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "handled"}
    assert "Available commands" in send.call_args.args[0]
    parser.assert_not_called()
