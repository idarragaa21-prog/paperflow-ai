from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from smtplib import SMTP, SMTPException, SMTP_SSL

from app.config import settings
from app.core.logger import logger
from app.models.membership import ProjectInvitation
from app.models.project import Project
from app.models.user import User


@dataclass(slots=True)
class EmailDeliveryResult:
    status: str
    method: str
    detail: str | None = None

    @property
    def sent(self) -> bool:
        return self.status == "sent"


def build_project_invitation_url(token: str) -> str:
    return f"{settings.invitation_base_url}/project-invitations/{token}"


def send_email(*, to_email: str, subject: str, text_body: str, html_body: str | None = None) -> EmailDeliveryResult:
    if not settings.mail_configured:
        return EmailDeliveryResult(
            status="manual_required",
            method="manual_link",
            detail="SMTP is not configured for this environment.",
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.MAIL_FROM_EMAIL
    message["To"] = to_email
    message.set_content(text_body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    smtp_cls = SMTP_SSL if settings.MAIL_SMTP_USE_SSL else SMTP

    try:
        with smtp_cls(settings.MAIL_SMTP_HOST, settings.MAIL_SMTP_PORT, timeout=15) as smtp:
            if settings.MAIL_SMTP_USE_TLS and not settings.MAIL_SMTP_USE_SSL:
                smtp.starttls()
            if settings.MAIL_SMTP_USERNAME:
                smtp.login(settings.MAIL_SMTP_USERNAME, settings.MAIL_SMTP_PASSWORD or "")
            smtp.send_message(message)
        return EmailDeliveryResult(status="sent", method="smtp", detail="Invitation email sent.")
    except (OSError, SMTPException) as exc:
        logger.warning("Email delivery failed to {} via SMTP: {}", to_email, exc)
        return EmailDeliveryResult(
            status="manual_required",
            method="manual_link",
            detail="SMTP delivery failed; share the secure link manually.",
        )


def send_project_invitation_email(
    *,
    invitation: ProjectInvitation,
    project: Project,
    invited_by: User,
) -> EmailDeliveryResult:
    invitation_url = build_project_invitation_url(invitation.token)
    subject = f"Invitation to collaborate on {project.title} in PaperFlow AI"
    inviter_name = invited_by.full_name or invited_by.email
    text_body = "\n".join(
        [
            f"{inviter_name} invited you to collaborate on the PaperFlow project \"{project.title}\".",
            f"Assigned role: {invitation.role}.",
            "",
            "Open this secure invitation link to accept access:",
            invitation_url,
            "",
            "If you do not recognize this invitation, you can ignore this message.",
        ]
    )
    html_body = (
        f"<p><strong>{inviter_name}</strong> invited you to collaborate on "
        f"<strong>{project.title}</strong> in PaperFlow AI.</p>"
        f"<p>Assigned role: <strong>{invitation.role}</strong>.</p>"
        f"<p><a href=\"{invitation_url}\">Open the secure invitation link</a></p>"
        "<p>If you do not recognize this invitation, you can ignore this message.</p>"
    )
    return send_email(
        to_email=invitation.email,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
    )


def send_password_reset_code_email(*, to_email: str, code: str) -> EmailDeliveryResult:
    return send_email(
        to_email=to_email,
        subject="PaperFlow AI password reset code",
        text_body="\n".join(
            [
                "You requested a password reset for PaperFlow AI.",
                f"Your verification code is: {code}",
                "",
                "If you did not request this, you can ignore this message.",
            ]
        ),
        html_body=(
            "<p>You requested a password reset for PaperFlow AI.</p>"
            f"<p>Your verification code is <strong>{code}</strong>.</p>"
            "<p>If you did not request this, you can ignore this message.</p>"
        ),
    )
