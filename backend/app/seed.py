from datetime import date, timedelta
from .database import get_connection, log_activity


def seed_if_empty() -> None:
    with get_connection() as db:
        if db.execute("SELECT COUNT(*) FROM inventory_items").fetchone()[0]:
            return
        today = date.today()
        items = [
            ("Prepared Veg Meals", "Cooked Meals", 48, "kg", today + timedelta(days=1), "Hotel Sunshine", "FB-1001", "Collect before 6 PM", "available"),
            ("Whole Wheat Bread", "Bakery", 32, "kg", today + timedelta(days=2), "City Bakery", "FB-1002", "Packed this morning", "available"),
            ("Seasonal Vegetables", "Fruits & Veg", 64, "kg", today + timedelta(days=4), "FreshMart", "FB-1003", "Keep refrigerated", "reserved"),
            ("Rice & Curry", "Cooked Meals", 28, "kg", today, "Campus Canteen", "FB-1004", "Urgent pickup", "available"),
            ("Mixed Cooked Food", "Cooked Meals", 42, "kg", today + timedelta(days=3), "Spice Garden", "FB-1005", "", "distributed"),
            ("Yogurt Cups", "Dairy", 18, "kg", today - timedelta(days=1), "Dairy Delight", "FB-1006", "Expired sample", "available"),
        ]
        for item in items:
            cursor = db.execute(
                """INSERT INTO inventory_items
                   (name, category, quantity, unit, expiry_date, donor, barcode, notes, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (*item[:4], item[4].isoformat(), *item[5:]),
            )
            log_activity(db, cursor.lastrowid, "Seeded", f"Added {item[0]} from {item[5]}")
