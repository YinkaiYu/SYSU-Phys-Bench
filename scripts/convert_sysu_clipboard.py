from __future__ import annotations

import argparse
import csv
import hashlib
import re
import subprocess
import sys
from pathlib import Path

from validate_submissions import (
    FIELDS,
    SUBMISSIONS_DIR,
    SubmissionValidationError,
    load_validated_records,
    validate_row,
)


CATEGORY_ALIASES = {
    "公必": "公必",
    "公共必修": "公必",
    "专必": "专必",
    "专业必修": "专必",
    "公选": "公选",
    "公共选修": "公选",
    "专选": "专选",
    "专业选修": "专选",
    "荣誉": "荣誉课程",
    "荣誉课程": "荣誉课程",
    "其他": "其他",
}
SEMESTER_ALIASES = {
    "第一学期": "第一学期",
    "第1学期": "第一学期",
    "1": "第一学期",
    "第二学期": "第二学期",
    "第2学期": "第二学期",
    "2": "第二学期",
    "暑期": "暑期",
    "其他": "其他",
}
ACADEMIC_YEAR_NAMES = ["大一", "大二", "大三", "大四"]
YEAR_PATTERN = re.compile(r"^(20\d{2})-(20\d{2})$")
RANK_PATTERN = re.compile(r"^(\d+)\s*/\s*(\d+)$")


class ConversionError(Exception):
    pass


def normalize_token(value: str) -> str:
    return (
        value.replace("\u00a0", " ")
        .replace("\u200b", "")
        .replace("—", "-")
        .replace("–", "-")
        .strip()
    )


def tokenize(text: str) -> list[str]:
    return [token for part in re.split(r"[\t\r\n]+", text) if (token := normalize_token(part))]


def row_starts(tokens: list[str]) -> list[int]:
    return [
        index
        for index in range(len(tokens) - 1)
        if tokens[index].isdigit() and tokens[index + 1] in CATEGORY_ALIASES
    ]


def term_fields(year_range: str, semester: str, cohort: int) -> tuple[str, str]:
    match = YEAR_PATTERN.fullmatch(year_range)
    if not match:
        raise ConversionError(f"无法识别学年：{year_range}")
    start_year, end_year = (int(value) for value in match.groups())
    if end_year != start_year + 1:
        raise ConversionError(f"学年范围不连续：{year_range}")

    semester = SEMESTER_ALIASES.get(semester, semester)
    suffix_and_year = {
        "第一学期": ("fall", start_year),
        "第二学期": ("spring", end_year),
        "暑期": ("summer", end_year),
        "其他": ("other", start_year),
    }
    if semester not in suffix_and_year:
        raise ConversionError(f"无法识别学期：{semester}")
    suffix, calendar_year = suffix_and_year[semester]
    offset = start_year - cohort
    academic_year = ACADEMIC_YEAR_NAMES[offset] if 0 <= offset < len(ACADEMIC_YEAR_NAMES) else "其他"
    return academic_year, f"{calendar_year}-{suffix}"


def stable_record_id(
    contributor_id: str,
    term_id: str,
    source_index: str,
    category: str,
    course_name: str,
    teacher: str,
) -> str:
    identity = "\0".join((term_id, source_index, category, course_name, teacher))
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:8]
    return f"{contributor_id}-{term_id}-{digest}"


def parse_row(segment: list[str], contributor_id: str, cohort: int, program: str) -> dict[str, str]:
    source_index = segment[0]
    category = CATEGORY_ALIASES.get(segment[1])
    if category is None:
        raise ConversionError(f"第 {source_index} 行类别无法识别：{segment[1]}")
    if len(segment) < 11:
        raise ConversionError(f"第 {source_index} 行字段过少，请确认复制了完整表格行")
    course_name = segment[2]

    year_index = next((index for index in range(3, len(segment)) if YEAR_PATTERN.fullmatch(segment[index])), None)
    if year_index is None:
        raise ConversionError(f"第 {source_index} 行未找到学年")
    teacher = ",".join(segment[3:year_index])

    rank_index = next((index for index in range(len(segment) - 1, year_index, -1) if RANK_PATTERN.fullmatch(segment[index])), None)
    if rank_index is None:
        raise ConversionError(f"第 {source_index} 行未找到教学班排名")
    if rank_index - year_index < 8:
        raise ConversionError(f"第 {source_index} 行成绩字段不完整")

    semester = SEMESTER_ALIASES.get(segment[year_index + 1], segment[year_index + 1])
    academic_year, term_id = term_fields(segment[year_index], semester, cohort)
    credits = segment[year_index + 2]
    final_grade = segment[year_index + 4]
    grade_point = segment[rank_index - 3]
    rank_match = RANK_PATTERN.fullmatch(segment[rank_index])
    assert rank_match is not None
    class_rank, class_size = rank_match.groups()

    record_id = stable_record_id(contributor_id, term_id, source_index, category, course_name, teacher)
    return {
        "record_id": record_id,
        "contributor_id": contributor_id,
        "cohort": str(cohort),
        "program": program,
        "course_name": course_name,
        "teacher": teacher,
        "category": category,
        "academic_year": academic_year,
        "semester": semester,
        "term_id": term_id,
        "credits": credits,
        "final_grade": final_grade,
        "grade_point": grade_point,
        "class_rank": class_rank,
        "class_size": class_size,
    }


def parse_text(text: str, contributor_id: str, cohort: int, program: str) -> list[dict[str, str]]:
    tokens = tokenize(text)
    starts = row_starts(tokens)
    if not starts:
        raise ConversionError("没有识别到成绩行；请从成绩查询表格中复制完整课程记录")

    records = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(tokens)
        records.append(parse_row(tokens[start:end], contributor_id, cohort, program))
    return records


def read_clipboard() -> str:
    try:
        import tkinter

        root = tkinter.Tk()
        root.withdraw()
        try:
            return str(root.clipboard_get())
        finally:
            root.destroy()
    except Exception as tkinter_error:
        if sys.platform == "win32":
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); Get-Clipboard -Raw",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                return completed.stdout
        raise ConversionError("无法读取剪贴板；请将复制内容保存为 UTF-8 文本文件后重试") from tkinter_error


def read_source(path: Path) -> str:
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ConversionError(f"无法读取文本文件编码：{path}")


def stringify_record(record: dict[str, object]) -> dict[str, str]:
    values = {field: str(record.get(field, "")) for field in FIELDS}
    for field in ("credits", "grade_point"):
        number = float(values[field])
        values[field] = f"{number:g}"
    return values


def load_existing(output: Path) -> list[dict[str, str]]:
    if not output.exists():
        return []
    return [stringify_record(record) for record in load_validated_records([str(output)])]


def merge_records(existing: list[dict[str, str]], incoming: list[dict[str, str]]) -> tuple[list[dict[str, str]], int, int, int]:
    merged = {record["record_id"]: record for record in existing}
    added = updated = unchanged = 0
    for record in incoming:
        previous = merged.get(record["record_id"])
        if previous is None:
            added += 1
        elif previous == record:
            unchanged += 1
        else:
            updated += 1
        merged[record["record_id"]] = record
    ordered = sorted(merged.values(), key=lambda record: (record["term_id"], record["course_name"], record["record_id"]))
    return ordered, added, updated, unchanged


def write_csv(output: Path, records: list[dict[str, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser(description="将中山大学教务系统复制的成绩表转换为 SYSU-Phys-Bench CSV")
    parser.add_argument("files", nargs="*", type=Path, help="从教务系统复制后保存的 UTF-8 文本文件，可一次提供多个学期")
    parser.add_argument("--clipboard", action="store_true", help="直接读取当前剪贴板中的一个学期成绩")
    parser.add_argument("--contributor-id", required=True, help="匿名贡献者 ID，例如 phys-2023-a7")
    parser.add_argument("--cohort", required=True, type=int, help="入学年份，例如 2023")
    parser.add_argument("--program", required=True, help="专业或培养方向，例如 物理学")
    parser.add_argument("--output", type=Path, help="输出 CSV；默认写入 data/submissions/<contributor_id>.csv")
    parser.add_argument("--dry-run", action="store_true", help="只解析和校验，不写入文件")
    arguments = parser.parse_args()

    if not arguments.clipboard and not arguments.files:
        parser.error("请使用 --clipboard，或提供至少一个文本文件")

    output = (arguments.output or SUBMISSIONS_DIR / f"{arguments.contributor_id}.csv").resolve()
    if output.stem != arguments.contributor_id:
        parser.error("输出文件名必须与 contributor_id 完全一致")

    try:
        source_texts = []
        if arguments.clipboard:
            source_texts.append(read_clipboard())
        source_texts.extend(read_source(path.resolve()) for path in arguments.files)
        incoming = [
            record
            for text in source_texts
            for record in parse_text(text, arguments.contributor_id, arguments.cohort, arguments.program)
        ]
        validated = [
            stringify_record(validate_row(record, output, index))
            for index, record in enumerate(incoming, start=2)
        ]
        merged, added, updated, unchanged = merge_records(load_existing(output), validated)
    except (ConversionError, SubmissionValidationError) as error:
        print(f"转换失败：{error}", file=sys.stderr)
        return 1

    if not arguments.dry_run:
        write_csv(output, merged)
    action = "预览" if arguments.dry_run else f"已写入 {output.relative_to(Path.cwd()) if output.is_relative_to(Path.cwd()) else output}"
    print(f"{action}：识别 {len(validated)} 条，本次新增 {added} 条、更新 {updated} 条、跳过重复 {unchanged} 条；文件共 {len(merged)} 条")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
