"""Check archive checksums, JSON integrity, and residual contact/credential fields.

Reports field locations only, never the matched private values. Automated checks
do not establish rights or replace review of source categories before publication.
"""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

spec = importlib.util.spec_from_file_location("exporter", Path(__file__).with_name("build_raw_archive.py"))
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-dir", type=Path, required=True)
    args = parser.parse_args()
    directory = args.assets_dir
    manifest = json.loads((directory / "raw-release-manifest.json").read_text(encoding="utf-8"))
    issues = []
    checked = collections.Counter()
    text_keys = {"content", "title", "text", "summary", "body", "remark", "public_label", "label", "full_text"}

    def walk(value, location="", field=""):
        if isinstance(value, dict):
            for key, item in value.items():
                if exporter.keyform(key) in exporter.SECRET_KEYS:
                    issues.append({"location": location, "kind": "sensitive_field", "field": key})
                walk(item, location, key)
        elif isinstance(value, list):
            for item in value:
                walk(item, location, field)
        elif isinstance(value, str) and field in text_keys:
            for kind, pattern in exporter.CONTACT_PATTERNS:
                if kind != "local_path" and pattern.search(value):
                    issues.append({"location": location, "kind": kind, "field": field})

    for asset in manifest["assets"]:
        path = directory / asset["name"]
        if path.stat().st_size != asset["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != asset["sha256"]:
            raise RuntimeError("Asset checksum failed: " + asset["name"])
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as z:
                if z.testzip() is not None:
                    raise RuntimeError("ZIP integrity failed")
                for name in z.namelist():
                    raw = z.read(name)
                    if hashlib.sha256(raw).hexdigest() != Path(name).stem:
                        raise RuntimeError("Stored snapshot checksum failed")
                    if name.endswith(".json"):
                        walk(json.loads(raw), path.name + ":" + name)
                    elif name.endswith(".jsonl"):
                        for line in raw.decode("utf-8").splitlines():
                            if line:
                                walk(json.loads(line), path.name + ":" + name)
                    elif name.endswith((".txt", ".html")):
                        walk(raw.decode("utf-8"), path.name + ":" + name, "text")
                    checked["stored_snapshots"] += 1
        elif path.name.endswith("-objects.jsonl.gz"):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                for line in f:
                    value = json.loads(line)
                    if hashlib.sha256(exporter.dumps(value["data"])).hexdigest() != value["sha256"]:
                        raise RuntimeError("Post object checksum failed")
                    walk(value["data"], path.name + ":" + value["sha256"])
                    checked["post_objects"] += 1
        print("AUDITED", path.name, flush=True)
    report = {"checked": dict(checked), "issues": issues, "passed": not issues}
    (directory / "audit-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checked": dict(checked), "issues": len(issues)}, ensure_ascii=False), flush=True)
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
