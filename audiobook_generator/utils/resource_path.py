import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Get absolute path to resource, works for dev and for PyInstaller bundles.

    - In dev: relative to project root (two parents up from this file)
    - In frozen: from sys._MEIPASS base directory
    """
    base_path = None
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parents[2]
    return base_path / relative_path
