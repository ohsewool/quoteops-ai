from __future__ import annotations

import sqlite3
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from backend.config import get_settings
from backend.services.auth_service import hash_password

try:
    import psycopg
except ImportError:  # pragma: no cover - exercised only when PostgreSQL is configured.
    psycopg = None


class DatabaseRow(dict):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


def _normalize_params(params: Iterable[Any] | None) -> tuple[Any, ...]:
    if params is None:
        return ()
    if isinstance(params, tuple):
        return params
    if isinstance(params, list):
        return tuple(params)
    return (params,)


def _postgresify_sql(sql: str) -> str:
    statement = sql.strip()
    if not statement:
        return statement

    if statement.upper().startswith("PRAGMA "):
        return ""

    statement = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        statement,
        flags=re.IGNORECASE,
    )

    insert_ignore = re.match(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b", statement, re.IGNORECASE)
    if insert_ignore:
        statement = re.sub(
            r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\b",
            "INSERT INTO",
            statement,
            flags=re.IGNORECASE,
        )
        statement = statement.rstrip(";")
        if " ON CONFLICT " not in statement.upper():
            statement = f"{statement} ON CONFLICT DO NOTHING"

    statement = statement.replace("?", "%s")
    return statement


def _split_sql_script(script: str) -> list[str]:
    return [statement.strip() for statement in script.split(";") if statement.strip()]


def _should_return_insert_id(statement: str) -> bool:
    upper = statement.upper()
    return (
        upper.startswith("INSERT INTO ")
        and " VALUES " in upper
        and " RETURNING " not in upper
        and " ON CONFLICT " not in upper
    )


class PostgresCursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor
        self.lastrowid: int | None = None

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> "PostgresCursor":
        statement = _postgresify_sql(sql)
        self.lastrowid = None
        if not statement:
            return self

        returning_id = _should_return_insert_id(statement)
        if returning_id:
            statement = f"{statement.rstrip(';')} RETURNING id"

        self._cursor.execute(statement, _normalize_params(params))
        if returning_id:
            row = self._cursor.fetchone()
            if row is not None:
                self.lastrowid = row[0]
        return self

    def executemany(self, sql: str, params_seq: Iterable[Iterable[Any]]) -> "PostgresCursor":
        statement = _postgresify_sql(sql)
        self.lastrowid = None
        if statement:
            self._cursor.executemany(statement, [_normalize_params(params) for params in params_seq])
        return self

    def fetchone(self) -> DatabaseRow | None:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return self._row_to_dict(row)

    def fetchall(self) -> list[DatabaseRow]:
        return [self._row_to_dict(row) for row in self._cursor.fetchall()]

    def _row_to_dict(self, row: Any) -> DatabaseRow:
        columns = [column.name for column in self._cursor.description or []]
        return DatabaseRow({column: row[index] for index, column in enumerate(columns)})


class PostgresConnection:
    def __init__(self, connection: Any):
        self._connection = connection

    def execute(self, sql: str, params: Iterable[Any] | None = None) -> PostgresCursor:
        cursor = PostgresCursor(self._connection.cursor())
        return cursor.execute(sql, params)

    def executemany(self, sql: str, params_seq: Iterable[Iterable[Any]]) -> PostgresCursor:
        cursor = PostgresCursor(self._connection.cursor())
        return cursor.executemany(sql, params_seq)

    def executescript(self, script: str) -> None:
        for statement in _split_sql_script(script):
            self.execute(statement)

    def commit(self) -> None:
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_database_path() -> Path:
    return get_settings().sqlite_database_path()


@contextmanager
def get_connection() -> Iterator[Any]:
    settings = get_settings()
    if settings.is_postgres:
        if psycopg is None:
            raise RuntimeError(
                "PostgreSQL DATABASE_URL requires the psycopg package. "
                "Install dependencies with: pip install -r requirements.txt"
            )
        connection = PostgresConnection(psycopg.connect(settings.psycopg_database_url))
    elif settings.is_sqlite:
        db_path = get_database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
    else:
        raise ValueError(
            "Unsupported DATABASE_URL. Use sqlite:///./quoteops.db or "
            "postgresql://user:password@host:5432/dbname."
        )
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def create_tables(connection: Any) -> None:
    if isinstance(connection, PostgresConnection):
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS product_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                description TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quantity_ladders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                quantities_json TEXT NOT NULL DEFAULT '[]',
                description TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            quantity_ladder_id INTEGER,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES product_categories(id),
            FOREIGN KEY (quantity_ladder_id) REFERENCES quantity_ladders(id)
        );

        CREATE TABLE IF NOT EXISTS product_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS quantity_ladders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            quantities_json TEXT NOT NULL DEFAULT '[]',
            description TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS strategy_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL DEFAULT '',
            product_id INTEGER,
            product_category_id INTEGER,
            strategy_name TEXT NOT NULL
                CHECK (strategy_name IN ('margin_protect', 'balanced_market', 'premium_local')),
            market_position TEXT NOT NULL
                CHECK (market_position IN ('conservative', 'balanced', 'premium')),
            margin_bias TEXT NOT NULL
                CHECK (margin_bias IN ('low', 'medium', 'high')),
            competitor_weight_mode TEXT NOT NULL
                CHECK (competitor_weight_mode IN ('ignore_large_online_lowest', 'balanced_reference', 'premium_reference')),
            rounding_unit INTEGER NOT NULL
                CHECK (rounding_unit IN (100, 500, 1000)),
            is_default INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (product_category_id) REFERENCES product_categories(id)
        );

        CREATE TABLE IF NOT EXISTS product_options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            option_type TEXT NOT NULL,
            option_name TEXT NOT NULL,
            option_value TEXT NOT NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS competitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            competitor_type TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS competitor_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            competitor_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            price REAL NOT NULL,
            source_note TEXT NOT NULL DEFAULT '',
            collected_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (competitor_id) REFERENCES competitors(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS cost_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            unit_cost REAL NOT NULL,
            fixed_cost REAL NOT NULL,
            minimum_margin_rate REAL NOT NULL,
            minimum_price REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS price_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS price_table_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price_table_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            final_price REAL NOT NULL,
            margin_rate REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (price_table_id) REFERENCES price_tables(id)
        );

        CREATE TABLE IF NOT EXISTS pricing_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'generated'
                CHECK (status IN ('generated', 'reviewed', 'approved', 'rejected', 'discarded')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS candidate_tables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pricing_session_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'generated'
                CHECK (status IN ('generated', 'reviewed', 'approved', 'rejected', 'discarded')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (pricing_session_id) REFERENCES pricing_sessions(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS candidate_table_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_table_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            candidate_price REAL NOT NULL,
            unit_price REAL NOT NULL,
            cost_floor_price REAL NOT NULL,
            estimated_margin_rate REAL NOT NULL,
            market_lowest_price REAL,
            market_average_price REAL,
            market_median_price REAL,
            market_highest_price REAL,
            market_reference_count INTEGER NOT NULL DEFAULT 0,
            decision_reason_codes TEXT NOT NULL DEFAULT '[]',
            warnings TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (candidate_table_id) REFERENCES candidate_tables(id)
        );

        CREATE TABLE IF NOT EXISTS validation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_table_id INTEGER NOT NULL,
            overall_status TEXT NOT NULL
                CHECK (overall_status IN ('pass', 'pass_with_warnings', 'fail')),
            risk_level TEXT NOT NULL
                CHECK (risk_level IN ('low', 'medium', 'high')),
            summary_json TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (candidate_table_id) REFERENCES candidate_tables(id)
        );

        CREATE TABLE IF NOT EXISTS agent_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pricing_session_id INTEGER,
            candidate_table_id INTEGER,
            validation_result_id INTEGER,
            step_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL
                CHECK (status IN ('pending', 'running', 'completed', 'warning', 'error')),
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (pricing_session_id) REFERENCES pricing_sessions(id),
            FOREIGN KEY (candidate_table_id) REFERENCES candidate_tables(id),
            FOREIGN KEY (validation_result_id) REFERENCES validation_results(id)
        );

        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_table_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            action TEXT NOT NULL
                CHECK (action IN ('approve', 'reject')),
            status TEXT NOT NULL
                CHECK (status IN ('completed', 'failed')),
            reviewer_name TEXT,
            reviewer_note TEXT,
            created_price_table_id INTEGER,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (candidate_table_id) REFERENCES candidate_tables(id),
            FOREIGN KEY (product_id) REFERENCES products(id),
            FOREIGN KEY (created_price_table_id) REFERENCES price_tables(id)
        );

        CREATE TABLE IF NOT EXISTS quote_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name_snapshot TEXT NOT NULL,
            requester_name TEXT NOT NULL,
            requester_email TEXT NOT NULL,
            requester_phone TEXT,
            company_name TEXT,
            quantity INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            request_note TEXT,
            status TEXT NOT NULL
                CHECK (status IN ('submitted', 'reviewing', 'quoted', 'rejected', 'archived')),
            quoted_price REAL,
            quoted_unit_price REAL,
            quote_source TEXT,
            admin_note TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            role TEXT NOT NULL
                CHECK (role IN ('owner', 'manager', 'viewer')),
            password_hash TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS admin_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id INTEGER NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            FOREIGN KEY (admin_user_id) REFERENCES admin_users(id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            actor_name TEXT,
            actor_role TEXT,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            entity_label TEXT,
            before_json TEXT,
            after_json TEXT,
            metadata_json TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS agent_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL
                CHECK (job_type IN ('pricing_analysis', 'candidate_generation', 'validation', 'ai_explanation')),
            status TEXT NOT NULL
                CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
            title TEXT NOT NULL,
            input_json TEXT NOT NULL DEFAULT '{}',
            result_json TEXT,
            error_message TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS agent_job_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            step_type TEXT NOT NULL,
            status TEXT NOT NULL
                CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata_json TEXT,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES agent_jobs(id)
        );
        """
    )


def _table_sql(connection: Any, table_name: str) -> str:
    if isinstance(connection, PostgresConnection):
        row = connection.execute(
            """
            SELECT table_name AS sql
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = ?
            """,
            (table_name,),
        ).fetchone()
        return row["sql"] if row else ""

    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row["sql"] if row and row["sql"] else ""


def _column_exists(connection: Any, table_name: str, column_name: str) -> bool:
    if isinstance(connection, PostgresConnection):
        row = connection.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = ? AND column_name = ?
            """,
            (table_name, column_name),
        ).fetchone()
        return row is not None

    columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(column["name"] == column_name for column in columns)


def migrate_product_catalog_columns(connection: Any) -> None:
    if not _column_exists(connection, "products", "category_id"):
        connection.execute("ALTER TABLE products ADD COLUMN category_id INTEGER")
    if not _column_exists(connection, "products", "quantity_ladder_id"):
        connection.execute("ALTER TABLE products ADD COLUMN quantity_ladder_id INTEGER")


def _recreate_pricing_sessions_for_statuses(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS pricing_sessions_status_migration;
        CREATE TABLE pricing_sessions_status_migration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            option_summary TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'generated'
                CHECK (status IN ('generated', 'reviewed', 'approved', 'rejected', 'discarded')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        INSERT INTO pricing_sessions_status_migration (
            id, product_id, option_summary, strategy_name, status, created_at, updated_at
        )
        SELECT id, product_id, option_summary, strategy_name, status, created_at, updated_at
        FROM pricing_sessions;
        DROP TABLE pricing_sessions;
        ALTER TABLE pricing_sessions_status_migration RENAME TO pricing_sessions;
        """
    )


def _recreate_candidate_tables_for_statuses(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DROP TABLE IF EXISTS candidate_tables_status_migration;
        CREATE TABLE candidate_tables_status_migration (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pricing_session_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            strategy_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'generated'
                CHECK (status IN ('generated', 'reviewed', 'approved', 'rejected', 'discarded')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (pricing_session_id) REFERENCES pricing_sessions(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        INSERT INTO candidate_tables_status_migration (
            id, pricing_session_id, product_id, name, strategy_name, status, created_at, updated_at
        )
        SELECT id, pricing_session_id, product_id, name, strategy_name, status, created_at, updated_at
        FROM candidate_tables;
        DROP TABLE candidate_tables;
        ALTER TABLE candidate_tables_status_migration RENAME TO candidate_tables;
        """
    )


def migrate_candidate_status_constraints(connection: Any) -> None:
    if isinstance(connection, PostgresConnection):
        return

    needs_pricing_session_migration = (
        "pricing_sessions" in _table_sql(connection, "pricing_sessions")
        and "'approved'" not in _table_sql(connection, "pricing_sessions")
    )
    needs_candidate_table_migration = (
        "candidate_tables" in _table_sql(connection, "candidate_tables")
        and "'approved'" not in _table_sql(connection, "candidate_tables")
    )
    if not needs_pricing_session_migration and not needs_candidate_table_migration:
        return

    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("PRAGMA legacy_alter_table = ON")
    try:
        if needs_pricing_session_migration:
            _recreate_pricing_sessions_for_statuses(connection)
        if needs_candidate_table_migration:
            _recreate_candidate_tables_for_statuses(connection)
    finally:
        connection.execute("PRAGMA legacy_alter_table = OFF")
        connection.execute("PRAGMA foreign_keys = ON")
    connection.commit()


def seed_database(connection: sqlite3.Connection) -> None:
    if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] > 0:
        return

    now = utc_now()

    products = [
        (
            "A3 Flyer",
            "a3-flyer",
            "Sample MVP product for quantity-based A3 flyer pricing.",
            1,
            now,
            now,
        ),
        (
            "Product Sticker",
            "product-sticker",
            "Sample MVP product for product and brand sticker pricing.",
            1,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO products (name, slug, description, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        products,
    )

    product_ids = {
        row["slug"]: row["id"]
        for row in connection.execute("SELECT id, slug FROM products").fetchall()
    }

    options = [
        (product_ids["a3-flyer"], "paper_type", "Paper Type", "Snow paper", 10, 1, now, now),
        (product_ids["a3-flyer"], "side_type", "Print Side", "Single-sided", 20, 1, now, now),
        (product_ids["a3-flyer"], "quantity", "Quantity", "100 / 500 / 1000", 30, 1, now, now),
        (product_ids["product-sticker"], "size", "Size", "50mm circle", 10, 1, now, now),
        (product_ids["product-sticker"], "material", "Material", "Standard paper", 20, 1, now, now),
        (product_ids["product-sticker"], "quantity", "Quantity", "100 / 500 / 1000", 30, 1, now, now),
    ]
    connection.executemany(
        """
        INSERT INTO product_options (
            product_id, option_type, option_name, option_value, sort_order,
            is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        options,
    )

    competitors = [
        (
            "Sample Large Online Print Mall",
            "large_online",
            "Clearly sample large online competitor reference.",
            1,
            now,
            now,
        ),
        (
            "Sample Local Print Shop",
            "local_shop",
            "Clearly sample local shop competitor reference.",
            1,
            now,
            now,
        ),
        (
            "Sample Premium Sticker Studio",
            "premium_brand",
            "Clearly sample premium brand competitor reference.",
            1,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO competitors (name, competitor_type, description, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        competitors,
    )

    competitor_ids = {
        row["name"]: row["id"]
        for row in connection.execute("SELECT id, name FROM competitors").fetchall()
    }

    competitor_prices = [
        (
            competitor_ids["Sample Large Online Print Mall"],
            product_ids["a3-flyer"],
            100,
            "A3 / snow paper / single-sided / full color",
            32000,
            "Sample manually entered reference price; not real market data.",
            now,
            now,
            now,
        ),
        (
            competitor_ids["Sample Local Print Shop"],
            product_ids["a3-flyer"],
            500,
            "A3 / snow paper / single-sided / full color",
            94000,
            "Sample manually entered reference price; not real market data.",
            now,
            now,
            now,
        ),
        (
            competitor_ids["Sample Premium Sticker Studio"],
            product_ids["product-sticker"],
            100,
            "50mm circle / standard paper / matte coating",
            28000,
            "Sample manually entered reference price; not real market data.",
            now,
            now,
            now,
        ),
        (
            competitor_ids["Sample Local Print Shop"],
            product_ids["product-sticker"],
            500,
            "50mm circle / standard paper / matte coating",
            76000,
            "Sample manually entered reference price; not real market data.",
            now,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO competitor_prices (
            competitor_id, product_id, quantity, option_summary, price, source_note,
            collected_at, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        competitor_prices,
    )

    cost_profiles = [
        (
            product_ids["a3-flyer"],
            100,
            "A3 / snow paper / single-sided / full color",
            120,
            12000,
            0.25,
            32000,
            now,
            now,
        ),
        (
            product_ids["a3-flyer"],
            500,
            "A3 / snow paper / single-sided / full color",
            82,
            18000,
            0.25,
            78667,
            now,
            now,
        ),
        (
            product_ids["product-sticker"],
            100,
            "50mm circle / standard paper / matte coating",
            95,
            9000,
            0.3,
            26429,
            now,
            now,
        ),
        (
            product_ids["product-sticker"],
            500,
            "50mm circle / standard paper / matte coating",
            64,
            13000,
            0.3,
            64286,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO cost_profiles (
            product_id, quantity, option_summary, unit_cost, fixed_cost,
            minimum_margin_rate, minimum_price, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        cost_profiles,
    )

    price_tables = [
        (
            product_ids["a3-flyer"],
            "Sample A3 flyer draft table",
            "draft",
            "Local Competition Strategy",
            now,
            now,
        ),
        (
            product_ids["product-sticker"],
            "Sample sticker active table",
            "active",
            "Margin Protection Strategy",
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO price_tables (product_id, name, status, strategy_name, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        price_tables,
    )

    table_ids = {
        row["name"]: row["id"]
        for row in connection.execute("SELECT id, name FROM price_tables").fetchall()
    }

    price_table_items = [
        (
            table_ids["Sample A3 flyer draft table"],
            100,
            "A3 / snow paper / single-sided / full color",
            35000,
            0.31,
            now,
            now,
        ),
        (
            table_ids["Sample A3 flyer draft table"],
            500,
            "A3 / snow paper / single-sided / full color",
            98000,
            0.28,
            now,
            now,
        ),
        (
            table_ids["Sample sticker active table"],
            100,
            "50mm circle / standard paper / matte coating",
            31000,
            0.39,
            now,
            now,
        ),
        (
            table_ids["Sample sticker active table"],
            500,
            "50mm circle / standard paper / matte coating",
            82000,
            0.45,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT INTO price_table_items (
            price_table_id, quantity, option_summary, final_price,
            margin_rate, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        price_table_items,
    )


def seed_catalog_metadata(connection: sqlite3.Connection) -> None:
    now = utc_now()
    categories = [
        (
            "Print Products",
            "print-products",
            "Flyers, posters, business cards, banners, and other print products.",
            10,
            1,
            now,
            now,
        ),
        (
            "Sticker And Label Products",
            "sticker-label-products",
            "Product stickers, labels, packaging stickers, and related adhesive goods.",
            20,
            1,
            now,
            now,
        ),
        (
            "Custom Goods",
            "custom-goods",
            "Future category for mugs, T-shirts, eco bags, acrylic keyrings, and other goods.",
            30,
            1,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO product_categories (
            name, slug, description, sort_order, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        categories,
    )

    ladders = [
        (
            "Standard Print Quantity Ladder",
            "standard-print-quantity-ladder",
            "[100, 500, 1000, 2000, 4000, 8000]",
            "Sample quantity points for flyer, poster, and business-card style products.",
            now,
            now,
        ),
        (
            "Small Custom Goods Quantity Ladder",
            "small-custom-goods-quantity-ladder",
            "[10, 20, 50, 100, 200, 500]",
            "Sample quantity points for future custom goods. Not a separate pricing path.",
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO quantity_ladders (
            name, slug, quantities_json, description, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ladders,
    )

    category_ids = {
        row["slug"]: row["id"]
        for row in connection.execute("SELECT id, slug FROM product_categories").fetchall()
    }
    ladder_ids = {
        row["slug"]: row["id"]
        for row in connection.execute("SELECT id, slug FROM quantity_ladders").fetchall()
    }
    connection.execute(
        """
        UPDATE products
        SET category_id = COALESCE(category_id, ?),
            quantity_ladder_id = COALESCE(quantity_ladder_id, ?),
            updated_at = ?
        WHERE slug = 'a3-flyer'
        """,
        (
            category_ids.get("print-products"),
            ladder_ids.get("standard-print-quantity-ladder"),
            now,
        ),
    )
    connection.execute(
        """
        UPDATE products
        SET category_id = COALESCE(category_id, ?),
            quantity_ladder_id = COALESCE(quantity_ladder_id, ?),
            updated_at = ?
        WHERE slug = 'product-sticker'
        """,
        (
            category_ids.get("sticker-label-products"),
            ladder_ids.get("small-custom-goods-quantity-ladder"),
            now,
        ),
    )


def seed_strategy_templates(connection: sqlite3.Connection) -> None:
    now = utc_now()
    product_ids = {
        row["slug"]: row["id"]
        for row in connection.execute("SELECT id, slug FROM products").fetchall()
    }
    category_ids = {
        row["slug"]: row["id"]
        for row in connection.execute("SELECT id, slug FROM product_categories").fetchall()
    }
    templates = [
        (
            "A3 Flyer Balanced Template",
            "a3-flyer-balanced-template",
            "Sample default template for A3 flyer candidate generation; not a real market strategy.",
            product_ids.get("a3-flyer"),
            category_ids.get("print-products"),
            "balanced_market",
            "balanced",
            "medium",
            "balanced_reference",
            100,
            1,
            1,
            now,
            now,
        ),
        (
            "Sticker Margin Protect Template",
            "sticker-margin-protect-template",
            "Sample default template for sticker pricing with margin protection; not a real market strategy.",
            product_ids.get("product-sticker"),
            category_ids.get("sticker-label-products"),
            "margin_protect",
            "conservative",
            "high",
            "ignore_large_online_lowest",
            100,
            1,
            1,
            now,
            now,
        ),
        (
            "Premium Local Print Template",
            "premium-local-print-template",
            "Sample category template for premium local print positioning; not a real market strategy.",
            None,
            category_ids.get("print-products"),
            "premium_local",
            "premium",
            "high",
            "premium_reference",
            500,
            0,
            1,
            now,
            now,
        ),
    ]
    connection.executemany(
        """
        INSERT OR IGNORE INTO strategy_templates (
            name, slug, description, product_id, product_category_id,
            strategy_name, market_position, margin_bias, competitor_weight_mode,
            rounding_unit, is_default, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        templates,
    )


def seed_demo_admin_user(connection: sqlite3.Connection) -> None:
    settings = get_settings()
    if not settings.seed_demo_admin:
        return
    if connection.execute("SELECT COUNT(*) FROM admin_users").fetchone()[0] > 0:
        return

    now = utc_now()
    connection.execute(
        """
        INSERT INTO admin_users (
            email, display_name, role, password_hash, is_active, created_at, updated_at
        )
        VALUES (?, ?, 'owner', ?, 1, ?, ?)
        """,
        (
            settings.demo_admin_email.lower(),
            "Local Demo Owner",
            hash_password(settings.demo_admin_password),
            now,
            now,
        ),
    )


def initialize_database() -> None:
    with get_connection() as connection:
        create_tables(connection)
        migrate_product_catalog_columns(connection)
        migrate_candidate_status_constraints(connection)
        seed_database(connection)
        seed_catalog_metadata(connection)
        seed_strategy_templates(connection)
        seed_demo_admin_user(connection)


def rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
