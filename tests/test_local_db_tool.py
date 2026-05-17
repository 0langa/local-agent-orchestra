from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from core.errors import ToolSafetyError
from core.tool_protocol import RiskLevel, ToolContext
from tools.local_db import LocalDBTool


class TestLocalDBToolSchema:
    def test_tool_id(self) -> None:
        tool = LocalDBTool()
        assert tool.tool_id == "local_db"

    def test_risk_level(self) -> None:
        tool = LocalDBTool()
        assert tool.risk_level == RiskLevel.MEDIUM

    def test_schema_has_required_params(self) -> None:
        tool = LocalDBTool()
        assert "operation" in tool.schema.parameters
        assert tool.schema.parameters["operation"].required is True
        assert "db_path" in tool.schema.parameters
        assert tool.schema.parameters["db_path"].required is True


class TestLocalDBToolSafety:
    def test_missing_db(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        ctx = ToolContext()
        result = tool.invoke({"operation": "query", "db_path": "nonexistent.db", "sql": "SELECT 1"}, ctx)
        assert result.success is False
        assert "not found" in result.error

    def test_path_escapes_workspace(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        ctx = ToolContext()
        result = tool.invoke({"operation": "query", "db_path": "../outside.db", "sql": "SELECT 1"}, ctx)
        assert result.success is False
        assert "escapes workspace" in result.error

    def test_path_outside_allowed_boundaries(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        ctx = ToolContext(allowed_paths=[str(tmp_path / "subdir")])
        db_path = tmp_path / "data.db"
        db_path.touch()
        result = tool.invoke({"operation": "query", "db_path": "data.db", "sql": "SELECT 1"}, ctx)
        assert result.success is False
        assert "outside allowed boundaries" in result.error


class TestLocalDBToolSQLSanitization:
    def test_empty_sql(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke({"operation": "query", "db_path": "test.db", "sql": "   "}, ToolContext())
        assert result.success is False
        assert "cannot be empty" in result.error

    def test_insert_blocked(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "INSERT INTO users VALUES (1, 'x')"},
            ToolContext(),
        )
        assert result.success is False
        assert "read-only" in result.error.lower()

    def test_update_blocked(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "UPDATE users SET name='x'"},
            ToolContext(),
        )
        assert result.success is False
        assert "read-only" in result.error.lower()

    def test_delete_blocked(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "DELETE FROM users"},
            ToolContext(),
        )
        assert result.success is False
        assert "read-only" in result.error.lower()

    def test_drop_blocked(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "DROP TABLE users"},
            ToolContext(),
        )
        assert result.success is False
        assert "read-only" in result.error.lower()

    def test_create_blocked(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "CREATE TABLE foo (id INT)"},
            ToolContext(),
        )
        assert result.success is False
        assert "read-only" in result.error.lower()

    def test_select_allowed(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "SELECT * FROM users"},
            ToolContext(),
        )
        assert result.success is True
        assert result.data["row_count"] == 2

    def test_pragma_allowed(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "PRAGMA user_version"},
            ToolContext(),
        )
        assert result.success is True
        assert result.data["row_count"] == 1

    def test_explain_allowed(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "EXPLAIN SELECT * FROM users"},
            ToolContext(),
        )
        assert result.success is True

    def test_with_allowed(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {
                "operation": "query",
                "db_path": "test.db",
                "sql": "WITH nums AS (SELECT 1 AS n) SELECT n FROM nums",
            },
            ToolContext(),
        )
        assert result.success is True
        assert result.data["row_count"] == 1

    def test_dangerous_keyword_inside_select_blocked(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "SELECT * FROM users; DROP TABLE users"},
            ToolContext(),
        )
        assert result.success is False
        assert "disallowed keyword" in result.error.lower()


class TestLocalDBToolQuery:
    def test_query_returns_columns_and_rows(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "SELECT id, name FROM users ORDER BY id"},
            ToolContext(),
        )
        assert result.success is True
        assert result.data["columns"] == ["id", "name"]
        assert len(result.data["rows"]) == 2
        assert result.data["rows"][0] == {"id": 1, "name": "Alice"}
        assert result.data["rows"][1] == {"id": 2, "name": "Bob"}
        assert result.metadata["has_more"] is False

    def test_query_limit(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {
                "operation": "query",
                "db_path": "test.db",
                "sql": "SELECT * FROM users ORDER BY id",
                "limit": 1,
            },
            ToolContext(),
        )
        assert result.success is True
        assert result.data["row_count"] == 1
        assert result.metadata["has_more"] is True

    def test_query_bad_sql(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "query", "db_path": "test.db", "sql": "SELECT * FROM nonexistent_table"},
            ToolContext(),
        )
        assert result.success is False
        assert "SQLite error" in result.error


class TestLocalDBToolListTables:
    def test_list_tables(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        # Add a view
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE VIEW active_users AS SELECT * FROM users WHERE id > 0")
        conn.commit()
        conn.close()

        result = tool.invoke({"operation": "list_tables", "db_path": "test.db"}, ToolContext())
        assert result.success is True
        names = {t["name"] for t in result.data}
        assert "users" in names
        assert "active_users" in names
        assert result.metadata["count"] >= 2


class TestLocalDBToolDescribe:
    def test_describe_table(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "describe", "db_path": "test.db", "table_name": "users"},
            ToolContext(),
        )
        assert result.success is True
        assert result.data["table_name"] == "users"
        assert result.data["row_count"] == 2
        columns = {c["name"]: c for c in result.data["columns"]}
        assert "id" in columns
        assert "name" in columns
        assert columns["id"]["pk"] is True
        assert result.metadata["column_count"] == 2

    def test_describe_missing_table_name(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "describe", "db_path": "test.db"},
            ToolContext(),
        )
        assert result.success is False
        assert "table_name" in result.error.lower()

    def test_describe_invalid_table_name(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        db_path = tmp_path / "test.db"
        _create_test_db(db_path)
        result = tool.invoke(
            {"operation": "describe", "db_path": "test.db", "table_name": "users'; DROP TABLE users; --"},
            ToolContext(),
        )
        assert result.success is False
        assert "Invalid table name" in result.error


class TestLocalDBToolResolvePath:
    def test_resolve_inside_workspace(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        path = tool._resolve_db_path("data/test.db", ToolContext())
        assert path == tmp_path / "data" / "test.db"

    def test_resolve_escapes_workspace(self, tmp_path: Path) -> None:
        tool = LocalDBTool(repo_root=tmp_path)
        with pytest.raises(ToolSafetyError, match="escapes workspace"):
            tool._resolve_db_path("../../etc/passwd", ToolContext())


def _create_test_db(db_path: Path) -> None:
    """Helper to create a test SQLite database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO users VALUES (1, 'Alice')")
    conn.execute("INSERT INTO users VALUES (2, 'Bob')")
    conn.commit()
    conn.close()
