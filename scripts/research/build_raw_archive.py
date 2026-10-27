"""Export source snapshots for collaboration without publishing private workspaces.

Offline only. Every candidate is accounted for in source-inventory.jsonl. Archives
contain source responses with explicit redactions, not a claim of human review.
No account, browser state, network request, or original file is modified.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SCHEMA = "fudan-source-snapshots/1"
LICENSE_URL = "https://danxi.fduhole.com/doc/community-user-agreement"
SECRET_KEYS = {
    "password", "passwd", "pwd", "token", "accesstoken", "refreshtoken",
    "authorization", "cookie", "cookies", "setcookie", "session", "sessionid",
    "csrf", "csrftoken", "ticket", "credential", "credentials", "headers",
    "siwcbypassbearertoken", "xsectoken", "secret", "clientsecret", "email", "phone",
    "mobile", "telephone", "openid", "unionid", "wxid", "wechatid", "qq",
    "studentid", "studentnumber", "stdid", "stdcode", "stdnumber", "sno",
    "userid", "realname", "fullname", "identitynumber", "idcard", "ip",
    "ipaddress", "avatar", "avatarurl", "useravatar", "studentlist",
    "students", "studentnames", "stdlist", "createdby", "updatedby",
    "operator", "loginname", "account", "username", "userprofile",
}
SIGNED_PARAMS = {
    "token", "access_token", "refresh_token", "xsec_token", "ticket",
    "authorization", "session", "sessionid", "sid", "jsessionid", "auth",
    "pwd", "password", "secret", "signature", "sig", "key", "code",
}
URL_RE = re.compile(r"https?://[^\s<>\"'\]\)]+")
CONTACT_PATTERNS = [
    ("email", re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")),
    ("student_number", re.compile(r"(?<!\d)2\d{10}(?!\d)")),
    ("id_card", re.compile(r"(?<!\d)[1-9]\d{16}[0-9Xx](?![\dXx])")),
    ("wechat_id", re.compile(r"wxid_[A-Za-z0-9_-]+", re.I)),
    ("chatroom_id", re.compile(r"\d{5,}@chatroom", re.I)),
    ("jwt", re.compile(r"eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("access_secret", re.compile(r"(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|art_v\d_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_-]{20,})")),
    ("contact", re.compile(r"(?i)(?:微信(?:号)?|微[信xX]|vx|v信|QQ(?:号)?|q群|qq群|扣扣|扣群|加群|群号)\s*[:：=]?\s*[A-Za-z0-9_-]{5,}")),
    ("share_password", re.compile(r"(?:提取码|提取密码|访问码|访问密码|解压码|解压密码|口令)\s*[:：=]?\s*[^\s，。；;、<>]{1,30}")),
    ("inline_secret", re.compile(r"(?i)\b(?:password|passwd|access_token|refresh_token|authorization)\s*[:=]\s*[^\s,;<>]{3,}")),
    ("local_path", re.compile(r"[A-Za-z]:[\\/](?:Users|下载|wx|xwechat_files|danxi)[^\s<>\"']*", re.I)),
]
NO_REPRINT = re.compile(r"禁止转载|不得转载|请勿转载|谢绝转载|不许转载|严禁转载|不允许转载|禁止转发|未经.{0,12}(?:许可|允许|同意).{0,8}转载")
BODY_FIELDS = {"content", "body", "text", "html", "title", "remark", "excerpt", "quote", "full_text"}
EXTERNAL_BODY_FIELDS = (BODY_FIELDS - {"title"}) | {"raw", "raw_text", "raw_html", "source_text", "page_text", "screenshot", "slides", "source_excerpts", "quotes", "excerpts"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def keyform(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def dumps(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")


def read_jsonl(raw: bytes, changes: collections.Counter, category: str):
    records, invalid = [], []
    for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(sanitize(json.loads(line), changes, category))
        except ValueError:
            invalid.append({"line": number, "bytes": len(line.encode("utf-8")), "sha256": sha(line.encode("utf-8"))})
    if not records and invalid:
        raise ValueError("No valid JSONL records")
    return records, invalid


def public_url(value: str, changes: collections.Counter) -> str:
    try:
        parts = urlsplit(value)
        if parts.hostname in {"pan.baidu.com", "pan.quark.cn", "www.aliyundrive.com", "www.alipan.com", "qm.qq.com", "jq.qq.com"}:
            changes["private_share_url"] += 1
            return "[分享链接已省略]"
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        clean = [(k, v) for k, v in pairs if k.lower() not in SIGNED_PARAMS]
        if parts.username or parts.password or clean != pairs:
            changes["signed_url"] += 1
            return urlunsplit((parts.scheme, parts.hostname or "", parts.path, urlencode(clean), parts.fragment))
    except ValueError:
        changes["invalid_url"] += 1
        return "[无效链接已省略]"
    return value


def clean_text(value: str, changes: collections.Counter) -> str:
    value = URL_RE.sub(lambda m: public_url(m.group(), changes), value)
    for name, pattern in CONTACT_PATTERNS:
        value, count = pattern.subn("[已脱敏]", value)
        changes[name] += count
    return value


def sanitize(value, changes: collections.Counter, category: str):
    if isinstance(value, str):
        return clean_text(value, changes)
    if isinstance(value, list):
        return [sanitize(v, changes, category) for v in value]
    if not isinstance(value, dict):
        return value
    withheld = None
    # A response can contain many independent floors/reviews. Restrict each item,
    # rather than withdrawing an entire course group because one author opted out.
    is_post = any(k in value for k in ("floor_id", "ranking", "review_id")) or (
        "content" in value and any(k in value for k in ("rank", "time_created"))
    )
    if is_post:
        body = "\n".join(str(value.get(k, "")) for k in BODY_FIELDS)
        if value.get("deleted") in (True, 1, "true"):
            withheld = "original_deleted"
        elif NO_REPRINT.search(body):
            withheld = "author_restricts_republication"
    out = {}
    for k, v in value.items():
        normalized = keyform(k)
        if normalized in SECRET_KEYS or normalized.endswith(("accesstoken", "refreshtoken", "password", "sessiontoken", "xsectoken")):
            changes["removed_identity_or_secret_field"] += 1
            continue
        if k in {"user", "author"} and isinstance(v, dict):
            # Preserve supplied public attribution, not a profile/account graph.
            label = v.get("nickname") or v.get("name") or v.get("display_name")
            if label:
                out[k] = {"public_label": clean_text(str(label), changes)}
            changes["profile_reduced_to_public_attribution"] += 1
            continue
        if category == "external-web" and k.lower() in EXTERNAL_BODY_FIELDS:
            changes["external_fulltext_not_redistributed"] += 1
            continue
        if withheld and k.lower() in BODY_FIELDS:
            out[k] = "[正文未公开：" + withheld + "]"
            continue
        out[k] = sanitize(v, changes, category)
    if withheld:
        out["archive_body_status"] = withheld
        changes[withheld] += 1
    return out


def category_for(p: Path, workspace: Path):
    rel = p.relative_to(workspace)
    parts = rel.parts
    lower = p.name.lower()
    external_capture_dir = any(s in parts for s in ("外部课评补搜_20261024", "继续补查_20261024", "续查_20261024", "新增群聊与全网续查_20261025_2", "public_research"))
    if external_capture_dir and p.suffix.lower() in {".txt", ".html", ".png", ".jpg", ".jpeg"}:
        return "excluded-external-fulltext"
    if "jwc_research_private" in parts and p.suffix.lower() in {".html", ".txt", ".json"}:
        return "official-rules"
    if p.suffix.lower() not in {".json", ".jsonl", ".txt"}:
        return None
    if any(s in parts for s in (".git", "node_modules", "__pycache__", "依赖", "_deps", "wechat-tools")):
        return None
    if any(s in lower for s in ("chat", "群聊", "xianghui", "info2", "caicai", "unmapped_batch2_private", "attribution_groups")):
        return "excluded-private-chat"
    if "年级群课评_20261025" in parts:
        return "excluded-private-chat"
    if "forum" in parts:
        return "treehole"
    if "danke" in parts:
        return "danke"
    if "enrollment_private" in parts:
        return "official-enrollment"
    if "教务大纲" in parts and ("已取大纲" in parts or lower == "official_lesson_index.json"):
        return "official-outlines"
    if "计智学院_20261026" in parts:
        if any(s in parts for s in ("outlines", "outline_errors", "programs", "public")):
            return "official-programs-and-outlines"
        if lower.startswith(("official_index", "caic_offerings", "program_courses", "programs_manifest", "outline_", "scope")):
            return "official-programs-and-outlines"
    if "暑期通识增补_20261026" in parts and (
        "outlines" in parts or lower.startswith(("official_summer", "recognition", "summer_ge_index", "summer_offerings", "summer_scope", "summer_notice", "summer_official_materials"))
    ):
        return "official-summer"
    if "sources" in parts and "成果_扩充版" not in parts:
        return "source-documents"
    if parts[:1] == ("outputs",) and any(s in parts for s in ("directions", "directions_exact", "数院推免_20261022_122112")):
        return "treehole" if lower in {"holes.json", "search.json", "manifest.json"} else None
    if lower.startswith("baseline_"):
        return "excluded-generated-baseline"
    if p.suffix.lower() == ".json" and (
        any(term in lower for term in ("manifest", "ledger", "queries", "tasks", "registry", "aliases", "coverage", "progress", "curated", "records", "unread", "priority", "exclusions", "corrections"))
        or lower.startswith(("batch_", "holes_", "teacher_aliases", "forum_", "danke_"))
    ):
        return "external-web" if any(term in lower for term in ("web", "wechat", "xhs", "zhihu", "blogger", "edge", "public_leads", "public_reading", "public_records")) else "research-ledgers"
    return None


def collect_candidates(workspace: Path):
    roots = [workspace / "课程评价整理_20261023"]
    roots += [workspace / "outputs" / name for name in ("directions", "directions_exact", "数院推免_20261022_122112")]
    # Publication/export trees duplicate data and are not crawler cache roots.
    prune = {".git", "node_modules", "__pycache__", "依赖", "_deps", "成果", "成果_扩充版", "reading_packets", "evidence_packs", "wechat-tools", "FDU-Sharing完整离线", "FDU-Sharing目录", "FDU-Sharing样本"}
    import os
    for root in roots:
        if not root.is_dir():
            continue
        for here, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in prune)
            for name in sorted(files):
                p = Path(here) / name
                category = category_for(p, workspace)
                if category:
                    yield p, category


def build(workspace: Path, out: Path, repo: Path, shard_mib: int):
    if not (workspace / "课程评价整理_20261023").is_dir():
        raise ValueError("Expected course source directory is missing; preserve the existing index")
    if out.is_relative_to(repo) or out.is_relative_to(workspace / "课程评价整理_20261023"):
        raise ValueError("Archive output must stay outside the repository and source cache")
    out.mkdir(parents=True, exist_ok=True)
    repo_index = repo / "research"
    repo_index.mkdir(parents=True, exist_ok=True)
    records = []
    excluded = collections.Counter()
    totals = collections.Counter()
    changes_total = collections.Counter()
    seen = {}
    archives = []
    current = {}
    object_writers = {}
    object_ids = collections.defaultdict(set)
    sizes = collections.Counter()
    sequences = collections.Counter()
    limit = shard_mib * 1048576

    def writer(category: str, length: int):
        if category not in current or sizes[category] + length > limit:
            if category in current:
                current[category].close()
            sequences[category] += 1
            file = f"{category}-{sequences[category]:03d}.zip"
            current[category] = zipfile.ZipFile(out / file, "w", zipfile.ZIP_DEFLATED, compresslevel=9)
            sizes[category] = 0
            archives.append(file)
        sizes[category] += length
        return current[category], f"{category}-{sequences[category]:03d}.zip"

    def reference_objects(value, category):
        # Search snapshots repeat the same floors across many queries. Keep all
        # response shapes/versions, but put each identical post object in one bank.
        if category not in {"treehole", "danke"}:
            return value
        if isinstance(value, dict):
            is_post = ("content" in value or "archive_body_status" in value) and (
                "floor_id" in value or "ranking" in value or "review_id" in value or
                ("id" in value and "time_created" in value and ("title" in value or "rank" in value))
            )
            if is_post:
                data = dumps(value)
                identity = sha(data)
                if identity not in object_ids[category]:
                    if category not in object_writers:
                        object_writers[category] = gzip.open(out / f"{category}-objects.jsonl.gz", "wb", compresslevel=9)
                    object_writers[category].write(dumps({"sha256": identity, "data": value}))
                    object_ids[category].add(identity)
                return {"$raw_object": identity}
            return {k: reference_objects(v, category) for k, v in value.items()}
        if isinstance(value, list):
            return [reference_objects(v, category) for v in value]
        return value

    try:
        for count, (p, category) in enumerate(collect_candidates(workspace), 1):
            relative = p.relative_to(workspace).as_posix()
            if category.startswith("excluded-"):
                excluded[category] += 1
                records.append({"source_path": relative, "status": category, "published": False})
                continue
            raw = p.read_bytes()
            entry = {"source_path": relative, "category": category, "original_sha256": sha(raw), "original_bytes": len(raw), "read_status": "machine_collected_not_equivalent_to_reviewed"}
            changes = collections.Counter()
            try:
                if p.suffix.lower() == ".jsonl":
                    lines, invalid = read_jsonl(raw, changes, category)
                    if invalid:
                        entry["integrity"] = {"status": "partial_jsonl_recovery", "valid_lines": len(lines), "withheld_invalid_lines": invalid}
                    clean = b"".join(dumps(line) for line in lines)
                    stored = b"".join(dumps(reference_objects(line, category)) for line in lines)
                elif p.suffix.lower() == ".json":
                    parsed = json.loads(raw.decode("utf-8-sig"))
                    parsed = sanitize(parsed, changes, category)
                    clean = dumps(parsed)
                    stored = dumps(reference_objects(parsed, category))
                else:
                    value = raw.decode("utf-8-sig")
                    if p.suffix.lower() == ".html":
                        value = re.sub(r"(?is)<(?:script|style)\b[^>]*>.*?</(?:script|style)>", "", value)
                        value = re.sub(r"(?is)<input\b[^>]*>", "", value)
                        changes["html_scripts_forms_removed"] += 1
                    clean = clean_text(value, changes).encode("utf-8")
                    stored = clean
            except (ValueError, UnicodeError) as e:
                entry.update(status="excluded-invalid-source", published=False, error=type(e).__name__)
                records.append(entry)
                excluded[entry["status"]] += 1
                continue
            digest = sha(clean)
            stored_digest = sha(stored)
            key = (category, stored_digest, p.suffix.lower())
            if key not in seen:
                z, archive = writer(category, len(stored))
                member = f"blobs/{stored_digest}{p.suffix.lower()}"
                z.writestr(member, stored)
                seen[key] = {"archive": archive, "member": member}
            entry.update(status="published-redacted-snapshot", published=True, **seen[key], sha256=digest, bytes=len(clean), stored_sha256=stored_digest, encoding="object-refs-v1" if stored != clean else "plain", redactions={k: v for k, v in changes.items() if v})
            records.append(entry)
            totals[category] += 1
            changes_total.update(changes)
            if count % 1000 == 0:
                print("EXPORTED", count, "source files", flush=True)
    finally:
        for z in current.values():
            z.close()
        for f in object_writers.values():
            f.close()
    inv = b"".join(dumps(r) for r in records)
    (out / "source-inventory.jsonl").write_bytes(inv)
    (repo_index / "source-inventory.jsonl").write_bytes(inv)
    assets = []
    object_banks = {k: {"name": f"{k}-objects.jsonl.gz", "objects": len(v)} for k, v in object_ids.items() if v}
    for name in [*archives, *[x["name"] for x in object_banks.values()], "source-inventory.jsonl"]:
        p = out / name
        if p.suffix == ".zip":
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None:
                    raise RuntimeError("Archive CRC failure: " + name)
        assets.append({"name": name, "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())})
    manifest = {
        "schema": SCHEMA, "created_at": datetime.now(timezone.utc).isoformat(),
        "release_tag": "raw-snapshots-20261027", "source_file_count": sum(totals.values()),
        "unique_blob_count": len(seen), "categories": dict(totals), "excluded": dict(excluded),
        "object_banks": object_banks,
        "redactions": {k: v for k, v in changes_total.items() if v}, "assets": assets,
        "license_note": "Third-party source rights remain unchanged. Treehole/DanKe original text follows the community agreement unless the author declares otherwise. Explicitly restricted/deleted bodies are withheld. External copyrighted article full texts and private chats are not republished.",
        "community_agreement": LICENSE_URL,
        "limitations": ["Redacted source snapshots, not byte-identical raw originals.", "Machine-collected hits are not a reading/adoption ledger.", "No original private group chats, account/profile graphs, cookies or login state.", "External article full text and screenshots are excluded; use attributed summaries and canonical links.", "Media URLs do not imply their binaries are available offline.", "Earlier official materials/exam PDFs remain in their existing reference releases; this release avoids duplicate binaries."],
    }
    data = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    (out / "raw-release-manifest.json").write_bytes(data)
    (repo_index / "raw-release-manifest.json").write_bytes(data)
    sums = "\n".join(f"{a['sha256']}  {a['name']}" for a in assets) + "\n"
    (out / "SHA256SUMS").write_text(sums, encoding="utf-8", newline="\n")
    print(json.dumps({"source_files": sum(totals.values()), "blobs": len(seen), "categories": dict(totals), "excluded": dict(excluded), "archive_bytes": sum(a["bytes"] for a in assets if a["name"].endswith((".zip", ".gz")))}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--shard-mib", type=int, default=128)
    args = parser.parse_args()
    if args.shard_mib < 1:
        parser.error("--shard-mib must be positive")
    build(args.workspace.resolve(), args.output.resolve(), args.repo.resolve(), args.shard_mib)


if __name__ == "__main__":
    main()
