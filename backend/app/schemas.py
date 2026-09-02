from datetime import date
from pydantic import BaseModel, Field


class InventoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: str = Field(min_length=2, max_length=60)
    quantity: float = Field(gt=0, le=100000)
    unit: str = Field(default="kg", min_length=1, max_length=12)
    expiry_date: date
    donor: str = Field(min_length=2, max_length=120)
    barcode: str | None = Field(default=None, max_length=100)
    notes: str = Field(default="", max_length=500)


class InventoryUpdate(InventoryCreate):
    status: str = Field(default="available", pattern="^(available|reserved|distributed)$")
