# karaoke-clip 🎤

長時間のカラオケ録音（1ファイルに数十曲）から、**歌った曲を1曲ずつ自動で切り抜く** [Claude Code](https://claude.com/claude-code) スキル。
区間検出 → 整音 → GPU文字起こし → 歌詞から曲名特定 → 「曲名＋日付＋歌唱開始時刻」で命名まで。会話・無音は除外し、伴奏アウトロは残す。

> **English:** A Claude Code Skill that splits a long karaoke recording into per-song clips — auto segment detection, audio cleanup, GPU transcription (faster-whisper), song-title identification from lyrics, and naming as `{title}_{date}_{start-time}.m4a`. Conversation/silence excluded, instrumental outros kept.

## ✨ 特徴
- **区間自動検出**：1秒RMSの移動平均で曲/会話/無音を判定、無音まで境界拡張
- **整音(M1)**：声を鮮明に保つ軽い処理（強いノイズ除去はしない）。無フェード
- **GPU文字起こし**：faster-whisper large-v3。歌声に最適化（VAD無し・プロンプト無し・幻覚対策済）
- **曲名特定**：歌詞の特徴フレーズをWeb検索。不明分はユーザーと協調
- **時系列命名**：ファイル作成日時＝歌唱時刻。日付順ソートで一日のsetlistが並ぶ
- **2曲マージの分割・伴奏終止の検出**に対応
- 実運用（約7時間・78曲）で確立したノウハウと **NG集** を同梱（[`references/recipe.md`](references/recipe.md)）

## 🔧 必要環境
- **ffmpeg / ffprobe**（PATHに通す）
- **Python 3.10+** と依存（`pip install -r requirements.txt`）
- **NVIDIA GPU**（文字起こし用。CUDA対応。CPUでも動くが遅い）

```bash
pip install -r requirements.txt
# ffmpeg は各OSのパッケージマネージャ等で別途インストール
```

## 📦 Claude Code スキルとして登録
このフォルダをClaude Codeのスキル探索パスに置く（またはリンク）：

```powershell
# Windows: ユーザースキルにジャンクション（管理者権限）
New-Item -ItemType Junction -Path "$HOME\.claude\skills\karaoke-clip" -Target "<このリポジトリのパス>"
```
```bash
# macOS/Linux: シンボリックリンク
ln -s "$(pwd)" ~/.claude/skills/karaoke-clip
```
登録後、Claude Codeで「カラオケ 切り抜き」等と言うと発動する。

## 🚀 使い方（手動でスクリプトを回す場合）
```bash
# 1. 区間検出（16k化→曲区間JSON）
python scripts/detect_songs.py "録音.aac" segments.json

# 2. GPU文字起こし（各区間の歌詞）
python scripts/transcribe.py "録音.aac" segments.json lyrics_out/

# 3. 歌詞から曲名を特定 → names.json を作る（idx→曲名、null=会話でスキップ）
#    例: {"1":"曲名A","2":null,"3":"曲名B", ...}

# 4. 切出し・整音・命名（録音開始秒とは 録音開始時刻を秒に直した値）
python scripts/process.py "録音.aac" segments.json names.json 切り抜き/ 34980 2026-07-17

# 5. 作成日時＝歌唱時刻に設定（時系列ソート用）
pwsh -File scripts/set_dates.ps1 切り抜き/ 2026-07-17

# 補助: 長区間の2曲分割・伴奏終止の解析
python scripts/boundary_probe.py segments_16k.wav 4273 4769
```
Claude Code経由なら、SKILL.mdの手順に沿ってこれらを対話的に実行する。

## 📁 構成
| ファイル | 役割 |
|---|---|
| `SKILL.md` | スキル定義（トリガー・ワークフロー） |
| `scripts/detect_songs.py` | 区間検出 |
| `scripts/transcribe.py` | GPU文字起こし |
| `scripts/process.py` | 切出し・整音・命名 |
| `scripts/boundary_probe.py` | 伴奏終止/2曲分割の解析 |
| `scripts/set_dates.ps1` | 作成日時＝歌唱時刻 |
| `references/recipe.md` | 詳細レシピ＆**NG集**（必読） |

## ⚠️ よくある落とし穴（詳細は recipe.md）
- **loudnorm を普通に使うと** 静音イントロのヒスが爆音化 → 一定ゲイン＋リミッターで
- **強いノイズ除去は** 声が「扇風機の前で喋る」ようにこもる → afftdn nr=6 が上限
- **Whisper に initial_prompt を付けると** プロンプトをエコーする幻覚 → 付けない
- **区間の終わりは「最後の歌詞」でなく「伴奏の終止」で切る**（アウトロを残す）

## 📝 ライセンス
[MIT](LICENSE)（必要に応じて変更してね）

🤖 このスキルは [Claude Code](https://claude.com/claude-code) との共同作業で作られました。
