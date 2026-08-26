# SYSU-Phys-Bench

中山大学物理学院本科课程给分基准测试。项目基于余荫铠 2020—2024 年本科成绩与教学班排名数据，以交互式网页呈现课程绩点、排名分布、Yu Index、课程明细及数据集统计。

[在线访问 SYSU-Phys-Bench](https://www.yykspace.com/show/sysu-phys-bench/) · [阅读 Yu Index 技术报告](https://www.yykspace.com/show/sysu-phys-bench/yu-index.html)

## 项目内容

- **课程绩点与排名分布图**：以教学班排名百分位和课程绩点呈现各课程数据，支持类别、学年、学期和具体课程多选筛选。
- **Yu Index 与排名分布图**：展示课程给分友好度指标与教学班排名的关系，并标出数据集基准线。
- **课程明细**：完整列出课程、Yu Index、绩点、成绩、学分、排名、教师、学年、学期及类别，支持搜索、筛选与排序。
- **数据集统计**：汇总总绩点、总排名、学分构成、绩点分布、学期趋势及各类别学分加权平均绩点。
- **大图查看与导出**：两张分布图均支持全屏查看和 PNG 下载；桌面端与移动端均可查看数据详情。
- **Yu Index 计算器**：输入个人绩点、教学班名次与教学班人数，即可计算对应课程的 Yu Index。

## Yu Index

Yu Index 是 SYSU-Phys-Bench 的课程给分友好度指标：

$$
Y=G-\frac{1}{3}\Phi^{-1}\!\left(\frac{n-r+\frac{5}{8}}{n+\frac{1}{4}}\right)
$$

其中：

- $G$ 为个人绩点；
- $r$ 为教学班名次，第 1 名为最高；
- $n$ 为教学班人数；
- $\Phi^{-1}$ 为标准正态分布的逆累积分布函数。

Yu Index 使用教学班排名估计个人相对表现，再从个人绩点中分离这一部分，得到与 GPA 同尺度的课程给分水平估计。Yu Index 越高，说明课程给分越友好。完整推导、参数选择、数据校验与计算示例见 [Yu Index 技术报告](https://www.yykspace.com/show/sysu-phys-bench/yu-index.html)。

## 数据

网页数据来自两份本科成绩表：

- 成绩总览：各学期绩点、排名、学分及累计数据；
- 成绩明细：逐门课程的成绩、绩点、学分、教学班排名、教师、学年、学期与课程类别。

用于网页渲染的完整数据保存在 [`data.js`](data.js) 中。原始 Excel 工作簿位于维护者的本地上级目录，不纳入本仓库；[`scripts/extract_data.py`](scripts/extract_data.py) 用于从这两份工作簿重新生成 `data.js`。

## 项目结构

```text
.
├── index.html               # 基准测试主页
├── yu-index.html            # Yu Index 技术报告
├── styles.css               # 页面、图表与响应式样式
├── app.js                   # 筛选、表格、图表、计算器及 PNG 导出
├── data.js                  # 网页使用的成绩数据
└── scripts/
    └── extract_data.py      # Excel 数据提取脚本
```

项目采用原生 HTML、CSS、JavaScript 和 SVG，无前端框架或构建步骤。

## 本地运行

直接打开 `index.html`，或在仓库目录启动静态文件服务器：

```powershell
python -m http.server 8000
```

然后访问 <http://localhost:8000/>。

## 更新数据

数据提取脚本依赖 Python 与 `openpyxl`。将以下文件放在仓库上一级目录：

```text
余荫铠-成绩总览.xlsx
余荫铠-成绩明细.xlsx
```

安装依赖并重新生成数据：

```powershell
python -m pip install openpyxl
python scripts/extract_data.py
```

## 作者

余荫铠 · [yykspace.com](https://www.yykspace.com/)
