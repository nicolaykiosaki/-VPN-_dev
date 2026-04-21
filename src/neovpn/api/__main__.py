"""Run the FastAPI app with uvicorn.

Usage::

    neovpn-api            # defaults: 0.0.0.0:8000
    neovpn-api --reload   # dev mode
"""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(prog="neovpn-api")
    parser.add_argument("--host", default="0.0.0.0")  # noqa: S104 — container
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "neovpn.api.app:create_app",
        host=args.host,
        port=args.port,
        factory=True,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
