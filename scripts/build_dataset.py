from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from validate_submissions import SubmissionValidationError, load_validated_records


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "community-data.js"
STATS_OUTPUT = ROOT / "assets" / "readme" / "dataset-stats.json"


def build_payload() -> dict[str, object]:
    records = load_validated_records()
    contributors = sorted({str(record["contributor_id"]) for record in records})
    courses = sorted({str(record["course_name"]) for record in records})
    category_counts = Counter(str(record["category"]) for record in records)
    return {
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


def render_dataset(payload: dict[str, object]) -> str:
    return "window.COMMUNITY_GRADE_DATA = " + json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
    ) + ";\n"


def render_stats(payload: dict[str, object]) -> str:
    metadata = payload["metadata"]
    return json.dumps(
        {
            "record_count": metadata["record_count"],
            "course_count": metadata["course_count"],
            "contributor_count": metadata["contributor_count"],
        },
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 SYSU-Phys-Bench 社区网页数据")
    parser.add_argument("--check", action="store_true", help="检查 community-data.js 是否已是最新版本")
    arguments = parser.parse_args()
    try:
        payload = build_payload()
        content = render_dataset(payload)
        stats_content = render_stats(payload)
    except SubmissionValidationError as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 1

    if arguments.check:
        files_are_current = (
            OUTPUT.exists()
            and OUTPUT.read_text(encoding="utf-8") == content
            and STATS_OUTPUT.exists()
            and STATS_OUTPUT.read_text(encoding="utf-8") == stats_content
        )
        if not files_are_current:
            print("生成文件不是最新版本；请运行 python scripts/build_dataset.py", file=sys.stderr)
            return 1
        print("community-data.js 与数据集徽章统计已同步")
        return 0

    OUTPUT.write_text(content, encoding="utf-8")
    STATS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    STATS_OUTPUT.write_text(stats_content, encoding="utf-8")
    print(f"已生成 {OUTPUT.relative_to(ROOT)} 与 {STATS_OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
