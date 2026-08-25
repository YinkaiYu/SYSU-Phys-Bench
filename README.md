# SYSU-Phys-Bench

静态网页，无构建步骤。

- `index.html`：基准测试主页
- `yu-index.html`：Yu Index 技术报告

## 本地预览

直接打开 `index.html`，或在本目录启动任意静态文件服务器。

## 更新数据

源表位于仓库上一级目录：

- `余荫铠-成绩总览.xlsx`
- `余荫铠-成绩明细.xlsx`

运行：

```powershell
python scripts/extract_data.py
```

脚本会重新生成 `data.js`。
