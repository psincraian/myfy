"""
Services module - demonstrates importing from sibling files.
"""


class UserService:
    """Service that would be imported from app.py."""

    def get_user(self, user_id: int) -> dict:
        return {"id": user_id, "name": f"User {user_id}"}


class ProductService:
    """Another service in the same directory."""

    def get_product(self, product_id: int) -> dict:
        return {"id": product_id, "name": f"Product {product_id}", "price": 9.99}
