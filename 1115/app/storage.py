import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent / "data"


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(relative_path: str, payload: Dict[str, Any]) -> str:
    target = DATA_DIR / relative_path
    _ensure_dir(target)
    target.write_text(json.dumps(payload, default=str, indent=2))
    return str(target)


def read_json(relative_path: str) -> Optional[Dict[str, Any]]:
    target = DATA_DIR / relative_path
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text())
    except Exception:
        return None


def list_json(prefix: str) -> List[Dict[str, Any]]:
    base = DATA_DIR / prefix
    if not base.exists():
        return []
    results = []
    for file in sorted(base.glob("*.json"), reverse=True):
        data = read_json(str(file.relative_to(DATA_DIR)))
        if data is not None:
            results.append(data)
    return results
