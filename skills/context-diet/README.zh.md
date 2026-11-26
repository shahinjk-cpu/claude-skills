[English](README.md) | [繁體中文](README.zh.md)

# context-diet

稽核並最佳化 Claude Code 的記憶檔案，降低啟動時的 token 用量。

## 說明

Context Diet 掃描 Claude Code 啟動時載入的所有記憶檔案（CLAUDE.md、rules/*.md、MEMORY.md），測量其 token 佔用量，並套用五種針對性最佳化：修剪學術或參考性內容、合併同領域檔案、將 CJK 內容轉換為英文、將穩定模式推進至正確的設定層，以及刪除可從其他來源推導的內容。每次執行已驗證可達到 25-30% 的 token 減少。

## 功能特色

- 跨所有記憶檔案的 token 與 CJK% 稽核，含前後比較
- 領域重疊偵測，識別合併候選檔案
- 五種最佳化動作：Trim（修剪）、Merge（合併）、Convert（CJK→英文）、Promote（提升）、Delete（刪除）
- 層級檢查：將 MEMORY.md 中穩定的模式提升至全域 `~/.claude/rules/` 或專案規則
- 平行探索 agent 進行深度跨檔案分析
- 修改前強制備份
- 各指標的健康/警告/危急閾值（token 數、CJK%、檔案數、MEMORY.md 行數）
- 稽核腳本支援 `--json` 旗標輸出機器可讀格式

## 使用方式

```
/context-diet
```

觸發語句：

- "context diet"
- "optimize memory files"
- "減少 token 用量"
- "整理 memory"
- "audit claude config"

## 運作原理

Context Diet 執行 `scripts/audit.py` 建立所有記憶檔案的 token 基準線。接著啟動 2-3 個平行探索 agent——每個檔案群組一個（全域規則、專案規則、MEMORY.md）——對每一行檢查：是否影響決策、是否在正確層級、是否可推導、是否為學術內容、是否重複，以及是否為 CJK。根據發現生成含預估節省 token 量的五動作最佳化計畫，透過暫存目錄先備份再執行變更，最後重新執行稽核確認減少量。

## 系統需求

- Claude Code CLI
- `~/.claude/skills/context-diet/scripts/audit.py`
- `~/.local/bin/python3`（uv 管理的 Python 3.12）

## 授權條款

MIT
