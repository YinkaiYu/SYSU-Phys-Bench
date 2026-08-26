from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from validate_submissions import SubmissionValidationError, load_validated_records


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "community-data.js"


def render_dataset() -> str:
    records = load_validated_records()
    contributors = sorted({str(record["contributor_id"]) for record in records})
    courses = sorted({str(record["course_name"]) for record in records})
    category_counts = Counter(str(record["category"]) for record in records)
    payload = {
        "schema_version": "1.0",
        "metadata": {
            "contributor_count": len(contributors),
            "record_count": len(records),
            "course_count": len(courses),
            "contributors": contributors,
            "category_counts": dict(sorted(category_counts.items())),
        },
        "records": records,
    }
    return "window.COMMUNITY_GRADE_DATA = " + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + ";\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 SYSU-Phys-Bench 社区网页数据")
    parser.add_argument("--check", action="store_true", help="检查 community-data.js 是否已是最新版本")
    arguments = parser.parse_args()
    try:
        content = render_dataset()
    except SubmissionValidationError as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 1

    if arguments.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            print("community-data.js 不是最新版本；请运行 python scripts/build_dataset.py", file=sys.stderr)
            return 1
        print("community-data.js 已与投稿数据同步")
        return 0

    OUTPUT.write_text(content, encoding="utf-8")
    print(f"已生成 {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
