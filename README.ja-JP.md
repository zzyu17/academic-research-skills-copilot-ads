# Academic Research Skills for Copilot CLI

[![Version](https://img.shields.io/badge/version-v3.9.4.2-blue)](https://github.com/Imbad0202/academic-research-skills/releases/tag/v3.9.4.2)
[![License: CC BY-NC 4.0](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](https://creativecommons.org/licenses/by-nc/4.0/)

[English](README.md) | [简体中文版](README.zh-CN.md) | [繁體中文版](README.zh-TW.md)

Copilot CLI 向けの学術研究スキルスイート — 4 スキル、25+ モード、42 エージェントアンサンブル。研究から出版までの全パイプラインをカバーします。

> **これは Copilot CLI ブランチ版です。** 基準となる Claude Code 版については、[上流の README](https://github.com/Imbad0202/academic-research-skills) を参照してください。機能ドキュメント、バージョン履歴、設計仕様、アーキテクチャの詳細については、上流のドキュメントおよび本リポジトリの `docs/` ディレクトリを参照してください。このドキュメントは Copilot CLI 固有のインストールと使用方法のみをカバーしています。

---

## インストール

Copilot CLI セッションで：

```text
/plugin marketplace add zzyu17/academic-research-skills-copilot
/plugin install academic-research-skills@academic-research-skills
```

**初回セッションのみ — 拡張機能の登録：**

`ars-bootstrap` スキルが学術キーワードで自動起動します。不足している拡張機能を検出し、`setup-copilot-extension.sh` の実行承認を求め（1回の bash 許可）、シンボリックリンクを作成し、拡張機能を自動リロードします。13のスラッシュコマンド（`/ars-full`、`/ars-plan` など）は同じセッション内で即座に有効化されます。

以降のセッションでは、ブートストラップはサイレント終了し、繰り返しのプロンプトは表示されません。

> **プラグイン更新後:** `/plugin update academic-research-skills@academic-research-skills` を実行した場合、拡張機能のシンボリックリンクは更新されたソースファイルを自動的に追跡します。
更新された `extension.mjs` を有効にするには、`/restart` を実行するか、`/clear` で新しいセッションを開始してください。

詳細な手順については [QUICKSTART.md](QUICKSTART.md) を参照してください。

---

## スラッシュコマンド

| スラッシュコマンド | コマンドの機能 |
|---|---|
| `/ars-full` | フルパイプライン — 研究 → 執筆 → 査読 → 改訂 → 最終化 |
| `/ars-plan` | ソクラテス式の章別計画 |
| `/ars-outline` | 詳細アウトライン + エビデンスマップ |
| `/ars-revision` | 改訂原稿 + R&R 回答 |
| `/ars-revision-coach` | 査読コメント解析 → 改訂ロードマップ |
| `/ars-reviewer` | 多角的模擬ピアレビュー |
| `/ars-abstract` | バイリンガル抄録 + キーワード |
| `/ars-lit-review` | 注釈付き文献リスト |
| `/ars-format-convert` | LaTeX / DOCX / PDF / Markdown 変換 |
| `/ars-citation-check` | 引用エラーレポート |
| `/ars-disclosure` | ジャーナル別 AI 利用開示 |
| `/ars-mark-read` | 引用文献の既読マークを記録 |
| `/ars-unmark-read` | 記録した既読マークを取り消し |

**自動生成されるスキルコマンド** (プラグインインストール直後から使用可能、拡張機能の登録は不要):

`/academic-research-skills:deep-research`, `/academic-research-skills:academic-paper`, `/academic-research-skills:academic-paper-reviewer`, `/academic-research-skills:academic-pipeline`, `/academic-research-skills:ars-bootstrap`

---

## モデルルーティング（オプション）

環境変数を用いた階層別モデルのルーティング設定用：

```bash
export ARS_MODEL_ARCHITECT="claude-opus-4-5"    # アーキテクト層 (full pipeline, revision-coach, reviewer)
export ARS_MODEL_EXECUTION="claude-sonnet-4-5"   # 実行層 (plan, outline, revision, abstract など)
```

環境変数がない場合、すべてのサブエージェントはセッションのデフォルトモデルを使用します。両層ともに、同じプロバイダーエンドポイント (`COPILOT_PROVIDER_BASE_URL`) (BYOKモードの場合) を経由するか、Copilotのサブスクリプションで利用可能である必要があります。

---

## スキル一覧

| スキル | 目的 |
|-------|---------|
| `deep-research` v2.9.4 | 13エージェントの研究チーム — 7モード |
| `academic-paper` v3.1.2 | 12エージェントの論文執筆 — 10モード |
| `academic-paper-reviewer` v1.9.1 | 多角的模擬ピアレビュー — 6モード |
| `academic-pipeline` v3.9.4.2 | 全10段階パイプラインオーケストレーター |

---

## 詳細情報

- **[上流 README](https://github.com/Imbad0202/academic-research-skills)** — 全機能ドキュメント、アーキテクチャ、バージョン履歴、設計思想
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — パイプライン構造、ステージマトリクス、品質ゲート
- **[docs/design/](docs/design/)** — すべての設計仕様（v3.6.2 – v3.9.4.2 + Copilot移植版）
- **[QUICKSTART.md](QUICKSTART.md)** — Copilot CLI セットアップのステップバイステップ手順
- **[POSITIONING.md](POSITIONING.md)** — ARS の位置づけと非推奨事項
- **[CHANGELOG.md](CHANGELOG.md)** — リリース履歴（Copilot移植版が先頭）

## ライセンス

[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)
