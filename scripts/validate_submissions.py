from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_DIR = ROOT / "data" / "submissions"
TEMPLATE_NAME = "template.csv"
FIELDS = [
    "record_id",
    "contributor_id",
    "cohort",
    "program",
    "course_name",
    "teacher",
    "category",
    "academic_year",
    "semester",
    "term_id",
    "credits",
    "final_grade",
    "grade_point",
    "class_rank",
    "class_size",
]
ALLOWED_CATEGORIES = {"公必", "专必", "公选", "专选", "荣誉课程", "其他"}
ALLOWED_ACADEMIC_YEARS = {"大一", "大二", "大三", "大四", "其他"}
ALLOWED_SEMESTERS = {"第一学期", "第二学期", "暑期", "其他"}
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{2,31}$")
TERM_PATTERN = re.compile(r"^20\d{2}-(fall|spring|summer|other)$")
SEMESTER_TERM_SUFFIX = {
    "第一学期": "fall",
    "第二学期": "spring",
    "暑期": "summer",
    "其他": "other",
}


class SubmissionValidationError(Exception):
    pass


def parse_integer(value: str, field: str, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except ValueError as error:
        raise SubmissionValidationError(f"{field} 必须是整数") from error
    if not minimum <= parsed <= maximum:
        raise SubmissionValidationError(f"{field} 必须位于 {minimum}—{maximum}")
    return parsed


def parse_number(value: str, field: str, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except ValueError as error:
        raise SubmissionValidationError(f"{field} 必须是数值") from error
    if not minimum <= parsed <= maximum:
        raise SubmissionValidationError(f"{field} 必须位于 {minimum:g}—{maximum:g}")
    return parsed


def submission_paths(arguments: list[str] | None = None) -> list[Path]:
    if arguments:
        paths = [Path(argument).resolve() for argument in arguments]
    else:
        paths = sorted(path for path in SUBMISSIONS_DIR.glob("*.csv") if path.name != TEMPLATE_NAME)
    if not paths:
        raise SubmissionValidationError("没有找到待校验的 CSV 投稿文件")
    return paths


def normalize_row(raw_row: dict[str, str | None]) -> dict[str, str]:
    return {field: (raw_row.get(field) or "").strip() for field in FIELDS}


def validate_row(row: dict[str, str], path: Path, line_number: int) -> dict[str, object]:
    prefix = f"{path.as_posix()}:{line_number}"
    try:
        contributor_id = row["contributor_id"]
        if not IDENTIFIER_PATTERN.fullmatch(contributor_id):
            raise SubmissionValidationError("contributor_id 只能使用 3—32 位小写字母、数字、连字符或下划线")
        if path.stem != contributor_id:
            raise SubmissionValidationError("文件名必须与 contributor_id 完全一致")

        record_id = row["record_id"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{2,63}", record_id):
            raise SubmissionValidationError("record_id 格式不正确")
        if not record_id.startswith(f"{contributor_id}-"):
            raise SubmissionValidationError("record_id 必须以 contributor_id 和连字符开头")

        cohort = parse_integer(row["cohort"], "cohort", 2000, 2100)
        if not row["program"]:
            raise SubmissionValidationError("program 不能为空")
        if not row["course_name"]:
            raise SubmissionValidationError("course_name 不能为空")
        if row["category"] not in ALLOWED_CATEGORIES:
            raise SubmissionValidationError(f"category 必须是 {sorted(ALLOWED_CATEGORIES)} 之一")
        if row["academic_year"] not in ALLOWED_ACADEMIC_YEARS:
            raise SubmissionValidationError(f"academic_year 必须是 {sorted(ALLOWED_ACADEMIC_YEARS)} 之一")
        if row["semester"] not in ALLOWED_SEMESTERS:
            raise SubmissionValidationError(f"semester 必须是 {sorted(ALLOWED_SEMESTERS)} 之一")
        if not TERM_PATTERN.fullmatch(row["term_id"]):
            raise SubmissionValidationError("term_id 必须使用 YYYY-fall、YYYY-spring、YYYY-summer 或 YYYY-other")
        if not row["term_id"].endswith(f"-{SEMESTER_TERM_SUFFIX[row['semester']]}"):
            raise SubmissionValidationError("term_id 后缀必须与 semester 一致")

        credits = parse_number(row["credits"], "credits", 0.1, 20)
        grade_point = parse_number(row["grade_point"], "grade_point", 0, 5)
        class_rank = parse_integer(row["class_rank"], "class_rank", 1, 10000)
        class_size = parse_integer(row["class_size"], "class_size", 2, 10000)
        if class_rank > class_size:
            raise SubmissionValidationError("class_rank 不能大于 class_size")
    except SubmissionValidationError as error:
        raise SubmissionValidationError(f"{prefix}：{error}") from error

    return {
        "record_id": record_id,
        "contributor_id": contributor_id,
        "cohort": cohort,
        "program": row["program"],
        "course_name": row["course_name"],
        "teacher": row["teacher"],
        "category": row["category"],
        "academic_year": row["academic_year"],
        "semester": row["semester"],
        "term_id": row["term_id"],
        "credits": credits,
        "final_grade": row["final_grade"],
        "grade_point": grade_point,
        "class_rank": class_rank,
        "class_size": class_size,
    }


def load_validated_records(arguments: list[str] | None = None) -> list[dict[str, object]]:
    paths = submission_paths(arguments)
    records: list[dict[str, object]] = []
    seen_record_ids: dict[str, Path] = {}

    for path in paths:
        if not path.is_file():
            raise SubmissionValidationError(f"文件不存在：{path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != FIELDS:
                raise SubmissionValidationError(
                    f"{path.as_posix()}：表头必须与 data/submissions/template.csv 完全一致"
                )
            file_records = []
            for line_number, raw_row in enumerate(reader, start=2):
                if None in raw_row:
                    raise SubmissionValidationError(f"{path.as_posix()}:{line_number}：列数多于表头")
                if not any((value or "").strip() for value in raw_row.values()):
                    continue
                file_records.append(validate_row(normalize_row(raw_row), path, line_number))

        if not file_records:
            raise SubmissionValidationError(f"{path.as_posix()}：投稿文件至少需要一条记录")
        for record in file_records:
            record_id = str(record["record_id"])
            if record_id in seen_record_ids:
                raise SubmissionValidationError(
                    f"重复的 record_id：{record_id}（{seen_record_ids[record_id].as_posix()} 与 {path.as_posix()}）"
                )
            seen_record_ids[record_id] = path
            records.append(record)

    return sorted(records, key=lambda record: str(record["record_id"]))


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 SYSU-Phys-Bench 社区 CSV 投稿")
    parser.add_argument("files", nargs="*", help="可选：只校验指定 CSV 文件")
    arguments = parser.parse_args()
    try:
        records = load_validated_records(arguments.files or None)
    except SubmissionValidationError as error:
        print(f"校验失败：{error}", file=sys.stderr)
        return 1

    contributors = {str(record["contributor_id"]) for record in records}
    courses = {str(record["course_name"]) for record in records}
    print(f"校验通过：{len(records)} 条记录，{len(contributors)} 位贡献者，{len(courses)} 门课程")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
