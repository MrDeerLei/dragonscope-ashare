# GitHub 项目管理清单

这份文档用于指导 `DragonScope-AShare` 在 GitHub 上进行标准化管理。

## 1. 建议先做的 3 个 Milestone

### Milestone 1

名称：

`v0.2 数据底座`

目标：

1. 建立本地数据库
2. 打通单日数据同步
3. 存储单日市场统计

### Milestone 2

名称：

`v0.3 周期复盘`

目标：

1. 增加 5 日 / 10 日 / 20 日周期复盘
2. 增加周期主线与龙头汇总

### Milestone 3

名称：

`v0.4 横向对比`

目标：

1. 增加多日横向对比
2. 增加区间对比
3. 增加拐点识别

## 2. 第一批建议创建的 Issues

### Issue 1

标题：

`v0.2: 建立本地数据库结构`

建议内容：

```text
目标：
- 为复盘系统建立本地数据库结构

范围：
- trade_dates
- daily_market_stats
- daily_stock_snapshot
- daily_theme_stats
- daily_review
- period_review

验收标准：
- 有明确 schema
- 可在本地创建数据库
- 文档同步更新
```

### Issue 2

标题：

`v0.2: 增加单日数据同步流程`

建议内容：

```text
目标：
- 从 Tushare 拉取指定交易日数据并写入本地数据库

范围：
- 指数日线
- 个股日线
- 涨跌停价格
- 股票基础信息

验收标准：
- 支持按 trade_date 同步
- 支持重复执行
- 有基本日志输出
```

### Issue 3

标题：

`v0.2: 入库单日市场统计`

建议内容：

```text
目标：
- 生成并存储单日市场统计

范围：
- 上涨/下跌家数
- 非ST涨停/跌停
- 非ST最高连板
- 昨日涨停溢价
- 昨日涨停晋级率
- 情绪分

验收标准：
- daily_market_stats 表可查询
- 指标口径清晰
- 文档更新
```

### Issue 4

标题：

`v0.3: 建立周期复盘引擎`

建议内容：

```text
目标：
- 支持最近 5 日 / 10 日 / 20 日周期复盘

范围：
- 情绪均值与极值
- 主线出现频次
- 龙头切换统计
- 周期复盘 markdown 输出

验收标准：
- 可传入起止日期
- 可生成周期复盘报告
```

### Issue 5

标题：

`v0.4: 建立多日横向对比引擎`

建议内容：

```text
目标：
- 支持多个交易日或两个区间的横向对比

范围：
- 情绪分变化
- 成交额变化
- 主线变化
- 龙头高度变化
- 拐点提示

验收标准：
- 可生成 compare 报告
- 可识别明显拐点
```

## 3. 建议使用的 Labels

建议先建这些：

1. `bug`
2. `feature`
3. `docs`
4. `enhancement`
5. `good first issue`
6. `data`
7. `review-engine`
8. `period-review`
9. `comparison`
10. `security`

## 4. 第一个 Release 建议

版本号：

`v0.1.0`

标题：

`v0.1.0 - 文档版与单日复盘 Demo`

说明建议：

```text
本版本是 DragonScope-AShare 的首个公开版本。

已包含：
- 开源仓库基础骨架
- 系统设计文档
- 系统详细设计说明
- 基于 Tushare 的单日复盘 Demo
- Token 本地环境变量配置示例

下一步将进入 v0.2 数据底座阶段：
- 本地数据库
- 单日数据同步
- 单日市场统计入库
```

## 5. 推荐管理节奏

建议节奏：

1. 用 Milestone 管阶段
2. 用 Issue 管任务
3. 用 PR 管合并
4. 用 Release 管版本

一句话理解：

> Milestone 管阶段，Issue 管事情，PR 管代码，Release 管结果。

