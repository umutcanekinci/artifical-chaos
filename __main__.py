import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "src" / "pygame_core"))

# Packaged (PyInstaller) builds set sys.frozen; artifical-chaos.spec unpacks
# assets/ next to the executable, exposed as sys._MEIPASS in both onedir and
# onefile mode. Running from source never takes this branch, so the cwd ==
# repo root assumption documented in CLAUDE.md is unchanged for that case.
if getattr(sys, "frozen", False):
    os.chdir(sys._MEIPASS)

from app.game import Game

if __name__ == "__main__":
    Game().run()