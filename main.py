import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="Honey & Bees Store API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Honey & Bees Store Backend is running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# -------- Products Endpoints --------

@app.get("/api/products", response_model=List[Product])
def list_products():
    try:
        docs = get_documents("product")
        # Convert ObjectId to string for any _id present
        for d in docs:
            if "_id" in d:
                d["_id"] = str(d["_id"])
        # Return as list of Product-like dicts (response_model will validate)
        return [
            Product(
                title=d.get("title"),
                description=d.get("description"),
                price=float(d.get("price", 0)),
                category=d.get("category", "honey"),
                in_stock=bool(d.get("in_stock", True)),
                image=d.get("image"),
                rating=float(d.get("rating", 4.8)),
                stock_qty=int(d.get("stock_qty", 10)),
            ).model_dump()
            for d in docs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CreateProduct(Product):
    pass

@app.post("/api/products", status_code=201)
def create_product(product: CreateProduct):
    try:
        inserted_id = create_document("product", product)
        return {"id": inserted_id, "message": "Product created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Seed some default products if collection empty
@app.post("/api/seed", status_code=201)
def seed_products():
    try:
        existing = get_documents("product", limit=1)
        if existing:
            return {"message": "Products already exist"}

        defaults = [
            {
                "title": "Wildflower Honey",
                "description": "Raw, unfiltered wildflower honey with rich floral notes.",
                "price": 12.99,
                "category": "honey",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1519681393784-d120267933ba", 
                "rating": 4.9,
                "stock_qty": 120,
            },
            {
                "title": "Beeswax Candles (Set of 3)",
                "description": "Hand-poured 100% beeswax candles with natural honey aroma.",
                "price": 18.5,
                "category": "beeswax",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1505575972945-381d50a4ac7b",
                "rating": 4.7,
                "stock_qty": 80,
            },
            {
                "title": "Propolis Tincture",
                "description": "High-potency propolis extract for immunity support.",
                "price": 22.0,
                "category": "propolis",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1517686469429-dc1c37a393f5",
                "rating": 4.6,
                "stock_qty": 60,
            },
            {
                "title": "Bee Pollen Granules",
                "description": "Nutrient-rich bee pollen harvested sustainably.",
                "price": 15.75,
                "category": "pollen",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1505577058444-a3dab90d4253",
                "rating": 4.8,
                "stock_qty": 95,
            },
        ]

        for p in defaults:
            create_document("product", p)

        return {"message": "Seeded default products"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------- Orders Endpoints --------

class CreateOrder(BaseModel):
    customer_name: str
    customer_email: EmailStr
    shipping_address: str
    items: List[OrderItem]
    notes: Optional[str] = None

@app.post("/api/orders", status_code=201)
def create_order(order: CreateOrder):
    try:
        # Compute total
        total = sum(item.unit_price * item.quantity for item in order.items)
        order_doc = order.model_dump()
        order_doc["total"] = round(total, 2)
        inserted_id = create_document("order", order_doc)
        return {"id": inserted_id, "message": "Order placed", "total": order_doc["total"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
