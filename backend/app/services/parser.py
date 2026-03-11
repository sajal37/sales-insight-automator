"""File parser service — CSV/XLSX ingestion with sanitization."""

import io
import re
from typing import BinaryIO

import pandas as pd

from app.config import settings

# Characters that trigger formula execution in spreadsheet apps
_FORMULA_PREFIXES = re.compile(r"^[\s]*(=|\+|-|@|\t|\r)")


class ParserError(Exception):
    """Raised when file parsing fails validation."""


def _sanitize_cell(value: object) -> object:
    """Strip potential CSV-injection payloads from string cells."""
    if isinstance(value, str) and _FORMULA_PREFIXES.match(value):
        return "'" + value  # prefix with single-quote to neutralize
    return value


def _validate_magic_bytes(content: bytes, filename: str) -> str:
    """Detect real file type from magic bytes. Returns 'csv' or 'xlsx'."""
    # XLSX (ZIP / PK header)
    if content[:4] == b"PK\x03\x04":
        return "xlsx"
    # Try to detect CSV by checking if it's valid UTF-8 text
    try:
        head = content[:4096].decode("utf-8")
        # Basic heuristic: comma-separated values with newlines
        if "," in head and ("\n" in head or "\r" in head):
            return "csv"
    except UnicodeDecodeError:
        pass

    # Fallback: use extension
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("csv", "xlsx", "xls"):
        return ext
    raise ParserError(
        "Unsupported file type. Only .csv and .xlsx files are accepted."
    )


def parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """
    Parse uploaded file bytes into a sanitised DataFrame.

    Validates:
    - File size against MAX_UPLOAD_SIZE_MB
    - File type via magic bytes
    - Row count against MAX_ROWS
    """
    # ── Size guard ──
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise ParserError(
            f"File exceeds the {settings.max_upload_size_mb} MB size limit."
        )

    # ── Type detection ──
    file_type = _validate_magic_bytes(content, filename)

    # ── Read into DataFrame ──
    try:
        if file_type == "csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
    except Exception as exc:
        raise ParserError(f"Failed to read file: {exc}") from exc

    # ── Row guard ──
    if len(df) > settings.max_rows:
        raise ParserError(
            f"File has {len(df):,} rows, which exceeds the "
            f"{settings.max_rows:,} row limit."
        )

    if df.empty:
        raise ParserError("The uploaded file contains no data rows.")

    # ── Sanitize all string cells ──
    str_cols = df.select_dtypes(include=["object", "string"]).columns
    for col in str_cols:
        df[col] = df[col].map(_sanitize_cell)

    return df
