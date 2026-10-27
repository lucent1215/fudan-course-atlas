"""Download verified raw-source shards; optionally reconstruct redacted snapshots.

This downloads an existing public Release, never logs into or crawls a source site.
"""
from __future__ import annotations

import argparse
import hashlib
import gzip
import json
import shutil
import urllib.request
import zipfile
from pathlib import Path
from contextlib import ExitStack

RELEASE = "https://github.com/pythonbug225/fudan-course-atlas/releases/download/raw-snapshots-20261027/"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def contained(base, relative):
    target = (base / relative).resolve()
    if not target.is_relative_to(base.resolve()):
        raise ValueError("Path escapes target directory")
    return target


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("data/source-snapshots"))
    ap.add_argument("--category", action="append", help="Only this source category; repeatable")
    ap.add_argument("--verify-only", action="store_true", help="Never access the network")
    ap.add_argument("--materialize", action="store_true", help="Restore source paths under data-dir/snapshots")
    ap.add_argument("--source-match", help="Only inspect/restore source paths containing this fragment")
    a = ap.parse_args()
    repo = Path(__file__).resolve().parents[2]
    manifest = json.loads((repo / "research/raw-release-manifest.json").read_text(encoding="utf-8"))
    category_set = set(a.category or manifest["categories"])
    unknown = category_set - set(manifest["categories"])
    if unknown:
        ap.error("Unknown categories: " + ", ".join(sorted(unknown)))
    a.data_dir.mkdir(parents=True, exist_ok=True)
    assets = [x for x in manifest["assets"] if x["name"] == "source-inventory.jsonl" or any(x["name"].startswith(c + "-") for c in category_set)]
    for asset in assets:
        path = contained(a.data_dir, asset["name"])
        if not (path.is_file() and digest(path) == asset["sha256"]):
            if a.verify_only:
                raise RuntimeError("Missing or corrupt asset: " + asset["name"])
            tmp = path.with_suffix(path.suffix + ".partial")
            req = urllib.request.Request(RELEASE + asset["name"], headers={"User-Agent": "Fudan-Course-Source-Download"})
            with urllib.request.urlopen(req, timeout=120) as response, tmp.open("wb") as out:
                shutil.copyfileobj(response, out, 1024 * 1024)
            if tmp.stat().st_size != asset["bytes"] or digest(tmp) != asset["sha256"]:
                raise RuntimeError("Downloaded asset failed verification: " + asset["name"])
            tmp.replace(path)
        print("VERIFIED", asset["name"], path.stat().st_size, flush=True)
    rows = [json.loads(s) for s in (repo / "research/source-inventory.jsonl").read_text(encoding="utf-8").splitlines() if s]
    rows = [r for r in rows if r.get("published") and r["category"] in category_set and (not a.source_match or a.source_match in r["source_path"])]
    if not rows:
        raise RuntimeError("No published source paths match the selected filters")
    verified = set()
    objects = {}
    if a.materialize:
        needed = set()

        def need(value):
            if isinstance(value, dict):
                if set(value) == {"$raw_object"}:
                    needed.add(value["$raw_object"])
                else:
                    for item in value.values():
                        need(item)
            elif isinstance(value, list):
                for item in value:
                    need(item)

        with ExitStack() as stack:
            refs = {}
            for row in rows:
                if row.get("encoding") != "object-refs-v1":
                    continue
                name = row["archive"]
                if name not in refs:
                    refs[name] = stack.enter_context(zipfile.ZipFile(a.data_dir / name))
                data = refs[name].read(row["member"])
                if row["source_path"].endswith(".jsonl"):
                    for line in data.decode("utf-8").splitlines():
                        if line:
                            need(json.loads(line))
                else:
                    need(json.loads(data))
        for category, info in manifest.get("object_banks", {}).items():
            if category not in category_set:
                continue
            with gzip.open(a.data_dir / info["name"], "rt", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry["sha256"] not in needed:
                        continue
                    data = (json.dumps(entry["data"], ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                        raise RuntimeError("Post object failed SHA verification")
                    objects[entry["sha256"]] = entry["data"]
        if needed - objects.keys():
            raise RuntimeError("Source references missing post objects")

    def restore(value):
        if isinstance(value, dict):
            if set(value) == {"$raw_object"}:
                return objects[value["$raw_object"]]
            return {k: restore(v) for k, v in value.items()}
        if isinstance(value, list):
            return [restore(v) for v in value]
        return value

    def encoded(value):
        return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    with ExitStack() as stack:
        archives = {}
        for row in rows:
            if not row.get("published") or row["category"] not in category_set:
                continue
            name = row["archive"]
            if name not in archives:
                archives[name] = stack.enter_context(zipfile.ZipFile(a.data_dir / name))
            key = (name, row["member"])
            if key not in verified or a.materialize:
                data = archives[name].read(row["member"])
                if hashlib.sha256(data).hexdigest() != row.get("stored_sha256", row["sha256"]):
                    raise RuntimeError("Snapshot failed SHA verification")
                verified.add(key)
                if a.materialize:
                    if row.get("encoding") == "object-refs-v1":
                        if row["source_path"].endswith(".jsonl"):
                            data = b"".join(encoded(restore(json.loads(line))) for line in data.decode("utf-8").splitlines() if line)
                        else:
                            data = encoded(restore(json.loads(data)))
                    if hashlib.sha256(data).hexdigest() != row["sha256"]:
                        raise RuntimeError("Reconstructed source failed SHA verification")
                    out = contained(a.data_dir / "snapshots", row["source_path"])
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(data)
    print("Source blobs verified:", len(verified), flush=True)


if __name__ == "__main__":
    main()
