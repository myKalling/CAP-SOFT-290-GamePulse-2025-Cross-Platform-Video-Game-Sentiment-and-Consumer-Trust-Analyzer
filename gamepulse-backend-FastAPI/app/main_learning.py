"""Compatibility import for the original learning entry point.

Run the complete GamePulse API with ``uvicorn app.main_learning:app`` or the
documented ``uvicorn app.main:app`` command; both expose the same app.
"""

from app.main import app
