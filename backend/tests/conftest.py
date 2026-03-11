"""Shared test fixtures — initialise DB before any test that uses the app."""

import os
import tempfile

import pytest

from app.database import init_db


@pytest.fixture(autouse=True, scope="session")
def _init_test_db():
    """Create the jobs table in a temp SQLite DB before the test session."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield
    try:
        os.unlink(path)
    except OSError:
        pass
