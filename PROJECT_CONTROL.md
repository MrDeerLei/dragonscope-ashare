# 项目总控文件

这是 `DragonScope-AShare` 的项目执行总控文件。  
后续你推进这个开源项目时，可以优先看这里。

项目名：

1. `DragonScope-AShare`

本地目录：

1. `/Users/ray/Myworkspace/DragonScope-AShare`

GitHub 仓库：

1. `dragonscope-ashare`

## 一、当前定位

当前版本定位：

1. `v0.1 文档 + Demo`

当前目标：

1. 把仓库形象搭好
2. 把项目定位讲清楚
3. 放出一个可运行的单日复盘示例
4. 为下一阶段的数据底座开发做准备

## 二、当前仓库中已经准备好的内容

1. `README.md`
2. `LICENSE`
3. `CONTRIBUTING.md`
4. `ROADMAP.md`
5. `PROJECT_CONTROL.md`
6. `docs/system-design.md`
7. `docs/system-spec-v1.md`
8. `scripts/generate_daily_review.py`

## 三、你接下来要按顺序做的事情

### Step 1. 完善 GitHub 首页

去仓库首页补这几项：

1. Description
2. Topics
3. Release

推荐 Description：

```text
An open-source A-share dragon-head review and research system for daily review, period review, and multi-day comparison.
```

推荐 Topics：

```text
a-share
quant
trading-system
market-review
stock-research
python
tushare
```

### Step 2. 用 VS Code 管理本地项目

建议工作方式：

1. GitHub 页面负责仓库展示、Issues、Release、路线管理
2. VS Code 负责改文档、改代码、提交版本

### Step 3. 做第一批 Issues

建议先建这 5 个：

1. `v0.2: 建立本地数据库结构`
2. `v0.2: 增加单日数据同步流程`
3. `v0.2: 入库单日市场统计`
4. `v0.3: 建立周期复盘引擎`
5. `v0.4: 建立多日横向对比引擎`

### Step 4. 做第一个 Release

建议版本号：

1. `v0.1.0`

建议标题：

1. `v0.1.0 - 文档版与单日复盘 Demo`

### Step 5. 进入下一阶段开发

下一阶段重点不是继续润色文档，而是开始做：

1. 数据库
2. 单日同步
3. 周期复盘
4. 横向对比

## 四、标准提交演练

以后每次改完，都尽量按下面方式提交：

### 文档类提交

```bash
git add .
git commit -m "docs: 中文化 README 和项目基础文档"
git push
```

### 功能类提交

```bash
git add .
git commit -m "feat: 新增周期复盘引擎"
git push
```

### 修复类提交

```bash
git add .
git commit -m "fix: 修正非ST连板梯队统计口径"
git push
```

## 五、第一阶段成功标准

第一阶段是否成功，看这几点：

1. 仓库公开
2. README 清楚
3. Demo 能跑
4. 有第一批 Issues
5. 有第一个 Release

## 六、当前建议

当前最优先事项：

1. 中文化仓库文档
2. 做一次标准提交
3. 建第一批 Issues
4. 发 `v0.1.0`

一句话总结：

> 现在先把仓库做成“像一个开源项目”，再进入功能开发阶段。
