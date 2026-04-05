import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
STATIC_DIR = ROOT / "backend" / "static"


def clear_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child, ignore_errors=True)
        else:
            child.unlink()


def copy_dist_to_static() -> None:
    dist_dir = FRONTEND_DIR / "dist"
    if not dist_dir.exists():
        raise FileNotFoundError("frontend/dist not found. Run `npm run build` first.")
    if STATIC_DIR.exists():
        clear_directory(STATIC_DIR)
    else:
        STATIC_DIR.mkdir(parents=True)

    for item in dist_dir.iterdir():
        target = STATIC_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


if __name__ == "__main__":
    copy_dist_to_static()
