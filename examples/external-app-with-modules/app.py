"""
Example app that imports from sibling Python files.

This tests that when using --app-path, other Python files
in the same directory can be imported correctly.
"""

# Import from sibling file - this is the key test
from services import ProductService, UserService

from myfy.core import SINGLETON, Application, provider
from myfy.web import WebModule, route


@provider(scope=SINGLETON)
def user_service() -> UserService:
    return UserService()


@provider(scope=SINGLETON)
def product_service() -> ProductService:
    return ProductService()


@route.get("/")
async def home() -> dict:
    return {"message": "App with sibling imports"}


@route.get("/users/{user_id}")
async def get_user(user_id: int, service: UserService) -> dict:
    return service.get_user(user_id)


@route.get("/products/{product_id}")
async def get_product(product_id: int, service: ProductService) -> dict:
    return service.get_product(product_id)


app = Application(auto_discover=False)
app.add_module(WebModule())
