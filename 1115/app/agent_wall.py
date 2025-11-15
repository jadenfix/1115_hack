import json
import os
from datetime import datetime
from pathlib import Path
from typing import List

from app.models import AgentWindowState

DATA_ROOT = Path("/data")
if not DATA_ROOT.exists():
    DATA_ROOT = Path(__file__).resolve().parent / "data"

RUNS_DIR = DATA_ROOT / "runs"
RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _windows_path(run_id: str) -> Path:
    return RUNS_DIR / run_id / "windows.json"


def update_window_state(run_id: str, window: AgentWindowState) -> None:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    path = _windows_path(run_id)
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
    path.write_text(json.dumps([w.model_dump() for w in filtered], default=str, indent=2))


def list_window_states(run_id: str) -> List[AgentWindowState]:
    path = _windows_path(run_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text())
        return [AgentWindowState(**w) for w in raw]
    except Exception:
        return []
