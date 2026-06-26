import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_import_products_csv_creates_products():
    csv_text = "name,sku,category,description,active\nCSV Product,CSV-PRODUCT-10,A3 Flyer,Imported,true\n"
    response = _post_csv("/api/import/products", csv_text)

    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "products"
    assert data["received_rows"] == 1
    assert data["created_rows"] == 1
    assert data["failed_rows"] == 0


def test_import_products_csv_updates_existing_product_by_sku():
    csv_text = "name,sku,category,description,active\nCSV Product Updated,CSV-PRODUCT-10,A3 Flyer,Updated,false\n"
    response = _post_csv("/api/import/products", csv_text)

    assert response.status_code == 200
    data = response.json()
    assert data["created_rows"] == 0
    assert data["updated_rows"] == 1


def test_product_import_reports_invalid_rows():
    csv_text = "name,sku,category\nMissing SKU,,A3 Flyer\n"
    response = _post_csv("/api/import/products", csv_text)

    assert response.status_code == 200
    data = response.json()
    assert data["received_rows"] == 1
    assert data["failed_rows"] == 1
    assert data["errors"][0]["row_number"] == 2
    assert "sku" in data["errors"][0]["message"]


def test_import_cost_profiles_csv_creates_or_updates_cost_profile():
    _post_csv(
        "/api/import/products",
        "name,sku,category\nCost CSV Product,CSV-COST-PRODUCT,A3 Flyer\n",
    )
    csv_text = (
        "product_sku,material_cost,labor_cost,overhead_cost,target_margin_rate,active\n"
        "CSV-COST-PRODUCT,100,200,300,0.4,true\n"
    )
    create_response = _post_csv("/api/import/cost-profiles", csv_text)
    update_response = _post_csv(
        "/api/import/cost-profiles",
        "product_sku,material_cost,labor_cost,overhead_cost,target_margin_rate\n"
        "CSV-COST-PRODUCT,150,250,350,0.3\n",
    )

    assert create_response.status_code == 200
    assert create_response.json()["created_rows"] == 1
    assert update_response.status_code == 200
    assert update_response.json()["updated_rows"] == 1


def test_cost_profile_import_fails_for_missing_product_sku():
    csv_text = (
        "product_sku,material_cost,labor_cost,overhead_cost,target_margin_rate\n"
        "MISSING-SKU,100,200,300,0.4\n"
    )
    response = _post_csv("/api/import/cost-profiles", csv_text)

    assert response.status_code == 200
    assert response.json()["failed_rows"] == 1
    assert "Product not found" in response.json()["errors"][0]["message"]


def test_import_competitor_prices_csv_creates_reference_prices():
    _post_csv(
        "/api/import/products",
        "name,sku,category\nCompetitor CSV Product,CSV-COMPETITOR-PRODUCT,A3 Flyer\n",
    )
    csv_text = (
        "competitor_name,product_sku,reference_price,channel,source_note,observed_at\n"
        "CSV Competitor,CSV-COMPETITOR-PRODUCT,12345,local_shop,Manual CSV,2026-01-01T00:00:00\n"
    )
    response = _post_csv("/api/import/competitor-prices", csv_text)

    assert response.status_code == 200
    data = response.json()
    assert data["entity_type"] == "competitor_prices"
    assert data["created_rows"] == 1
    assert data["failed_rows"] == 0


def test_competitor_price_import_fails_for_missing_product_sku():
    csv_text = "competitor_name,product_sku,reference_price\nCSV Competitor,MISSING-SKU,12345\n"
    response = _post_csv("/api/import/competitor-prices", csv_text)

    assert response.status_code == 200
    assert response.json()["failed_rows"] == 1
    assert "Product not found" in response.json()["errors"][0]["message"]


def test_export_products_returns_csv_content_type():
    response = client.get("/api/export/products.csv", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "id,name,sku,category,description,active,created_at,updated_at" in response.text
    assert "password_hash" not in response.text


def test_export_cost_profiles_returns_csv_content_type():
    response = client.get("/api/export/cost-profiles.csv", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "product_sku" in response.text


def test_export_competitor_prices_returns_csv_content_type():
    response = client.get("/api/export/competitor-prices.csv", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "competitor_name,product_sku,reference_price" in response.text


def test_import_creates_audit_log_summary():
    csv_text = "name,sku,category\nAudit CSV Product,CSV-AUDIT-PRODUCT,A3 Flyer\n"
    response = _post_csv("/api/import/products", csv_text)
    assert response.status_code == 200

    logs = client.get(
        "/api/audit-logs",
        params={"action": "csv_products_imported", "limit": 1},
        headers=_auth_headers("admin"),
    )
    assert logs.status_code == 200
    metadata = logs.json()[0]["metadata_json"]
    assert '"entity_type":"products"' in metadata
    assert '"received_rows":1' in metadata
    assert "CSV-AUDIT-PRODUCT" not in metadata


def test_openapi_includes_import_export_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/import/products" in paths
    assert "/api/import/cost-profiles" in paths
    assert "/api/import/competitor-prices" in paths
    assert "/api/export/products.csv" in paths
    assert "/api/export/cost-profiles.csv" in paths
    assert "/api/export/competitor-prices.csv" in paths


def _post_csv(path: str, csv_text: str):
    return client.post(
        path,
        headers=_auth_headers("manager"),
        files={"file": ("import.csv", csv_text, "text/csv")},
    )


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
