from datetime import datetime, timedelta, timezone
import psycopg

SLA_HOURS_BY_SEVERITY = {
    "CRITICAL": 4,
    "HIGH": 24,
    "MEDIUM": 48,
    "LOW": 72,
}


def create_or_upvote_ticket(
    conn: psycopg.Connection,
    citizen_id: str,
    dept_code: str,
    subcategory: str,
    description: str,
    severity: str,
    lat: float,
    lon: float,
    image_path: str,
    confidence: float,
) -> dict:
    with conn.cursor() as cur:
        # Spatial-temporal deduplication: 50m radius + 48h window + same department
        cur.execute(
            """
            SELECT ticket_id, upvote_count, status, severity
            FROM tickets
            WHERE department_code = %s
              AND status IN ('OPEN', 'IN_PROGRESS')
              AND created_at >= NOW() - INTERVAL '48 hours'
              AND ST_DWithin(
                    geom,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    50.0
                  )
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE;
            """,
            (dept_code, lon, lat),
        )
        existing = cur.fetchone()

        if existing:
            ticket_id, _, status, existing_severity = existing
            final_severity = "CRITICAL" if severity == "CRITICAL" else existing_severity
            cur.execute(
                """
                UPDATE tickets
                SET upvote_count = upvote_count + 1,
                    severity = %s,
                    updated_at = NOW()
                WHERE ticket_id = %s
                RETURNING upvote_count;
                """,
                (final_severity, ticket_id),
            )
            updated_upvotes = cur.fetchone()[0]

            cur.execute(
                """
                INSERT INTO ticket_evidence (ticket_id, citizen_id, image_path, vlm_confidence)
                VALUES (%s, %s, %s, %s);
                """,
                (ticket_id, citizen_id, image_path, confidence),
            )
            cur.execute(
                """
                INSERT INTO audit_logs (ticket_id, actor_id, action, details)
                VALUES (%s, %s, 'DEDUP_UPVOTE', %s);
                """,
                (ticket_id, citizen_id, f"Merged duplicate report within 50m; total upvotes={updated_upvotes}"),
            )
            conn.commit()
            return {
                "action": "MERGED_UPVOTE",
                "ticket_id": str(ticket_id),
                "upvote_count": updated_upvotes,
                "status": status,
                "severity": final_severity,
                "escalated": final_severity == "CRITICAL",
            }

        sla_hours = SLA_HOURS_BY_SEVERITY.get(severity, 48)
        sla_deadline = datetime.now(timezone.utc) + timedelta(hours=sla_hours)

        cur.execute(
            """
            INSERT INTO tickets (department_code, issue_subcategory, description, severity, geom, sla_deadline)
            VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, %s)
            RETURNING ticket_id;
            """,
            (dept_code, subcategory, description, severity, lon, lat, sla_deadline),
        )
        new_ticket_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO ticket_evidence (ticket_id, citizen_id, image_path, vlm_confidence)
            VALUES (%s, %s, %s, %s);
            """,
            (new_ticket_id, citizen_id, image_path, confidence),
        )
        action_name = "CRITICAL_ESCALATION" if severity == "CRITICAL" else "TICKET_CREATED"
        cur.execute(
            """
            INSERT INTO audit_logs (ticket_id, actor_id, action, details)
            VALUES (%s, %s, %s, %s);
            """,
            (new_ticket_id, citizen_id, action_name, f"Dept={dept_code}, Subcategory={subcategory}, SLA={sla_hours}h"),
        )
        conn.commit()
        return {
            "action": "CREATED_NEW",
            "ticket_id": str(new_ticket_id),
            "upvote_count": 1,
            "status": "OPEN",
            "severity": severity,
            "escalated": severity == "CRITICAL",
        }
