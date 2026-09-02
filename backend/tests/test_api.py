from fastapi.testclient import TestClient
from uuid import uuid4
from app.main import app


def test_health_and_seeded_inventory():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert len(client.get("/api/inventory").json()) >= 6


def test_create_lookup_update_delete_inventory():
    with TestClient(app) as client:
        created = client.post("/api/inventory", json={"name":"Test Apples","category":"Fruits & Veg","quantity":8,"unit":"kg","expiry_date":"2030-01-04","donor":"Test Donor","barcode":"TEST-2030","notes":"test"})
        assert created.status_code == 201
        item_id = created.json()["id"]
        assert client.get("/api/inventory/scan/TEST-2030").json()["id"] == item_id
        updated = client.put(f"/api/inventory/{item_id}", json={"name":"Test Apples","category":"Fruits & Veg","quantity":5,"unit":"kg","expiry_date":"2030-01-04","donor":"Test Donor","barcode":"TEST-2030","notes":"updated","status":"reserved"})
        assert updated.json()["status"] == "reserved"
        assert client.delete(f"/api/inventory/{item_id}").status_code == 204


def test_csv_import_and_expiry_endpoint():
    code = f"CSV-{uuid4()}"
    csv = f"name,category,quantity,unit,expiry_date,donor,barcode,notes\nCSV Rice,Grains,12,kg,2030-02-01,CSV Donor,{code},bulk import\n"
    with TestClient(app) as client:
        response = client.post("/api/inventory/import", files={"file": ("items.csv", csv, "text/csv")})
        assert response.status_code == 200
        assert response.json()["added"] == 1
        assert client.get(f"/api/inventory/scan/{code}").json()["name"] == "CSV Rice"
        assert isinstance(client.get("/api/expiry").json(), list)
