"""Integration tests for API endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import settings


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"X-API-Key": settings.api_key}


SAMPLE_CSV = b"Date,Product_Category,Region,Units_Sold,Unit_Price,Revenue,Status\n2026-01-05,Electronics,North,150,1200,180000,Shipped\n"


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("healthy", "degraded")
        assert data["service"] == "sales-insight-automator"


class TestRootEndpoint:
    def test_root_returns_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert data["docs"] == "/docs"


class TestAuthMiddleware:
    def test_missing_api_key_returns_401(self, client):
        response = client.post(
            "/api/v1/upload",
            files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
        )
        assert response.status_code == 401

    def test_invalid_api_key_returns_403(self, client):
        response = client.post(
            "/api/v1/upload",
            headers={"X-API-Key": "wrong-key"},
            files={"file": ("test.csv", SAMPLE_CSV, "text/csv")},
        )
        assert response.status_code == 403


class TestUploadEndpoint:
    @patch("app.routers.upload._enqueue_job")
    def test_upload_valid_csv(self, mock_enqueue, client, auth_headers):
        mock_enqueue.side_effect = Exception("Redis down")
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

    def test_upload_unsupported_file(self, client, auth_headers):
        response = client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("test.png", b"\x89PNG\r\n", "image/png")},
            data={"to_email": "test@example.com"},
        )
        assert response.status_code == 400


class TestSendEndpoint:
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

    def test_send_invalid_email(self, client, auth_headers):
        response = client.post(
            "/api/v1/send",
            headers=auth_headers,
            json={
                "to_email": "not-an-email",
                "summary": "Test",
            },
        )
        assert response.status_code == 422  # Pydantic validation error


class TestSwaggerDocs:
    def test_swagger_accessible(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_json_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "/api/v1/upload" in data["paths"]

    def test_redoc_accessible(self, client):
        response = client.get("/redoc")
        assert response.status_code == 200
