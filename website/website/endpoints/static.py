"""Static file endpoints for favicon and Apple touch icons."""

from pathlib import Path

from starlette.responses import FileResponse

from myfy.web import route


@route.get("/favicon.ico")
async def favicon():
    """Serve favicon.ico from static images directory.

    Returns:
        FileResponse with favicon.ico and caching headers
    """
    favicon_path = Path("frontend/static/images/favicon.ico")
    return FileResponse(
        favicon_path,
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=31536000"},  # 1 year cache
    )


@route.get("/apple-touch-icon.png")
async def apple_touch_icon_default():
    """Serve default Apple touch icon (180x180).

    This is the fallback that Apple devices look for automatically.

    Returns:
        FileResponse with 180x180 Apple touch icon and caching headers
    """
    icon_path = Path("frontend/static/images/apple-touch-icon-180x180.png")
    return FileResponse(
        icon_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},  # 1 year cache
    )


@route.get("/apple-touch-icon-180x180.png")
async def apple_touch_icon_180():
    """Serve 180x180 Apple touch icon.

    For iPhone (6 Plus and newer) and iPad Retina.

    Returns:
        FileResponse with 180x180 Apple touch icon and caching headers
    """
    icon_path = Path("frontend/static/images/apple-touch-icon-180x180.png")
    return FileResponse(
        icon_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},  # 1 year cache
    )


@route.get("/apple-touch-icon-152x152.png")
async def apple_touch_icon_152():
    """Serve 152x152 Apple touch icon.

    For iPad Retina.

    Returns:
        FileResponse with 152x152 Apple touch icon and caching headers
    """
    icon_path = Path("frontend/static/images/apple-touch-icon-152x152.png")
    return FileResponse(
        icon_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},  # 1 year cache
    )


@route.get("/apple-touch-icon-120x120.png")
async def apple_touch_icon_120():
    """Serve 120x120 Apple touch icon.

    For iPhone Retina.

    Returns:
        FileResponse with 120x120 Apple touch icon and caching headers
    """
    icon_path = Path("frontend/static/images/apple-touch-icon-120x120.png")
    return FileResponse(
        icon_path,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000"},  # 1 year cache
    )
