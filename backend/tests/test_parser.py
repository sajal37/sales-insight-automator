"""Tests for the file parser service."""

import pytest
import pandas as pd

from app.services.parser import parse_file, ParserError, _sanitize_cell


class TestSanitizeCell:
    def test_normal_string_unchanged(self):
        assert _sanitize_cell("Hello World") == "Hello World"

    def test_number_unchanged(self):
        assert _sanitize_cell(42) == 42

    def test_formula_injection_equals(self):
        result = _sanitize_cell("=CMD('calc')")
        assert result.startswith("'")

    def test_formula_injection_plus(self):
        result = _sanitize_cell("+CMD('calc')")
        assert result.startswith("'")

    def test_formula_injection_minus(self):
        result = _sanitize_cell("-1+1")
        assert result.startswith("'")

    def test_formula_injection_at(self):
        result = _sanitize_cell("@SUM(A1:A10)")
        assert result.startswith("'")

    def test_none_unchanged(self):
        assert _sanitize_cell(None) is None


class TestParseFile:
    def _make_csv(self, content: str) -> bytes:
        return content.encode("utf-8")

    def test_valid_csv(self):
        csv = self._make_csv(
            "Date,Product,Revenue\n2026-01-01,Widget,1000\n2026-01-02,Gadget,2000\n"
        )
        df = parse_file(csv, "test.csv")
        assert len(df) == 2
        assert "Revenue" in df.columns

    def test_empty_csv_raises(self):
        csv = self._make_csv("Date,Product,Revenue\n")
        with pytest.raises(ParserError, match="no data"):
            parse_file(csv, "test.csv")

    def test_oversized_file_raises(self):
        # Create content larger than max (we temporarily set max to tiny)
        from unittest.mock import patch
        csv = self._make_csv("a,b\n" + "1,2\n" * 100)
        with patch("app.services.parser.settings") as mock_settings:
            mock_settings.max_upload_size_mb = 0  # 0 MB = reject everything
            mock_settings.max_rows = 100000
            with pytest.raises(ParserError, match="size limit"):
                parse_file(csv, "test.csv")

    def test_unsupported_file_type(self):
        with pytest.raises(ParserError, match="Unsupported"):
            parse_file(b"\x89PNG\r\n\x1a\n", "image.png")

    def test_csv_injection_sanitized(self):
        csv = self._make_csv(
            "Name,Value\n=MALICIOUS,100\nnormal,200\n"
        )
        df = parse_file(csv, "test.csv")
        assert df.iloc[0]["Name"].startswith("'")
        assert df.iloc[1]["Name"] == "normal"
