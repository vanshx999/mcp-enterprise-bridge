from typing import TypedDict, Optional, Any
from enum import Enum


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class BridgeState(TypedDict):
    session_id: str
    agent_id: str
    user_message: str

    tool_name: Optional[str]
    tool_args: Optional[dict]
    intent_summary: Optional[str]
    db_name: Optional[str]

    has_permission: Optional[bool]
    risk_level: Optional[RiskLevel]
    risk_reason: Optional[str]
    auto_approve: Optional[bool]

    approval_request_id: Optional[str]
    approval_status: Optional[ApprovalStatus]
    reviewer_note: Optional[str]

    tool_result: Optional[Any]
    execution_error: Optional[str]

    final_response: Optional[str]
    error_message: Optional[str]
