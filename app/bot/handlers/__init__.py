"""Telegram command and callback handlers."""

from app.bot.handlers.admin import create_admin_router, router as admin_router
from app.bot.handlers.start import create_start_router, router as start_router

__all__ = ["admin_router", "create_admin_router", "create_start_router", "start_router"]
