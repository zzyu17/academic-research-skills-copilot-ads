# Academic Research Skills (ADS 版) for Copilot CLI

[![Version](https://img.shields.io/badge/version-v3.11.1--ads-blue)](https://github.com/Imbad0202/academic-research-skills/releases/tag/v3.11.1)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](https://creativecommons.org/licenses/by-nc/4.0/)

[English](README.md) | [繁體中文版](README.zh-TW.md) | [日本語版](README.ja-JP.md)

专为 Copilot CLI 设计的学术研究技能套件 — 4 个技能、25+ 种模式、42 个智能体，覆盖从研究到发表的完整流程。

**这是 ADS 版** — 将 SAO/NASA 天体物理数据系统 (ADS) 作为天文学与天体物理学研究的一级文献来源。标准版（不含 ADS）请见[标准分发版](https://github.com/zzyu17/academic-research-skills-copilot)。

> **这是 Copilot CLI 分支版本。** 完整的特性文档、版本历史、设计规格和架构说明请参考[上游 Claude Code 版 README](https://github.com/Imbad0202/academic-research-skills) 及本仓库 `docs/` 目录中的设计文档。本文档仅涵盖 Copilot CLI 专属的安装与使用说明。

---

## ADS 版新增功能

当您的研究学科为**天文学**或**天体物理学**时，此版本将：

- **研究阶段**：查询 SAO/NASA ADS（除 arXiv、Crossref、OpenAlex、Semantic Scholar 外）进行文献搜索与来源发现
- **引文验证**：在完整性检查中将 ADS bibcode 解析作为 Tier-0 权威来源 — 经 ADS 匹配的引文将跳过所有低层级解析器
- **文献监控**：在研究后监控阶段包含 ADS 提醒策略

请在环境中设置 `ADS_API_TOKEN` 以启用 ADS API 访问（必填 — 不支持匿名访问）。未设置时，ADS 功能将优雅降级：流程回退至 arXiv 及其他数据库。

---

## 安装

在 Copilot CLI 会话中：

```text
/plugin marketplace add zzyu17/academic-research-skills-copilot-ads
/plugin install academic-research-skills-ads@academic-research-skills-ads
```

**首次会话 — 扩展注册：**

`ars-bootstrap` 技能会在检测到学术关键词时自动触发。它会检测缺失的扩展、请您批准执行 `setup-copilot-extension.sh`（一次 bash 授权）、建立符号链接，并自动重新载入扩展。13 个斜杠命令（`/ars-full`、`/ars-plan` 等）会在同一会话中立即可用。

此后所有会话中，引导技能会静默退出 — 不会重复提示。

> **插件更新后：** 若您执行 `/plugin update academic-research-skills-ads@academic-research-skills-ads`，扩展符号链接会自动指向更新后的源文件。
要启用更新后的 `extension.mjs`，请执行 `/restart` 或使用 `/clear` 开始新会话。

详见 [QUICKSTART.md](QUICKSTART.md) 了解完整流程（英文）。

---

## 斜杠命令

| 命令 | 功能 |
|---|---|
| `/ars-full` | 完整流程 — 研究 → 写作 → 审阅 → 修改 → 定稿 |
| `/ars-plan` | 苏格拉底式逐章规划 |
| `/ars-outline` | 详细大纲 + 证据映射 |
| `/ars-revision` | 修订稿 + R&R 回复 |
| `/ars-revision-coach` | 解析审稿意见 → 修订路线图 |
| `/ars-reviewer` | 多视角模拟同行评审 |
| `/ars-abstract` | 双语摘要 + 关键词 |
| `/ars-lit-review` | 注释文献列表 |
| `/ars-format-convert` | LaTeX / DOCX / PDF / Markdown 格式转换 |
| `/ars-citation-check` | 引文错误报告 |
| `/ars-disclosure` | 期刊专属 AI 使用声明 |
| `/ars-mark-read` | 为引文记录人工已读信号 |
| `/ars-unmark-read` | 撤销之前的人工已读标记 |

**自动生成的技能命令**（插件安装后立即生效，无需扩展注册）：

`/academic-research-skills-ads:deep-research`, `/academic-research-skills-ads:academic-paper`, `/academic-research-skills-ads:academic-paper-reviewer`, `/academic-research-skills-ads:academic-pipeline`, `/academic-research-skills-ads:ars-bootstrap`

---

## 模型路由（可选）

通过环境变量进行分层模型调度：

```bash
export ARS_MODEL_ARCHITECT="claude-opus-4-5"    # 架构层（完整流程, 审稿意见指导, 模拟审稿人）
export ARS_MODEL_EXECUTION="claude-sonnet-4-5"   # 执行层（计划, 大纲, 修订, 摘要等）
```

若未设置环境变量，所有子智能体调用将默认使用当前会话的模型。上述两层模型必须由同一端点提供服务（`COPILOT_PROVIDER_BASE_URL`）（BYOK 模式），或在您的 Copilot 订阅中受支持。

---

## 技能概览

| 技能 | 用途 |
|-------|---------|
| `deep-research` v2.9.4 | 13个智能体的研究团队 — 7 种模式（+ 天文学 ADS） |
| `academic-paper` v3.1.2 | 12个智能体的论文写作团队 — 10 种模式（+ ADS 引文来源） |
| `academic-paper-reviewer` v1.9.1 | 多视角模拟同行评审 — 6 种模式 |
| `academic-pipeline` v3.11.1 | 完整的 10 阶段流程编排器（+ ADS 完整性门） |

---

## 更多信息

- **[上游 README](https://github.com/Imbad0202/academic-research-skills)** — 完整特性文档、架构、版本历史、设计理念
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 流程架构、阶段矩阵、质量门
- **[docs/design/](docs/design/)** — 所有设计规格（v3.6.2 – v3.11.1 + Copilot 移植）
- **[QUICKSTART.md](QUICKSTART.md)** — 逐步的 Copilot CLI 设置指南
- **[POSITIONING.md](POSITIONING.md)** — ARS 的功能边界说明
- **[CHANGELOG.md](CHANGELOG.md)** — 发布历史（Copilot 版本在最前）

## 许可证

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
