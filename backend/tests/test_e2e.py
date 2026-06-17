"""End-to-end tests for the RAGuard pipeline.

Verifies the complete flow:
  Document Upload → Conflict Scan → Resolution → Repair → Audit → QA
"""

import pytest
import io
from datetime import datetime


# ============================================================
# Helpers
# ============================================================

def create_test_pdf(content: str) -> bytes:
    """Create a minimal PDF with given text content."""
    # Minimal PDF with embedded text
    text_bytes = content.encode('utf-8')
    pdf = f"""%PDF-1.4
1 0 obj<</Type /Catalog /Pages 2 0 R>>endobj
2 0 obj<</Type /Pages /Kids [3 0 R] /Count 1>>endobj
3 0 obj<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length {len(text_bytes) + 60}>>
stream
BT /F1 12 Tf 72 700 Td ({content}) Tj ET
endstream
endobj
5 0 obj<</Type /Font /Subtype /Type1 /BaseFont /Courier>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000385 00000 n
trailer<</Size 6 /Root 1 0 R>>
startxref
456
%%EOF"""
    return pdf.encode('latin-1', errors='replace')


def create_test_md(content: str) -> bytes:
    """Create a markdown file with given content."""
    return content.encode('utf-8')


def upload_file(client, filename: str, content: bytes) -> dict:
    """Upload a single file and return the document dict."""
    resp = client.post(
        "/api/documents/upload",
        files=[("files", (filename, io.BytesIO(content), "application/octet-stream"))],
    )
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    data = resp.json()
    assert len(data["documents"]) > 0
    return data["documents"][0]


# ============================================================
# Tests
# ============================================================

class TestDocumentIngestion:
    """Phase 1: Verify document upload and management."""

    def test_upload_markdown(self, client):
        """Upload a markdown file and verify it appears in listings."""
        doc = upload_file(client, "policy.md", create_test_md("# 退款政策\n客户可在购买后7天内申请退款。"))

        assert doc["filename"] == "policy.md"
        assert "id" in doc

        # List documents
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0
        assert any(d["filename"] == "policy.md" for d in items)

    def test_get_document_detail(self, client):
        """Upload a doc and fetch its detail."""
        doc = upload_file(client, "guide.md", create_test_md("# 用户指南\nVIP用户享受30天退款期。"))

        resp = client.get(f"/api/documents/{doc['id']}")
        assert resp.status_code == 200
        assert resp.json()["filename"] == "guide.md"

    def test_delete_document(self, client):
        """Upload then soft-delete a document."""
        doc = upload_file(client, "temp.md", create_test_md("临时文档内容"))
        resp = client.delete(f"/api/documents/{doc['id']}")
        assert resp.status_code == 204

        # Verify it's gone from listing
        resp = client.get("/api/documents")
        items = resp.json()["items"]
        assert not any(d["id"] == doc["id"] for d in items)

    def test_duplicate_detection(self, client):
        """Uploading the same file twice should be rejected."""
        content = create_test_md("# 退款政策\n退款期为14天。")
        upload_file(client, "dup1.md", content)

        resp = client.post(
            "/api/documents/upload",
            files=[("files", ("dup2.md", io.BytesIO(content), "application/octet-stream"))],
        )
        assert resp.status_code == 409
        assert "duplicate" in resp.json()["detail"].lower()


class TestConflictDetection:
    """Phase 2: Verify conflict scanning and detection."""

    def test_scan_without_documents(self, client):
        """Scanning an empty knowledge base should not crash."""
        resp = client.post("/api/scans/start?threshold=0.85")
        assert resp.status_code == 202
        assert "scan_id" in resp.json()

    def test_scan_list_and_detail(self, client):
        """Verify scan jobs can be listed and fetched."""
        # Create a scan
        resp = client.post("/api/scans/start")
        scan_id = resp.json()["scan_id"]

        # List scans
        resp = client.get("/api/scans")
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

        # Get specific scan
        resp = client.get(f"/api/scans/{scan_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == scan_id


class TestConflictsAPI:
    """Phase 2: Verify conflict listing and statistics."""

    def test_list_conflicts_empty(self, client):
        """Listing conflicts on empty DB returns empty result."""
        resp = client.get("/api/conflicts")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_conflict_stats(self, client):
        """Stats endpoint returns all counters."""
        resp = client.get("/api/conflicts/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_status" in data
        assert "by_severity" in data
        assert "by_type" in data


class TestHealthEndpoints:
    """Verify health check endpoints."""

    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_health_chroma(self, client):
        resp = client.get("/api/health/chroma")
        # Chroma may or may not be available; any non-500 is acceptable
        assert resp.status_code in (200, 404, 503)


class TestQASessions:
    """Phase 4: Verify QA session management."""

    def test_create_and_list_sessions(self, client):
        resp = client.post("/api/qa/sessions", json={"title": "测试对话"})
        assert resp.status_code == 201
        session_id = resp.json()["id"]

        resp = client.get("/api/qa/sessions")
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_get_session_empty(self, client):
        resp = client.post("/api/qa/sessions", json={"title": "空对话"})
        session_id = resp.json()["id"]

        resp = client.get(f"/api/qa/sessions/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["session"]["title"] == "空对话"

    def test_delete_session(self, client):
        resp = client.post("/api/qa/sessions", json={})
        session_id = resp.json()["id"]

        resp = client.delete(f"/api/qa/sessions/{session_id}")
        assert resp.status_code == 204

    @pytest.mark.skip(reason="Requires Jina + DeepSeek API connectivity")
    def test_send_message_empty_kb(self, client):
        """Send a message when knowledge base is empty."""
        resp = client.post("/api/qa/sessions", json={"title": "问答测试"})
        session_id = resp.json()["id"]

        resp = client.post(
            f"/api/qa/sessions/{session_id}/messages",
            json={"content": "退款政策是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "content" in data["answer"]


class TestGovernanceAPI:
    """Phase 3: Verify governance endpoints."""

    def test_pending_resolutions_empty(self, client):
        resp = client.get("/api/governance/pending")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_governance_stats(self, client):
        resp = client.get("/api/governance/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data


class TestEvaluationAPI:
    """Phase 4: Verify evaluation endpoint."""

    def test_run_evaluation_empty(self, client):
        resp = client.post("/api/evaluation/run", json={"test_questions": []})
        assert resp.status_code == 400

    @pytest.mark.skip(reason="Requires Jina + DeepSeek API connectivity")
    def test_run_evaluation(self, client):
        resp = client.post("/api/evaluation/run", json={
            "test_questions": [
                {"question": "退款期限是多久？", "ground_truth": "7天内可退款"},
            ]
        })
        assert resp.status_code == 202
        data = resp.json()
        assert "metrics" in data
        assert "answered_rate" in data["metrics"]


class TestResolutionFlow:
    """Phase 3: Verify resolution API endpoints exist and handle errors."""

    def test_resolve_nonexistent_conflict(self, client):
        """Resolving a non-existent conflict returns 404."""
        resp = client.post("/api/conflicts/nonexistent-id/resolve")
        assert resp.status_code == 404

    def test_get_nonexistent_resolution(self, client):
        resp = client.get("/api/resolutions/nonexistent-id")
        assert resp.status_code == 404

    def test_approve_nonexistent_resolution(self, client):
        resp = client.post("/api/resolutions/nonexistent-id/approve")
        assert resp.status_code == 404


class TestRepairAudit:
    """Phase 3: Verify repair actions listing."""

    def test_list_repair_actions_empty(self, client):
        resp = client.get("/api/repair-actions")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
