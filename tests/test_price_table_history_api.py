import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import SessionLocal, create_db_and_tables
from backend.main import app
from backend.models import PriceTable, PriceTableItem, Product
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_price_table_summary_returns_item_count_and_averages():
    table_id = _create_table("Summary", [(1, 10000, 0.3), (2, 20000, 0.4)])
    response = client.get(
        f"/api/price-tables/{table_id}/summary", headers=_auth_headers("viewer")
    )

    assert response.status_code == 200
    data = response.json()
    assert data["item_count"] == 2
    assert data["average_price"] == 15000.0
    assert data["min_price"] == 10000.0
    assert data["max_price"] == 20000.0
    assert data["average_margin_rate"] == 0.35


def test_create_snapshot_successfully():
    table_id = _create_table("Snapshot", [(1, 10000, 0.3)])
    response = _create_snapshot(table_id, "Before February update")

    assert response.status_code == 201
    data = response.json()
    assert data["price_table_id"] == table_id
    assert data["label"] == "Before February update"
    assert data["item_count"] == 1
    assert data["items"][0]["product_name"] == "Demo A3 Flyer"


def test_list_snapshots_for_price_table():
    table_id = _create_table("List Snapshots", [(1, 10000, 0.3)])
    created = _create_snapshot(table_id, "List snapshot").json()
    response = client.get(
        f"/api/price-tables/{table_id}/snapshots", headers=_auth_headers("viewer")
    )

    assert response.status_code == 200
    assert any(snapshot["id"] == created["id"] for snapshot in response.json())


def test_get_snapshot_by_id():
    table_id = _create_table("Get Snapshot", [(1, 10000, 0.3)])
    created = _create_snapshot(table_id, "Get snapshot").json()
    response = client.get(
        f"/api/price-table-snapshots/{created['id']}", headers=_auth_headers("viewer")
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_compare_two_price_tables_with_changed_item():
    base_id = _create_table("Base Changed", [(1, 10000, 0.3)])
    target_id = _create_table("Target Changed", [(1, 12000, 0.35)])
    response = _compare_tables(base_id, target_id)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["changed_items"] == 1
    change = data["changes"][0]
    assert change["change_type"] == "changed"
    assert change["price_delta"] == 2000.0
    assert change["price_delta_rate"] == 0.2
    assert change["margin_delta"] == 0.05


def test_compare_two_price_tables_with_added_item():
    base_id = _create_table("Base Added", [(1, 10000, 0.3)])
    target_id = _create_table("Target Added", [(1, 10000, 0.3), (2, 20000, 0.4)])
    response = _compare_tables(base_id, target_id)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["added_items"] == 1
    assert any(change["change_type"] == "added" for change in data["changes"])


def test_compare_two_snapshots():
    base_table_id = _create_table("Snapshot Base", [(1, 10000, 0.3)])
    target_table_id = _create_table("Snapshot Target", [(1, 15000, 0.4)])
    base_snapshot_id = _create_snapshot(base_table_id, "Base snapshot").json()["id"]
    target_snapshot_id = _create_snapshot(target_table_id, "Target snapshot").json()["id"]
    response = client.post(
        "/api/price-table-snapshots/compare",
        headers=_auth_headers("viewer"),
        json={"base_snapshot_id": base_snapshot_id, "target_snapshot_id": target_snapshot_id},
    )

    assert response.status_code == 200
    assert response.json()["summary"]["changed_items"] == 1
    assert response.json()["changes"][0]["price_delta"] == 5000.0


def test_missing_price_table_returns_404():
    response = client.get("/api/price-tables/999999/summary", headers=_auth_headers("viewer"))

    assert response.status_code == 404


def test_missing_snapshot_returns_404():
    response = client.get("/api/price-table-snapshots/999999", headers=_auth_headers("viewer"))

    assert response.status_code == 404


def test_audit_log_is_created_after_snapshot_creation():
    table_id = _create_table("Snapshot Audit", [(1, 10000, 0.3)])
    created = _create_snapshot(table_id, "Audit snapshot").json()
    response = client.get(
        "/api/audit-logs",
        params={"action": "price_table_snapshot_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    assert response.json()[0]["entity_id"] == str(created["id"])


def test_audit_log_is_created_after_comparison():
    base_id = _create_table("Audit Compare Base", [(1, 10000, 0.3)])
    target_id = _create_table("Audit Compare Target", [(1, 12000, 0.35)])
    assert _compare_tables(base_id, target_id).status_code == 200
    response = client.get(
        "/api/audit-logs",
        params={"action": "price_table_comparison_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    assert '"changed_items":1' in response.json()[0]["metadata_json"]


def test_openapi_includes_price_table_history_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/price-tables/{price_table_id}/summary" in paths
    assert "/api/price-tables/{price_table_id}/snapshots" in paths
    assert "/api/price-table-snapshots/{snapshot_id}" in paths
    assert "/api/price-tables/compare" in paths
    assert "/api/price-table-snapshots/compare" in paths


def _create_table(label: str, items: list[tuple[int, float, float]]) -> int:
    db = SessionLocal()
    try:
        table = PriceTable(
            name=f"{label} {uuid4().hex[:8]}",
            status="draft",
            description="Test price table for history comparison.",
        )
        db.add(table)
        db.flush()
        for product_id, price, margin_rate in items:
            product = db.get(Product, product_id)
            assert product is not None
            db.add(
                PriceTableItem(
                    price_table_id=table.id,
                    product_id=product.id,
                    price=price,
                    margin_rate=margin_rate,
                )
            )
        db.commit()
        return table.id
    finally:
        db.close()


def _create_snapshot(table_id: int, label: str):
    return client.post(
        f"/api/price-tables/{table_id}/snapshots",
        headers=_auth_headers("manager"),
        json={"label": label, "note": "Snapshot for deterministic comparison."},
    )


def _compare_tables(base_id: int, target_id: int):
    return client.post(
        "/api/price-tables/compare",
        headers=_auth_headers("viewer"),
        json={"base_price_table_id": base_id, "target_price_table_id": target_id},
    )


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
