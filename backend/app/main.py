import csv
import io
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection, init_db, log_activity
from .schemas import InventoryCreate, InventoryUpdate
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_if_empty()
    yield


app = FastAPI(title="FoodBridge API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ai-food-waste-management.vercel.app",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def item_dict(row):
    item = dict(row)
    expiry = date.fromisoformat(item["expiry_date"])
    days = (expiry - date.today()).days
    item["days_to_expiry"] = days
    item["expiry_state"] = "expired" if days < 0 else "urgent" if days <= 1 else "soon" if days <= 3 else "fresh"
    return item


def get_item_or_404(item_id: int):
    with get_connection() as db:
        item = db.execute("SELECT * FROM inventory_items WHERE id = ?", (item_id,)).fetchone()
    if not item:
        raise HTTPException(404, "Inventory item not found")
    return item


@app.get("/api/health")
def health(): return {"status": "ok"}


@app.get("/api/inventory")
def list_inventory(query: str = "", status: str = "", category: str = ""):
    clauses, values = [], []
    if query:
        clauses.append("(name LIKE ? OR donor LIKE ? OR barcode LIKE ?)"); values.extend([f"%{query}%"] * 3)
    if status:
        clauses.append("status = ?"); values.append(status)
    if category:
        clauses.append("category = ?"); values.append(category)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_connection() as db:
        rows = db.execute(f"SELECT * FROM inventory_items{where} ORDER BY expiry_date ASC", values).fetchall()
    return [item_dict(row) for row in rows]


@app.post("/api/inventory", status_code=201)
def create_inventory(payload: InventoryCreate):
    try:
        data = payload.model_dump()
        data["expiry_date"] = data["expiry_date"].isoformat()
        with get_connection() as db:
            cursor = db.execute("""INSERT INTO inventory_items (name, category, quantity, unit, expiry_date, donor, barcode, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (*data.values(),))
            log_activity(db, cursor.lastrowid, "Added", f"Added {payload.name} from {payload.donor}")
            row = db.execute("SELECT * FROM inventory_items WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return item_dict(row)
    except Exception as error:
        if "UNIQUE" in str(error): raise HTTPException(409, "Barcode already exists")
        raise


@app.put("/api/inventory/{item_id}")
def update_inventory(item_id: int, payload: InventoryUpdate):
    get_item_or_404(item_id)
    try:
        data = payload.model_dump()
        with get_connection() as db:
            db.execute("""UPDATE inventory_items SET name=:name, category=:category, quantity=:quantity, unit=:unit,
              expiry_date=:expiry_date, donor=:donor, barcode=:barcode, notes=:notes, status=:status WHERE id=:id""", {**data, "expiry_date": data["expiry_date"].isoformat(), "id": item_id})
            log_activity(db, item_id, "Updated", f"Updated {data['name']}")
            row = db.execute("SELECT * FROM inventory_items WHERE id=?", (item_id,)).fetchone()
        return item_dict(row)
    except Exception as error:
        if "UNIQUE" in str(error): raise HTTPException(409, "Barcode already exists")
        raise


@app.delete("/api/inventory/{item_id}", status_code=204)
def delete_inventory(item_id: int):
    get_item_or_404(item_id)
    with get_connection() as db:
        log_activity(db, item_id, "Removed", f"Removed inventory item #{item_id}")
        db.execute("DELETE FROM inventory_items WHERE id = ?", (item_id,))


@app.get("/api/inventory/scan/{code}")
def scan_lookup(code: str):
    with get_connection() as db: row = db.execute("SELECT * FROM inventory_items WHERE barcode = ?", (code,)).fetchone()
    if not row: raise HTTPException(404, "No inventory item matches this code")
    return item_dict(row)


@app.get("/api/dashboard")
def dashboard():
    with get_connection() as db:
        rows = db.execute("SELECT * FROM inventory_items").fetchall()
        donors = db.execute("SELECT donor, ROUND(SUM(quantity), 1) quantity FROM inventory_items GROUP BY donor ORDER BY quantity DESC LIMIT 5").fetchall()
        activity = db.execute("SELECT * FROM activity_log ORDER BY created_at DESC, id DESC LIMIT 6").fetchall()
    items = [item_dict(row) for row in rows]
    active = [i for i in items if i["status"] != "distributed" and i["expiry_state"] != "expired"]
    by_category = {}
    for item in items:
        if item["status"] != "distributed": by_category[item["category"]] = by_category.get(item["category"], 0) + item["quantity"]
    return {"metrics": {"active_listings": len(active), "available_kg": round(sum(i["quantity"] for i in active), 1), "expiring_soon": len([i for i in active if i["days_to_expiry"] <= 1]), "donors": len(set(i["donor"] for i in items))}, "by_category": [{"category": k, "quantity": v} for k, v in by_category.items()], "top_donors": [dict(r) for r in donors], "recent_activity": [dict(r) for r in activity]}


@app.get("/api/expiry")
def expiry(days: int = 3):
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    with get_connection() as db: rows = db.execute("SELECT * FROM inventory_items WHERE expiry_date <= ? AND status != 'distributed' ORDER BY expiry_date", (cutoff,)).fetchall()
    return [item_dict(row) for row in rows]


@app.post("/api/inventory/import")
async def import_csv(file: Annotated[UploadFile, File(...)]):
    if not file.filename or not file.filename.lower().endswith(".csv"): raise HTTPException(400, "Please upload a CSV file")
    try:
        reader = csv.DictReader(io.StringIO((await file.read()).decode("utf-8-sig")))
        required = {"name", "category", "quantity", "unit", "expiry_date", "donor"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames): raise HTTPException(400, "CSV needs columns: name, category, quantity, unit, expiry_date, donor")
        added, errors = 0, []
        with get_connection() as db:
            for line, row in enumerate(reader, start=2):
                try:
                    payload = InventoryCreate(**{key: row.get(key, "") for key in ["name", "category", "quantity", "unit", "expiry_date", "donor", "barcode", "notes"]})
                    data = payload.model_dump(); data["expiry_date"] = data["expiry_date"].isoformat()
                    cursor = db.execute("INSERT INTO inventory_items (name,category,quantity,unit,expiry_date,donor,barcode,notes) VALUES (?,?,?,?,?,?,?,?)", (*data.values(),))
                    log_activity(db, cursor.lastrowid, "CSV import", f"Imported {payload.name}"); added += 1
                except Exception as error: errors.append({"line": line, "message": str(error)})
        return {"added": added, "errors": errors}
    except UnicodeDecodeError: raise HTTPException(400, "CSV must be UTF-8 encoded")
