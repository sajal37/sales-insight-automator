"""Tests for the SQLite job persistence layer."""

import os
import tempfile

import pytest

from app.database import init_db, create_job, update_job, get_job


@pytest.fixture(autouse=True)
def _temp_db(tmp_path):
    """Use a fresh temp DB for each test."""
    db_path = str(tmp_path / "test_jobs.db")
    init_db(db_path)
    yield


class TestJobLifecycle:
    def test_create_and_get(self):
        record = create_job(job_id="abc123", filename="test.csv", to_email="a@b.com", subject="Test")
        assert record["id"] == "abc123"
        assert record["status"] == "pending"

        fetched = get_job("abc123")
        assert fetched is not None
        assert fetched["id"] == "abc123"
        assert fetched["filename"] == "test.csv"

    def test_get_nonexistent_returns_none(self):
        assert get_job("nonexistent") is None

    def test_update_status(self):
        create_job(job_id="j1", filename="f.csv", to_email="x@y.com", subject="S")
        update_job("j1", status="processing")
        job = get_job("j1")
        assert job["status"] == "processing"

    def test_update_multiple_fields(self):
        create_job(job_id="j2", filename="f.csv", to_email="x@y.com", subject="S")
        update_job("j2", status="completed", rows_processed=100, email_status="sent")
        job = get_job("j2")
        assert job["status"] == "completed"
        assert job["rows_processed"] == 100
        assert job["email_status"] == "sent"

    def test_update_sets_updated_at(self):
        create_job(job_id="j3", filename="f.csv", to_email="x@y.com", subject="S")
        first = get_job("j3")
        update_job("j3", status="processing")
        second = get_job("j3")
        assert second["updated_at"] >= first["updated_at"]
