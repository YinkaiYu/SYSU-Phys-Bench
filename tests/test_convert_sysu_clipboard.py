from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from convert_sysu_clipboard import merge_records, parse_text  # noqa: E402


COPIED_TABLE = """序号\t类别\t课程\t教师\t学年\t学期\t学分\t原始成绩\t最终成绩\t特殊原因\t绩点\t考试性质\t是否通过\t教学班排名
1\t公必\t
大学英语III
杨晓红\t2020-2021\t第一学期\t2\t76\t76\t\t2.6\t期末成绩\t是\t22/35
2\t公必\t
思想道德修养与法律基础
王仕民\t2020-2021\t第一学期\t3\t86\t86\t\t3.6\t期末成绩\t是\t14/87
3\t公必\t
军事课
2020-2021\t第一学期\t4\t86\t86\t\t3.6\t期末成绩\t是\t65/349
"""


class ConvertSysuClipboardTests(unittest.TestCase):
    def test_parses_copied_table_and_missing_teacher(self) -> None:
        records = parse_text(COPIED_TABLE, "phys-2020-a7", 2020, "物理学")

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["course_name"], "大学英语III")
        self.assertEqual(records[0]["teacher"], "杨晓红")
        self.assertEqual(records[0]["term_id"], "2020-fall")
        self.assertEqual(records[0]["academic_year"], "大一")
        self.assertEqual(records[0]["class_rank"], "22")
        self.assertEqual(records[0]["class_size"], "35")
        self.assertEqual(records[2]["course_name"], "军事课")
        self.assertEqual(records[2]["teacher"], "")

    def test_repeated_import_is_idempotent(self) -> None:
        records = parse_text(COPIED_TABLE, "phys-2020-a7", 2020, "物理学")
        merged, added, updated, unchanged = merge_records(records, records)

        self.assertEqual(len(merged), 3)
        self.assertEqual((added, updated, unchanged), (0, 0, 3))

    def test_cli_writes_and_merges_submission_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "2020-fall.txt"
            output = temporary / "phys-2020-a7.csv"
            source.write_text(COPIED_TABLE, encoding="utf-8")
            command = [
                sys.executable,
                str(ROOT / "scripts" / "convert_sysu_clipboard.py"),
                str(source),
                "--contributor-id",
                "phys-2020-a7",
                "--cohort",
                "2020",
                "--program",
                "物理学",
                "--output",
                str(output),
            ]

            environment = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=environment)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=environment)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("本次新增 3 条", first.stdout)
            self.assertIn("跳过重复 3 条", second.stdout)
            with output.open("r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            military = next(row for row in rows if row["course_name"] == "军事课")
            self.assertEqual(military["teacher"], "")


if __name__ == "__main__":
    unittest.main()
