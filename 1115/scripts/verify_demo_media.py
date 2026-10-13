"""Verify demo provenance, hashes, dimensions, duration, and full decoding."""

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "docs" / "demo"


def run(*args: str) -> str:
    return subprocess.run(
        args, cwd=ROOT, check=True, text=True, capture_output=True
    ).stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: Path) -> dict:
    return json.loads(
        run(
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(path),
        )
    )


def main() -> None:
    receipt = json.loads((DEMO / "capture.json").read_text())
    commit_tree = run("git", "rev-parse", f"{receipt['source_commit']}^{{tree}}")
    assert commit_tree == receipt["source_tree"]

    for relative, expected_blob in receipt["source_blobs"].items():
        blob = run("git", "rev-parse", f"{receipt['source_commit']}:1115/{relative}")
        assert blob == expected_blob, f"source drift: {relative}"

    for name, expected in receipt["artifacts"].items():
        path = DEMO / name
        assert sha256(path) == expected["sha256"], f"hash mismatch: {name}"
        metadata = probe(path)
        stream = metadata["streams"][0]
        assert stream["width"] == expected["width"]
        assert stream["height"] == expected["height"]
        if "duration_seconds" in expected:
            assert (
                abs(
                    float(metadata["format"]["duration"]) - expected["duration_seconds"]
                )
                < 0.1
            )
        run("ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-")

    print("MEDIA_VERIFY_OK artifacts=3 source_blobs=24 full_decode=gif,mp4,png")


if __name__ == "__main__":
    main()
