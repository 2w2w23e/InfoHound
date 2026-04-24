# 1. 任务理解

首周 QA 目标不是补齐体系，而是用最少动作尽快判断主链路是否可用，优先卡住这条链路：

`source sync -> 单源 crawl -> 抓取 -> HTML/PDF 解析 -> 去重 -> 入库 -> 导出/API`

本周验收标准只回答三个问题：

- 关键入口是否能跑通。
- 坏数据是否能被尽早发现。
- 当前版本是否已经满足“按天更新、可查、可导出”的最小可用门槛。


# 2. 首周关键测试点

按优先级执行，前 6 项为阻断级。

| 优先级 | 测试点 | 执行动作 | 通过标准 | 失败信号 |
| --- | --- | --- | --- | --- |
| P0 | `source sync` 基础有效性 | 执行 `python -m backend.app.cli sync-sources` 或 `POST /sources/sync` | 返回非 0 条 source，slug 唯一，`is_active=true` 的源可见 | source 数量异常、名称乱码、关键字段为空 |
| P0 | 单源 crawl 可跑通 | 对 1 个英文源和 1 个中文源分别执行 `python -m backend.app.cli crawl --source-slug <slug>` | crawl 返回成功，`saved_count > 0`，无整源失败 | source not found、整源 0 条、超时、异常回滚 |
| P0 | HTML 解析可读 | 抽取 5 条 HTML 文档核查标题、正文、发布日期、语言 | 至少 4/5 可读，正文不是导航拼接，标题不是站点名 | 标题为 `Untitled`、正文过短、噪声行过多 |
| P0 | PDF 解析可读 | 抽取 3 条 PDF 文档核查标题、页数、正文长度 | 至少 2/3 可读，能提取正文，页数合理 | 标题缺失、正文空白、仅抽到页眉页脚 |
| P0 | 去重有效 | 同源重复 URL 和同内容不同 URL 各验证 1 次 | URL 重复不新增，内容 hash 重复不新增 | 重复入库、导出出现重复记录 |
| P0 | 导出可交付 | 执行 `python -m backend.app.cli export --limit 20` 或 `GET /exports/latest?limit=20` | 生成 JSONL 文件，字段稳定，可被下游读取 | 空文件、字段缺失、时间字段非法 |
| P0 | API 基础查询 | 访问 `/health`、`/sources`、`/documents`、`/documents/{id}` | 200 返回，基础筛选可用 | 500、空结果异常、详情接口找不到刚入库数据 |
| P1 | 中英文语言识别 | 抽查中英各 5 条 | 语言字段与正文主语言一致 | 中文误判为 `en` 或英文误判为 `zh` |
| P1 | 原始文件落盘 | 检查 `data/raw/<source>/<day>/` | HTML/TXT/PDF 原始文件存在且可打开 | 数据库有记录但原始文件不存在 |
| P1 | 异常站点容错 | 对 1 个超时或 404 链接源执行 crawl | 单链接失败不拖垮整源任务 | 整个 crawl job 失败 |


# 3. 手工抽样检查清单

每天至少抽样 10 条，建议分布：

- 中文 HTML 3 条
- 英文 HTML 3 条
- PDF 2 条
- 导出记录 2 条

每条记录按下面清单逐项打勾，任一条命中前 5 项问题即判为坏数据：

| 检查项 | 检查方法 | 合格标准 |
| --- | --- | --- |
| Source 是否正确 | 看 `source_slug`、来源站点、URL 域名 | 三者一致，无串源 |
| 标题是否可读 | 对比网页标题和导出标题 | 不是站点名，不是栏目名，不是 `Untitled` |
| 正文是否为正文 | 打开原网页或 PDF 对比 `content_text` | 不是菜单、导航、版权、分页拼接 |
| 发布日期是否可信 | 对比页面显式日期 | 日期不为空或至少不明显错误 |
| 语言是否正确 | 肉眼判断正文主语言 | 中文为 `zh`，英文为 `en` |
| 摘要是否可用 | 看 `summary` 前 1 到 2 句 | 能概括正文，不是噪声句 |
| 关键词是否可读 | 看 `keywords` | 不是无意义碎词，不全是 stopwords |
| 去重是否生效 | 搜同标题、同 URL、同正文片段 | 不应出现重复记录 |
| 原始文件是否齐全 | 查 `data/raw` 对应路径 | HTML/TXT/PDF 路径有效 |
| 导出是否可消费 | 用文本工具打开 JSONL | 每行一个 JSON，对象字段完整 |

抽样记录建议直接写表：

| 日期 | source_slug | doc_id/url | 类型 | 是否通过 | 问题标签 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-04-24 | `fao_newsroom` | `...` | HTML | 是/否 | 标题错/正文短/重复/日期错 | 1 句话 |

问题标签只用这 8 个，避免发散：

- `标题错误`
- `正文噪声`
- `正文过短`
- `PDF 空文本`
- `日期错误`
- `语言错误`
- `重复入库`
- `导出异常`


# 4. 自动化测试建议

首周只保留最小自动化，目标是每天 5 分钟内知道版本有没有明显退化。

## 已补充的最小测试

- `tests/test_source_sync_and_discovery.py`
  覆盖 `source sync` 配置合并、HTML 发现过滤、XML/RSS 发现。
- `tests/test_parser_and_pipeline.py`
  覆盖 HTML fallback 解析、PDF 解析、单源 crawl 去重与原始文件落盘。
- `tests/test_api_smoke.py`
  覆盖 `/health`、`/sources`、`/documents`、`/documents/{id}`、`/exports/latest`。
- `tests/test_postprocessing.py`
  保留摘要、语言、关键词、导出字段稳定性校验。

## 每次提交后的最小回归命令

```powershell
python -m unittest discover -s tests -v
```

## 首周自动化判定规则

- 任何 1 个测试文件失败，当前版本不进入“可用”。
- `test_parser_and_pipeline.py` 失败，直接判主链路不可用。
- `test_api_smoke.py` 失败，直接判对外不可验收。
- 新增 source 前，至少手工过一遍单源 crawl，再进每日任务。


# 5. 当前最高风险

当前最高风险不是“抓不到数据”，而是“坏数据已经入库，但导出/API 看不出来”。

具体表现：

- `process_document()` 已经生成 `parse_status` 和 `parse_warning`。
- `crawl_source()` 没把这两个字段写入主文档可见字段，只写进了 `document_raw.raw_metadata_json`。
- `/documents` 和导出 JSONL 也没有暴露这些解析质量标记。

结果是：

- QA 很难快速筛出坏数据。
- PM 会误以为“有数据就是可用”。
- 回归时只能靠人工打开正文肉眼看，效率很低。

本周先不改业务代码，但必须把它作为上线阻断风险管理：

- 每天手工抽样必须覆盖短正文、`Untitled`、PDF 空文本。
- 若抽样坏数据率超过 20%，当前版本不建议对 PM 宣布可用。

次高风险：

- 导出接口先按 `limit` 截断数据库结果，再做“是否可导出”的过滤。
- 结果是：如果最新 1 条恰好是短正文或低质量记录，`/exports/latest?limit=1` 可能返回空文件，即使库里还有可导出的旧记录。

补充风险：

- `backend/config/sources.yaml` 里部分中文 source 名称已出现乱码，说明配置文件编码或历史写入链路存在风险。


# 6. 执行建议

首周按下面节奏执行，够快，也能控风险。

## Day 1

- 跑一次 `sync-sources`
- 跑 2 个单源 crawl
- 跑自动化回归
- 完成首批 10 条人工抽样

## Day 2 到 Day 5

- 每天先跑 `python -m unittest discover -s tests -v`
- 每天固定抽样 10 条
- 新增 source 只允许逐个开启，不允许批量放开
- 发现坏数据先归类到 8 个固定标签，再决定是否提 bug

## PM / 总工快速判断是否“当前版本可用”

同时满足以下 5 条，才建议标记为“可用”：

- 自动化测试全绿
- 2 个以上 source 单源 crawl 成功
- 最近一次导出文件可打开且字段稳定
- API `/documents` 能查到最近入库数据
- 当日人工抽样坏数据率小于 20%，且没有 `重复入库` 或 `导出异常`

只要命中以下任一条，就不要对外说“已可用”：

- 单源 crawl 连续失败
- PDF 连续 2 条为空文本
- 导出文件为空或字段异常
- API 查不到刚入库数据
- 抽样出现系统性标题错误或重复入库
