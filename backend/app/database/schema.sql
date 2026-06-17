-- ==========================================
-- RAGuard SQLite Schema
-- ==========================================

-- Documents
CREATE TABLE IF NOT EXISTS documents (
    id              TEXT PRIMARY KEY,
    filename        TEXT NOT NULL,
    title           TEXT,
    doc_type        TEXT NOT NULL CHECK(doc_type IN ('pdf','docx','markdown')),
    file_path       TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','processing','indexed','failed','deleted')),
    page_count      INTEGER,
    file_size       INTEGER,
    checksum        TEXT,
    error_message   TEXT,
    metadata        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chunks
CREATE TABLE IF NOT EXISTS chunks (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    chunk_index     INTEGER NOT NULL,
    chroma_id       TEXT,
    page_number     INTEGER,
    token_count     INTEGER,
    is_active       BOOLEAN DEFAULT TRUE,
    -- V2: structured chunk metadata
    section_path    TEXT DEFAULT '',
    heading_level   INTEGER DEFAULT 0,
    prev_chunk_id   TEXT DEFAULT NULL,
    next_chunk_id   TEXT DEFAULT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_is_active ON chunks(is_active);

-- Conflicts
CREATE TABLE IF NOT EXISTS conflicts (
    id              TEXT PRIMARY KEY,
    scan_job_id     TEXT REFERENCES scan_jobs(id),
    conflict_type   TEXT NOT NULL
                    CHECK(conflict_type IN (
                        'factual_contradiction',
                        'numerical_discrepancy',
                        'temporal_conflict',
                        'definition_mismatch',
                        'conditional_vs_absolute'
                    )),
    summary         TEXT NOT NULL,
    description     TEXT,
    status          TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','in_review','resolved','dismissed')),
    severity        TEXT NOT NULL DEFAULT 'medium'
                    CHECK(severity IN ('low','medium','high','critical')),
    detection_method TEXT DEFAULT 'llm'
                    CHECK(detection_method IN ('embedding','llm','rule_based')),
    detected_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at     TIMESTAMP,
    metadata        TEXT
);

CREATE INDEX IF NOT EXISTS idx_conflicts_status ON conflicts(status);
CREATE INDEX IF NOT EXISTS idx_conflicts_severity ON conflicts(severity);
CREATE INDEX IF NOT EXISTS idx_conflicts_scan_job ON conflicts(scan_job_id);

-- Conflict-Chunk Association (N:N)
CREATE TABLE IF NOT EXISTS conflict_chunks (
    conflict_id     TEXT NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    chunk_id        TEXT NOT NULL REFERENCES chunks(id) ON DELETE CASCADE,
    claim           TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'source_a'
                    CHECK(role IN ('source_a','source_b')),
    similarity_score REAL,
    PRIMARY KEY (conflict_id, chunk_id)
);

-- Scan Jobs
CREATE TABLE IF NOT EXISTS scan_jobs (
    id              TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'pending'
                    CHECK(status IN ('pending','running','completed','failed')),
    total_pairs     INTEGER DEFAULT 0,
    conflict_pairs  INTEGER DEFAULT 0,
    conflicts_found INTEGER DEFAULT 0,
    threshold       REAL DEFAULT 0.85,
    started_at      TIMESTAMP,
    completed_at    TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message   TEXT
);

-- Resolutions
CREATE TABLE IF NOT EXISTS resolutions (
    id                TEXT PRIMARY KEY,
    conflict_id       TEXT NOT NULL REFERENCES conflicts(id) ON DELETE CASCADE,
    graph_thread_id   TEXT,
    proposed_action   TEXT NOT NULL
                      CHECK(proposed_action IN (
                          'replace_both',
                          'keep_a_remove_b',
                          'keep_b_remove_a',
                          'merge',
                          'manual_rewrite'
                      )),
    proposed_content  TEXT,
    reasoning         TEXT NOT NULL,
    status            TEXT NOT NULL DEFAULT 'pending_review'
                      CHECK(status IN (
                          'pending_review','approved','rejected',
                          'modified','applied','failed'
                      )),
    human_decision    TEXT
                      CHECK(human_decision IN ('approved','rejected','modified')),
    human_notes       TEXT,
    human_modified_content TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at       TIMESTAMP,
    applied_at        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resolutions_conflict ON resolutions(conflict_id);
CREATE INDEX IF NOT EXISTS idx_resolutions_status ON resolutions(status);

-- Repair Actions (Audit Trail)
CREATE TABLE IF NOT EXISTS repair_actions (
    id              TEXT PRIMARY KEY,
    resolution_id   TEXT NOT NULL REFERENCES resolutions(id) ON DELETE CASCADE,
    action_type     TEXT NOT NULL
                    CHECK(action_type IN (
                        'delete_chunk','update_chunk',
                        'create_chunk','merge_chunks'
                    )),
    chunk_id        TEXT,
    old_content     TEXT,
    new_content     TEXT,
    executed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success         BOOLEAN DEFAULT TRUE,
    error_message   TEXT
);

CREATE INDEX IF NOT EXISTS idx_repair_resolution ON repair_actions(resolution_id);

-- QA Sessions
CREATE TABLE IF NOT EXISTS qa_sessions (
    id              TEXT PRIMARY KEY,
    title           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS qa_messages (
    id              TEXT PRIMARY KEY,
    session_id      TEXT NOT NULL REFERENCES qa_sessions(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK(role IN ('user','assistant')),
    content         TEXT NOT NULL,
    sources         TEXT,
    conflict_warning TEXT,
    tokens_used     INTEGER,
    latency_ms      INTEGER,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_qa_messages_session ON qa_messages(session_id);

-- View: efficiently look up all chunk_ids involved in open conflicts
CREATE VIEW IF NOT EXISTS v_open_conflict_chunks AS
SELECT DISTINCT cc.chunk_id
FROM conflict_chunks cc
JOIN conflicts c ON cc.conflict_id = c.id
WHERE c.status IN ('open','in_review');
