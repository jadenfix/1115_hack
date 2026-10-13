import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data" if Path("/data").exists() else str(Path(__file__).resolve().parent / "data")))


def _target(relative_path: str) -> Path:
    base = DATA_DIR.resolve()
    target = (base / relative_path).resolve()
    if target == base or not target.is_relative_to(base):
        raise ValueError("Storage path must stay inside DATA_DIR")
    return target


def _ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_json(relative_path: str, payload: Dict[str, Any]) -> str:
    target = _target(relative_path)
    _ensure_dir(target)
    # Readers see a complete snapshot even while a worker replaces it.
    with tempfile.NamedTemporaryFile(mode="w", dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(payload, handle, default=str, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return str(target)


def read_json(relative_path: str) -> Optional[Dict[str, Any]]:
    target = _target(relative_path)
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text())
    except Exception:
        return None


def list_json(prefix: str) -> List[Dict[str, Any]]:
    base = _target(prefix)
    if not base.exists():
        return []
    results = []
    for file in sorted(base.glob("*.json"), reverse=True):
        data = read_json(str(file.relative_to(DATA_DIR)))
        if data is not None:
            results.append(data)
    return results
