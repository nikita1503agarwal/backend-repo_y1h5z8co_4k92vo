"""
Database Schemas for the Shopping System

Each Pydantic model represents a collection in MongoDB.
Collection name is the lowercase class name.
"""
from typing import List, Optional
from pydantic import BaseModel, Field

class Category(BaseModel):
    name: str = Field(..., description="Category name")
    slug: str = Field(..., description="URL-friendly unique identifier")
    description: Optional[str] = Field(None, description="Short description of the category")
    image: Optional[str] = Field(None, description="Cover image URL")

class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None, description="Product description")
    price: float = Field(..., ge=0, description="Price in dollars")
    compare_at_price: Optional[float] = Field(None, ge=0, description="Original price for discount display")
    category: str = Field(..., description="Category slug")
    images: List[str] = Field(default_factory=list, description="Image URLs")
    rating: float = Field(4.8, ge=0, le=5, description="Average rating")
    in_stock: bool = Field(True, description="Whether product is in stock")
    tags: List[str] = Field(default_factory=list, description="Search tags")

class CartItem(BaseModel):
    cart_id: str = Field(..., description="Client cart/session id")
    product_id: str = Field(..., description="Product document id as string")
    quantity: int = Field(1, ge=1, description="Quantity of the product")

class Order(BaseModel):
    cart_id: str = Field(..., description="Cart used to create this order")
    items: List[CartItem] = Field(..., description="Items purchased")
    subtotal: float = Field(..., ge=0)
    total: float = Field(..., ge=0)
    currency: str = Field("USD")
    status: str = Field("processing")
