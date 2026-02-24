"""
Compatibility ASGI module.

Allows running:
    uvicorn app.main:app --reload
for this Django project.
"""

from config.asgi import application as app

