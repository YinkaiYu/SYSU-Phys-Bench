(() => {
  "use strict";

  const overviewRows = window.GRADE_DATA.overview;
  const detailRows = window.GRADE_DATA.details;
  const overviewHeaders = overviewRows[0];
  const detailHeaders = detailRows[0];
  const rows = detailRows.slice(1).map((row, index) => ({
    index,
    类别: row[0],
    课程: row[1],
    教师: row[2] ?? "",
    学年: row[3],
    学期: row[4],
    学分: Number(row[5]),
    最终成绩: row[6],
    绩点: Number(row[7]),
    教学班排名: row[8],
  }));

  const palette = ["#386b81", "#b48a3a", "#c87542", "#748061", "#a96e78"];
  const categoryColors = {
    公必: "#386b81",
    专必: "#244e61",
    公选: "#b48a3a",
    专选: "#748061",
  };
  const yearOrder = ["大一", "大二", "大三", "大四"];
  const termOrder = ["第一学期", "第二学期"];
  const semesterOrder = yearOrder.flatMap((year) => termOrder.map((term) => `${year}${term}`));
  const numberFormatter = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 4 });

  let sortState = { key: "index", direction: "asc" };

  const $ = (selector) => document.querySelector(selector);
  const svgNS = "http://www.w3.org/2000/svg";

  function svgElement(name, attributes = {}, text = "") {
    const node = document.createElementNS(svgNS, name);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, value));
    if (text !== "") node.textContent = text;
    return node;
  }

  function formatValue(value, digits = 2) {
    return Number(value).toLocaleString("zh-CN", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    });
  }

  function parseRank(value) {
    const match = String(value).match(/^(\d+)\/(\d+)$/);
    if (!match) return { rank: NaN, total: NaN, percentile: NaN };
    const rank = Number(match[1]);
    const total = Number(match[2]);
    return { rank, total, percentile: (rank / total) * 100 };
  }

  function weightedAverage(items, valueAccessor, weightAccessor = (item) => item.学分) {
    const valid = items.filter((item) => Number.isFinite(valueAccessor(item)) && weightAccessor(item) > 0);
    const weight = valid.reduce((sum, item) => sum + weightAccessor(item), 0);
    return weight ? valid.reduce((sum, item) => sum + valueAccessor(item) * weightAccessor(item), 0) / weight : 0;
  }

  function renderMetrics() {
    const overviewTotal = overviewRows.find((row) => row[0] === "合计");
    const rankRow = overviewRows.at(-1);
    const metrics = [
      ["课程数", rows.length],
      ["已获学分", overviewTotal[2]],
      ["平均学分绩点", overviewTotal[3]],
      ["必修、专选平均绩点", rankRow[1]],
      ["排名 / 总人数", rankRow[3]],
    ];

    const strip = $("#metric-strip");
    metrics.forEach(([label, value]) => {
      const card = document.createElement("div");
      card.className = "metric-card";
      const labelElement = document.createElement("span");
      labelElement.className = "metric-label";
      labelElement.textContent = label;
      const valueElement = document.createElement("strong");
      valueElement.className = "metric-value";
      valueElement.textContent = typeof value === "number" ? numberFormatter.format(value) : value;
      card.append(labelElement, valueElement);
      strip.append(card);
    });
  }

  function renderOverviewTable() {
    const table = $("#overview-table");
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    overviewHeaders.forEach((header) => {
      const th = document.createElement("th");
      th.scope = "col";
      th.textContent = header;
      headRow.append(th);
    });
    thead.append(headRow);

    const tbody = document.createElement("tbody");
    overviewRows.slice(1).forEach((row) => {
      const tr = document.createElement("tr");
      row.forEach((value, index) => {
        const td = document.createElement("td");
        if (typeof value === "number") td.className = "numeric";
        td.textContent = value ?? "";
        if (index > 0) td.dataset.label = overviewHeaders[index];
        tr.append(td);
      });
      tbody.append(tr);
    });
    table.append(thead, tbody);
  }

  function addOptions(select, values) {
    values.forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.append(option);
    });
  }

  function setupFilters() {
    addOptions($("#category-filter"), [...new Set(rows.map((row) => row.类别))]);
    addOptions($("#year-filter"), yearOrder.filter((value) => rows.some((row) => row.学年 === value)));
    addOptions($("#term-filter"), termOrder.filter((value) => rows.some((row) => row.学期 === value)));

    ["#search", "#category-filter", "#year-filter", "#term-filter", "#credit-filter"].forEach((selector) => {
      $(selector).addEventListener(selector === "#search" ? "input" : "change", renderDetailsBody);
    });

    $("#reset-filters").addEventListener("click", () => {
      $("#search").value = "";
      $("#category-filter").value = "";
      $("#year-filter").value = "";
      $("#term-filter").value = "";
      $("#credit-filter").value = "";
      sortState = { key: "index", direction: "asc" };
      updateSortIndicators();
      renderDetailsBody();
    });
  }

  function creditMatches(credit, filter) {
    if (!filter) return true;
    if (filter === "0-1") return credit <= 1;
    if (filter === "1.5-2") return credit >= 1.5 && credit <= 2;
    if (filter === "3") return credit === 3;
    if (filter === "4") return credit === 4;
    if (filter === "5-6") return credit >= 5 && credit <= 6;
    return true;
  }

  function filteredRows() {
    const query = $("#search").value.trim().toLocaleLowerCase("zh-CN");
    const category = $("#category-filter").value;
    const year = $("#year-filter").value;
    const term = $("#term-filter").value;
    const credit = $("#credit-filter").value;

    const filtered = rows.filter((row) => {
      const searchable = `${row.课程} ${row.教师}`.toLocaleLowerCase("zh-CN");
      return (
        (!query || searchable.includes(query)) &&
        (!category || row.类别 === category) &&
        (!year || row.学年 === year) &&
        (!term || row.学期 === term) &&
        creditMatches(row.学分, credit)
      );
    });

    return filtered.sort((a, b) => {
      const aValue = a[sortState.key];
      const bValue = b[sortState.key];
      let result;
      if (sortState.key === "教学班排名") {
        result = parseRank(aValue).percentile - parseRank(bValue).percentile;
      } else if (typeof aValue === "number" && typeof bValue === "number") {
        result = aValue - bValue;
      } else if (typeof aValue === "number") {
        result = -1;
      } else if (typeof bValue === "number") {
        result = 1;
      } else {
        result = String(aValue).localeCompare(String(bValue), "zh-CN");
      }
      if (result === 0) result = a.index - b.index;
      return sortState.direction === "asc" ? result : -result;
    });
  }

  function creditLevel(credit) {
    if (credit >= 5) return 5;
    if (credit >= 4) return 4;
    if (credit >= 3) return 3;
    if (credit >= 1.5) return 2;
    return 1;
  }

  function renderDetailsHead() {
    const tr = document.createElement("tr");
    detailHeaders.forEach((header) => {
      const th = document.createElement("th");
      th.scope = "col";
      const button = document.createElement("button");
      button.className = "sort-button";
      button.type = "button";
      button.dataset.key = header;
      button.innerHTML = `<span>${header}</span><span class="sort-indicator" aria-hidden="true">↕</span>`;
      button.addEventListener("click", () => {
        if (sortState.key === header) {
          sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
        } else {
          sortState = { key: header, direction: "asc" };
        }
        updateSortIndicators();
        renderDetailsBody();
      });
      th.append(button);
      tr.append(th);
    });
    $("#details-table thead").append(tr);
  }

  function updateSortIndicators() {
    document.querySelectorAll(".sort-button").forEach((button) => {
      const active = button.dataset.key === sortState.key;
      const indicator = button.querySelector(".sort-indicator");
      indicator.textContent = active ? (sortState.direction === "asc" ? "↑" : "↓") : "↕";
      button.setAttribute("aria-sort", active ? (sortState.direction === "asc" ? "ascending" : "descending") : "none");
    });
  }

  function renderDetailsBody() {
    const data = filteredRows();
    const tbody = $("#details-table tbody");
    tbody.replaceChildren();
    $("#result-count").textContent = `${data.length} / ${rows.length} 门课程`;

    if (!data.length) {
      const tr = document.createElement("tr");
      tr.className = "empty-row";
      const td = document.createElement("td");
      td.colSpan = detailHeaders.length;
      td.textContent = "无匹配课程";
      tr.append(td);
      tbody.append(tr);
      return;
    }

    data.forEach((row) => {
      const tr = document.createElement("tr");
      tr.dataset.creditLevel = creditLevel(row.学分);
      detailHeaders.forEach((header) => {
        const td = document.createElement("td");
        const value = row[header];
        td.textContent = value ?? "";
        if (["学分", "绩点"].includes(header) || typeof value === "number") td.classList.add("numeric");
        if (header === "课程") td.classList.add("course-cell");
        if (header === "教师") td.classList.add("teacher-cell");
        tr.append(td);
      });
      tbody.append(tr);
    });
  }

  function showTooltip(event, title, lines) {
    const tooltip = $("#chart-tooltip");
    tooltip.replaceChildren();
    const strong = document.createElement("strong");
    strong.textContent = title;
    tooltip.append(strong);
    lines.forEach((line) => {
      const span = document.createElement("span");
      span.textContent = line;
      tooltip.append(span);
    });
    tooltip.style.left = `${Math.min(event.clientX, window.innerWidth - 320)}px`;
    tooltip.style.top = `${Math.min(event.clientY, window.innerHeight - 120)}px`;
    tooltip.classList.add("is-visible");
    tooltip.setAttribute("aria-hidden", "false");
  }

  function hideTooltip() {
    const tooltip = $("#chart-tooltip");
    tooltip.classList.remove("is-visible");
    tooltip.setAttribute("aria-hidden", "true");
  }

  function renderDonut() {
    const container = $("#credit-composition");
    container.replaceChildren();
    const sourceRows = overviewRows.slice(1, 5).map((row, index) => ({
      label: row[0],
      value: Number(row[2]),
      color: palette[index],
    }));
    const total = sourceRows.reduce((sum, item) => sum + item.value, 0);
    let cursor = 0;
    const stops = sourceRows.map((item) => {
      const start = cursor;
      cursor += (item.value / total) * 100;
      return `${item.color} ${start}% ${cursor}%`;
    });

    const layout = document.createElement("div");
    layout.className = "donut-layout";
    const wrap = document.createElement("div");
    wrap.className = "donut-wrap";
    const donut = document.createElement("div");
    donut.className = "donut";
    donut.style.background = `conic-gradient(${stops.join(",")})`;
    donut.setAttribute("role", "img");
    donut.setAttribute("aria-label", sourceRows.map((item) => `${item.label} ${item.value} 学分`).join("，"));
    const totalElement = document.createElement("div");
    totalElement.className = "donut-total";
    totalElement.innerHTML = `<strong>${formatValue(total, 1)}</strong><span>学分</span>`;
    wrap.append(donut, totalElement);

    const legend = document.createElement("div");
    legend.className = "legend";
    sourceRows.forEach((item) => {
      const row = document.createElement("div");
      row.className = "legend-item";
      row.innerHTML = `<i class="legend-swatch" style="background:${item.color}"></i><span>${item.label}</span><span class="legend-value">${formatValue(item.value, 1)}</span>`;
      legend.append(row);
    });
    layout.append(wrap, legend);
    container.append(layout);
  }

  function renderHorizontalBars(containerSelector, items, options = {}) {
    const container = $(containerSelector);
    container.replaceChildren();
    const width = Math.max(320, container.clientWidth || 480);
    const rowHeight = options.rowHeight || 34;
    const margin = { top: 12, right: 46, bottom: 28, left: options.left || 82 };
    const height = margin.top + margin.bottom + items.length * rowHeight;
    const maxValue = options.maxValue || Math.max(...items.map((item) => item.value), 1);
    const plotWidth = width - margin.left - margin.right;
    const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": options.ariaLabel || "条形图" });

    for (let i = 0; i <= 4; i += 1) {
      const x = margin.left + (plotWidth * i) / 4;
      svg.append(svgElement("line", { x1: x, x2: x, y1: margin.top, y2: height - margin.bottom, class: "grid-line" }));
      svg.append(svgElement("text", { x, y: height - 8, "text-anchor": "middle", class: "tick-label" }, options.tickFormat ? options.tickFormat((maxValue * i) / 4) : formatValue((maxValue * i) / 4)));
    }

    items.forEach((item, index) => {
      const y = margin.top + index * rowHeight + 7;
      const barHeight = 18;
      const barWidth = (item.value / maxValue) * plotWidth;
      svg.append(svgElement("text", { x: margin.left - 10, y: y + 13, "text-anchor": "end", class: "tick-label" }, item.label));
      const rect = svgElement("rect", {
        x: margin.left,
        y,
        width: Math.max(barWidth, 1),
        height: barHeight,
        rx: 2,
        fill: item.color || "#386b81",
        stroke: item.stroke || "#244e61",
        "stroke-width": 0.7,
        tabindex: 0,
      });
      const tooltipLines = item.tooltip || [`${formatValue(item.value, options.valueDigits ?? 2)}${options.suffix || ""}`];
      rect.addEventListener("pointermove", (event) => showTooltip(event, item.label, tooltipLines));
      rect.addEventListener("pointerleave", hideTooltip);
      rect.addEventListener("focus", () => rect.setAttribute("opacity", "0.78"));
      rect.addEventListener("blur", () => rect.setAttribute("opacity", "1"));
      svg.append(rect);
      svg.append(svgElement("text", { x: Math.min(margin.left + barWidth + 7, width - 4), y: y + 13, class: "data-label" }, `${formatValue(item.value, options.valueDigits ?? 2)}${options.suffix || ""}`));
    });
    container.append(svg);
  }

  function renderGradeDistribution() {
    const bins = [
      { label: "95–100", count: 0 },
      { label: "90–94.9", count: 0 },
      { label: "85–89.9", count: 0 },
      { label: "80–84.9", count: 0 },
      { label: "<80", count: 0 },
      { label: "优秀", count: 0 },
      { label: "良好", count: 0 },
    ];
    rows.forEach((row) => {
      const score = row.最终成绩;
      if (typeof score === "number") {
        if (score >= 95) bins[0].count += 1;
        else if (score >= 90) bins[1].count += 1;
        else if (score >= 85) bins[2].count += 1;
        else if (score >= 80) bins[3].count += 1;
        else bins[4].count += 1;
      } else if (score === "优秀") bins[5].count += 1;
      else if (score === "良好") bins[6].count += 1;
    });
    renderHorizontalBars(
      "#grade-distribution",
      bins.map((bin, index) => ({ label: bin.label, value: bin.count, color: index < 5 ? "#386b81" : "#b48a3a", tooltip: [`${bin.count} 门课程`] })),
      { left: 74, rowHeight: 34, suffix: "", valueDigits: 0, ariaLabel: "最终成绩分布" },
    );
  }

  function semesterData(valueAccessor) {
    return semesterOrder
      .map((label) => {
        const year = yearOrder.find((value) => label.startsWith(value));
        const term = termOrder.find((value) => label.endsWith(value));
        const items = rows.filter((row) => row.学年 === year && row.学期 === term);
        return {
          label: `${year}${term === "第一学期" ? "上" : "下"}`,
          fullLabel: `${year} ${term}`,
          value: weightedAverage(items, valueAccessor),
          credits: items.reduce((sum, row) => sum + row.学分, 0),
          count: items.length,
        };
      })
      .filter((item) => item.count);
  }

  function renderLineChart(containerSelector, data, options) {
    const container = $(containerSelector);
    container.replaceChildren();
    const width = Math.max(360, container.clientWidth || 720);
    const height = width < 520 ? 280 : 310;
    const margin = { top: 26, right: 18, bottom: 48, left: 48 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const min = options.min;
    const max = options.max;
    const x = (index) => margin.left + (index / Math.max(data.length - 1, 1)) * plotWidth;
    const y = (value) => margin.top + ((max - value) / (max - min)) * plotHeight;
    const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": options.ariaLabel });

    for (let i = 0; i <= 4; i += 1) {
      const value = min + ((max - min) * i) / 4;
      const yPos = y(value);
      svg.append(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: yPos, y2: yPos, class: "grid-line" }));
      svg.append(svgElement("text", { x: margin.left - 9, y: yPos + 4, "text-anchor": "end", class: "tick-label" }, options.tickFormat(value)));
    }

    const points = data.map((item, index) => [x(index), y(item.value)]);
    const line = points.map(([xPos, yPos], index) => `${index ? "L" : "M"}${xPos},${yPos}`).join(" ");
    const area = `${line} L${points.at(-1)[0]},${margin.top + plotHeight} L${points[0][0]},${margin.top + plotHeight} Z`;
    svg.append(svgElement("path", { d: area, class: "line-area" }));
    svg.append(svgElement("path", { d: line, class: "line-path" }));

    data.forEach((item, index) => {
      const [xPos, yPos] = points[index];
      svg.append(svgElement("text", { x: xPos, y: height - 17, "text-anchor": "middle", class: "tick-label" }, item.label));
      svg.append(svgElement("text", { x: xPos, y: Math.max(yPos - 11, 12), "text-anchor": "middle", class: "data-label" }, options.valueFormat(item.value)));
      const circle = svgElement("circle", { cx: xPos, cy: yPos, r: 4.5, class: "data-point", tabindex: 0 });
      circle.addEventListener("pointermove", (event) => showTooltip(event, item.fullLabel, [options.tooltipValue(item.value), `${formatValue(item.credits, 1)} 学分`, `${item.count} 门课程`]));
      circle.addEventListener("pointerleave", hideTooltip);
      svg.append(circle);
    });
    container.append(svg);
  }

  function renderSemesterCharts() {
    const gpa = semesterData((row) => row.绩点);
    renderLineChart("#semester-gpa", gpa, {
      min: 3,
      max: 5,
      tickFormat: (value) => value.toFixed(1),
      valueFormat: (value) => value.toFixed(3),
      tooltipValue: (value) => `绩点 ${value.toFixed(4)}`,
      ariaLabel: "各学期学分加权绩点折线图",
    });

    const ranks = semesterData((row) => parseRank(row.教学班排名).percentile);
    const maxRank = Math.max(40, Math.ceil(Math.max(...ranks.map((item) => item.value)) / 10) * 10);
    renderLineChart("#semester-rank", ranks, {
      min: 0,
      max: maxRank,
      tickFormat: (value) => `${value.toFixed(0)}%`,
      valueFormat: (value) => `${value.toFixed(1)}%`,
      tooltipValue: (value) => `排名百分位 ${value.toFixed(2)}%`,
      ariaLabel: "各学期学分加权平均教学班排名百分位折线图",
    });
  }

  function renderCategoryGpa() {
    const categories = [...new Set(rows.map((row) => row.类别))];
    const items = categories
      .map((category) => {
        const courses = rows.filter((row) => row.类别 === category);
        return {
          label: category,
          value: weightedAverage(courses, (row) => row.绩点),
          color: categoryColors[category],
          tooltip: [`绩点 ${weightedAverage(courses, (row) => row.绩点).toFixed(4)}`, `${courses.reduce((sum, row) => sum + row.学分, 0)} 学分`],
        };
      })
      .sort((a, b) => b.value - a.value);
    renderHorizontalBars("#category-gpa", items, {
      left: 56,
      rowHeight: 48,
      maxValue: 5,
      valueDigits: 4,
      ariaLabel: "各类别学分加权平均绩点",
    });
  }

  function renderScatter() {
    const container = $("#score-rank-scatter");
    container.replaceChildren();
    const data = rows
      .filter((row) => typeof row.最终成绩 === "number")
      .map((row) => ({ ...row, rankPercentile: parseRank(row.教学班排名).percentile }));
    const width = Math.max(360, container.clientWidth || 720);
    const height = width < 520 ? 300 : 330;
    const margin = { top: 38, right: 20, bottom: 48, left: 52 };
    const plotWidth = width - margin.left - margin.right;
    const plotHeight = height - margin.top - margin.bottom;
    const minScore = 75;
    const maxScore = 100;
    const maxRank = Math.ceil(Math.max(...data.map((row) => row.rankPercentile)) / 10) * 10;
    const x = (score) => margin.left + ((score - minScore) / (maxScore - minScore)) * plotWidth;
    const y = (rank) => margin.top + (rank / maxRank) * plotHeight;
    const svg = svgElement("svg", { viewBox: `0 0 ${width} ${height}`, role: "img", "aria-label": "课程最终成绩与教学班排名百分位散点图" });

    [75, 80, 85, 90, 95, 100].forEach((value) => {
      const xPos = x(value);
      svg.append(svgElement("line", { x1: xPos, x2: xPos, y1: margin.top, y2: height - margin.bottom, class: "grid-line" }));
      svg.append(svgElement("text", { x: xPos, y: height - 17, "text-anchor": "middle", class: "tick-label" }, value));
    });
    for (let value = 0; value <= maxRank; value += 20) {
      const yPos = y(value);
      svg.append(svgElement("line", { x1: margin.left, x2: width - margin.right, y1: yPos, y2: yPos, class: "grid-line" }));
      svg.append(svgElement("text", { x: margin.left - 8, y: yPos + 4, "text-anchor": "end", class: "tick-label" }, `${value}%`));
    }
    svg.append(svgElement("text", { x: width - margin.right, y: height - 3, "text-anchor": "end", class: "tick-label" }, "最终成绩"));
    svg.append(svgElement("text", { x: margin.left, y: 13, class: "tick-label" }, "排名百分位"));

    const legend = svgElement("g", { transform: `translate(${margin.left},20)` });
    Object.entries(categoryColors).forEach(([label, color], index) => {
      const offset = index * 64;
      legend.append(svgElement("circle", { cx: offset + 4, cy: 0, r: 4, fill: color }));
      legend.append(svgElement("text", { x: offset + 12, y: 4, class: "tick-label" }, label));
    });
    svg.append(legend);

    data.forEach((row) => {
      const circle = svgElement("circle", {
        cx: x(row.最终成绩),
        cy: y(row.rankPercentile),
        r: 3 + Math.sqrt(row.学分) * 1.15,
        fill: categoryColors[row.类别],
        stroke: "#ffffff",
        "stroke-width": 1,
        opacity: 0.78,
        tabindex: 0,
      });
      circle.addEventListener("pointermove", (event) => showTooltip(event, row.课程, [`成绩 ${row.最终成绩}`, `教学班排名 ${row.教学班排名}（${row.rankPercentile.toFixed(2)}%）`, `${row.学分} 学分 · ${row.类别}`]));
      circle.addEventListener("pointerleave", hideTooltip);
      circle.addEventListener("focus", () => circle.setAttribute("opacity", "1"));
      circle.addEventListener("blur", () => circle.setAttribute("opacity", "0.78"));
      svg.append(circle);
    });
    container.append(svg);
  }

  function renderCharts() {
    renderDonut();
    renderGradeDistribution();
    renderSemesterCharts();
    renderCategoryGpa();
    renderScatter();
  }

  renderMetrics();
  renderOverviewTable();
  renderDetailsHead();
  setupFilters();
  updateSortIndicators();
  renderDetailsBody();
  renderCharts();

  let resizeTimer;
  window.addEventListener("resize", () => {
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(renderCharts, 140);
  });
})();
