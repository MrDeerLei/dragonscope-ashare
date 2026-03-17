# DragonScope-AShare

中文名：`龙头复盘系统`

`DragonScope-AShare` 是一个面向 **A 股龙头战法** 的开源复盘与研究系统。  
它不是通用行情看板，也不是单一脚本工具，而是一套围绕以下场景展开的复盘工作台：

1. 单日复盘
2. 周期复盘
3. 多日横向对比
4. 主线题材追踪
5. 龙头梯队追踪
6. 明日预案沉淀

## 项目定位

很多交易者的复盘是碎片化的：

1. 今天看涨停板
2. 明天看竞价
3. 周末再凭感觉总结
4. 过一段时间后很难回看市场到底是怎么演化的

这个项目要解决的是：

> 把零散的龙头复盘，变成一套结构化、可追踪、可对比、可沉淀的研究系统。

## 核心能力

### 1. 单日复盘

自动生成当天的关键短线口径数据：

1. 指数与市场宽度
2. 非 ST 涨停 / 跌停
3. 非 ST 连板梯队
4. 主线题材活跃度
5. 龙头、容量核心、风险锚
6. 标准化复盘初稿

### 2. 周期复盘

支持对一段时间进行汇总分析：

1. 最近 5 日
2. 最近 10 日
3. 最近 20 日
4. 月度
5. 自定义区间

重点看：

1. 市场情绪变化
2. 主线持续性
3. 龙头切换次数
4. 接力环境变化
5. 风格是否发生切换

### 3. 多日横向对比

支持比较多个交易日或两个时间段：

1. 情绪分强弱
2. 成交额变化
3. 主线题材变化
4. 龙头高度变化
5. 昨日涨停溢价变化
6. 拐点日识别

## 为什么值得做

这个项目最有价值的地方，不是“再做一个股票工具”，而是：

1. 聚焦 A 股龙头战法
2. 默认采用非 `ST` 的短线实战口径
3. 不只看单日，还看阶段演化
4. 强调复盘结果的沉淀和复用

一句话总结：

> 这是一个服务于龙头交易认知建设的开源复盘系统。

## 当前进度

当前阶段：`v0.2 数据底座起步版`

已完成：

1. 系统设计文档
2. 详细设计说明
3. 开源仓库基础骨架
4. 一个基于 `Tushare` 的单日复盘生成脚本 Demo
5. 本地 SQLite 数据库结构
6. 单日同步脚本
7. 周期复盘脚本
8. 多日横向对比脚本

下一阶段：

1. 题材聚合能力增强
2. 周期复盘指标增强
3. 横向对比结果增强
4. 本地 Web 工作台

## 仓库结构

```text
DragonScope-AShare/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── ROADMAP.md
├── PROJECT_CONTROL.md
├── requirements.txt
├── pyproject.toml
├── docs/
├── scripts/
├── app/
├── tests/
├── data/
└── reviews/
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置统一设置（推荐）

复制示例配置：

```bash
cp data/app_settings.example.json data/app_settings.json
```

然后填写：

1. `tushare.token`
2. `llm.base_url`
3. `llm.model`
4. `llm.api_key`

或者直接启动工作台后进入“设置中心”页面填写并保存。

### 2.1 兼容旧方式：仅配置环境变量 Tushare Token

```bash
export TUSHARE_TOKEN=你的token
```

### 3. 生成某日复盘

```bash
python scripts/generate_daily_review.py --date 20260316
```

### 4. 初始化本地数据库

```bash
python scripts/init_db.py
```

### 5. 同步单日数据到本地数据库

```bash
export TUSHARE_TOKEN=你的token
python scripts/sync_day.py --date 20260316
```

### 5.1 可选：自定义主线题材映射

项目内置了一份示例映射：

```text
data/theme_rules.example.json
```

如果你想按自己的龙头复盘口径定义主线题材，可以复制一份本地规则：

```bash
cp data/theme_rules.example.json data/theme_rules.json
```

然后修改：

1. `industry_aliases`
2. `stock_themes`
3. `keyword_themes`

注意：

1. `data/theme_rules.json` 默认不会进入 Git 版本控制
2. 这样适合保留你自己的主线判断口径

### 6. 生成周期复盘

```bash
python scripts/generate_period_review.py --start 20260313 --end 20260316 --period-type custom
```

### 7. 生成横向对比

```bash
python scripts/compare_periods.py \
  --left-start 20260313 --left-end 20260313 \
  --right-start 20260316 --right-end 20260316 \
  --compare-type day_vs_day
```

### 8. 生成多日对比矩阵与拐点记录

```bash
python scripts/generate_compare_matrix.py --start 20260313 --end 20260316
```

### 9. 启动本地复盘工作台（v0.5-dev）

```bash
python scripts/run_dashboard.py
```

打开：

```text
http://127.0.0.1:8000
```

工作台能力：

1. 首页看最新市场状态、主线题材、龙头梯队和拐点提示
2. 首页支持“今日一键采集+复盘”手动触发
3. 单日页支持交易日历状态查看（已采集/待创建/已归档）
4. 一键采集改为后台任务，点击后立即返回并显示运行状态
5. 单日页支持人工编辑复盘字段（主线、龙头、明日计划等）
6. 单日页支持“一键归档/恢复”，归档状态写入 `daily_review.review_status`
7. 单日页支持自定义总结，并提示先到“设置中心”配置模型
8. 历史回查页支持按区间/主线/龙头/归档状态筛选
9. 新增“设置中心”统一维护 Tushare + LLM Token
10. 周期页和矩阵页支持区间复盘与多日横向对比

### 10. 交易日收盘后自动跑当日采集+复盘（可用于定时任务）

```bash
python scripts/run_daily_pipeline.py --date 2026-03-17
```

不传 `--date` 时默认使用当天日期。

cron 示例（工作日 15:20 自动执行）：

```bash
20 15 * * 1-5 cd /Users/ray/Myworkspace/DragonScope-AShare && /usr/bin/env bash -lc 'python3 scripts/run_daily_pipeline.py >> data/exports/eod.log 2>&1'
```

### 11. 配置大模型（用于自定义总结扩展）

```bash
cp data/app_settings.example.json data/app_settings.json
```

然后填入你自己的：

1. `llm.base_url`
2. `llm.model`
3. `llm.api_key`

## 文档入口

1. [系统设计稿](./docs/system-design.md)
2. [系统详细设计说明](./docs/system-spec-v1.md)
3. [项目路线图](./ROADMAP.md)
4. [项目总控文件](./PROJECT_CONTROL.md)
5. [GitHub 管理清单](./GITHUB_SETUP.md)

## 项目命名说明

主项目名：

1. `DragonScope-AShare`

命名含义：

1. `Dragon`：对应龙头战法
2. `Scope`：强调观察、研究、复盘系统感
3. `AShare`：明确聚焦 A 股市场

## 风险声明

本项目仅用于复盘研究、数据分析与交易工作流辅助。  
不构成任何投资建议。

## 许可证

MIT
