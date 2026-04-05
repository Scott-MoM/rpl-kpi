from __future__ import annotations

import os
import platform
import sys
import traceback

def main() -> None:
    try:
        import uvicorn
    except BaseException:
        print("[render_start] Failed while importing uvicorn", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

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
    print("[render_start] Importing backend.app.main:app", file=sys.stderr, flush=True)

    try:
        from backend.app.main import app
    except BaseException:
        print("[render_start] Failed while importing backend.app.main:app", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise

    print("[render_start] App import succeeded; starting uvicorn", file=sys.stderr, flush=True)

    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except BaseException:
        print("[render_start] Uvicorn exited with an exception", file=sys.stderr, flush=True)
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
