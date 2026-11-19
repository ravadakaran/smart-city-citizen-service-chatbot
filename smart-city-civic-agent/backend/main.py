import os
import uuid
from typing import Literal, Optional
import psycopg
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from services.agent_orchestrator import run_civic_agent
from services.geo_dedup import create_or_upvote_ticket
from services.vision_triage import analyze_grievance_image

DB_DSN = os.getenv("DATABASE_URL", "postgresql://civic_admin:civic_password@localhost:5434/smartcity_db")
OFFICER_DEMO_TOKEN = os.getenv("OFFICER_DEMO_TOKEN", "officer-demo-token")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Smart City Citizen Service Chatbot API",
    description="Multimodal RAG-Enabled Civic Digital Agent with PostGIS 50m Geospatial Deduplication",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    session_id: str = "default-session"
    message: str


class TicketStatusUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "RESOLVED"]
    officer_note: Optional[str] = ""


def verify_officer_rbac(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing RBAC Bearer token.")
    token = authorization.split(" ", 1)[1].strip()
    if token != OFFICER_DEMO_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid or unauthorized Municipal Officer token.")


@app.get("/api/v1/health")
def health_check():
    return {"status": "ok", "service": "smart-city-civic-agent"}


@app.post("/api/v1/chat/message")
def chat_message(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    return run_civic_agent(req.session_id, req.message)


@app.post("/api/v1/grievances/submit")
async def submit_grievance(
    citizen_id: str = Form("citizen-101"),
    description: str = Form(...),
    lat: float = Form(...),
    lon: float = Form(...),
    photo: UploadFile = File(...),
):
    allowed_mimes = {"image/jpeg", "image/png", "image/webp"}
    if photo.content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WEBP photographs are supported.")

    img_bytes = await photo.read()
    if len(img_bytes) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image exceeds 8 MB maximum upload size.")

    triage = analyze_grievance_image(img_bytes, photo.content_type, description)
    if not triage.is_valid_civic_issue or triage.confidence < 0.70:
        raise HTTPException(
            status_code=422,
            detail=f"Photo rejected by Vision Triage ({triage.reasoning}). Please upload a clear outdoor photo of the civic issue.",
        )

    ext = ".png" if photo.content_type == "image/png" else ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(img_bytes)

    with psycopg.connect(DB_DSN) as conn:
        ticket_result = create_or_upvote_ticket(
            conn=conn,
            citizen_id=citizen_id,
            dept_code=triage.department_code,
            subcategory=triage.issue_subcategory,
            description=description,
            severity=triage.severity,
            lat=lat,
            lon=lon,
            image_path=filename,
            confidence=triage.confidence,
        )

    return {
        "triage": triage.model_dump(),
        "ticket": ticket_result,
    }


@app.get("/api/v1/grievances/{ticket_id}")
def get_ticket_details(ticket_id: str):
    with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticket_id, department_code, issue_subcategory, description, severity, status,
                   upvote_count, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lon,
                   sla_deadline, created_at
            FROM tickets
            WHERE ticket_id = %s;
            """,
            (ticket_id,),
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Ticket not found.")
        cols = [d[0] for d in cur.description]
        data = dict(zip(cols, row))
        data["ticket_id"] = str(data["ticket_id"])
        return data


@app.get("/api/v1/admin/heatmap")
def get_admin_heatmap(authorization: Optional[str] = Header(None)):
    verify_officer_rbac(authorization)
    with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT ticket_id, department_code, issue_subcategory, description, severity, status,
                   upvote_count, ST_Y(geom::geometry) AS lat, ST_X(geom::geometry) AS lon,
                   sla_deadline, created_at
            FROM tickets
            ORDER BY
                CASE severity
                    WHEN 'CRITICAL' THEN 1
                    WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3
                    ELSE 4
                END,
                upvote_count DESC,
                created_at DESC;
            """
        )
        cols = [d[0] for d in cur.description]
        rows = []
        for r in cur.fetchall():
            item = dict(zip(cols, r))
            item["ticket_id"] = str(item["ticket_id"])
            rows.append(item)
        return {"tickets": rows}


@app.patch("/api/v1/admin/tickets/{ticket_id}")
def update_ticket_status(
    ticket_id: str,
    payload: TicketStatusUpdate,
    authorization: Optional[str] = Header(None),
):
    verify_officer_rbac(authorization)
    with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
            UPDATE tickets
            SET status = %s, updated_at = NOW()
            WHERE ticket_id = %s
            RETURNING ticket_id, status;
            """,
            (payload.status, ticket_id),
        )
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Ticket not found.")

        cur.execute(
            """
            INSERT INTO audit_logs (ticket_id, actor_id, action, details)
            VALUES (%s, 'officer-01', 'STATUS_UPDATED', %s);
            """,
            (ticket_id, f"Status changed to {payload.status}. Note: {payload.officer_note}"),
        )
        conn.commit()
        return {"ticket_id": str(updated[0]), "status": updated[1]}
