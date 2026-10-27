"""Publish verified local collaboration archives as one resumable GitHub Release.

Needs repository release-write permission. Uses GITHUB_TOKEN when explicitly set,
otherwise an existing Git credential helper; never saves or prints credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--assets-dir", type=Path, required=True)
    ap.add_argument("--repository", default="pythonbug225/fudan-course-atlas")
    args = ap.parse_args()
    directory = args.assets_dir.resolve()
    manifest = json.loads((directory / "raw-release-manifest.json").read_text(encoding="utf-8"))
    repo = Path(__file__).resolve().parents[2]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
        result = subprocess.run(["git", "credential", "fill"], input="protocol=https\nhost=github.com\n\n", text=True, capture_output=True, env=env, encoding="utf-8")
        credentials = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        token = credentials.pop("password", None)
        credentials.clear()
    if not token:
        raise RuntimeError("No authorized GitHub credential is available")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(url, method="GET", data=None, content_type="application/json", timeout=120):
        if data is not None and not isinstance(data, bytes):
            data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, method=method, data=data, headers={
            "Authorization": "Bearer " + token, "User-Agent": "Fudan-Course-Collaboration-Archive",
            "Accept": "application/vnd.github+json", "Content-Type": content_type,
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with opener.open(req, timeout=timeout) as response:
            return json.load(response)

    names = [a["name"] for a in manifest["assets"]] + ["raw-release-manifest.json", "SHA256SUMS"]
    expected = {a["name"]: a for a in manifest["assets"]}
    for name in names:
        path = (directory / name).resolve()
        if path.parent != directory or not path.is_file():
            raise ValueError("Unexpected or missing upload asset")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if name in expected and (digest != expected[name]["sha256"] or path.stat().st_size != expected[name]["bytes"]):
            raise RuntimeError("Local manifest verification failed: " + name)
    base = "https://api.github.com/repos/" + args.repository
    tag = manifest["release_tag"]
    body = (
        f"全校课评库多人协作的既有原始抓取快照（脱敏版）：{manifest['source_file_count']:,}个源文件，按来源分包，并保留查询参数、分页停止原因、原相对路径、原档与发布版SHA-256。当前课程范围仍为既有整理，不表示全校覆盖完成。\n\n"
        "相同帖子对象共享保存，历史不同版本保留。请用仓库的 `python scripts/research/fetch_raw_archive.py --materialize` 下载、核验并还原路径；无需源站账号。\n\n"
        "包含树洞、蛋壳、官方教学班与人数汇总、大纲、培养方案、暑期课程和查询/阅读台账。作者限制转载或已删除正文不公开；私密群聊、个人身份、账号凭证和未获许可的外部文章全文不在公开数据包中。外部课评保留来源链接、摘要与对应关系。媒体二进制和此前PDF/试卷/手册继续使用已有参考Release，避免重复下载。\n\n"
        "抓取命中不等于阅读或采用；分页触顶、未读队列、归属待确认和损坏源文件的恢复情况均保留。第三方来源沿用原许可，不因仓库公开而统一改为开放许可。完整方法与分工见仓库README和research目录。"
    )
    try:
        release = call(base + "/releases/tags/" + urllib.parse.quote(tag))
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        release = call(base + "/releases", "POST", {"tag_name": tag, "target_commitish": head, "name": "全校课评库协作 · 原始抓取快照 2026-10-27", "body": body, "draft": True, "prerelease": False})
    rid = release["id"]
    assets = {a["name"]: a for a in call(base + f"/releases/{rid}/assets?per_page=100")}
    for name in names:
        path = directory / name
        data = path.read_bytes()
        digest = "sha256:" + hashlib.sha256(data).hexdigest()
        old = assets.get(name)
        if old:
            if old.get("digest") == digest and old["size"] == len(data):
                print("ALREADY_VERIFIED", name, len(data), flush=True)
                continue
            raise RuntimeError("Existing release asset differs; preserve it and select a new release tag")
        mime = "application/zip" if name.endswith(".zip") else "application/gzip" if name.endswith(".gz") else "application/json" if name.endswith(".json") else "text/plain"
        url = f"https://uploads.github.com/repos/{args.repository}/releases/{rid}/assets?name=" + urllib.parse.quote(name)
        item = call(url, "POST", data, mime, timeout=300)
        if item["size"] != len(data) or item.get("digest") != digest:
            raise RuntimeError("Uploaded file failed server digest verification: " + name)
        print("UPLOADED_VERIFIED", name, len(data), flush=True)
    release = call(base + f"/releases/{rid}", "PATCH", {"body": body, "draft": False})
    remote = call(base + f"/releases/{rid}/assets?per_page=100")
    if not set(names).issubset(a["name"] for a in remote):
        raise RuntimeError("Published release is missing assets")
    result = {"url": release["html_url"], "tag": tag, "draft": release["draft"], "target_commit": head,
              "assets": [{k: a.get(k) for k in ("name", "size", "digest", "browser_download_url")} for a in remote]}
    (directory / "publication-receipt.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PUBLISHED", result["url"], "assets", len(remote), flush=True)
    token = None


if __name__ == "__main__":
    main()
