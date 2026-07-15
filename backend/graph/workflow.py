from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from graph.state import BridgeState, ApprovalStatus
from graph.nodes import (
    intent_analysis_node,
    permission_check_node,
    hitl_gate_node,
    mcp_execution_node,
    audit_log_node,
)


def route_after_permission(state: BridgeState) -> str:
    if state.get("final_response") or not state.get("has_permission"):
        return "audit_log_node"
    return "hitl_gate_node"


def route_after_hitl(state: BridgeState) -> str:
    if state.get("final_response") or state.get("error_message"):
        return "audit_log_node"
    if state.get("approval_status") == ApprovalStatus.APPROVED:
        return "mcp_execution_node"
    return "audit_log_node"


def route_after_intent(state: BridgeState) -> str:
    if state.get("final_response"):
        return "audit_log_node"
    return "permission_check_node"


def build_graph() -> StateGraph:
    builder = StateGraph(BridgeState)

    builder.add_node("intent_analysis_node", intent_analysis_node)
    builder.add_node("permission_check_node", permission_check_node)
    builder.add_node("hitl_gate_node", hitl_gate_node)
    builder.add_node("mcp_execution_node", mcp_execution_node)
    builder.add_node("audit_log_node", audit_log_node)

    builder.add_edge(START, "intent_analysis_node")
    builder.add_conditional_edges(
        "intent_analysis_node",
        route_after_intent,
        {"permission_check_node": "permission_check_node", "audit_log_node": "audit_log_node"},
    )
    builder.add_conditional_edges(
        "permission_check_node",
        route_after_permission,
        {"hitl_gate_node": "hitl_gate_node", "audit_log_node": "audit_log_node"},
    )
    builder.add_conditional_edges(
        "hitl_gate_node",
        route_after_hitl,
        {"mcp_execution_node": "mcp_execution_node", "audit_log_node": "audit_log_node"},
    )
    builder.add_edge("mcp_execution_node", "audit_log_node")
    builder.add_edge("audit_log_node", END)

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


graph = build_graph()
