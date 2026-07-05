"""Shared Jinja2 templates instance."""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app.config import TEMPLATE_DIR

templates = Jinja2Templates(directory=TEMPLATE_DIR)
