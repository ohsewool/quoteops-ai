from __future__ import annotations

import json
from typing import Any

from backend.db import get_connection, utc_now


DEMO_CONFIRMATION = "RESET_DEMO_DATA"
DEMO_PRODUCT_SLUGS = ("demo-a3-flyer", "demo-product-sticker")
DEMO_COMPETITOR_NAMES = (
    "Demo Large Online Printer",
    "Demo Local Print Studio",
    "Demo Premium Sticker Shop",
)
DEMO_QUOTE_EMAIL = "demo-customer@quoteops.local"
DEMO_ENTITY_LABEL = "QuoteOps demo data"


def _fetchone_id(connection: Any, sql: str, params: tuple[Any, ...]) -> int | None:
    row = connection.execute(sql, params).fetchone()
    return int(row["id"]) if row else None


def _ensure_product(
    connection: Any,
    *,
    name: str,
    slug: str,
    description: str,
    now: str,
) -> int:
    product_id = _fetchone_id(connection, "SELECT id FROM products WHERE slug = ?", (slug,))
    if product_id is None:
        cursor = connection.execute(
            """
            INSERT INTO products (name, slug, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (name, slug, description, now, now),
        )
        return int(cursor.lastrowid)

    connection.execute(
        """
        UPDATE products
        SET name = ?, description = ?, is_active = 1, updated_at = ?
        WHERE id = ?
        """,
        (name, description, now, product_id),
    )
    return product_id


def _ensure_product_option(
    connection: Any,
    *,
    product_id: int,
    option_type: str,
    option_name: str,
    option_value: str,
    sort_order: int,
    now: str,
) -> None:
    option_id = _fetchone_id(
        connection,
        """
        SELECT id FROM product_options
        WHERE product_id = ? AND option_type = ? AND option_value = ?
        """,
        (product_id, option_type, option_value),
    )
    if option_id is None:
        connection.execute(
            """
            INSERT INTO product_options (
                product_id, option_type, option_name, option_value, sort_order,
                is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (product_id, option_type, option_name, option_value, sort_order, now, now),
        )
        return

    connection.execute(
        """
        UPDATE product_options
        SET option_name = ?, sort_order = ?, is_active = 1, updated_at = ?
        WHERE id = ?
        """,
        (option_name, sort_order, now, option_id),
    )


def _ensure_competitor(
    connection: Any,
    *,
    name: str,
    competitor_type: str,
    description: str,
    now: str,
) -> int:
    competitor_id = _fetchone_id(connection, "SELECT id FROM competitors WHERE name = ?", (name,))
    if competitor_id is None:
        cursor = connection.execute(
            """
            INSERT INTO competitors (
                name, competitor_type, description, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, 1, ?, ?)
            """,
            (name, competitor_type, description, now, now),
        )
        return int(cursor.lastrowid)

    connection.execute(
        """
        UPDATE competitors
        SET competitor_type = ?, description = ?, is_active = 1, updated_at = ?
        WHERE id = ?
        """,
        (competitor_type, description, now, competitor_id),
    )
    return competitor_id


def _ensure_competitor_price(
    connection: Any,
    *,
    competitor_id: int,
    product_id: int,
    quantity: int,
    option_summary: str,
    price: float,
    now: str,
) -> None:
    price_id = _fetchone_id(
        connection,
        """
        SELECT id FROM competitor_prices
        WHERE competitor_id = ? AND product_id = ? AND quantity = ? AND option_summary = ?
        """,
        (competitor_id, product_id, quantity, option_summary),
    )
    source_note = "Demo manually entered reference price; not real market data."
    if price_id is None:
        connection.execute(
            """
            INSERT INTO competitor_prices (
                competitor_id, product_id, quantity, option_summary, price,
                source_note, collected_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (competitor_id, product_id, quantity, option_summary, price, source_note, now, now, now),
        )
        return

    connection.execute(
        """
        UPDATE competitor_prices
        SET price = ?, source_note = ?, collected_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (price, source_note, now, now, price_id),
    )


def _ensure_cost_profile(
    connection: Any,
    *,
    product_id: int,
    quantity: int,
    option_summary: str,
    unit_cost: float,
    fixed_cost: float,
    minimum_margin_rate: float,
    minimum_price: float,
    now: str,
) -> None:
    profile_id = _fetchone_id(
        connection,
        """
        SELECT id FROM cost_profiles
        WHERE product_id = ? AND quantity = ? AND option_summary = ?
        """,
        (product_id, quantity, option_summary),
    )
    if profile_id is None:
        connection.execute(
            """
            INSERT INTO cost_profiles (
                product_id, quantity, option_summary, unit_cost, fixed_cost,
                minimum_margin_rate, minimum_price, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                quantity,
                option_summary,
                unit_cost,
                fixed_cost,
                minimum_margin_rate,
                minimum_price,
                now,
                now,
            ),
        )
        return

    connection.execute(
        """
        UPDATE cost_profiles
        SET unit_cost = ?, fixed_cost = ?, minimum_margin_rate = ?,
            minimum_price = ?, updated_at = ?
        WHERE id = ?
        """,
        (unit_cost, fixed_cost, minimum_margin_rate, minimum_price, now, profile_id),
    )


def _ensure_price_table(
    connection: Any,
    *,
    product_id: int,
    name: str,
    status: str,
    strategy_name: str,
    now: str,
) -> int:
    table_id = _fetchone_id(
        connection,
        "SELECT id FROM price_tables WHERE product_id = ? AND name = ?",
        (product_id, name),
    )
    if table_id is None:
        cursor = connection.execute(
            """
            INSERT INTO price_tables (product_id, name, status, strategy_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (product_id, name, status, strategy_name, now, now),
        )
        return int(cursor.lastrowid)

    connection.execute(
        """
        UPDATE price_tables
        SET status = ?, strategy_name = ?, updated_at = ?
        WHERE id = ?
        """,
        (status, strategy_name, now, table_id),
    )
    return table_id


def _ensure_price_table_item(
    connection: Any,
    *,
    price_table_id: int,
    quantity: int,
    option_summary: str,
    final_price: float,
    margin_rate: float,
    now: str,
) -> None:
    item_id = _fetchone_id(
        connection,
        """
        SELECT id FROM price_table_items
        WHERE price_table_id = ? AND quantity = ? AND option_summary = ?
        """,
        (price_table_id, quantity, option_summary),
    )
    if item_id is None:
        connection.execute(
            """
            INSERT INTO price_table_items (
                price_table_id, quantity, option_summary, final_price,
                margin_rate, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (price_table_id, quantity, option_summary, final_price, margin_rate, now, now),
        )
        return

    connection.execute(
        """
        UPDATE price_table_items
        SET final_price = ?, margin_rate = ?, updated_at = ?
        WHERE id = ?
        """,
        (final_price, margin_rate, now, item_id),
    )


def _ensure_quote_request(
    connection: Any,
    *,
    product_id: int,
    product_name: str,
    quantity: int,
    option_summary: str,
    now: str,
) -> None:
    request_id = _fetchone_id(
        connection,
        """
        SELECT id FROM quote_requests
        WHERE requester_email = ? AND product_id = ? AND quantity = ? AND option_summary = ?
        """,
        (DEMO_QUOTE_EMAIL, product_id, quantity, option_summary),
    )
    values = (
        product_id,
        product_name,
        "Demo Customer",
        DEMO_QUOTE_EMAIL,
        "010-0000-0000",
        "Demo Company",
        quantity,
        option_summary,
        "Demo quote request for local/staging verification.",
        "submitted",
        "Demo request; sample data only.",
        now,
        now,
    )
    if request_id is None:
        connection.execute(
            """
            INSERT INTO quote_requests (
                product_id, product_name_snapshot, requester_name, requester_email,
                requester_phone, company_name, quantity, option_summary,
                request_note, status, admin_note, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return

    connection.execute(
        """
        UPDATE quote_requests
        SET product_name_snapshot = ?, requester_name = ?, requester_phone = ?,
            company_name = ?, request_note = ?, status = ?, admin_note = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            product_name,
            "Demo Customer",
            "010-0000-0000",
            "Demo Company",
            "Demo quote request for local/staging verification.",
            "submitted",
            "Demo request; sample data only.",
            now,
            request_id,
        ),
    )


def _log_demo_event(connection: Any, *, action: str, now: str, metadata: dict[str, Any]) -> None:
    existing = _fetchone_id(
        connection,
        "SELECT id FROM audit_logs WHERE action = ? AND entity_type = 'demo_data'",
        (action,),
    )
    metadata_json = json.dumps(metadata, ensure_ascii=True, sort_keys=True)
    if existing is None:
        connection.execute(
            """
            INSERT INTO audit_logs (
                actor_name, actor_role, action, entity_type, entity_label,
                metadata_json, created_at
            )
            VALUES ('system', 'system', ?, 'demo_data', ?, ?, ?)
            """,
            (action, DEMO_ENTITY_LABEL, metadata_json, now),
        )
        return
    connection.execute(
        """
        UPDATE audit_logs
        SET metadata_json = ?, created_at = ?
        WHERE id = ?
        """,
        (metadata_json, now, existing),
    )


def seed_demo_data() -> dict[str, Any]:
    now = utc_now()
    with get_connection() as connection:
        flyer_id = _ensure_product(
            connection,
            name="Demo A3 Flyer",
            slug="demo-a3-flyer",
            description="Demo product for repeatable QuoteOps AI reviews. Sample data only.",
            now=now,
        )
        sticker_id = _ensure_product(
            connection,
            name="Demo Product Sticker",
            slug="demo-product-sticker",
            description="Demo sticker product for repeatable QuoteOps AI reviews. Sample data only.",
            now=now,
        )

        for option in [
            (flyer_id, "paper_type", "Paper Type", "Demo snow paper", 10),
            (flyer_id, "side_type", "Print Side", "Demo single-sided", 20),
            (flyer_id, "quantity", "Quantity", "100 / 500 / 1000", 30),
            (sticker_id, "size", "Size", "Demo 50mm circle", 10),
            (sticker_id, "material", "Material", "Demo standard paper", 20),
            (sticker_id, "quantity", "Quantity", "100 / 500 / 1000", 30),
        ]:
            _ensure_product_option(
                connection,
                product_id=option[0],
                option_type=option[1],
                option_name=option[2],
                option_value=option[3],
                sort_order=option[4],
                now=now,
            )

        large_id = _ensure_competitor(
            connection,
            name="Demo Large Online Printer",
            competitor_type="large_online",
            description="Demo manually entered competitor reference; not real market data.",
            now=now,
        )
        local_id = _ensure_competitor(
            connection,
            name="Demo Local Print Studio",
            competitor_type="local_shop",
            description="Demo manually entered competitor reference; not real market data.",
            now=now,
        )
        premium_id = _ensure_competitor(
            connection,
            name="Demo Premium Sticker Shop",
            competitor_type="premium_brand",
            description="Demo manually entered competitor reference; not real market data.",
            now=now,
        )

        flyer_summary = "Demo A3 / snow paper / single-sided / full color"
        sticker_summary = "Demo 50mm circle / standard paper / matte coating"
        for row in [
            (large_id, flyer_id, 100, flyer_summary, 33000),
            (local_id, flyer_id, 500, flyer_summary, 97000),
            (premium_id, sticker_id, 100, sticker_summary, 29500),
            (local_id, sticker_id, 500, sticker_summary, 79000),
        ]:
            _ensure_competitor_price(
                connection,
                competitor_id=row[0],
                product_id=row[1],
                quantity=row[2],
                option_summary=row[3],
                price=row[4],
                now=now,
            )

        for row in [
            (flyer_id, 100, flyer_summary, 125, 12000, 0.25, 33000),
            (flyer_id, 500, flyer_summary, 85, 18000, 0.25, 80667),
            (sticker_id, 100, sticker_summary, 98, 9000, 0.3, 26857),
            (sticker_id, 500, sticker_summary, 66, 13000, 0.3, 65714),
        ]:
            _ensure_cost_profile(
                connection,
                product_id=row[0],
                quantity=row[1],
                option_summary=row[2],
                unit_cost=row[3],
                fixed_cost=row[4],
                minimum_margin_rate=row[5],
                minimum_price=row[6],
                now=now,
            )

        flyer_table_id = _ensure_price_table(
            connection,
            product_id=flyer_id,
            name="Demo A3 flyer active price table",
            status="active",
            strategy_name="Demo Balanced Strategy",
            now=now,
        )
        sticker_table_id = _ensure_price_table(
            connection,
            product_id=sticker_id,
            name="Demo sticker draft price table",
            status="draft",
            strategy_name="Demo Margin Protection Strategy",
            now=now,
        )
        for row in [
            (flyer_table_id, 100, flyer_summary, 36000, 0.3333),
            (flyer_table_id, 500, flyer_summary, 102000, 0.2843),
            (sticker_table_id, 100, sticker_summary, 32000, 0.4125),
            (sticker_table_id, 500, sticker_summary, 85000, 0.4588),
        ]:
            _ensure_price_table_item(
                connection,
                price_table_id=row[0],
                quantity=row[1],
                option_summary=row[2],
                final_price=row[3],
                margin_rate=row[4],
                now=now,
            )

        _ensure_quote_request(
            connection,
            product_id=flyer_id,
            product_name="Demo A3 Flyer",
            quantity=500,
            option_summary=flyer_summary,
            now=now,
        )

        _log_demo_event(
            connection,
            action="demo_data_seeded",
            now=now,
            metadata={"source": "PR-29 demo seed", "sample_data_only": True},
        )

        return demo_data_status(connection)


def reset_demo_data(*, confirm: str) -> dict[str, Any]:
    if confirm != DEMO_CONFIRMATION:
        raise ValueError(f'Explicit confirmation is required: {DEMO_CONFIRMATION}')

    with get_connection() as connection:
        product_rows = connection.execute(
            "SELECT id FROM products WHERE slug IN (?, ?)",
            DEMO_PRODUCT_SLUGS,
        ).fetchall()
        product_ids = [row["id"] for row in product_rows]
        competitor_rows = connection.execute(
            "SELECT id FROM competitors WHERE name IN (?, ?, ?)",
            DEMO_COMPETITOR_NAMES,
        ).fetchall()
        competitor_ids = [row["id"] for row in competitor_rows]
        price_table_rows = []
        pricing_session_rows = []
        candidate_table_rows = []
        validation_rows = []
        if product_ids:
            placeholders = ",".join("?" for _ in product_ids)
            price_table_rows = connection.execute(
                f"SELECT id FROM price_tables WHERE product_id IN ({placeholders})",
                tuple(product_ids),
            ).fetchall()
            pricing_session_rows = connection.execute(
                f"SELECT id FROM pricing_sessions WHERE product_id IN ({placeholders})",
                tuple(product_ids),
            ).fetchall()
            candidate_table_rows = connection.execute(
                f"SELECT id FROM candidate_tables WHERE product_id IN ({placeholders})",
                tuple(product_ids),
            ).fetchall()
        price_table_ids = [row["id"] for row in price_table_rows]
        pricing_session_ids = [row["id"] for row in pricing_session_rows]
        candidate_table_ids = [row["id"] for row in candidate_table_rows]
        if candidate_table_ids:
            placeholders = ",".join("?" for _ in candidate_table_ids)
            validation_rows = connection.execute(
                f"SELECT id FROM validation_results WHERE candidate_table_id IN ({placeholders})",
                tuple(candidate_table_ids),
            ).fetchall()
        validation_result_ids = [row["id"] for row in validation_rows]

        deleted = {
            "agent_logs": 0,
            "approvals": 0,
            "validation_results": 0,
            "candidate_table_items": 0,
            "candidate_tables": 0,
            "pricing_sessions": 0,
            "price_table_items": 0,
            "price_tables": 0,
            "quote_requests": 0,
            "cost_profiles": 0,
            "competitor_prices": 0,
            "product_options": 0,
            "products": 0,
            "competitors": 0,
            "audit_logs": 0,
        }

        def delete_where(table: str, condition: str, params: tuple[Any, ...]) -> None:
            before = connection.execute(f"SELECT COUNT(*) AS count FROM {table} WHERE {condition}", params).fetchone()["count"]
            connection.execute(f"DELETE FROM {table} WHERE {condition}", params)
            deleted[table] += int(before)

        if validation_result_ids:
            placeholders = ",".join("?" for _ in validation_result_ids)
            delete_where("agent_logs", f"validation_result_id IN ({placeholders})", tuple(validation_result_ids))
        if candidate_table_ids:
            placeholders = ",".join("?" for _ in candidate_table_ids)
            params = tuple(candidate_table_ids)
            delete_where("agent_logs", f"candidate_table_id IN ({placeholders})", params)
            delete_where("approvals", f"candidate_table_id IN ({placeholders})", params)
            delete_where("validation_results", f"candidate_table_id IN ({placeholders})", params)
            delete_where("candidate_table_items", f"candidate_table_id IN ({placeholders})", params)
            delete_where("candidate_tables", f"id IN ({placeholders})", params)
        if pricing_session_ids:
            placeholders = ",".join("?" for _ in pricing_session_ids)
            params = tuple(pricing_session_ids)
            delete_where("agent_logs", f"pricing_session_id IN ({placeholders})", params)
            delete_where("pricing_sessions", f"id IN ({placeholders})", params)
        if price_table_ids:
            placeholders = ",".join("?" for _ in price_table_ids)
            delete_where("approvals", f"created_price_table_id IN ({placeholders})", tuple(price_table_ids))
            delete_where("price_table_items", f"price_table_id IN ({placeholders})", tuple(price_table_ids))
            delete_where("price_tables", f"id IN ({placeholders})", tuple(price_table_ids))
        if product_ids:
            placeholders = ",".join("?" for _ in product_ids)
            params = tuple(product_ids)
            delete_where("quote_requests", f"product_id IN ({placeholders})", params)
            delete_where("cost_profiles", f"product_id IN ({placeholders})", params)
            delete_where("competitor_prices", f"product_id IN ({placeholders})", params)
            delete_where("product_options", f"product_id IN ({placeholders})", params)
            delete_where("products", f"id IN ({placeholders})", params)
        if competitor_ids:
            placeholders = ",".join("?" for _ in competitor_ids)
            delete_where("competitor_prices", f"competitor_id IN ({placeholders})", tuple(competitor_ids))
            delete_where("competitors", f"id IN ({placeholders})", tuple(competitor_ids))

        delete_where(
            "audit_logs",
            "entity_type = 'demo_data' OR action IN ('demo_data_seeded', 'demo_data_reset')",
            (),
        )

    seeded_status = seed_demo_data()
    with get_connection() as connection:
        _log_demo_event(
            connection,
            action="demo_data_reset",
            now=utc_now(),
            metadata={"source": "PR-29 demo reset", "deleted": deleted, "sample_data_only": True},
        )

    seeded_status["deleted"] = deleted
    return seeded_status


def demo_data_status(connection: Any | None = None) -> dict[str, Any]:
    close_connection = connection is None
    manager = get_connection() if close_connection else None
    active_connection = manager.__enter__() if manager else connection
    try:
        product_count = active_connection.execute(
            "SELECT COUNT(*) AS count FROM products WHERE slug IN (?, ?)",
            DEMO_PRODUCT_SLUGS,
        ).fetchone()["count"]
        competitor_count = active_connection.execute(
            "SELECT COUNT(*) AS count FROM competitors WHERE name IN (?, ?, ?)",
            DEMO_COMPETITOR_NAMES,
        ).fetchone()["count"]
        quote_count = active_connection.execute(
            "SELECT COUNT(*) AS count FROM quote_requests WHERE requester_email = ?",
            (DEMO_QUOTE_EMAIL,),
        ).fetchone()["count"]
        audit_count = active_connection.execute(
            "SELECT COUNT(*) AS count FROM audit_logs WHERE entity_type = 'demo_data'",
        ).fetchone()["count"]
        return {
            "status": "present" if product_count >= 2 and competitor_count >= 3 else "partial",
            "products": int(product_count),
            "competitors": int(competitor_count),
            "quote_requests": int(quote_count),
            "audit_logs": int(audit_count),
            "sample_data_only": True,
        }
    finally:
        if manager:
            manager.__exit__(None, None, None)
