from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
SCHEMA_PATH = SQL_DIR / "schema.sql"
MIGRATION_STRATEGY_PATH = ROOT / "docs" / "DATABASE_MIGRATION_STRATEGY.md"
MIGRATION_FILE_PATTERN = re.compile(r"^(?P<number>\d{3})_[a-z0-9_]+\.sql$")
DOCUMENTED_NUMBER_GAPS = {1, 8, 9, 10, 11}
REQUIRED_EXTENSIONS = {"vector", "pgcrypto"}


class MigrationVerificationError(RuntimeError):
    pass


def main() -> None:
    args = parse_args()
    result: dict[str, object] = {}

    if args.mode in {"static", "all"}:
        result["static"] = verify_static_contract()

    if args.mode in {"runtime", "all"}:
        result["runtime"] = verify_runtime_replay()

    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="验证 SQL 迁移目录契约和真实 PostgreSQL 回放")
    parser.add_argument(
        "--mode",
        choices=("static", "runtime", "all"),
        default="all",
        help="static=不连接数据库；runtime=真实 PostgreSQL 临时 schema 回放；all=两者都跑",
    )
    return parser.parse_args()


def verify_static_contract() -> dict[str, object]:
    if not SCHEMA_PATH.exists():
        raise MigrationVerificationError("缺少 sql/schema.sql 全量快照")

    if not MIGRATION_STRATEGY_PATH.exists():
        raise MigrationVerificationError("缺少 docs/DATABASE_MIGRATION_STRATEGY.md 迁移策略文档")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    strategy_text = MIGRATION_STRATEGY_PATH.read_text(encoding="utf-8")
    migrations = list_migration_files()
    numbers = [number for number, _ in migrations]
    missing_numbers = sorted(set(range(1, max(numbers) + 1)) - set(numbers))
    undocumented_gaps = sorted(set(missing_numbers) - DOCUMENTED_NUMBER_GAPS)

    if undocumented_gaps:
        raise MigrationVerificationError(
            f"发现未登记的迁移编号缺口：{undocumented_gaps}。新增迁移必须连续编号，历史缺口要写入迁移策略。"
        )

    for gap in sorted(DOCUMENTED_NUMBER_GAPS):
        if f"{gap:03d}" not in strategy_text:
            raise MigrationVerificationError(f"迁移策略未说明历史缺口 {gap:03d}")

    schema_tables = extract_created_tables(schema_sql)
    schema_indexes = extract_created_indexes(schema_sql)
    migration_tables: set[str] = set()
    migration_indexes: set[str] = set()
    migration_columns: list[tuple[str, str, str]] = []

    for _, path in migrations:
        sql_text = path.read_text(encoding="utf-8")

        if path.name not in strategy_text:
            raise MigrationVerificationError(f"迁移策略未登记 {path.name}")

        migration_tables.update(extract_created_tables(sql_text))
        migration_indexes.update(extract_created_indexes(sql_text))
        migration_columns.extend(
            (path.name, table, column)
            for table, column in extract_added_columns(sql_text)
        )

    missing_tables = sorted(table for table in migration_tables if table not in schema_tables)
    if missing_tables:
        raise MigrationVerificationError(f"schema.sql 缺少迁移创建的表：{missing_tables}")

    missing_indexes = sorted(index for index in migration_indexes if index not in schema_indexes)
    if missing_indexes:
        raise MigrationVerificationError(f"schema.sql 缺少迁移创建的索引：{missing_indexes}")

    missing_columns: list[str] = []
    for filename, table, column in migration_columns:
        table_block = extract_table_block(schema_sql, table)
        if table_block is None or not re.search(rf"\b{re.escape(column)}\b", table_block):
            missing_columns.append(f"{filename}:{table}.{column}")

    if missing_columns:
        raise MigrationVerificationError(f"schema.sql 缺少迁移新增字段：{missing_columns}")

    return {
        "migration_count": len(migrations),
        "migration_numbers": numbers,
        "documented_number_gaps": missing_numbers,
        "schema_tables_checked": sorted(migration_tables),
        "schema_indexes_checked": sorted(migration_indexes),
        "schema_columns_checked": [f"{table}.{column}" for _, table, column in migration_columns],
        "note": "static migration contract check; no mock/stub/fake/monkeypatch",
    }


def verify_runtime_replay() -> dict[str, object]:
    import psycopg
    from psycopg import sql

    database_url = resolve_database_url()
    schema_name = f"verify_sql_migrations_{uuid4().hex}"
    migrations = list_migration_files()

    with psycopg.connect(database_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            try:
                installed_extensions = load_installed_extensions(cur)
                missing_extensions = sorted(REQUIRED_EXTENSIONS - installed_extensions)
                if missing_extensions:
                    raise MigrationVerificationError(
                        f"当前 PostgreSQL 缺少必需扩展：{missing_extensions}"
                    )

                cur.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                set_search_path(cur, schema_name)
                cur.execute(strip_extension_statements(SCHEMA_PATH.read_text(encoding="utf-8")))

                for _, path in migrations:
                    set_search_path(cur, schema_name)
                    cur.execute(path.read_text(encoding="utf-8"))

                tables = load_schema_tables(cur, schema_name)
                indexes = load_schema_indexes(cur, schema_name)
            finally:
                cur.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema_name)))

    return {
        "schema_name": schema_name,
        "migration_count": len(migrations),
        "migration_files": [path.name for _, path in migrations],
        "table_count": len(tables),
        "index_count": len(indexes),
        "note": "real PostgreSQL temporary schema replay; no mock/stub/fake/monkeypatch",
    }


def list_migration_files() -> list[tuple[int, Path]]:
    migrations: list[tuple[int, Path]] = []

    for path in sorted(SQL_DIR.glob("[0-9][0-9][0-9]_*.sql")):
        match = MIGRATION_FILE_PATTERN.match(path.name)
        if not match:
            raise MigrationVerificationError(f"迁移文件命名不符合 NNN_slug.sql：{path.name}")

        migrations.append((int(match.group("number")), path))

    if not migrations:
        raise MigrationVerificationError("sql/ 下没有增量迁移文件")

    numbers = [number for number, _ in migrations]
    if len(numbers) != len(set(numbers)):
        raise MigrationVerificationError(f"迁移编号重复：{numbers}")

    if numbers != sorted(numbers):
        raise MigrationVerificationError(f"迁移文件排序异常：{numbers}")

    return migrations


def extract_created_tables(sql_text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-z][a-z0-9_]*)",
            sql_text,
            flags=re.IGNORECASE,
        )
    }


def extract_created_indexes(sql_text: str) -> set[str]:
    return {
        match.group(1)
        for match in re.finditer(
            r"CREATE\s+INDEX\s+IF\s+NOT\s+EXISTS\s+([a-z][a-z0-9_]*)",
            sql_text,
            flags=re.IGNORECASE,
        )
    }


def extract_added_columns(sql_text: str) -> list[tuple[str, str]]:
    return [
        (match.group(1), match.group(2))
        for match in re.finditer(
            r"ALTER\s+TABLE\s+([a-z][a-z0-9_]*)\s+ADD\s+COLUMN\s+IF\s+NOT\s+EXISTS\s+([a-z][a-z0-9_]*)",
            sql_text,
            flags=re.IGNORECASE,
        )
    ]


def extract_table_block(schema_sql: str, table: str) -> str | None:
    match = re.search(
        rf"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+{re.escape(table)}\s*\((.*?)\n\);",
        schema_sql,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return match.group(1) if match else None


def strip_extension_statements(sql_text: str) -> str:
    return "\n".join(
        line
        for line in sql_text.splitlines()
        if not line.strip().upper().startswith("CREATE EXTENSION")
    )


def resolve_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    sys.path.insert(0, str(ROOT))
    from app.config import settings

    return settings.database_url


def load_installed_extensions(cur) -> set[str]:
    cur.execute("SELECT extname FROM pg_extension;")
    return {str(row[0]) for row in cur.fetchall()}


def set_search_path(cur, schema_name: str) -> None:
    from psycopg import sql

    cur.execute(
        sql.SQL("SET search_path TO {}, public").format(sql.Identifier(schema_name))
    )


def load_schema_tables(cur, schema_name: str) -> set[str]:
    cur.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE';
        """,
        (schema_name,),
    )
    return {str(row[0]) for row in cur.fetchall()}


def load_schema_indexes(cur, schema_name: str) -> set[str]:
    cur.execute(
        """
        SELECT indexname
        FROM pg_indexes
        WHERE schemaname = %s;
        """,
        (schema_name,),
    )
    return {str(row[0]) for row in cur.fetchall()}


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"SQL 迁移验证失败：{error}") from error
