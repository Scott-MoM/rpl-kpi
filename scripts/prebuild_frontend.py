import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
STATIC_DIR = ROOT / "backend" / "static"
NPM = "npm.cmd" if os.name == "nt" else "npm"


def run_command(command: list[str], cwd: Path) -> None:
    subprocess.run(command, check=True, cwd=cwd)


def build_frontend() -> None:
    run_command([NPM, "run", "build"], FRONTEND_DIR)


def copy_dist_to_static() -> None:
    if STATIC_DIR.exists():
        shutil.rmtree(STATIC_DIR)
    shutil.copytree(FRONTEND_DIR / "dist", STATIC_DIR)


if __name__ == "__main__":
    build_frontend()
    copy_dist_to_static()
