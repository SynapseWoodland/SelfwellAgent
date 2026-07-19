# V1.6 Run Snapshot

> **用途**：2.1.1 冻结 V1.6 run，记录 `run_id` + `current_phase`。
> **执行者**：你手动执行（因为这是你当前 session 的状态）。

## 执行步骤

1. Read 当前 `harness/state/harness-state.json`（若存在）
2. 若无，创建一个示例文件（见下方模板）
3. Commit 并 push

---

## 快照模板（若 state.json 不存在）

```json
{
  "run_id": "FR-<DOMAIN>-<NN>-<YYYYMMDD>",
  "version": "1.6",
  "current_phase": "<当前 phase>",
  "current_agent": "<当前 agent>",
  "phase_started_at": "<ISO 8601 时间>",
  "exit_criteria_met": [false, false, false],
  "next_phase_hint": null,
  "updated_at": "<ISO 8601 时间>",
  "note": "V1.6 冻结快照，V2 切换后此文件保留审计历史"
}
```

---

## 示例（若 state.json 存在）

```json
{
  "run_id": "FR-DIAG-01-20260717",
  "version": "1.6",
  "current_phase": "CODE",
  "current_agent": "developer",
  "phase_started_at": "2026-07-17T20:00:00+08:00",
  "exit_criteria_met": [true, true, false],
  "next_phase_hint": null,
  "updated_at": "2026-07-18T09:00:00+08:00",
  "note": "V1.6 run 冻结：此为最后一个 V1.6 run 的状态快照，用于审计历史"
}
```

---

## 快照文件路径

```
harness/state/snapshots/
├── harness-state-v1.6-FR-DIAG-01-20260717.json   ← 你的快照
└── README.md                                        ← 说明
```
