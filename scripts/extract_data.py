from __future__ import annotations

import json
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT.parent
FILES = {
    "overview": SOURCE_ROOT / "余荫铠-成绩总览.xlsx",
    "details": SOURCE_ROOT / "余荫铠-成绩明细.xlsx",
}


def read_rows(path: Path) -> list[list[object]]:
    workbook = load_workbook(path, data_only=True, read_only=True)
    worksheet = workbook.active
    return [
        [cell.value for cell in row]
        for row in worksheet.iter_rows()
        if any(cell.value is not None for cell in row)
    ]


payload = {
    "overview": read_rows(FILES["overview"]),
    "details": read_rows(FILES["details"]),
}

output = "window.GRADE_DATA = " + json.dumps(
    payload,
    ensure_ascii=False,
    separators=(",", ":"),
) + ";\n"
(ROOT / "data.js").write_text(output, encoding="utf-8")

