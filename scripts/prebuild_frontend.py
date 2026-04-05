import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
STATIC_DIR = ROOT / "backend" / "static"


def copy_dist_to_static() -> None:
    if not (FRONTEND_DIR / "dist").exists():
        raise FileNotFoundError("frontend/dist not found. Run `npm run build` first.")
    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(FRONTEND_DIR / "dist", STATIC_DIR)


if __name__ == "__main__":
    copy_dist_to_static()
