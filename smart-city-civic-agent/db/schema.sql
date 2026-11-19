CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS departments (
    code VARCHAR(32) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    default_sla_hours INT NOT NULL DEFAULT 48
);

INSERT INTO departments (code, name, default_sla_hours) VALUES
('ROADS', 'Roads & Traffic Infrastructure', 24),
('WASTE', 'Solid Waste Management', 24),
('WATER', 'Water Supply & Drainage', 12),
('EMERGENCY', 'Electrical & Disaster Response', 4)
ON CONFLICT (code) DO NOTHING;

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(64) PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    role VARCHAR(24) NOT NULL CHECK (role IN ('CITIZEN', 'WARD_OFFICER', 'SUPER_ADMIN')),
    ward_code VARCHAR(32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO users (user_id, full_name, role, ward_code) VALUES
('citizen-101', 'Aarav Sharma', 'CITIZEN', 'WARD-04'),
('officer-01', 'Eng. Meera Krishnan', 'WARD_OFFICER', 'WARD-04'),
('admin-01', 'Municipal Commissioner Desk', 'SUPER_ADMIN', 'ALL')
ON CONFLICT (user_id) DO NOTHING;

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    department_code VARCHAR(32) NOT NULL REFERENCES departments(code),
    issue_subcategory VARCHAR(100) NOT NULL,
    description TEXT,
    severity VARCHAR(16) NOT NULL CHECK (severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'IN_PROGRESS', 'RESOLVED')),
    geom GEOGRAPHY(Point, 4326) NOT NULL,
    upvote_count INT NOT NULL DEFAULT 1,
    sla_deadline TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tickets_geom ON tickets USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_tickets_status_dept ON tickets (status, department_code, created_at);

CREATE TABLE IF NOT EXISTS ticket_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    citizen_id VARCHAR(64) NOT NULL,
    image_path TEXT NOT NULL,
    vlm_confidence NUMERIC(4,3),
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    ticket_id UUID NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    actor_id VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    details TEXT,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS utility_bills (
    assessment_id VARCHAR(32) PRIMARY KEY,
    owner_name VARCHAR(120) NOT NULL,
    ward_code VARCHAR(32) NOT NULL,
    property_tax_due NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    water_charge_due NUMERIC(10,2) NOT NULL DEFAULT 0.00,
    due_date DATE NOT NULL
);

INSERT INTO utility_bills (assessment_id, owner_name, ward_code, property_tax_due, water_charge_due, due_date) VALUES
('PROP-2026-001', 'Ravada Karan', 'WARD-04', 4250.00, 680.00, CURRENT_DATE + INTERVAL '15 days'),
('PROP-2026-002', 'Nandini Rao', 'WARD-07', 0.00, 420.00, CURRENT_DATE + INTERVAL '10 days')
ON CONFLICT (assessment_id) DO NOTHING;

-- Seed initial realistic tickets for immediate map visualization
INSERT INTO tickets (ticket_id, department_code, issue_subcategory, description, severity, status, geom, upvote_count, sla_deadline)
VALUES
(
    '11111111-1111-1111-1111-111111111101',
    'ROADS',
    'Deep Carriageway Pothole',
    'Large water-filled pothole near main bus stop causing two-wheeler skids.',
    'HIGH',
    'OPEN',
    ST_SetSRID(ST_MakePoint(80.0442, 12.8231), 4326)::geography,
    4,
    NOW() + INTERVAL '18 hours'
),
(
    '11111111-1111-1111-1111-111111111102',
    'WASTE',
    'Overflowing Community Bin',
    'Uncollected municipal solid waste spilling onto pedestrian footpath.',
    'MEDIUM',
    'IN_PROGRESS',
    ST_SetSRID(ST_MakePoint(80.0468, 12.8245), 4326)::geography,
    2,
    NOW() + INTERVAL '12 hours'
),
(
    '11111111-1111-1111-1111-111111111103',
    'EMERGENCY',
    'Exposed Live Feeder Cable',
    'Storm-damaged streetlamp junction box with exposed wiring near school crossing.',
    'CRITICAL',
    'OPEN',
    ST_SetSRID(ST_MakePoint(80.0425, 12.8219), 4326)::geography,
    7,
    NOW() + INTERVAL '3 hours'
)
ON CONFLICT (ticket_id) DO NOTHING;
