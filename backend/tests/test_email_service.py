from __future__ import annotations

from app.services import email as email_service


def test_build_project_invitation_url_uses_configured_app_base(monkeypatch):
    monkeypatch.setattr(email_service.settings, "APP_BASE_URL", "https://app.paperflow.ai/")

    assert email_service.build_project_invitation_url("tok-123") == "https://app.paperflow.ai/project-invitations/tok-123"


def test_send_email_returns_manual_fallback_when_mail_is_not_configured(monkeypatch):
    monkeypatch.setattr(email_service.settings, "MAIL_ENABLED", False)
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_HOST", None)
    monkeypatch.setattr(email_service.settings, "MAIL_FROM_EMAIL", None)

    result = email_service.send_email(
        to_email="invitee@example.com",
        subject="PaperFlow invite",
        text_body="Join the project",
    )

    assert result.status == "manual_required"
    assert result.method == "manual_link"
    assert "SMTP" in (result.detail or "")


def test_send_email_uses_smtp_when_configured(monkeypatch):
    sent_messages: list[tuple[str, str]] = []

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int):
            assert host == "smtp.paperflow.test"
            assert port == 2525
            assert timeout == 15

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            sent_messages.append(("tls", "started"))

        def login(self, username: str, password: str):
            sent_messages.append(("login", f"{username}:{password}"))

        def send_message(self, message):
            sent_messages.append((message["To"], message["Subject"]))

    monkeypatch.setattr(email_service.settings, "MAIL_ENABLED", True)
    monkeypatch.setattr(email_service.settings, "MAIL_FROM_EMAIL", "noreply@paperflow.test")
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_HOST", "smtp.paperflow.test")
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_PORT", 2525)
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_USE_TLS", True)
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_USE_SSL", False)
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_USERNAME", "mailer")
    monkeypatch.setattr(email_service.settings, "MAIL_SMTP_PASSWORD", "secret")
    monkeypatch.setattr(email_service, "SMTP", FakeSMTP)

    result = email_service.send_email(
        to_email="invitee@example.com",
        subject="PaperFlow invite",
        text_body="Join the project",
    )

    assert result.status == "sent"
    assert result.method == "smtp"
    assert ("tls", "started") in sent_messages
    assert ("login", "mailer:secret") in sent_messages
    assert ("invitee@example.com", "PaperFlow invite") in sent_messages
