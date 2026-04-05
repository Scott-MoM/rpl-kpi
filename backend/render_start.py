from __future__ import annotations

import os
import platform
import sys
import traceback

import uvicorn


def main() -> None:
    port_value = os.getenv("PORT", "10000").strip()
    try:
        port = int(port_value)
    except ValueError as exc:
        print(f"[render_start] Invalid PORT value: {port_value!r}", file=sys.stderr, flush=True)
        raise SystemExit(1) from exc

    print(
        f"[render_start] Python {platform.python_version()} starting on port {port}",
        file=sys.stderr,
        flush=True,
    )
    print(
        f"[render_start] CWD={os.getcwd()}",
        file=sys.stderr,
        flush=True,
    )

    try:
        from backend.app.main import app
    except Exception:
        print("[render_start] Failed to import backend.app.main:app", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
