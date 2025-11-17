import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson.objectid import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Category, CartItem, Order

app = FastAPI(title="Shopping System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utilities
class IdModel(BaseModel):
    id: str

def to_str_id(doc: dict):
    if doc is None:
        return None
    d = dict(doc)
    if d.get("_id"):
        d["id"] = str(d.pop("_id"))
    return d

@app.get("/")
def root():
    return {"message": "Shopping System Backend is running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set",
        "database_name": "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Seed minimal demo data if empty
@app.on_event("startup")
async def seed_data():
    if db is None:
        return
    if db["category"].count_documents({}) == 0:
        for c in [
            {"name": "Featured", "slug": "featured", "description": "Editor's picks", "image": None},
            {"name": "Accessories", "slug": "accessories", "description": "Bags & more", "image": None},
            {"name": "Tech", "slug": "tech", "description": "Gadgets & gear", "image": None},
        ]:
            db["category"].insert_one(c)
    if db["product"].count_documents({}) == 0:
        sample = [
            {
                "title": "Aurora Leather Tote",
                "description": "Premium full‑grain leather tote with magnetic closure.",
                "price": 189,
                "compare_at_price": 249,
                "category": "accessories",
                "images": [
                    "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?q=80&w=1200&auto=format&fit=crop",
                ],
                "rating": 4.9,
                "in_stock": True,
                "tags": ["bag", "leather", "tote"],
            },
            {
                "title": "Nebula Wireless Earbuds",
                "description": "Active noise cancelation with 36h battery life.",
                "price": 129,
                "compare_at_price": 159,
                "category": "tech",
                "images": [
                    "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?q=80&w=1200&auto=format&fit=crop",
                ],
                "rating": 4.7,
                "in_stock": True,
                "tags": ["audio", "wireless"],
            },
            {
                "title": "Orbit Ceramic Mug",
                "description": "Matte ceramic with heat‑retaining double wall.",
                "price": 24,
                "compare_at_price": 0,
                "category": "featured",
                "images": [
                    "https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?q=80&w=1200&auto=format&fit=crop",
                ],
                "rating": 4.8,
                "in_stock": True,
                "tags": ["mug", "ceramic"],
            },
        ]
        db["product"].insert_many(sample)

# Catalog endpoints
@app.get("/api/categories", response_model=List[Category])
def list_categories():
    docs = get_documents("category")
    return [Category(**{k: v for k, v in d.items() if k != "_id"}) for d in docs]

@app.get("/api/products")
def list_products(category: Optional[str] = None, q: Optional[str] = None):
    filt = {}
    if category:
        filt["category"] = category
    if q:
        filt["title"] = {"$regex": q, "$options": "i"}
    docs = get_documents("product", filt)
    return [to_str_id(d) for d in docs]

@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    try:
        doc = db["product"].find_one({"_id": ObjectId(product_id)})
    except Exception:
        raise HTTPException(404, "Invalid product id")
    if not doc:
        raise HTTPException(404, "Product not found")
    return to_str_id(doc)

# Cart endpoints (session based via cart_id)
@app.post("/api/cart/add")
def add_to_cart(item: CartItem):
    # Upsert quantity
    existing = db["cartitem"].find_one({"cart_id": item.cart_id, "product_id": item.product_id})
    if existing:
        db["cartitem"].update_one({"_id": existing["_id"]}, {"$inc": {"quantity": item.quantity}})
        return {"status": "updated"}
    create_document("cartitem", item)
    return {"status": "added"}

@app.get("/api/cart")
def get_cart(cart_id: str):
    items = list(db["cartitem"].find({"cart_id": cart_id}))
    result = []
    for it in items:
        p = db["product"].find_one({"_id": ObjectId(it["product_id"])})
        if p:
            result.append({
                "id": str(it["_id"]),
                "product": to_str_id(p),
                "quantity": it["quantity"],
            })
    return result

@app.post("/api/cart/remove")
def remove_from_cart(payload: IdModel):
    try:
        res = db["cartitem"].delete_one({"_id": ObjectId(payload.id)})
    except Exception:
        raise HTTPException(400, "Invalid id")
    if res.deleted_count == 0:
        raise HTTPException(404, "Item not found")
    return {"status": "removed"}

# Checkout (demo calculation only)
class CheckoutRequest(BaseModel):
    cart_id: str

class CheckoutResponse(BaseModel):
    subtotal: float
    total: float
    currency: str = "USD"

@app.post("/api/checkout", response_model=CheckoutResponse)
def checkout(payload: CheckoutRequest):
    items = list(db["cartitem"].find({"cart_id": payload.cart_id}))
    subtotal = 0.0
    for it in items:
        p = db["product"].find_one({"_id": ObjectId(it["product_id"])})
        if p:
            subtotal += float(p.get("price", 0)) * int(it.get("quantity", 1))
    total = round(subtotal * 1.08, 2)  # tax 8%
    return CheckoutResponse(subtotal=round(subtotal, 2), total=total)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
