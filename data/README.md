# SYSU-Phys-Bench 数据集

`data/submissions/` 保存社区提交的标准化课程记录。每位贡献者对应一个 CSV 文件，文件名与匿名 `contributor_id` 一致。

## 数据流

```text
data/submissions/*.csv
        │
        ├── scripts/validate_submissions.py  校验格式与取值
        │
        └── scripts/build_dataset.py         生成 community-data.js
                                                │
                                                └── SYSU-Phys-Bench 网页
```

`community-data.js` 是确定性生成文件：相同 CSV 输入会产生完全相同的输出。Pull Request 必须同时提交新增或修改的 CSV 与重新生成的 `community-data.js`。

## 记录粒度

一行表示一位贡献者在一门课程中的一次正式成绩记录。记录保留课程、学期、教师、学分、成绩、绩点、教学班名次与教学班人数，不保存姓名、学号、联系方式或原始成绩单文件。

完整字段定义与投稿步骤见 [`CONTRIBUTING.md`](../CONTRIBUTING.md)。

## 课程匹配

课程默认按 `course_name` 与 `category` 汇总。贡献时应优先使用教务系统中的正式课程名，避免自行缩写、添加教师姓名或添加不属于课程名的班级备注。确需合并课程别名时，由维护者在数据审查中统一处理。

## 指标计算

每条记录独立计算 Yu Index；课程级 Yu Index 是当前筛选范围内同名课程观测值的算术平均。网页同时报告样本数和独立贡献者数量，不将多条观测伪装成单条原始成绩。
