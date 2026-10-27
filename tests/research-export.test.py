"""Checks for data actually withheld or transformed by the public-source export."""
import collections
import importlib.util
import pathlib
import tempfile
import json
import gzip
import zipfile
import hashlib
import unittest

p = pathlib.Path(__file__).resolve().parents[1] / "scripts/research/build_raw_archive.py"
spec = importlib.util.spec_from_file_location("archive", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ExportTests(unittest.TestCase):
    def clean(self, obj, category="treehole"):
        return m.sanitize(obj, collections.Counter(), category)

    def test_credentials_and_profile_removed_but_source_ids_remain(self):
        out = self.clean({"floor_id": 42, "hole_id": 7, "ranking": 3, "user_id": 99,
                          "Cookie": "session=sensitive", "xsec_token": "sensitive",
                          "content": "这门课程每周两次作业。", "user": {"name": "公开笔名", "email": "private@example.invalid"}})
        self.assertEqual(out["floor_id"], 42)
        self.assertEqual(out["content"], "这门课程每周两次作业。")
        self.assertNotIn("user_id", out)
        self.assertNotIn("Cookie", out)
        self.assertNotIn("xsec_token", out)
        self.assertEqual(out["user"], {"public_label": "公开笔名"})

    def test_restricted_or_deleted_body_not_republished(self):
        for obj in [{"floor_id": 1, "content": "请勿转载。正文。"}, {"floor_id": 2, "content": "正文。", "deleted": True}]:
            out = self.clean(obj)
            self.assertIn("archive_body_status", out)
            self.assertNotIn("正文。", out["content"])

    def test_nested_external_body_removed_but_summary_and_title_remain(self):
        out = self.clean({"records": [{"title": "课程笔记", "content": "未获转载许可的原文", "summary": "作者讨论了作业量。", "url": "https://example.com/note?xsec_token=secret&note=123"}]}, "external-web")
        r = out["records"][0]
        self.assertEqual(r["title"], "课程笔记")
        self.assertNotIn("content", r)
        self.assertNotIn("secret", r["url"])
        self.assertEqual(r["summary"], "作者讨论了作业量。")

    def test_course_codes_unaffected_contact_details_removed(self):
        out = self.clean({"content": "MATH30011，联系 wxid_synthetic_example，邮箱 fake@example.invalid，提取码：abcd"})
        self.assertIn("MATH30011", out["content"])
        self.assertNotIn("wxid_synthetic", out["content"])
        self.assertNotIn("example.invalid", out["content"])
        self.assertNotIn("abcd", out["content"])

    def test_partial_jsonl_preserves_valid_records_and_records_damaged_lines(self):
        rows, invalid = m.read_jsonl(b'{"floor_id":1,"content":"ok"}\ninvalid\n{"floor_id":2,"content":"ok"}\n', collections.Counter(), "treehole")
        self.assertEqual(len(rows), 2)
        self.assertEqual(invalid[0]["line"], 2)
        self.assertEqual(len(invalid[0]["sha256"]), 64)

    def test_shared_post_can_be_reconstructed_and_hash_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            base = pathlib.Path(directory)
            source = base / "workspace/课程评价整理_20261023/forum/search"
            source.mkdir(parents=True)
            floor = {"floor_id": 42, "hole_id": 7, "ranking": 3, "content": "A course has two assignments.", "user_id": 99}
            for i, word in enumerate(("course", "teacher")):
                (source / f"{i}.json").write_text(json.dumps({"query": word, "items": [floor]}), encoding="utf-8")
            out, repo = base / "export", base / "repo"
            m.build(base / "workspace", out, repo, 1)
            manifest = json.loads((out / "raw-release-manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_file_count"], 2)
            self.assertEqual(manifest["object_banks"]["treehole"]["objects"], 1)
            objects = {}
            with gzip.open(out / "treehole-objects.jsonl.gz", "rt", encoding="utf-8") as f:
                for line in f:
                    item = json.loads(line)
                    objects[item["sha256"]] = item["data"]
            for line in (out / "source-inventory.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                with zipfile.ZipFile(out / row["archive"]) as z:
                    value = json.loads(z.read(row["member"]))
                value["items"][0] = objects[value["items"][0]["$raw_object"]]
                self.assertNotIn("user_id", value["items"][0])
                raw = (json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["sha256"])


if __name__ == "__main__":
    unittest.main()
