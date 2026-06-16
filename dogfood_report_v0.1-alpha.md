# RepoMind OS 新项目 Dogfood 测试清单

## 0. 测试目标

验证 RepoMind OS 在一个新项目中是否能做到：

* 用户能看懂怎么开始；
* `template/` 能正确复制到目标项目；
* 第一个 GPT 窗口能进入 Project Governor Bootstrap Window；
* GPT 不会只总结 `BOOT.md` 后停止；
* 能识别项目类型、已有上下文和用户偏好；
* 能选择 minimal setup（最小设置）或 custom roles（自定义角色）；
* 能正确生成 Role Task Packet / Role Result Packet；
* 能生成有边界的 Codex prompt；
* 能判断哪些信息需要 writeback（写回）；
* 不覆盖用户已有治理体系；
* 不让 AI 角色依赖隐藏聊天记忆。

---

## 1. 准备测试项目

* [ ] 新建一个空项目仓库，例如 `repomind-dogfood-test`
* [ ] 添加一个简单 README，说明这是测试项目
* [ ] 确认项目初始状态干净：

```bash
git status --short
```

期望结果：

```text
无未提交改动，或只有你明确知道的初始化文件
```

---

## 2. 安装 RepoMind OS 模板

* [ ] 从 RepoMind OS 仓库复制 `template/` 内容到测试项目根目录
* [ ] 确认目标项目包含：

```text
.ai-governance/BOOT.md
.ai-governance/CONTEXT_INDEX.md
.ai-governance/FIRST_WINDOW_PROTOCOL.md
.ai-governance/roles/
.ai-governance/prompts/
```

* [ ] 如果目标项目已有 `AGENTS.md`，不要直接覆盖，应合并
* [ ] 如果目标项目没有 `AGENTS.md`，可以复制 `template/AGENTS.md`

检查项：

```text
docs/ 文件夹不需要复制到目标项目
README.md 不需要复制到目标项目
template/ 外层目录本身不应出现在目标项目中
```

---

## 3. 第一窗口启动测试

打开新的 GPT 网页窗口，输入：

```text
你是这个仓库的 Project Governor Bootstrap Window（项目总管启动窗口）。

请先读取 `.ai-governance/BOOT.md`，然后使用 `.ai-governance/CONTEXT_INDEX.md` 选择最小必要上下文。
如果这是该项目的第一个 GPT 窗口，请继续遵守 `.ai-governance/FIRST_WINDOW_PROTOCOL.md`。

不要写实现代码。
不要让 Codex 修改文件。
完成读取后，不要停在总结阶段；请继续进入 bootstrap 流程并提出第一批问题。
```

### 通过标准

GPT 必须输出：

* [ ] 已读取哪些文件
* [ ] 当前 startup mode（例如 first-window bootstrap）
* [ ] 是否缺少项目上下文
* [ ] 第一批 bootstrap 问题
* [ ] 当前不能做什么，例如不能写代码、不能让 Codex 修改文件

### 失败标准

如果 GPT 只说：

```text
我已阅读 BOOT.md，等待你的指令
```

则判定失败，记录为：

```text
FAIL: first window stopped after BOOT summary
```

---

## 4. 项目 intake 测试

向 GPT 提供一个简单项目说明，例如：

```text
这是一个测试项目，用来验证 RepoMind OS 是否能帮助一个新项目建立 AI 协作治理。项目目前没有代码，只有 README。
```

检查 GPT 是否：

* [ ] 判断项目类型
* [ ] 明确不确定项
* [ ] 询问是否已有旧角色、旧 prompt、旧上下文、偏好或工作习惯
* [ ] 询问使用 minimal setup 还是 custom roles
* [ ] 不直接创建角色文件
* [ ] 不直接安排 Codex 修改

通过标准：

```text
GPT 应该先建议 minimal setup，并说明是否需要更多角色。
```

---

## 5. 已有治理体系导入测试

模拟用户已有旧治理体系，粘贴一段：

```text
这个项目以前有一套规则：
1. 所有 AI 角色每次回答前必须读取仓库文件；
2. 不允许直接让 Codex 修改未授权文件；
3. 所有长期规则必须写回治理文件；
4. 项目总管负责阶段规划。
```

检查 GPT 是否：

* [ ] 不直接覆盖 RepoMind OS 规则
* [ ] 识别这是 existing governance context（已有治理上下文）
* [ ] 进入合并 / 导入判断
* [ ] 区分哪些是全局规则、角色规则、项目规则、临时任务规则
* [ ] 提醒需要用户批准后才能写回
* [ ] 安排后续角色文件是否需要更新

失败标准：

```text
GPT 只说“已记录”，但没有安排治理合并和角色复审。
```

---

## 6. 角色读取规则测试

要求 GPT 扮演 Project Governor，问一个项目方向问题。

检查它是否：

* [ ] 先说明读取了哪些仓库文件
* [ ] 没有只依赖聊天记忆
* [ ] 使用 `CONTEXT_INDEX.md` 判断是否需要更多文件
* [ ] 对重大判断输出结构化分析
* [ ] 没有直接推进实现

通过标准：

```text
每个重要回答前都应出现“已读取 / 已刷新”的仓库文件说明。
```

---

## 7. Role Task Packet 测试

让 Project Governor 准备一个角色任务，例如：

```text
请准备一个给 Repo Governor 的任务包，让它审计当前测试项目的 .ai-governance 安装是否完整。
```

检查输出是否包含：

* [ ] Target role
* [ ] Purpose
* [ ] Files to read
* [ ] Context summary
* [ ] Task
* [ ] Boundaries
* [ ] Required output
* [ ] Stop conditions
* [ ] Writeback requirements

失败标准：

```text
任务包没有明确 files to read / boundaries / required output。
```

---

## 8. Role Result Packet 测试

新开一个 GPT 窗口，作为 Repo Governor，粘贴 Role Task Packet。

检查它是否：

* [ ] 读取 `BOOT.md`
* [ ] 读取 `CONTEXT_INDEX.md`
* [ ] 读取自己的 role 文件
* [ ] 不假设隐藏聊天历史
* [ ] 返回 Role Result Packet
* [ ] 明确 evidence / uncertainty / risks
* [ ] 不直接修改仓库文件

通过标准：

```text
Repo Governor 能审计安装完整性，并返回可复制给 Project Governor 的结果包。
```

---

## 9. Codex Prompt 测试

让 Project Governor 或 Prompt Architect 准备一个极小 Codex 任务，例如：

```text
让 Codex 在 docs/dogfood_report_v0.1-alpha.md 中创建本次测试报告草稿。
```

检查 Codex prompt 是否包含：

* [ ] Task
* [ ] Purpose
* [ ] Files to read first
* [ ] Allowed files
* [ ] Forbidden files
* [ ] Before editing commands
* [ ] Implementation scope
* [ ] Validation commands
* [ ] Done when
* [ ] Final report format
* [ ] Docs impact check
* [ ] Commit / push / PR rules

关键要求：

```text
Allowed files 只能包含 docs/dogfood_report_v0.1-alpha.md
不能允许 git add .
不能允许改 .ai-governance unless explicitly approved
```

---

## 10. Writeback 判断测试

给 Project Governor 粘贴 Repo Governor 或 Codex 的结果，让它判断是否需要 writeback。

检查它是否：

* [ ] 区分 NO\_WRITEBACK / HANDOFF\_UPDATE / MEMORY\_UPDATE / DECISION\_LOG\_UPDATE / ROLE\_UPDATE 等类型
* [ ] 不把临时聊天内容直接写入长期文件
* [ ] 不写 secrets 或私密聊天记录
* [ ] 对角色规则变化要求用户批准
* [ ] 对项目状态变化要求用户批准

失败标准：

```text
GPT 把未经确认的聊天内容直接当成项目事实写回。
```

---

## 11. 完整闭环通过标准

本次 dogfood 成功，需要满足：

* [ ] 用户能按 README / quickstart 启动
* [ ] 第一个 GPT 窗口能进入 bootstrap
* [ ] 能识别已有治理体系并引导合并
* [ ] 所有角色回答前会读取仓库文件
* [ ] Project Governor 不会忘记角色改进
* [ ] Role Task Packet 可用
* [ ] Role Result Packet 可用
* [ ] Codex prompt 有边界
* [ ] Writeback 判断清楚
* [ ] 没有覆盖用户项目状态文件
* [ ] 没有声称自动化能力超过当前实现

---

## 12. 记录失败项

每个失败项按这个格式记录：

```text
FAIL ID:
阶段:
输入:
实际输出:
期望输出:
风险:
建议修复文件:
```

示例：

```text
FAIL ID: FW-001
阶段: First Window Bootstrap
输入: 请读取 BOOT.md
实际输出: 只总结 BOOT，等待用户指令
期望输出: 继续读取 CONTEXT_INDEX 和 FIRST_WINDOW_PROTOCOL，并提出 bootstrap 问题
风险: 用户启动失败
建议修复文件: BOOT.md / quickstart.md
```

---

## 13. 最终测试结论模板

```text
Dogfood Result: PASS / PARTIAL PASS / FAIL

已通过:
- ...

失败项:
- ...

需要修复:
- ...

是否阻塞 v0.1-alpha:
- 是 / 否

下一步:
- ...
```
