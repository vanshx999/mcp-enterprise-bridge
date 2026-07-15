import json
import httpx
from core.config import settings
from core.logging import logger
from core.email_notifier import notify_pending_approval_email, notify_approval_resolved_email


async def send_slack_notification(message: str, webhook_url: str | None = None) -> None:
    url = webhook_url or settings.slack_webhook_url
    if not url:
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"text": message})
            resp.raise_for_status()
    except Exception as e:
        logger.warning(f"Failed to send Slack notification: {e}")


async def notify_pending_approval(
    request_id: str,
    agent_id: str,
    tool_name: str,
    tool_args: dict,
    risk_level: str,
    risk_reason: str | None,
) -> None:
    args_summary = json.dumps(tool_args, default=str)[:200]
    message = (
        f"*Pending Approval*\n"
        f"• Agent: `{agent_id}`\n"
        f"• Tool: `{tool_name}`\n"
        f"• Args: `{args_summary}`\n"
        f"• Risk: *{risk_level.upper()}*\n"
        f"• Reason: {risk_reason or 'N/A'}\n"
        f"• Approve: `POST /api/approvals/{request_id}/approve`"
    )
    await send_slack_notification(message)
    await notify_pending_approval_email(request_id, agent_id, tool_name, risk_level, risk_reason)
