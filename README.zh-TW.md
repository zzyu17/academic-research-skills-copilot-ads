# Academic Research Skills (ADS 版) for Copilot CLI

[![Version](https://img.shields.io/badge/version-v3.11.1--ads-blue)](https://github.com/Imbad0202/academic-research-skills/releases/tag/v3.11.1)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](https://creativecommons.org/licenses/by-nc/4.0/)

[English](README.md) | [简体中文版](README.zh-CN.md) | [日本語版](README.ja-JP.md)

專為 Copilot CLI 設計的學術研究技能套件 — 4 個技能、25+ 種模式、42 個智能體，涵蓋從研究到發表的完整流程。

**這是 ADS 版** — 將 SAO/NASA 天體物理數據系統 (ADS) 作為天文學與天體物理學研究的一級文獻來源。標準版（不含 ADS）請見[標準分發版](https://github.com/zzyu17/academic-research-skills-copilot)。

> **這是 Copilot CLI 分支版本。** 完整的特性文件、版本歷史、設計規格和架構說明請參考[上游 Claude Code 版 README](https://github.com/Imbad0202/academic-research-skills) 及本倉庫 `docs/` 目錄中的設計文件。本文件僅涵蓋 Copilot CLI 專屬的安裝與使用說明。

---

## ADS 版新增功能

當您的研究學科為**天文學**或**天體物理學**時，此版本將：

- **研究階段**：查詢 SAO/NASA ADS（除 arXiv、Crossref、OpenAlex、Semantic Scholar 外）進行文獻搜尋與來源發現
- **引文驗證**：在完整性檢查中將 ADS bibcode 解析作為 Tier-0 權威來源 — 經 ADS 匹配的引文將跳過所有低層級解析器
- **文獻監控**：在研究後監控階段包含 ADS 提醒策略

請在環境中設定 `ADS_API_TOKEN` 以啟用 ADS API 存取（必填 — 不支援匿名存取）。未設定時，ADS 功能將優雅降級：流程回退至 arXiv 及其他資料庫。

---

## 安裝

在 Copilot CLI 會話中：

```text
/plugin marketplace add zzyu17/academic-research-skills-copilot-ads
/plugin install academic-research-skills-ads@academic-research-skills-ads
```

**首次會話 — 擴展註冊：**

`ars-bootstrap` 技能會在偵測到學術關鍵詞時自動觸發。它會偵測缺失的擴展、請您批准執行 `setup-copilot-extension.sh`（一次 bash 授權）、建立符號連結，並自動重新載入擴展。13 個斜槓命令（`/ars-full`、`/ars-plan` 等）會在同一會話中立即啟用。

此後所有會話中，引導技能會靜默退出 — 不會重複提示。

> **外掛更新後：** 若您執行 `/plugin update academic-research-skills-ads@academic-research-skills-ads`，擴展符號連結會自動追蹤更新後的來源檔案。
要啟用更新後的 `extension.mjs`，請執行 `/restart` 或使用 `/clear` 開始新會話。

詳見 [QUICKSTART.md](QUICKSTART.md) 獲取完整指南。

---

## 斜槓命令

| 命令 | 功能 |
|---|---|
| `/ars-full` | 完整流程 — 研究 → 寫作 → 審閱 → 修改 → 定稿 |
| `/ars-plan` | 蘇格拉底式逐章規劃 |
| `/ars-outline` | 詳細大綱 + 證據映射 |
| `/ars-revision` | 修訂稿 + R&R 回覆 |
| `/ars-revision-coach` | 解析審稿意見 → 修訂路線圖 |
| `/ars-reviewer` | 多視角模擬同行評審 |
| `/ars-abstract` | 雙語摘要 + 關鍵詞 |
| `/ars-lit-review` | 註釋文獻列表 |
| `/ars-format-convert` | LaTeX / DOCX / PDF / Markdown 格式轉換 |
| `/ars-citation-check` | 引文錯誤報告 |
| `/ars-disclosure` | 期刊專屬 AI 使用聲明 |
| `/ars-mark-read` | 記錄引文的人工閱讀標記 |
| `/ars-unmark-read` | 撤銷先前的人工閱讀標記 |

**自動生成的技能命令**（安裝外掛後可立即使用，無需擴展）：

`/academic-research-skills-ads:deep-research`, `/academic-research-skills-ads:academic-paper`, `/academic-research-skills-ads:academic-paper-reviewer`, `/academic-research-skills-ads:academic-pipeline`, `/academic-research-skills-ads:ars-bootstrap`

---

## 模型路由（可選）

透過環境變數進行分層模型調度：

```bash
export ARS_MODEL_ARCHITECT="claude-opus-4-5"    # 架構層 (完整流程、修訂教練、審閱者)
export ARS_MODEL_EXECUTION="claude-sonnet-4-5"   # 執行層 (計畫、大綱、修訂、摘要等)
```

若未設定環境變數，所有子智能體調度將使用會話預設模型。這兩個層級必須由同一個提供者端點（`COPILOT_PROVIDER_BASE_URL`）（BYOK 模式）提供服務，或者在您的 Copilot 訂閱中可用。

---

## 技能一覽

| 技能 | 目的 |
|-------|---------|
| `deep-research` v2.9.4 | 13 個智能體組成的研究團隊 — 7 種模式（+ 天文學 ADS） |
| `academic-paper` v3.1.2 | 12 個智能體組成的論文寫作團隊 — 10 種模式（+ ADS 引文來源） |
| `academic-paper-reviewer` v1.9.1 | 多視角同行評審 — 6 種模式 |
| `academic-pipeline` v3.11.1 | 完整的 10 階段流程編排器（+ ADS 完整性門） |

---

## 更多資訊

- **[上游 README](https://github.com/Imbad0202/academic-research-skills)** — 完整特性文件、架構、版本歷史與設計理念
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — 流程架構、階段矩陣與品質門
- **[docs/design/](docs/design/)** — 所有設計規格（v3.6.2 – v3.11.1 + Copilot 版本）
- **[QUICKSTART.md](QUICKSTART.md)** — Copilot CLI 逐步設定指南
- **[POSITIONING.md](POSITIONING.md)** — ARS 的定位與範疇
- **[CHANGELOG.md](CHANGELOG.md)** — 發布歷史（Copilot 版本在最前）

## 授權條款

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
