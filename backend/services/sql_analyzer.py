"""SQL parsing and risk analysis."""

from __future__ import annotations

import re

import sqlglot
from sqlglot import exp

from core.config import settings
from schemas.query import SQLAnalysis

INJECTION_PATTERNS = [
    r";\s*--",
    r"\bunion\s+select\b",
    r"\bor\s+1\s*=\s*1\b",
    r"/\*",
]

SENSITIVE_COLUMN_SET = {c.lower() for c in settings.SENSITIVE_COLUMNS}


class SQLAnalyzer:
    """Analyze SQL string to structured risk metadata."""

    def analyze(self, sql: str) -> SQLAnalysis:
        if not sql or sql.strip().upper() == "UNSAFE_REQUEST":
            return SQLAnalysis(
                query_type="UNKNOWN",
                tables_accessed=[],
                has_where_clause=False,
                is_read_only=False,
                risk_level="CRITICAL",
                sensitive_columns_found=[],
                estimated_affected_rows="unknown",
                injection_patterns=["unsafe_request_marker"],
            )

        injection_hits = [pattern for pattern in INJECTION_PATTERNS if re.search(pattern, sql, flags=re.IGNORECASE)]

        try:
            ast = sqlglot.parse_one(sql, read="postgres")
        except Exception:
            return SQLAnalysis(
                query_type="INVALID",
                tables_accessed=[],
                has_where_clause=False,
                is_read_only=False,
                risk_level="CRITICAL",
                sensitive_columns_found=[],
                estimated_affected_rows="unknown",
                injection_patterns=injection_hits + ["parse_error"],
            )

        query_type = ast.key.upper() if ast.key else "UNKNOWN"
        tables = sorted({t.name for t in ast.find_all(exp.Table) if t.name})
        has_where = ast.find(exp.Where) is not None
        sensitive_columns = sorted({c.name for c in ast.find_all(exp.Column) if c.name and c.name.lower() in SENSITIVE_COLUMN_SET})

        risk_level = "LOW"
        estimated_rows = "unknown"

        if query_type in {"DROP", "TRUNCATE"}:
            risk_level = "CRITICAL"
        elif query_type in {"DELETE", "UPDATE"} and not has_where:
            risk_level = "CRITICAL"
            estimated_rows = "all"
        elif query_type in {"DELETE", "UPDATE"}:
            risk_level = "HIGH"
            estimated_rows = "many"
        elif query_type in {"INSERT"}:
            risk_level = "MEDIUM"
            estimated_rows = "few"

        if any(t.lower() in {x.lower() for x in settings.BLACKLISTED_TABLES} for t in tables):
            risk_level = "CRITICAL"

        if sensitive_columns and risk_level not in {"CRITICAL", "HIGH"}:
            risk_level = "HIGH"

        if injection_hits:
            risk_level = "CRITICAL"

        return SQLAnalysis(
            query_type=query_type,
            tables_accessed=tables,
            has_where_clause=has_where,
            is_read_only=query_type == "SELECT",
            risk_level=risk_level,  # type: ignore[arg-type]
            sensitive_columns_found=sensitive_columns,
            estimated_affected_rows=estimated_rows,  # type: ignore[arg-type]
            injection_patterns=injection_hits,
        )
