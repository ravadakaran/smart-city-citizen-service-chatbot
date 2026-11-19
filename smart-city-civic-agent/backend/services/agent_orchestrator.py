import os
import re
from typing import TypedDict
from dotenv import load_dotenv
import psycopg

load_dotenv()
from langgraph.graph import END, StateGraph
from services.rag_engine import answer_policy_query

DB_DSN = os.getenv("DATABASE_URL", "postgresql://civic_admin:civic_password@localhost:5434/smartcity_db")


class AgentState(TypedDict):
    session_id: str
    user_message: str
    intent: str
    reply: str
    citations: list[str]
    grounded: bool
    metadata: dict


def classify_intent_node(state: AgentState) -> AgentState:
    msg = state["user_message"].strip()
    lower = msg.lower()

    uuid_match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", msg)
    prop_match = re.search(r"PROP-\d{4}-\d{3}", msg.upper())

    if uuid_match or ("status" in lower and "ticket" in lower):
        intent = "TICKET_STATUS"
    elif prop_match or ("bill" in lower and ("tax" in lower or "water" in lower or "dues" in lower)):
        intent = "UTILITY_BILL"
    elif any(k in lower for k in ["report a", "file a complaint", "pothole", "garbage", "streetlight", "water leak", "broken wire"]):
        intent = "GRIEVANCE_GUIDE"
    else:
        intent = "POLICY_QA"

    return {**state, "intent": intent}


def execute_tool_node(state: AgentState) -> AgentState:
    intent = state["intent"]
    msg = state["user_message"]

    if intent == "TICKET_STATUS":
        uuid_match = re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", msg)
        if not uuid_match:
            return {
                **state,
                "reply": "Please share your 36-character Ticket ID (for example, `11111111-1111-1111-1111-111111111101`) so I can look up its live ward status and SLA timeline.",
                "citations": [],
                "grounded": True,
                "metadata": {"intent": intent},
            }
        tid = uuid_match.group(0)
        try:
            with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ticket_id, department_code, issue_subcategory, severity, status, upvote_count, sla_deadline
                    FROM tickets WHERE ticket_id = %s;
                    """,
                    (tid,),
                )
                row = cur.fetchone()
                if not row:
                    return {
                        **state,
                        "reply": f"No civic ticket was found with ID `{tid}`. Please verify the tracking number.",
                        "citations": [],
                        "grounded": True,
                        "metadata": {"intent": intent},
                    }
                _, dept, subcat, sev, status, upvotes, sla = row
                return {
                    **state,
                    "reply": (
                        f"**Ticket `{tid}` Status Update:**\n"
                        f"- **Department:** {dept}\n"
                        f"- **Issue:** {subcat} (Severity: **{sev}**)\n"
                        f"- **Current Status:** **{status}**\n"
                        f"- **Community Upvotes:** {upvotes}\n"
                        f"- **Target SLA Deadline:** {sla.strftime('%Y-%m-%d %H:%M UTC')}"
                    ),
                    "citations": ["Municipal 311 Live Ticketing Ledger"],
                    "grounded": True,
                    "metadata": {"intent": intent, "ticket_id": tid, "status": status},
                }
        except Exception as exc:
            return {
                **state,
                "reply": f"Unable to query ticket ledger right now: {exc}",
                "citations": [],
                "grounded": False,
                "metadata": {"intent": intent},
            }

    if intent == "UTILITY_BILL":
        prop_match = re.search(r"PROP-\d{4}-\d{3}", msg.upper())
        if not prop_match:
            return {
                **state,
                "reply": "Please provide your Property Assessment ID (e.g., `PROP-2026-001`) to fetch your current property tax and water charge dues.",
                "citations": [],
                "grounded": True,
                "metadata": {"intent": intent},
            }
        pid = prop_match.group(0)
        try:
            with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT assessment_id, owner_name, ward_code, property_tax_due, water_charge_due, due_date
                    FROM utility_bills WHERE assessment_id = %s;
                    """,
                    (pid,),
                )
                row = cur.fetchone()
                if not row:
                    return {
                        **state,
                        "reply": f"No utility account found for Assessment ID `{pid}`.",
                        "citations": [],
                        "grounded": True,
                        "metadata": {"intent": intent},
                    }
                _, owner, ward, ptax, water, due = row
                total = float(ptax) + float(water)
                return {
                    **state,
                    "reply": (
                        f"**Utility Dues Summary for `{pid}` ({owner} — {ward}):**\n"
                        f"- **Property Tax Due:** INR {ptax:,.2f}\n"
                        f"- **Water Supply Charge Due:** INR {water:,.2f}\n"
                        f"- **Total Payable:** **INR {total:,.2f}** (Due by {due})"
                    ),
                    "citations": ["Municipal Revenue & Water Billing Database"],
                    "grounded": True,
                    "metadata": {"intent": intent, "assessment_id": pid, "total_due": total},
                }
        except Exception as exc:
            return {
                **state,
                "reply": f"Billing database unavailable: {exc}",
                "citations": [],
                "grounded": False,
                "metadata": {"intent": intent},
            }

    if intent == "GRIEVANCE_GUIDE":
        return {
            **state,
            "reply": (
                "To file a verified 311 civic grievance with automatic PostGIS deduplication:\n"
                "1. Click **Report 311 Issue** (camera icon) in the chat toolbar.\n"
                "2. Upload a clear photo of the road, waste, water, or electrical hazard.\n"
                "3. Confirm your GPS location pin and submit — our Vision AI will verify severity and check for existing tickets within 50 meters."
            ),
            "citations": ["Smart City 311 Multimodal Intake Protocol"],
            "grounded": True,
            "metadata": {"intent": intent, "open_grievance_drawer": True},
        }

    rag_res = answer_policy_query(msg)
    return {
        **state,
        "reply": rag_res["answer"],
        "citations": rag_res["citations"],
        "grounded": rag_res["grounded"],
        "metadata": {"intent": "POLICY_QA"},
    }


workflow = StateGraph(AgentState)
workflow.add_node("classify_intent", classify_intent_node)
workflow.add_node("execute_tool", execute_tool_node)
workflow.set_entry_point("classify_intent")
workflow.add_edge("classify_intent", "execute_tool")
workflow.add_edge("execute_tool", END)
civic_agent = workflow.compile()


def run_civic_agent(session_id: str, user_message: str) -> dict:
    final_state = civic_agent.invoke(
        {
            "session_id": session_id,
            "user_message": user_message,
            "intent": "",
            "reply": "",
            "citations": [],
            "grounded": False,
            "metadata": {},
        }
    )
    return {
        "reply": final_state["reply"],
        "citations": final_state["citations"],
        "grounded": final_state["grounded"],
        "intent": final_state["intent"],
        "metadata": final_state["metadata"],
    }
