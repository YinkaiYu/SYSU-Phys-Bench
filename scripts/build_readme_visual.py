from __future__ import annotations

import argparse
import html
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

from validate_submissions import SubmissionValidationError, load_validated_records


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "readme" / "hero.svg"
CATEGORY_COLORS = {
    "公必": "#67a9c5",
    "专必": "#ed8257",
    "公选": "#d58ba4",
    "专选": "#a4b879",
    "荣誉课程": "#c6a15b",
    "其他": "#aab5bb",
}


def yu_index(gpa: float, rank: int, size: int) -> float:
    probability = (size - rank + 5 / 8) / (size + 1 / 4)
    return gpa - statistics.NormalDist().inv_cdf(probability) / 3


def aggregate_courses(records: list[dict[str, object]]) -> list[dict[str, object]]:
    groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        groups[(str(record["category"]), str(record["course_name"]))].append(record)

    courses = []
    for (category, name), items in groups.items():
        percentiles = [100 * int(item["class_rank"]) / int(item["class_size"]) for item in items]
        courses.append(
            {
                "category": category,
                "name": name,
                "gpa": statistics.fmean(float(item["grade_point"]) for item in items),
                "yu": statistics.fmean(
                    yu_index(float(item["grade_point"]), int(item["class_rank"]), int(item["class_size"]))
                    for item in items
                ),
                "percentile": math.exp(statistics.fmean(math.log(value) for value in percentiles)),
                "credits": statistics.fmean(float(item["credits"]) for item in items),
            }
        )
    return courses


def half_step_domain(values: list[float], *, floor: float | None = None, ceiling: float | None = None) -> tuple[float, float]:
    minimum = math.floor((min(values) - 0.2) * 2) / 2
    maximum = math.ceil((max(values) + 0.2) * 2) / 2
    if maximum - minimum < 1.5:
        center = statistics.fmean((minimum, maximum))
        minimum = math.floor((center - 0.75) * 2) / 2
        maximum = math.ceil((center + 0.75) * 2) / 2
    if floor is not None:
        minimum = max(floor, minimum)
    if ceiling is not None:
        maximum = min(ceiling, maximum)
    return minimum, maximum


def scale_x(percentile: float, left: float, width: float) -> float:
    minimum, maximum = math.log10(0.5), math.log10(100)
    return left + (maximum - math.log10(max(percentile, 0.5))) / (maximum - minimum) * width


def scale_y(value: float, top: float, height: float, minimum: float, maximum: float) -> float:
    return top + (maximum - value) / (maximum - minimum) * height


def render_panel(
    courses: list[dict[str, object]],
    *,
    x_origin: int,
    title: str,
    value_key: str,
    y_min: float,
    y_max: float,
    benchmark: float | None = None,
) -> str:
    panel_x, panel_y, panel_width, panel_height = x_origin, 42, 535, 362
    plot_left, plot_top = panel_x + 68, panel_y + 64
    plot_width, plot_height = 425, 238
    parts = [
        f'<rect x="{panel_x}" y="{panel_y}" width="{panel_width}" height="{panel_height}" rx="20" fill="#ffffff" fill-opacity=".075" stroke="#d9edf5" stroke-opacity=".18"/>',
        f'<text x="{panel_x + 28}" y="{panel_y + 38}" class="panel-title">{html.escape(title)}</text>',
    ]

    for rank in (1, 10, 100):
        x = scale_x(rank, plot_left, plot_width)
        parts.append(f'<line x1="{x:.2f}" x2="{x:.2f}" y1="{plot_top}" y2="{plot_top + plot_height}" class="grid"/>')
        parts.append(f'<text x="{x:.2f}" y="{plot_top + plot_height + 24}" text-anchor="middle" class="tick">{rank}%</text>')

    tick_count = round((y_max - y_min) / 0.5)
    for index in range(tick_count + 1):
        value = y_min + index * 0.5
        y = scale_y(value, plot_top, plot_height, y_min, y_max)
        parts.append(f'<line x1="{plot_left}" x2="{plot_left + plot_width}" y1="{y:.2f}" y2="{y:.2f}" class="grid"/>')
        parts.append(f'<text x="{plot_left - 13}" y="{y + 5:.2f}" text-anchor="end" class="tick">{value:g}</text>')

    if benchmark is not None:
        y = scale_y(benchmark, plot_top, plot_height, y_min, y_max)
        parts.append(f'<line x1="{plot_left}" x2="{plot_left + plot_width}" y1="{y:.2f}" y2="{y:.2f}" class="benchmark"/>')

    for course in courses:
        x = scale_x(float(course["percentile"]), plot_left, plot_width)
        y = scale_y(float(course[value_key]), plot_top, plot_height, y_min, y_max)
        radius = 3.4 + math.sqrt(float(course["credits"])) * 1.45
        color = CATEGORY_COLORS.get(str(course["category"]), CATEGORY_COLORS["其他"])
        label = html.escape(f'{course["name"]} · {float(course[value_key]):.2f}')
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{color}" fill-opacity=".88" '
            f'stroke="#ffffff" stroke-width="1.15"><title>{label}</title></circle>'
        )

    parts.append(
        f'<text x="{plot_left + plot_width / 2}" y="{panel_y + panel_height - 15}" '
        f'text-anchor="middle" class="axis">教学班排名百分位（对数刻度）</text>'
    )
    return "".join(parts)


def render_visual() -> str:
    records = load_validated_records()
    courses = aggregate_courses(records)
    contributors = {str(record["contributor_id"]) for record in records}
    gpa_min, gpa_max = half_step_domain([float(course["gpa"]) for course in courses], floor=0, ceiling=5)
    yu_values = [float(course["yu"]) for course in courses]
    yu_min, yu_max = half_step_domain(yu_values)
    benchmark = statistics.median(yu_values)
    categories = [category for category in CATEGORY_COLORS if any(course["category"] == category for course in courses)]

    left_panel = render_panel(
        courses,
        x_origin=45,
        title="课程绩点 × 排名",
        value_key="gpa",
        y_min=gpa_min,
        y_max=gpa_max,
    )
    right_panel = render_panel(
        courses,
        x_origin=620,
        title="Yu Index × 排名",
        value_key="yu",
        y_min=yu_min,
        y_max=yu_max,
        benchmark=benchmark,
    )

    legend_parts = []
    legend_start = 600 - (len(categories) * 82) / 2
    for index, category in enumerate(categories):
        x = legend_start + index * 82
        legend_parts.append(f'<circle cx="{x:.1f}" cy="435" r="5" fill="{CATEGORY_COLORS[category]}"/>')
        legend_parts.append(f'<text x="{x + 11:.1f}" y="440" class="legend">{category}</text>')

    stats = [(len(records), "课程记录"), (len(courses), "覆盖课程"), (len(contributors), "贡献者")]
    stat_parts = []
    for index, (value, label) in enumerate(stats):
        x = 360 + index * 240
        stat_parts.append(f'<text x="{x}" y="486" text-anchor="middle" class="stat-value">{value}</text>')
        stat_parts.append(f'<text x="{x}" y="512" text-anchor="middle" class="stat-label">{label}</text>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="540" viewBox="0 0 1200 540" role="img" aria-labelledby="title description">
  <title id="title">SYSU-Phys-Bench 数据快照</title>
  <desc id="description">当前课程绩点与 Yu Index 相对教学班排名百分位的真实数据分布</desc>
  <defs>
    <linearGradient id="background" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#14252d"/>
      <stop offset=".58" stop-color="#244e61"/>
      <stop offset="1" stop-color="#386b81"/>
    </linearGradient>
    <style>
      text {{ font-family: Inter, "Microsoft YaHei", "Noto Sans CJK SC", sans-serif; }}
      .panel-title {{ fill: #f4fafc; font-size: 22px; font-weight: 700; }}
      .tick {{ fill: #b9cdd5; font-size: 12px; }}
      .axis {{ fill: #d6e5eb; font-size: 13px; }}
      .grid {{ stroke: #d7eef6; stroke-opacity: .14; }}
      .benchmark {{ stroke: #f2c77f; stroke-width: 1.5; stroke-dasharray: 6 5; stroke-opacity: .8; }}
      .legend {{ fill: #dce9ee; font-size: 13px; }}
      .stat-value {{ fill: #ffffff; font-size: 26px; font-weight: 760; }}
      .stat-label {{ fill: #a9c2cc; font-size: 12px; }}
    </style>
  </defs>
  <rect width="1200" height="540" rx="28" fill="url(#background)"/>
  {left_panel}
  {right_panel}
  {''.join(legend_parts)}
  {''.join(stat_parts)}
</svg>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 README 的 SYSU-Phys-Bench 数据主视觉")
    parser.add_argument("--check", action="store_true", help="检查主视觉是否与公开数据同步")
    arguments = parser.parse_args()
    try:
        content = render_visual()
    except SubmissionValidationError as error:
        print(f"生成失败：{error}", file=sys.stderr)
        return 1

    if arguments.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != content:
            print("README 数据主视觉不是最新版本；请运行 python scripts/build_readme_visual.py", file=sys.stderr)
            return 1
        print("README 数据主视觉已与投稿数据同步")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"已生成 {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
