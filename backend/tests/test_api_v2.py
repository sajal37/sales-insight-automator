"""Integration tests for v2 API endpoints (async jobs, job status)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


SAMPLE_CSV = (
    b"Date,Product_Category,Region,Units_Sold,Unit_Price,Revenue,Status\n"
    b"2026-01-05,Electronics,North,150,1200,180000,Shipped\n"
    b"2026-01-12,Home Appliances,South,45,450,20250,Shipped\n"
)


class TestUploadCreatesJob:
    @patch("app.routers.upload._enqueue_job")
    def test_upload_returns_job_id(self, mock_enqueue, client, auth_headers):
        mock_enqueue.side_effect = Exception("Redis down")  # forces sync fallback
        with patch("app.routers.upload._process_sync", new_callable=AsyncMock):
            response = client.post(
                "/api/v1/upload",
                headers=auth_headers,
                files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
                data={"to_email": "test@example.com"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["status_url"].startswith("/api/v1/jobs/")

    def test_upload_invalid_file_returns_400(self, client, auth_headers):
        response = client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("test.png", b"\x89PNG\r\n", "image/png")},
            data={"to_email": "test@example.com"},
        )
        assert response.status_code == 400


class TestJobStatusEndpoint:
    @patch("app.routers.upload._enqueue_job")
    def test_get_job_status(self, mock_enqueue, client, auth_headers):
        mock_enqueue.side_effect = Exception("Redis down")
        with patch("app.routers.upload._process_sync", new_callable=AsyncMock):
            upload_resp = client.post(
                "/api/v1/upload",
                headers=auth_headers,
                files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
                data={"to_email": "test@example.com"},
            )
        job_id = upload_resp.json()["job_id"]

        status_resp = client.get(
            f"/api/v1/jobs/{job_id}",
            headers=auth_headers,
        )
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["job_id"] == job_id
        assert data["status"] in ("pending", "processing", "completed", "failed")

    def test_get_nonexistent_job_returns_404(self, client, auth_headers):
        response = client.get(
            "/api/v1/jobs/nonexistent",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestHealthV2:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert "redis" in data
        assert "database" in data

    def test_health_has_version(self, client):
        data = client.get("/api/v1/health").json()
        assert data["version"] == "2.0.0"


class TestLegacySendEndpoint:
    @patch("app.routers.upload.send_summary_email", new_callable=AsyncMock)
    def test_send_email(self, mock_email, client, auth_headers):
        mock_email.return_value = {"id": "email_123"}
        response = client.post(
            "/api/v1/send",
            headers=auth_headers,
            json={
                "to_email": "test@example.com",
                "summary": "## Brief\nContent here.",
                "subject": "Test Subject",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["email_id"] == "email_123"
