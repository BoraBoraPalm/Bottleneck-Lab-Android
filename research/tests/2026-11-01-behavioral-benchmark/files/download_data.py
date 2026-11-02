"""Optional: fetch immutable source portfolios and verify recorded SHA-256.

The compact bundle replays selected source returns without downloading these
large files. French/FX data may later be revised: never silently accept a changed
file as the original snapshot. The original small files are already bundled.
"""
import hashlib
import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def load(record):
    target = DATA / record["file"]
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == record["sha256"]:
        return "Already verified: " + target.name
    with urllib.request.urlopen(record["url"], timeout=50) as response:
        raw = response.read()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != record["sha256"]:
        raise RuntimeError("Source snapshot changed; refusing replacement: " + record["file"])
    assert len(raw) == record["bytes"]
    target.write_bytes(raw)
    return "Downloaded and verified: " + target.name


if __name__ == "__main__":
    records = json.loads((DATA / "sources.json").read_text())
    with ThreadPoolExecutor(max_workers=3) as pool:
        for status in pool.map(load, records):
            print(status, flush=True)
