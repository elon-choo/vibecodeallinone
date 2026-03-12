"""ASGI entrypoint for assistant-api."""

from __future__ import annotations

import uvicorn

from .app import create_app

app = create_app()


if __name__ == "__main__":
    uvicorn.run("assistant_api.main:app", host="127.0.0.1", port=8080, reload=False)
