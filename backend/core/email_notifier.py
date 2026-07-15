import asyncio
import smtplib
from email.message import EmailMessage
from core.config import settings
from core.logging import logger


async def send_email(subject: str, html_body: str) -> None:
    if not settings.smtp_enabled:
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = settings.notification_email_to
    msg.set_content(html_body, subtype="html")

    def _send():
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
                if settings.smtp_port == 587:
                    server.starttls()
                pw = settings.effective_smtp_password
                if settings.smtp_username and pw:
                    server.login(settings.smtp_username, pw)
                server.send_message(msg)
        except Exception as e:
            logger.warning(f"Failed to send email notification: {e}")

    await asyncio.to_thread(_send)


async def notify_pending_approval_email(
    request_id: str,
    agent_id: str,
    tool_name: str,
    risk_level: str,
    risk_reason: str | None,
) -> None:
    html = f"""<h2>Pending Approval Request</h2>
<table style="border-collapse:collapse;width:100%;max-width:600px">
<tr style="background:#f3f4f6"><td style="padding:8px;font-weight:bold">Agent</td><td style="padding:8px">{agent_id}</td></tr>
<tr><td style="padding:8px;font-weight:bold">Tool</td><td style="padding:8px">{tool_name}</td></tr>
<tr style="background:#f3f4f6"><td style="padding:8px;font-weight:bold">Risk Level</td><td style="padding:8px">{risk_level.upper()}</td></tr>
<tr><td style="padding:8px;font-weight:bold">Reason</td><td style="padding:8px">{risk_reason or 'N/A'}</td></tr>
</table>
<p><a href="{settings.frontend_url}/approvals" style="display:inline-block;padding:10px 20px;background:#6366f1;color:#fff;text-decoration:none;border-radius:6px">Review in Dashboard</a></p>"""
    await send_email(f"[MCP Bridge] Pending Approval - {agent_id}/{tool_name}", html)


async def notify_approval_resolved_email(
    request_id: str,
    agent_id: str,
    tool_name: str,
    status: str,
    reviewer_note: str | None,
) -> None:
    html = f"""<h2>Approval {status.title()}</h2>
<table style="border-collapse:collapse;width:100%;max-width:600px">
<tr style="background:#f3f4f6"><td style="padding:8px;font-weight:bold">Agent</td><td style="padding:8px;font-weight:bold">{agent_id}</td></tr>
<tr><td style="padding:8px;font-weight:bold">Tool</td><td style="padding:8px">{tool_name}</td></tr>
<tr style="background:#f3f4f6"><td style="padding:8px;font-weight:bold">Status</td><td style="padding:8px">{status.upper()}</td></tr>
</table>"""
    if reviewer_note:
        html += f"<p><strong>Note:</strong> {reviewer_note}</p>"
    await send_email(f"[MCP Bridge] Approval {status.title()} - {agent_id}/{tool_name}", html)
