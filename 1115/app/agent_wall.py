import json
import re
from pathlib import Path
from typing import List

from app.models import AgentWindowState
from app.storage import DATA_DIR

DATA_ROOT = DATA_DIR

RUNS_DIR = DATA_ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _windows_path(run_id: str) -> Path:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("Invalid run identifier")
    return RUNS_DIR / run_id / "windows.json"


def update_window_state(run_id: str, window: AgentWindowState) -> None:
    path = _windows_path(run_id)
    run_dir = path.parent
    run_dir.mkdir(parents=True, exist_ok=True)
    current: List[AgentWindowState] = []
    if path.exists():
        try:
            raw = json.loads(path.read_text())
            current = [AgentWindowState(**w) for w in raw]
        except Exception:
            current = []
    filtered = [w for w in current if w.slot != window.slot]
    filtered.append(window)
    filtered.sort(key=lambda w: w.slot)
    path.write_text(
        json.dumps([w.model_dump() for w in filtered], default=str, indent=2)
    )


def list_window_states(run_id: str) -> List[AgentWindowState]:
    path = _windows_path(run_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text())
        return [AgentWindowState(**w) for w in raw]
    except Exception:
        return []
